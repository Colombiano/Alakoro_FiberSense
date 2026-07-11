"""
Alakoro FiberSense - Controllers
Lógica de processamento e orquestração MVC.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

from app.core.config import get_settings
from app.core.events import EventType, publish_event
from app.models import (
    FiberParams,
    ProcessingJob,
    ProcessingStatus,
    SignalAlert,
    SignalAlertView,
    SignalData,
    SignalEvent,
    SignalType,
)
from app.views import (
    AnalysisResultView,
    ProcessingJobView,
    SignalDataView,
    SignalEventView,
    WaterfallDataView,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class SignalPipeline:
    """Pipeline de processamento de sinais DAS/DTS/DSS."""

    def __init__(self, signal_type: SignalType):
        self.signal_type = signal_type
        self.steps: List[str] = []
        self._configure_pipeline()

    def _configure_pipeline(self):
        if self.signal_type == SignalType.DAS:
            self.steps = ["denoise", "bandpass", "fft", "event_detection"]
        elif self.signal_type == SignalType.DTS:
            self.steps = ["denoise", "temperature_profile", "hotspot_detection"]
        elif self.signal_type == SignalType.DSS:
            self.steps = ["denoise", "strain_profile", "event_detection"]

    async def process(self, signal: SignalData, config: Dict[str, Any] = None) -> Dict[str, Any]:
        signal.status = ProcessingStatus.PROCESSING
        job = ProcessingJob(signal_id=signal.id, signal_type=self.signal_type, pipeline_config=config or {})
        job.status = ProcessingStatus.PROCESSING

        try:
            result = {"signal_id": signal.id, "steps": {}}
            data = signal.raw_data.copy()

            for step in self.steps:
                if step == "denoise":
                    data = self._denoise(data, config)
                    result["steps"]["denoise"] = {"completed": True}
                elif step == "bandpass":
                    data = self._bandpass_filter(data, config)
                    result["steps"]["bandpass"] = {"completed": True}
                elif step == "fft":
                    fft_result = self._compute_fft(data)
                    result["steps"]["fft"] = fft_result
                elif step == "event_detection":
                    events = self._detect_events(data, signal)
                    result["steps"]["event_detection"] = [e.to_dict() for e in events]
                elif step == "temperature_profile":
                    profile = self._compute_temperature_profile(data, signal)
                    result["steps"]["temperature_profile"] = profile
                elif step == "hotspot_detection":
                    hotspots = self._detect_hotspots(data, signal)
                    result["steps"]["hotspot_detection"] = [h.to_dict() for h in hotspots]
                elif step == "strain_profile":
                    profile = self._compute_strain_profile(data, signal)
                    result["steps"]["strain_profile"] = profile

            signal.processed_data = data
            signal.status = ProcessingStatus.COMPLETED
            job.status = ProcessingStatus.COMPLETED
            job.result = result

            await publish_event(EventType.PROCESSING_COMPLETED, {
                "job_id": job.id,
                "signal_id": signal.id,
                "signal_type": self.signal_type.value,
                "result": result,
            })

            return result

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            signal.status = ProcessingStatus.ERROR
            job.status = ProcessingStatus.ERROR
            job.error_message = str(e)
            await publish_event(EventType.PROCESSING_ERROR, {
                "job_id": job.id,
                "signal_id": signal.id,
                "error": str(e),
            })
            raise

    def _denoise(self, data: np.ndarray, config: Dict[str, Any] = None) -> np.ndarray:
        window = (config or {}).get("moving_avg_window", 5)
        if data.ndim == 1:
            kernel = np.ones(window) / window
            return np.convolve(data, kernel, mode="same")
        elif data.ndim == 2:
            result = np.zeros_like(data)
            for i in range(data.shape[0]):
                kernel = np.ones(window) / window
                result[i] = np.convolve(data[i], kernel, mode="same")
            return result
        return data

    def _bandpass_filter(self, data: np.ndarray, config: Dict[str, Any] = None) -> np.ndarray:
        low = (config or {}).get("lowcut", 1.0)
        high = (config or {}).get("highcut", 100.0)
        sr = (config or {}).get("sampling_rate", 1000.0)
        if data.ndim == 1:
            freqs = np.fft.rfftfreq(len(data), 1 / sr)
            fft_vals = np.fft.rfft(data)
            mask = (freqs >= low) & (freqs <= high)
            fft_vals[~mask] = 0
            return np.fft.irfft(fft_vals, n=len(data))
        return data

    def _compute_fft(self, data: np.ndarray, sr: float = 1000.0) -> Dict[str, Any]:
        if data.ndim == 1:
            n = len(data)
            freqs = np.fft.rfftfreq(n, 1 / sr)
            fft_vals = np.fft.rfft(data)
            return AnalysisResultView.serialize_fft(fft_vals, freqs)
        elif data.ndim == 2:
            row = data[data.shape[0] // 2]
            return self._compute_fft(row, sr)
        return {}

    def _detect_events(self, data: np.ndarray, signal: SignalData, threshold: float = 3.0) -> List[SignalEvent]:
        events = []
        if data.ndim == 1 and signal.distance is not None:
            mean_val = np.mean(data)
            std_val = np.std(data) + 1e-10
            z_scores = np.abs((data - mean_val) / std_val)
            peaks = np.where(z_scores > threshold)[0]
            if len(peaks) > 0:
                min_gap = int(50 / signal.params.spatial_resolution)
                grouped = []
                current = [peaks[0]]
                for p in peaks[1:]:
                    if p - current[-1] > min_gap:
                        grouped.append(current)
                        current = [p]
                    else:
                        current.append(p)
                grouped.append(current)
                for group in grouped:
                    idx = group[np.argmax(np.abs(data[group]))]
                    events.append(SignalEvent(
                        signal_type=self.signal_type,
                        event_type="anomaly",
                        position=float(signal.distance[idx]),
                        amplitude=float(data[idx]),
                        confidence=min(float(z_scores[idx]) / 10.0, 1.0),
                    ))
        return events

    def _compute_temperature_profile(self, data: np.ndarray, signal: SignalData) -> Dict[str, Any]:
        if data.ndim == 1 and signal.distance is not None:
            return AnalysisResultView.serialize_profile(signal.distance, data)
        elif data.ndim == 2:
            avg = np.mean(data, axis=0)
            return AnalysisResultView.serialize_profile(signal.distance, avg)
        return {}

    def _detect_hotspots(self, data: np.ndarray, signal: SignalData, threshold: float = 5.0) -> List[SignalEvent]:
        events = []
        if data.ndim == 2:
            avg_temp = np.mean(data, axis=0)
            baseline = np.mean(avg_temp)
            deviations = avg_temp - baseline
            hotspots = np.where(deviations > threshold)[0]
            if len(hotspots) > 0 and signal.distance is not None:
                min_gap = int(100 / signal.params.spatial_resolution)
                grouped = []
                current = [hotspots[0]]
                for h in hotspots[1:]:
                    if h - current[-1] > min_gap:
                        grouped.append(current)
                        current = [h]
                    else:
                        current.append(h)
                grouped.append(current)
                for group in grouped:
                    idx = group[np.argmax(avg_temp[group])]
                    events.append(SignalEvent(
                        signal_type=self.signal_type,
                        event_type="hotspot",
                        position=float(signal.distance[idx]),
                        amplitude=float(avg_temp[idx]),
                        confidence=min(float(deviations[idx]) / 20.0, 1.0),
                    ))
        return events

    def _compute_strain_profile(self, data: np.ndarray, signal: SignalData) -> Dict[str, Any]:
        if data.ndim == 1 and signal.distance is not None:
            return AnalysisResultView.serialize_profile(signal.distance, data)
        elif data.ndim == 2:
            avg = np.mean(data, axis=0)
            return AnalysisResultView.serialize_profile(signal.distance, avg)
        return {}


class AlertController:
    """Gerenciamento de alertas."""

    _alerts: List[SignalAlert] = []

    @classmethod
    def add_alert(cls, alert: SignalAlert) -> SignalAlert:
        cls._alerts.append(alert)
        return alert

    @classmethod
    def get_alerts(cls, signal_type: SignalType = None, level: str = None, acknowledged: bool = None) -> List[SignalAlert]:
        alerts = cls._alerts
        if signal_type:
            alerts = [a for a in alerts if a.signal_type == signal_type]
        if level:
            alerts = [a for a in alerts if a.level.value == level]
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        return sorted(alerts, key=lambda a: a.created_at, reverse=True)

    @classmethod
    def acknowledge(cls, alert_id: str) -> Optional[SignalAlert]:
        for alert in cls._alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return alert
        return None

    @classmethod
    def clear_all(cls):
        cls._alerts.clear()


class SignalStore:
    """Armazenamento em memória de sinais."""

    _signals: Dict[str, SignalData] = {}

    @classmethod
    def add(cls, signal: SignalData) -> SignalData:
        cls._signals[signal.id] = signal
        return signal

    @classmethod
    def get(cls, signal_id: str) -> Optional[SignalData]:
        return cls._signals.get(signal_id)

    @classmethod
    def list(cls, signal_type: SignalType = None) -> List[SignalData]:
        signals = list(cls._signals.values())
        if signal_type:
            signals = [s for s in signals if s.signal_type == signal_type]
        return sorted(signals, key=lambda s: s.created_at, reverse=True)

    @classmethod
    def delete(cls, signal_id: str) -> bool:
        if signal_id in cls._signals:
            del cls._signals[signal_id]
            return True
        return False

    @classmethod
    def clear(cls):
        cls._signals.clear()
