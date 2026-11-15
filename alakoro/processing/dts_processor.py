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

Onda 2 (SP:C-04, SP:C-05): parâmetros opcionais de máscara de ponta do cabo
(mask_end_meters) e de correção de atenuação single-ended
(attenuation_correction + reference_zone_m), com fallback NumPy quando o
alakoro_core não expõe a rotina, além de quality_flags por canal (snr_db e
dead_channel_mask).

Decisão de escopo / Scope decision: apenas correção single-ended é oferecida;
a correção double-ended (fibra loopada com aquisição nas duas pontas) fica
como extension point — a assinatura do construtor já aceita os parâmetros
necessários, mas a implementação double-ended fica para uma iteração futura.
Only single-ended attenuation correction is provided; double-ended
(loop fiber, dual-ended acquisition) correction is an extension point.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from alakoro.io.alakoro_spool import AlakoroPatch
from alakoro.io.dasdae import DASDAEAdapter
from alakoro.processing.advanced_processors import (
    butterworth_lowpass as cpp_lowpass,
    geothermal_baseline_correction as cpp_geothermal_baseline,
    spatial_median_filter as cpp_spatial_median,
    thermal_anomaly_detection as cpp_thermal_anomaly,
    thermal_gradient as cpp_thermal_gradient,
)

try:  # CL-07 — rotinas 2D novas da Onda 2 (fallback NumPy abaixo)
    from alakoro_core import (
        attenuation_correct_single_ended_d as _cpp_attenuation_correct,
        mask_trailing_meters_d as _cpp_mask_trailing,
    )

    _CPP_ONDA2_DISPONIVEL = True
except ImportError:  # pragma: no cover - extensão C++ opcional
    _cpp_attenuation_correct = None
    _cpp_mask_trailing = None
    _CPP_ONDA2_DISPONIVEL = False


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
        mask_end_meters: Metros finais de fibra mortos a mascarar com NaN (None = desligado).
        attenuation_correction: Se True, corrige deriva de atenuação single-ended.
        reference_zone_m: Zona de referência [inicio, fim) em metros para o ajuste linear.
        quality_flags: Últimos flags calculados por process() (snr_db, dead_channel_mask).
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
        mask_end_meters: Optional[float] = None,
        attenuation_correction: bool = False,
        reference_zone_m: Tuple[float, float] = (0.0, 50.0),
        dead_channel_eps: float = 1e-9,
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
            mask_end_meters: Se informado, mascara com NaN os últimos N metros
                de cada traço (zona de fibra morta na ponta do cabo, CL-07).
                If set, NaN-masks the trailing N meters of every trace.
            attenuation_correction: Se True, remove a deriva de atenuação por
                regressão linear-in-distância do fundo térmico na zona de
                referência (single-ended, CL-07). If True, removes attenuation
                drift via linear-in-distance regression of the thermal
                background over the reference zone.
            reference_zone_m: Faixa [inicio_m, fim_m) usada no ajuste de
                atenuação (default 0–50 m, zona não perturbada próxima à cabeça).
            dead_channel_eps: Desvio-padrão abaixo do qual o canal é marcado
                como morto em quality_flags["dead_channel_mask"].
        """
        self.depth_step_m = depth_step_m
        self.surface_temp = surface_temp
        self.geothermal_gradient = geothermal_gradient
        self.spatial_median_window = spatial_median_window
        self.anomaly_threshold_sigma = anomaly_threshold_sigma
        self.lowpass_cutoff_hz = lowpass_cutoff_hz
        self.sample_rate_hz = sample_rate_hz
        self.use_cpp_backend = use_cpp_backend
        self.mask_end_meters = mask_end_meters
        self.attenuation_correction = attenuation_correction
        self.reference_zone_m = (float(reference_zone_m[0]), float(reference_zone_m[1]))
        self.dead_channel_eps = float(dead_channel_eps)

        # SP:C-05 — flags de qualidade preenchidos por process()
        self.quality_flags: Dict[str, np.ndarray] = {}

    # ─── CL-07: máscara de ponta e correção de atenuação ───

    @staticmethod
    def _first_masked_index(n_z: int, step_m: float, mask_m: float) -> int:
        """Índice do primeiro canal mascarado (regra equivalente ao C++)."""
        first = int(np.floor(((n_z - 1) * step_m - mask_m) / step_m)) + 1
        return max(0, min(first, n_z))

    def _mask_trailing(self, data: np.ndarray) -> np.ndarray:
        """Aplica NaN nos últimos mask_end_meters de cada traço (C++ ou NumPy)."""
        n_z = data.shape[1]
        if _CPP_ONDA2_DISPONIVEL:
            return np.asarray(
                _cpp_mask_trailing(data, self.depth_step_m, float(self.mask_end_meters)),
                dtype=np.float64,
            )
        out = np.array(data, dtype=np.float64, copy=True)
        first = self._first_masked_index(n_z, self.depth_step_m, float(self.mask_end_meters))
        out[:, first:] = np.nan
        return out

    def _attenuation_correct(self, data: np.ndarray) -> Dict:
        """Corrige deriva de atenuação single-ended (C++ ou fallback NumPy)."""
        ref_start, ref_end = self.reference_zone_m
        if _CPP_ONDA2_DISPONIVEL:
            out = _cpp_attenuation_correct(data, self.depth_step_m, ref_start, ref_end)
            return {
                "corrected": np.asarray(out["corrected"], dtype=np.float64),
                "slope_per_m": float(out["slope_per_m"]),
                "intercept": float(out["intercept"]),
                "backend": "cpp",
            }

        # Fallback NumPy: regressão linear-in-distância do traço médio temporal
        # sobre a zona de referência [ref_start, ref_end), extrapolada para o
        # campo inteiro — espelha attenuation_correct_single_ended_d.
        n_z = data.shape[1]
        depth = np.arange(n_z, dtype=np.float64) * self.depth_step_m
        i0 = int(np.clip(np.floor(ref_start / self.depth_step_m), 0, n_z - 1))
        i1 = int(np.clip(np.ceil(ref_end / self.depth_step_m), i0 + 1, n_z))
        mean_trace = np.nanmean(data, axis=0)
        slope, intercept = np.polyfit(depth[i0:i1], mean_trace[i0:i1], 1)
        corrected = data - (slope * depth + intercept)[np.newaxis, :]
        return {
            "corrected": corrected,
            "slope_per_m": float(slope),
            "intercept": float(intercept),
            "backend": "numpy",
        }

    # ─── SP:C-05: quality flags por canal ───

    def _compute_snr_db(self, data: np.ndarray) -> np.ndarray:
        """
        SNR por canal em dB: potência do sinal (componente suavizada
        temporalmente) vs potência do ruído de alta frequência (resíduo).
        Per-channel SNR in dB: smoothed signal power vs high-frequency
        residual noise power.
        """
        from scipy.ndimage import gaussian_filter1d

        n_t, n_z = data.shape
        snr = np.full(n_z, np.nan, dtype=np.float64)
        if n_t < 4:
            return snr
        for c in range(n_z):
            x = data[:, c]
            if not np.all(np.isfinite(x)):
                continue
            signal = gaussian_filter1d(x, sigma=2.0)
            noise = x - signal
            p_signal = float(np.mean(signal ** 2)) + 1e-12
            p_noise = float(np.mean(noise ** 2)) + 1e-12
            snr[c] = 10.0 * np.log10(p_signal / p_noise)
        return snr

    def _compute_dead_channels(self, data: np.ndarray) -> np.ndarray:
        """Máscara booleana de canais mortos (desvio-padrão < dead_channel_eps)."""
        with np.errstate(invalid="ignore"):
            std = np.nanstd(data, axis=0)
        return np.nan_to_num(std, nan=0.0) < self.dead_channel_eps

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
            Dicionário com campos processados, quality_flags (snr_db por canal
            e dead_channel_mask) e metadados. Quando mask_end_meters está
            ativo, os últimos metros de fibra vêm NaN em todos os campos 2D.
        """
        n_t, n_z = temperature.shape
        working = np.asarray(temperature, dtype=np.float64)

        # 0. SP:C-05 — quality flags calculados sobre a entrada bruta
        self.quality_flags = {
            "snr_db": self._compute_snr_db(working),
            "dead_channel_mask": self._compute_dead_channels(working),
        }

        # 1. SP:C-04 — correção de atenuação single-ended (antes do restante)
        attenuation_info = None
        if self.attenuation_correction:
            attenuation_info = self._attenuation_correct(working)
            working = attenuation_info["corrected"]

        # 2. Pré-processamento espacial/temporal
        preproc_patch = self.preprocess(working)
        preproc = preproc_patch.data

        # 3. Remoção de baseline geotérmico
        corrected = self.remove_geothermal_baseline(preproc)

        # 4. Gradiente térmico
        gradient = self.compute_gradient(corrected)

        # 5. Detecção de anomalias
        anomalies = self.detect_anomalies(corrected)

        # 6. Estatísticas por canal
        mean_temp = np.mean(corrected, axis=0)
        std_temp = np.std(corrected, axis=0)
        max_anomaly_score = np.max(np.abs(corrected - mean_temp[np.newaxis, :]) /
                                   (std_temp[np.newaxis, :] + 1e-12), axis=0)

        # 7. CL-07 — máscara dos últimos metros de fibra (aplicada na saída
        #    para não contaminar as estatísticas internas com NaN)
        metadata = {
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
        }
        if attenuation_info is not None:
            metadata["attenuation"] = {
                "enabled": True,
                "reference_zone_m": self.reference_zone_m,
                "slope_per_m": attenuation_info["slope_per_m"],
                "intercept": attenuation_info["intercept"],
                "backend": attenuation_info["backend"],
            }
        else:
            metadata["attenuation"] = {"enabled": False}

        if self.mask_end_meters is not None:
            first = self._first_masked_index(n_z, self.depth_step_m, float(self.mask_end_meters))
            if first < n_z:
                # Os arrays vindos do pipeline C++/DASCore podem ser views
                # somente-leitura; copia antes de aplicar os NaN.
                preproc = np.array(preproc, dtype=np.float64, copy=True)
                corrected = np.array(corrected, dtype=np.float64, copy=True)
                gradient = np.array(gradient, dtype=np.float64, copy=True)
                anomalies = np.array(anomalies, dtype=np.float64, copy=True)
                preproc[:, first:] = np.nan
                corrected[:, first:] = np.nan
                gradient[:, first:] = np.nan
                anomalies[:, first:] = 0
            metadata["end_mask_m"] = float(self.mask_end_meters)
            metadata["end_mask_first_channel"] = first
            metadata["mask_backend"] = "cpp" if _CPP_ONDA2_DISPONIVEL else "numpy"

        return {
            "temperature_preprocessed": preproc,
            "temperature_corrected": corrected,
            "thermal_gradient": gradient,
            "anomalies": anomalies,
            "mean_temperature": mean_temp,
            "std_temperature": std_temp,
            "max_anomaly_score": max_anomaly_score,
            "quality_flags": {
                "snr_db": self.quality_flags["snr_db"],
                "dead_channel_mask": self.quality_flags["dead_channel_mask"],
            },
            "metadata": metadata,
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
