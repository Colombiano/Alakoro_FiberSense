"""Detection Service - Servico de deteccao de eventos"""

from typing import List, Optional, Dict, Any
import numpy as np

from ..models import DASFrame, DASEvent, EventClassification, ProcessingConfig
from ..events import EventBus, EventType, Event


class DetectionService:
    """Servico de deteccao e classificacao de eventos"""
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        self.config = config or ProcessingConfig()
        self.event_bus = EventBus()
        self._cpp_bindings = None
        self._initialize_bindings()
    
    def _initialize_bindings(self) -> None:
        try:
            import alakoro
            self._cpp_bindings = alakoro
        except ImportError:
            self._cpp_bindings = None
    
    def update_config(self, config: ProcessingConfig) -> None:
        self.config = config
    
    def detect_events(self, frame: DASFrame) -> List[DASEvent]:
        if self._cpp_bindings:
            return self._detect_events_cpp(frame)
        else:
            return self._detect_events_python(frame)
    
    def _detect_events_cpp(self, frame: DASFrame) -> List[DASEvent]:
        events = []
        
        try:
            detector_config = self._cpp_bindings.DetectorConfig()
            detector_config.threshold_snr = self.config.detection_threshold
            detector_config.min_duration_ms = self.config.min_event_duration_ms
            detector_config.max_duration_ms = self.config.max_event_duration_ms
            detector_config.min_frequency = self.config.low_cutoff
            detector_config.max_frequency = self.config.high_cutoff
            detector_config.min_channels = self.config.min_channels
            detector_config.merge_gap_ms = self.config.merge_gap_ms
            
            detector = self._cpp_bindings.EventDetector(detector_config)
            
            cpp_events = detector.detect_events(
                frame.data.astype(np.float64),
                frame.metadata.temporal_sampling
            )
            
            for cpp_event in cpp_events:
                event = DASEvent(
                    timestamp=cpp_event.timestamp,
                    channel_start=cpp_event.channel_start,
                    channel_end=cpp_event.channel_end,
                    frequency_center=cpp_event.frequency_center,
                    bandwidth=cpp_event.bandwidth,
                    amplitude=cpp_event.amplitude,
                    snr=cpp_event.snr,
                    confidence=cpp_event.confidence,
                    waveform=cpp_event.waveform if hasattr(cpp_event, 'waveform') else None,
                    features=dict(cpp_event.features) if hasattr(cpp_event, 'features') else {}
                )
                events.append(event)
        
        except Exception as e:
            print(f"Erro na deteccao C++: {e}")
            events = self._detect_events_python(frame)
        
        return events
    
    def _detect_events_python(self, frame: DASFrame) -> List[DASEvent]:
        events = []
        data = frame.data
        threshold = self.config.detection_threshold
        
        for ch in range(data.shape[1] if len(data.shape) > 1 else 1):
            channel_data = data[:, ch] if len(data.shape) > 1 else data
            
            signal_power = np.mean(channel_data ** 2)
            noise_estimate = np.std(np.diff(channel_data))
            noise_power = noise_estimate ** 2
            snr = 10.0 * np.log10(signal_power / (noise_power + 1e-10)) if noise_power > 1e-10 else 100.0
            
            if snr < threshold:
                continue
            
            mean_val = np.mean(channel_data)
            std_val = np.std(channel_data)
            event_threshold = mean_val + 2.0 * std_val
            
            in_event = False
            event_start = 0
            
            for i in range(len(channel_data)):
                if abs(channel_data[i]) > event_threshold and not in_event:
                    in_event = True
                    event_start = i
                elif abs(channel_data[i]) <= event_threshold and in_event:
                    in_event = False
                    event_end = i
                    
                    duration_ms = (event_end - event_start) / frame.metadata.temporal_sampling * 1000
                    
                    if duration_ms < self.config.min_event_duration_ms:
                        continue
                    if duration_ms > self.config.max_event_duration_ms:
                        continue
                    
                    waveform = channel_data[event_start:event_end]
                    
                    fft_vals = np.abs(np.fft.fft(waveform))
                    freqs = np.fft.fftfreq(len(waveform), 1.0 / frame.metadata.temporal_sampling)
                    dominant_freq = abs(freqs[np.argmax(fft_vals[:len(fft_vals)//2])])
                    
                    event = DASEvent(
                        timestamp=event_start / frame.metadata.temporal_sampling,
                        channel_start=ch,
                        channel_end=ch,
                        frequency_center=dominant_freq,
                        amplitude=float(np.max(np.abs(waveform))),
                        snr=float(snr),
                        confidence=min(snr / threshold, 1.0),
                        waveform=waveform,
                        features={
                            "duration": float(duration_ms),
                            "rms": float(np.sqrt(np.mean(waveform ** 2))),
                            "peak_amplitude": float(np.max(np.abs(waveform))),
                        }
                    )
                    events.append(event)
        
        return events
    
    def classify_event(self, event: DASEvent) -> EventClassification:
        if not self.config.classify_events:
            return EventClassification.UNKNOWN
        
        if event.frequency_center < 10.0:
            return EventClassification.FLOW
        elif event.frequency_center < 50.0:
            return EventClassification.VIBRATION
        elif event.bandwidth > 100.0:
            return EventClassification.FRACTURE
        else:
            return EventClassification.CUSTOM
    
    def classify_event_dict(self, event_dict: Dict[str, Any]) -> str:
        freq = event_dict.get("frequency_center", 0)
        bandwidth = event_dict.get("bandwidth", 0)
        
        if freq < 10.0:
            return EventClassification.FLOW.value
        elif freq < 50.0:
            return EventClassification.VIBRATION.value
        elif bandwidth > 100.0:
            return EventClassification.FRACTURE.value
        else:
            return EventClassification.CUSTOM.value
    
    def extract_features(self, waveform: np.ndarray, sample_rate: float) -> Dict[str, float]:
        if self._cpp_bindings and len(waveform) > 0:
            try:
                cpp_features = self._cpp_bindings.EventDetector().extract_features(
                    waveform.astype(np.float64), sample_rate
                )
                return dict(cpp_features)
            except:
                pass
        
        return {
            "rms": float(np.sqrt(np.mean(waveform ** 2))),
            "peak_amplitude": float(np.max(np.abs(waveform))),
            "duration": float(len(waveform) / sample_rate * 1000),
            "zero_crossing_rate": float(np.sum(np.diff(np.sign(waveform)) != 0) / len(waveform)),
        }
