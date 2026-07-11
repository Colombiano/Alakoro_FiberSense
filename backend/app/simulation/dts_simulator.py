"""
Alakoro FiberSense - DTS Simulator
Simulador para Distributed Temperature Sensing.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from app.models import FiberParams


class DTSSimulator:
    """Simulador de dados DTS."""

    def __init__(
        self,
        fiber_length: float = 10000.0,
        spatial_resolution: float = 1.0,
        sampling_rate: float = 1.0,
        duration: float = 3600.0,
        noise_level: float = 0.1,
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
        """Gera dados sinteticos DTS."""
        # Base temperature profile (linear gradient + seasonal)
        base_temp = np.zeros((self.n_samples, self.n_channels))
        for t in range(self.n_samples):
            # Linear temperature gradient along fiber
            base_temp[t, :] = 20.0 + 0.001 * self.distance
            # Slow temporal variation
            base_temp[t, :] += 5.0 * np.sin(2 * np.pi * t / self.n_samples)

        # Add random noise
        noise = np.random.randn(self.n_samples, self.n_channels) * self.noise_level
        data = base_temp + noise

        # Inject temperature events (hotspots, cold spots)
        if events:
            for event in events:
                event_signal = self._inject_event(event)
                data += event_signal

        return data.astype(np.float32)

    def _inject_event(self, event: Dict[str, Any]) -> np.ndarray:
        """Injeta um evento de temperatura no sinal."""
        position = event.get("position", self.fiber_length / 2)
        amplitude = event.get("amplitude", 10.0)
        width = event.get("width", 100.0)
        start_time = event.get("start_time", 0.0)
        event_duration = event.get("duration", 600.0)
        event_type = event.get("type", "hotspot")

        dist_idx = np.argmin(np.abs(self.distance - position))
        spatial_width_samples = int(width / self.spatial_resolution)

        # Spatial envelope (gaussian)
        spatial_env = amplitude * np.exp(
            -0.5 * ((np.arange(self.n_channels) - dist_idx) / max(spatial_width_samples / 2.5, 1)) ** 2
        )

        # Temporal envelope
        t_start_idx = int(start_time * self.sampling_rate)
        t_end_idx = min(int((start_time + event_duration) * self.sampling_rate), self.n_samples)
        t_duration = max(1, t_end_idx - t_start_idx)

        temporal_env = np.zeros(self.n_samples)

        if event_type == "hotspot":
            # Gradual increase and decrease
            rise = int(t_duration * 0.2)
            fall = int(t_duration * 0.3)
            steady = t_duration - rise - fall
            envelope = np.concatenate([
                np.linspace(0, 1, rise),
                np.ones(steady),
                np.linspace(1, 0, fall),
            ])
            temporal_env[t_start_idx:t_start_idx + len(envelope)] = envelope
        elif event_type == "coldspot":
            spatial_env = -spatial_env
            temporal_env[t_start_idx:t_end_idx] = 1.0
        elif event_type == "gradual":
            temporal_env[t_start_idx:t_end_idx] = np.linspace(0, 1, t_duration)
        else:
            temporal_env[t_start_idx:t_end_idx] = 1.0

        return np.outer(temporal_env, spatial_env)

    def detect_hotspots(self, signal: np.ndarray, threshold: float = 5.0) -> List[Dict[str, Any]]:
        """Detecta hotspots no sinal DTS."""
        avg_temp = np.mean(signal, axis=0)
        baseline = np.mean(avg_temp)
        deviations = avg_temp - baseline
        hotspots = []

        hot_indices = np.where(deviations > threshold)[0]
        if len(hot_indices) > 0:
            # Group contiguous regions
            groups = []
            current = [hot_indices[0]]
            for idx in hot_indices[1:]:
                if idx - current[-1] <= 5:
                    current.append(idx)
                else:
                    groups.append(current)
                    current = [idx]
            groups.append(current)

            for group in groups:
                peak_idx = group[np.argmax(avg_temp[group])]
                hotspots.append({
                    "position": float(self.distance[peak_idx]),
                    "temperature": float(avg_temp[peak_idx]),
                    "deviation": float(deviations[peak_idx]),
                    "width": len(group) * self.spatial_resolution,
                    "confidence": min(float(deviations[peak_idx]) / 20.0, 1.0),
                })

        return hotspots

    def generate_waterfall(self, signal: np.ndarray) -> Dict[str, Any]:
        """Gera waterfall plot."""
        return {
            "matrix": signal[:500, :2000].tolist() if signal.ndim == 2 else [],
            "distance": self.distance[:2000].tolist(),
            "time": self.time[:500].tolist(),
        }

    def generate_profile(self, signal: np.ndarray, time_idx: int = None) -> Dict[str, Any]:
        """Gera perfil de temperatura."""
        if time_idx is None:
            time_idx = signal.shape[0] // 2
        trace = signal[time_idx, :]
        return {
            "distance": self.distance.tolist(),
            "temperature": trace.tolist(),
        }

    def generate_heatmap(self, signal: np.ndarray) -> Dict[str, Any]:
        """Gera heatmap."""
        return {
            "matrix": signal[:500, :2000].tolist() if signal.ndim == 2 else [],
            "x_labels": [f"{d:.0f}" for d in self.distance[:2000:200]],
            "y_labels": [f"{t:.0f}" for t in self.time[:500:50]],
        }
