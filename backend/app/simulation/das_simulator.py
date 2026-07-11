"""
Alakoro FiberSense - DAS Simulator
Simulador para Distributed Acoustic Sensing.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
from scipy import signal as scipy_signal

from app.models import FiberParams


class DASSimulator:
    """Simulador de dados DAS."""

    def __init__(
        self,
        fiber_length: float = 10000.0,
        spatial_resolution: float = 1.0,
        sampling_rate: float = 1000.0,
        duration: float = 10.0,
        noise_level: float = 0.01,
        seed: Optional[int] = None,
    ):
        self.fiber_length = fiber_length
        self.spatial_resolution = spatial_resolution
        self.sampling_rate = sampling_rate
        self.duration = duration
        self.noise_level = noise_level
        self.seed = seed
        self.params = FiberParams(
            fiber_length=fiber_length,
            spatial_resolution=spatial_resolution,
            sampling_rate=sampling_rate,
        )

        if seed is not None:
            np.random.seed(seed)

        self.n_channels = int(fiber_length / spatial_resolution)
        self.n_samples = int(duration * sampling_rate)
        self.distance = np.linspace(0, fiber_length, self.n_channels)
        self.time = np.linspace(0, duration, self.n_samples)

    def generate(self, events: List[Dict[str, Any]] = None) -> np.ndarray:
        """Gera dados sinteticos DAS."""
        # Base noise
        data = np.random.randn(self.n_samples, self.n_channels) * self.noise_level

        # Add coherent background
        for i in range(self.n_channels):
            data[:, i] += 0.001 * np.sin(2 * np.pi * 5 * self.time + i * 0.01)

        # Inject events
        if events:
            for event in events:
                event_signal = self._inject_event(event)
                data += event_signal

        return data.astype(np.float32)

    def _inject_event(self, event: Dict[str, Any]) -> np.ndarray:
        """Injeta um evento no sinal."""
        position = event.get("position", self.fiber_length / 2)
        amplitude = event.get("amplitude", 1.0)
        frequency = event.get("frequency", 50.0)
        event_type = event.get("type", "gaussian")
        width = event.get("width", 100.0)
        start_time = event.get("start_time", 0.0)
        duration = event.get("duration", self.duration)

        # Spatial envelope
        dist_idx = np.argmin(np.abs(self.distance - position))
        spatial_width_samples = int(width / self.spatial_resolution)

        if event_type == "gaussian":
            spatial_env = amplitude * np.exp(-0.5 * ((np.arange(self.n_channels) - dist_idx) / (spatial_width_samples / 2.5)) ** 2)
        elif event_type == "exponential":
            spatial_env = amplitude * np.exp(-np.abs(np.arange(self.n_channels) - dist_idx) / (spatial_width_samples / 3))
        elif event_type == "boxcar":
            spatial_env = np.zeros(self.n_channels)
            half_w = spatial_width_samples // 2
            start = max(0, dist_idx - half_w)
            end = min(self.n_channels, dist_idx + half_w)
            spatial_env[start:end] = amplitude
        else:
            spatial_env = amplitude * np.exp(-0.5 * ((np.arange(self.n_channels) - dist_idx) / (spatial_width_samples / 2.5)) ** 2)

        # Temporal envelope
        t_start_idx = int(start_time * self.sampling_rate)
        t_end_idx = min(int((start_time + duration) * self.sampling_rate), self.n_samples)
        t_duration = t_end_idx - t_start_idx

        if t_duration <= 0:
            return np.zeros((self.n_samples, self.n_channels))

        temporal_env = np.zeros(self.n_samples)
        temporal_env[t_start_idx:t_end_idx] = np.sin(2 * np.pi * frequency * np.arange(t_duration) / self.sampling_rate)

        # Combine
        return np.outer(temporal_env, spatial_env)

    def generate_waterfall(self, signal: np.ndarray) -> Dict[str, Any]:
        """Gera waterfall plot."""
        return {
            "matrix": signal[:500, :2000].tolist() if signal.ndim == 2 else [],
            "distance": self.distance[:2000].tolist(),
            "time": self.time[:500].tolist(),
        }

    def generate_spectrogram(self, signal: np.ndarray, channel: int = None) -> Dict[str, Any]:
        """Gera espectrograma."""
        if channel is None:
            channel = signal.shape[1] // 2
        trace = signal[:, channel]
        f, t, Sxx = scipy_signal.spectrogram(trace, self.sampling_rate, nperseg=256)
        return {
            "frequencies": f.tolist(),
            "times": t.tolist(),
            "spectrogram": (10 * np.log10(Sxx + 1e-10)).tolist(),
        }

    def generate_profile(self, signal: np.ndarray, time_idx: int = None) -> Dict[str, Any]:
        """Gera perfil espacial."""
        if time_idx is None:
            time_idx = signal.shape[0] // 2
        trace = signal[time_idx, :]
        return {
            "distance": self.distance.tolist(),
            "amplitude": trace.tolist(),
        }

    def generate_fft(self, signal: np.ndarray, channel: int = None) -> Dict[str, Any]:
        """Gera FFT."""
        if channel is None:
            channel = signal.shape[1] // 2
        trace = signal[:, channel]
        fft_vals = np.fft.rfft(trace)
        freqs = np.fft.rfftfreq(len(trace), 1 / self.sampling_rate)
        return {
            "frequencies": freqs.tolist(),
            "magnitude": np.abs(fft_vals).tolist(),
        }

    def generate_heatmap(self, signal: np.ndarray) -> Dict[str, Any]:
        """Gera heatmap."""
        return {
            "matrix": signal[:500, :2000].tolist() if signal.ndim == 2 else [],
            "x_labels": [f"{d:.0f}" for d in self.distance[:2000:200]],
            "y_labels": [f"{t:.2f}" for t in self.time[:500:50]],
        }
