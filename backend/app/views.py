"""
Alakoro FiberSense - Views
Serializadores e formatadores para respostas API.
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from app.models import (
    AlertLevel,
    FiberParams,
    ProcessingJob,
    ProcessingStatus,
    SignalAlert,
    SignalData,
    SignalEvent,
    SignalType,
    SimulationConfig,
)


class SignalDataView:
    @staticmethod
    def serialize(signal: SignalData, include_data: bool = False) -> Dict[str, Any]:
        data = {
            "id": signal.id,
            "signal_type": signal.signal_type.value,
            "params": signal.params.to_dict(),
            "status": signal.status.value,
            "metadata": signal.metadata,
            "created_at": signal.created_at.isoformat(),
            "updated_at": signal.updated_at.isoformat() if signal.updated_at else None,
        }
        if include_data and signal.raw_data.size > 0:
            data["shape"] = list(signal.raw_data.shape)
            data["dtype"] = str(signal.raw_data.dtype)
            if signal.distance is not None:
                data["distance"] = signal.distance.tolist()
            if signal.time is not None:
                data["time"] = signal.time.tolist()
            if signal.raw_data.ndim == 1:
                data["raw_preview"] = signal.raw_data[:1000].tolist()
            elif signal.raw_data.ndim == 2:
                data["raw_preview"] = signal.raw_data[:100, :1000].tolist()
        return data

    @staticmethod
    def serialize_list(signals: List[SignalData]) -> List[Dict[str, Any]]:
        return [SignalDataView.serialize(s) for s in signals]


class SignalEventView:
    @staticmethod
    def serialize(event: SignalEvent) -> Dict[str, Any]:
        return event.to_dict()

    @staticmethod
    def serialize_list(events: List[SignalEvent]) -> List[Dict[str, Any]]:
        return [SignalEventView.serialize(e) for e in events]


class SignalAlertView:
    @staticmethod
    def serialize(alert: SignalAlert) -> Dict[str, Any]:
        return alert.to_dict()

    @staticmethod
    def serialize_list(alerts: List[SignalAlert]) -> List[Dict[str, Any]]:
        return [SignalAlertView.serialize(a) for a in alerts]


class ProcessingJobView:
    @staticmethod
    def serialize(job: ProcessingJob) -> Dict[str, Any]:
        return job.to_dict()

    @staticmethod
    def serialize_list(jobs: List[ProcessingJob]) -> List[Dict[str, Any]]:
        return [ProcessingJobView.serialize(j) for j in jobs]


class SimulationConfigView:
    @staticmethod
    def serialize(config: SimulationConfig) -> Dict[str, Any]:
        return config.to_dict()

    @staticmethod
    def serialize_list(configs: List[SimulationConfig]) -> List[Dict[str, Any]]:
        return [SimulationConfigView.serialize(c) for c in configs]


class AnalysisResultView:
    @staticmethod
    def serialize_fft(fft_result: np.ndarray, freqs: np.ndarray) -> Dict[str, Any]:
        return {
            "frequencies": freqs.tolist(),
            "magnitude": np.abs(fft_result).tolist(),
            "phase": np.angle(fft_result).tolist(),
            "dominant_freq": float(freqs[np.argmax(np.abs(fft_result))]) if len(freqs) > 0 else None,
        }

    @staticmethod
    def serialize_spectrogram(S: np.ndarray, freqs: np.ndarray, times: np.ndarray) -> Dict[str, Any]:
        return {
            "spectrogram": S.tolist(),
            "frequencies": freqs.tolist(),
            "times": times.tolist(),
        }

    @staticmethod
    def serialize_heatmap(data: np.ndarray, x_labels: list, y_labels: list) -> Dict[str, Any]:
        return {
            "matrix": data.tolist(),
            "x_labels": x_labels,
            "y_labels": y_labels,
        }

    @staticmethod
    def serialize_profile(distance: np.ndarray, amplitude: np.ndarray, events: List[SignalEvent] = None) -> Dict[str, Any]:
        result = {
            "distance": distance.tolist(),
            "amplitude": amplitude.tolist(),
            "min": float(np.min(amplitude)),
            "max": float(np.max(amplitude)),
            "mean": float(np.mean(amplitude)),
            "std": float(np.std(amplitude)),
        }
        if events:
            result["events"] = [e.to_dict() for e in events]
        return result


class WaterfallDataView:
    @staticmethod
    def serialize(data: np.ndarray, distance: np.ndarray, time: np.ndarray) -> Dict[str, Any]:
        return {
            "matrix": data.tolist() if data.ndim == 2 else data[:500, :2000].tolist(),
            "distance": distance[:2000].tolist() if len(distance) > 2000 else distance.tolist(),
            "time": time[:500].tolist() if len(time) > 500 else time.tolist(),
            "shape": list(data.shape),
        }
