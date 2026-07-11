"""
Alakoro FiberSense - DSS Simulator
Simulador para Distributed Strain Sensing.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from app.models import FiberParams


class DSSSimulator:
    """Simulador de dados DSS."""

    def __init__(
        self,
        fiber_length: float = 5000.0,
        spatial_resolution: float = 0.5,
        sampling_rate: float = 100.0,
        duration: float = 3600.0,
        noise_level: float = 0.001,
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
        """Gera dados sinteticos DSS."""
        # Base strain with thermal drift
        base_strain = np.zeros((self.n_samples, self.n_channels))
        for i in range(self.n_channels):
            base_strain[:, i] = 1e-6 * np.sin(2 * np.pi * self.time / 3600) + 1e-7 * np.random.randn(self.n_samples)

        # Add random noise
        noise = np.random.randn(self.n_samples, self.n_channels) * self.noise_level
        data = base_strain + noise

        # Inject strain events
        if events:
            for event in events:
                event_signal = self._inject_event(event)
                data += event_signal

        return data.astype(np.float32)

    def _inject_event(self, event: Dict[str, Any]) -> np.ndarray:
        """Injeta um evento de strain no sinal."""
        position = event.get("position", self.fiber_length / 2)
        amplitude = event.get("amplitude", 1e-4)
        width = event.get("width", 50.0)
        start_time = event.get("start_time", 0.0)
        event_duration = event.get("duration", 300.0)
        event_type = event.get("type", "step")

        dist_idx = np.argmin(np.abs(self.distance - position))
        spatial_width_samples = int(width / self.spatial_resolution)

        # Spatial envelope
        spatial_env = np.zeros(self.n_channels)
        half_w = max(1, spatial_width_samples // 2)
        start = max(0, dist_idx - half_w)
        end = min(self.n_channels, dist_idx + half_w)
        spatial_env[start:end] = 1.0

        # Temporal envelope
        t_start_idx = int(start_time * self.sampling_rate)
        t_end_idx = min(int((start_time + event_duration) * self.sampling_rate), self.n_samples)
        t_duration = max(1, t_end_idx - t_start_idx)

        temporal_env = np.zeros(self.n_samples)

        if event_type == "step":
            temporal_env[t_start_idx:] = amplitude
        elif event_type == "pulse":
            temporal_env[t_start_idx:t_end_idx] = amplitude
        elif event_type == "ramp":
            ramp = np.linspace(0, amplitude, t_duration)
            temporal_env[t_start_idx:t_end_idx] = ramp
        elif event_type == "sinusoidal":
            t = np.arange(t_duration) / self.sampling_rate
            temporal_env[t_start_idx:t_end_idx] = amplitude * np.sin(2 * np.pi * t / event_duration)
        else:
            temporal_env[t_start_idx:t_end_idx] = amplitude

        return np.outer(temporal_env, spatial_env)

    def generate_waterfall(self, signal: np.ndarray) -> Dict[str, Any]:
        """Gera waterfall plot."""
        return {
            "matrix": signal[:500, :2000].tolist() if signal.ndim == 2 else [],
            "distance": self.distance[:2000].tolist(),
            "time": self.time[:500].tolist(),
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

    def generate_heatmap(self, signal: np.ndarray) -> Dict[str, Any]:
        """Gera heatmap."""
        return {
            "matrix": signal[:500, :2000].tolist() if signal.ndim == 2 else [],
            "x_labels": [f"{d:.0f}" for d in self.distance[:2000:200]],
            "y_labels": [f"{t:.1f}" for t in self.time[:500:50]],
        }
