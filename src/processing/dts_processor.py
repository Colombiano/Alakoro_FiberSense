"""
Alakoro FiberSense — DTS Thermal Processor v1.0.0
Processador Térmico para DTS (Distributed Temperature Sensing)

Autor/Author: Luiz Paulo Colombiano
Data/Date: 2026-08-30
Versão/Version: 1.0.0
Licença/License: MIT

Pipeline de processamento térmico para perfis de temperatura em poços,
usando os processadores C++20 do alakoro_core com suporte explícito à
modalidade DTS.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from src.io.alakoro_spool import AlakoroPatch
from src.io.dasdae import DASDAEAdapter
from src.processing.advanced_processors import (
    butterworth_lowpass as cpp_lowpass,
    geothermal_baseline_correction as cpp_geothermal_baseline,
    spatial_median_filter as cpp_spatial_median,
    thermal_anomaly_detection as cpp_thermal_anomaly,
    thermal_gradient as cpp_thermal_gradient,
)


class DTSThermalProcessor:
    """
    Processador térmico para dados DTS.

    Oferece um pipeline completo para limpeza, detrending geotérmico,
    detecção de anomalias e cálculo de gradiente térmico ao longo da
    profundidade (dT/dz).

    Attributes:
        depth_step_m: Espaçamento entre canais de profundidade [m].
        surface_temp: Temperatura superficial de referência [°C].
        geothermal_gradient: Gradiente geotérmico linear [°C/m].
        spatial_median_window: Janela do filtro de mediana espacial.
        anomaly_threshold_sigma: Limiar de detecção de anomalias [σ].
        lowpass_cutoff_hz: Frequência de corte do filtro passa-baixa.
        sample_rate_hz: Taxa de amostragem temporal [Hz].
        use_cpp_backend: Se True, usa backends C++20 do alakoro_core.
    """

    def __init__(
        self,
        depth_step_m: float = 1.0,
        surface_temp: float = 20.0,
        geothermal_gradient: float = 0.03,
        spatial_median_window: int = 5,
        anomaly_threshold_sigma: float = 3.0,
        lowpass_cutoff_hz: Optional[float] = None,
        sample_rate_hz: float = 1.0,
        use_cpp_backend: bool = True,
    ):
        """
        Args:
            depth_step_m: Espaçamento vertical entre canais [m].
            surface_temp: Temperatura de superfície para baseline [°C].
            geothermal_gradient: Gradiente geotérmico esperado [°C/m].
            spatial_median_window: Tamanho da janela espacial de mediana (ímpar).
            anomaly_threshold_sigma: Threshold em desvios-padrão para anomalias.
            lowpass_cutoff_hz: Frequência de corte do filtro temporal (None = pular).
            sample_rate_hz: Taxa de amostragem temporal dos dados [Hz].
            use_cpp_backend: Usa implementações C++20 quando disponível.
        """
        self.depth_step_m = depth_step_m
        self.surface_temp = surface_temp
        self.geothermal_gradient = geothermal_gradient
        self.spatial_median_window = spatial_median_window
        self.anomaly_threshold_sigma = anomaly_threshold_sigma
        self.lowpass_cutoff_hz = lowpass_cutoff_hz
        self.sample_rate_hz = sample_rate_hz
        self.use_cpp_backend = use_cpp_backend

    def _to_patch(self, data: np.ndarray) -> AlakoroPatch:
        """Cria AlakoroPatch DTS a partir de array NumPy 2D."""
        patch = DASDAEAdapter.array_to_patch(
            data, modality="DTS", dx_m=self.depth_step_m
        )
        return AlakoroPatch(patch, modality="dts")

    def preprocess(self, temperature: np.ndarray) -> AlakoroPatch:
        """
        Pré-processamento: filtro espacial de mediana opcional e
        filtro passa-baixa temporal opcional.
        """
        patch = self._to_patch(temperature)

        if self.spatial_median_window > 1:
            patch = cpp_spatial_median(patch, window_size=self.spatial_median_window)

        if self.lowpass_cutoff_hz is not None and self.use_cpp_backend:
            patch = cpp_lowpass(
                patch,
                sample_rate_hz=self.sample_rate_hz,
                cutoff_hz=self.lowpass_cutoff_hz,
            )

        return patch

    def remove_geothermal_baseline(self, temperature: np.ndarray) -> np.ndarray:
        """Remove baseline geotérmico linear de cada perfil de temperatura."""
        if not self.use_cpp_backend:
            n_t, n_z = temperature.shape
            depth = np.arange(n_z) * self.depth_step_m
            baseline = self.surface_temp + self.geothermal_gradient * depth
            return temperature - baseline[np.newaxis, :]

        patch = self._to_patch(temperature)
        corrected = cpp_geothermal_baseline(
            patch,
            depth_step_m=self.depth_step_m,
            surface_temp=self.surface_temp,
            gradient=self.geothermal_gradient,
        )
        return corrected.data

    def detect_anomalies(self, temperature: np.ndarray) -> np.ndarray:
        """
        Detecta anomalias térmicas por canal usando threshold em σ.

        Returns:
            Array binário (n_times, n_channels) com 1 onde há anomalia.
        """
        patch = self._to_patch(temperature)
        return cpp_thermal_anomaly(patch, threshold_sigma=self.anomaly_threshold_sigma)

    def compute_gradient(self, temperature: np.ndarray) -> np.ndarray:
        """
        Calcula gradiente térmico dT/dz ao longo da profundidade.

        Returns:
            Array (n_times, n_channels) com gradiente em °C/m.
        """
        patch = self._to_patch(temperature)
        return cpp_thermal_gradient(patch, depth_step_m=self.depth_step_m)

    def process(self, temperature: np.ndarray) -> Dict:
        """
        Pipeline térmico completo para DTS.

        Args:
            temperature: Array (n_times, n_channels) em °C.

        Returns:
            Dicionário com campos processados e metadados.
        """
        n_t, n_z = temperature.shape

        # 1. Pré-processamento espacial/temporal
        preproc_patch = self.preprocess(temperature)
        preproc = preproc_patch.data

        # 2. Remoção de baseline geotérmico
        corrected = self.remove_geothermal_baseline(preproc)

        # 3. Gradiente térmico
        gradient = self.compute_gradient(corrected)

        # 4. Detecção de anomalias
        anomalies = self.detect_anomalies(corrected)

        # 5. Estatísticas por canal
        mean_temp = np.mean(corrected, axis=0)
        std_temp = np.std(corrected, axis=0)
        max_anomaly_score = np.max(np.abs(corrected - mean_temp[np.newaxis, :]) /
                                   (std_temp[np.newaxis, :] + 1e-12), axis=0)

        return {
            "temperature_preprocessed": preproc,
            "temperature_corrected": corrected,
            "thermal_gradient": gradient,
            "anomalies": anomalies,
            "mean_temperature": mean_temp,
            "std_temperature": std_temp,
            "max_anomaly_score": max_anomaly_score,
            "metadata": {
                "depth_step_m": self.depth_step_m,
                "surface_temp": self.surface_temp,
                "geothermal_gradient": self.geothermal_gradient,
                "spatial_median_window": self.spatial_median_window,
                "anomaly_threshold_sigma": self.anomaly_threshold_sigma,
                "lowpass_cutoff_hz": self.lowpass_cutoff_hz,
                "sample_rate_hz": self.sample_rate_hz,
                "use_cpp_backend": self.use_cpp_backend,
                "n_times": n_t,
                "n_channels": n_z,
            },
        }

    def compute_thermal_front_velocity(
        self,
        temperature: np.ndarray,
        depth: np.ndarray,
        time_s: np.ndarray,
        threshold: float = 0.5,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Estima velocidade de propagação de frente térmica ao longo do tempo.

        Args:
            temperature: Array (n_times, n_channels) em °C.
            depth: Vetor de profundidades [m].
            time_s: Vetor de tempos [s].
            threshold: Fração do máximo usada para rastrear o frente.

        Returns:
            (front_depth, front_velocity) — vetores de comprimento n_times-1.
        """
        n_t = temperature.shape[0]
        front_depth = np.full(n_t, np.nan)

        for t in range(n_t):
            profile = temperature[t, :]
            max_val = np.max(profile)
            if max_val <= 0:
                continue
            idx = np.argmax(profile >= threshold * max_val)
            front_depth[t] = depth[idx]

        velocity = np.diff(front_depth) / np.diff(time_s)
        return front_depth, velocity


__all__ = ["DTSThermalProcessor"]
