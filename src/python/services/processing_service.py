"""Processing Service - Servico de processamento de sinais"""

from typing import Optional, Dict, Any
import numpy as np

from ..models import DASFrame, ProcessingConfig
from ..events import EventBus, EventType, Event


class ProcessingService:
    """Servico de processamento de sinais DAS"""
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        self.config = config or ProcessingConfig()
        self.event_bus = EventBus()
        self._cpp_bindings = None
        self._initialize_bindings()
    
    def _initialize_bindings(self) -> None:
        try:
            import alakoro
            self._cpp_bindings = alakoro
            print("[Alakoro] Bindings C++ carregados com sucesso")
        except ImportError:
            print("[Alakoro] Bindings C++ nao disponiveis - usando fallback Python")
            self._cpp_bindings = None
    
    def update_config(self, config: ProcessingConfig) -> None:
        self.config = config
    
    def calibrate(self, frame: DASFrame) -> DASFrame:
        if not self.config.apply_calibration:
            return frame
        
        calibrated_data = frame.data.copy()
        
        if self.config.compensate_attenuation:
            calibrated_data = self._compensate_attenuation(calibrated_data)
        
        return DASFrame(
            data=calibrated_data,
            timestamp=frame.timestamp,
            frame_number=frame.frame_number,
            metadata=frame.metadata
        )
    
    def _compensate_attenuation(self, data: np.ndarray) -> np.ndarray:
        alpha = self.config.attenuation_coefficient
        num_channels = data.shape[1] if len(data.shape) > 1 else 1
        
        compensation = np.exp(alpha * np.arange(num_channels))
        return data * compensation[np.newaxis, :]
    
    def filter_signal(self, frame: DASFrame) -> np.ndarray:
        data = frame.data
        
        if self._cpp_bindings:
            return self._filter_signal_cpp(data, frame.metadata.temporal_sampling)
        else:
            return self._filter_signal_python(data, frame.metadata.temporal_sampling)
    
    def _filter_signal_cpp(self, data: np.ndarray, sample_rate: float) -> np.ndarray:
        result = np.zeros_like(data)
        
        for ch in range(data.shape[1]):
            signal = data[:, ch].astype(np.float64)
            
            if self.config.filter_type == "bandpass":
                filtered = self._cpp_bindings.SignalProcessor.butterworth_filter(
                    signal, self.config.low_cutoff, self.config.filter_order,
                    self._cpp_bindings.FilterType.BANDPASS, sample_rate
                )
            elif self.config.filter_type == "lowpass":
                filtered = self._cpp_bindings.SignalProcessor.butterworth_filter(
                    signal, self.config.high_cutoff, self.config.filter_order,
                    self._cpp_bindings.FilterType.LOWPASS, sample_rate
                )
            elif self.config.filter_type == "highpass":
                filtered = self._cpp_bindings.SignalProcessor.butterworth_filter(
                    signal, self.config.low_cutoff, self.config.filter_order,
                    self._cpp_bindings.FilterType.HIGHPASS, sample_rate
                )
            else:
                filtered = signal
            
            result[:, ch] = filtered
        
        return result
    
    def _filter_signal_python(self, data: np.ndarray, sample_rate: float) -> np.ndarray:
        try:
            from scipy import signal
            
            nyquist = sample_rate / 2.0
            result = np.zeros_like(data)
            
            if self.config.filter_type == "bandpass":
                low = self.config.low_cutoff / nyquist
                high = self.config.high_cutoff / nyquist
                b, a = signal.butter(self.config.filter_order, [low, high], btype="band")
            elif self.config.filter_type == "lowpass":
                cutoff = self.config.high_cutoff / nyquist
                b, a = signal.butter(self.config.filter_order, cutoff, btype="low")
            elif self.config.filter_type == "highpass":
                cutoff = self.config.low_cutoff / nyquist
                b, a = signal.butter(self.config.filter_order, cutoff, btype="high")
            else:
                return data
            
            for ch in range(data.shape[1]):
                result[:, ch] = signal.filtfilt(b, a, data[:, ch])
            
            return result
            
        except ImportError:
            print("SciPy nao disponivel - retornando dados sem filtrar")
            return data
    
    def compute_spectrogram(self, signal: np.ndarray, sample_rate: float) -> tuple:
        if self._cpp_bindings:
            spec = self._cpp_bindings.SignalProcessor.stft(
                signal.astype(np.float64),
                self.config.stft_window_size,
                self.config.stft_hop_size
            )
            return None, None, spec
        
        try:
            from scipy import signal as sp_signal
            return sp_signal.spectrogram(
                signal, fs=sample_rate,
                nperseg=self.config.stft_window_size,
                noverlap=self.config.stft_window_size - self.config.stft_hop_size
            )
        except ImportError:
            return None, None, np.array([])
    
    def compute_quality_metrics(self, data: np.ndarray) -> Dict[str, float]:
        metrics = {
            "mean": float(np.mean(data)),
            "std": float(np.std(data)),
            "snr": float(self._estimate_snr(data)),
            "dead_channels": int(self._count_dead_channels(data)),
        }
        return metrics
    
    def _estimate_snr(self, data: np.ndarray) -> float:
        signal_power = np.mean(data ** 2)
        if len(data.shape) > 1:
            noise_estimate = np.std(np.diff(data, axis=0))
        else:
            noise_estimate = np.std(np.diff(data))
        
        noise_power = noise_estimate ** 2
        if noise_power < 1e-10:
            return 100.0
        return 10.0 * np.log10(signal_power / noise_power)
    
    def _count_dead_channels(self, data: np.ndarray) -> int:
        if not self.config.detect_dead_channels:
            return 0
        
        threshold = self.config.dead_channel_threshold
        dead_count = 0
        
        for ch in range(data.shape[1] if len(data.shape) > 1 else 1):
            channel_data = data[:, ch] if len(data.shape) > 1 else data
            variance = np.var(channel_data)
            if variance < threshold:
                dead_count += 1
        
        return dead_count
    
    def get_cpp_status(self) -> Dict[str, Any]:
        return {
            "cpp_bindings_available": self._cpp_bindings is not None,
            "version": getattr(self._cpp_bindings, "__version__", "N/A") if self._cpp_bindings else None,
        }
