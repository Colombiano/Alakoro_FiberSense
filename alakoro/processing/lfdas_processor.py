"""
Alakoro FiberSense — LF-DAS / eXDTS Processor (M1) v1.1.0
Low-Frequency DAS / enhanced Extended DTS Processor

Autor/Author: Luiz Paulo Colombiano
Data/Date: 2026-07-18
Versão/Version: 1.1.0
Licença/License: MIT

Extrator de temperatura de alta taxa a partir de DAS Rayleigh < 1 Hz.
High-rate temperature extractor from Rayleigh DAS < 1 Hz.

Baseado em / Based on:
- SPE-219546: eXDTS (Expro)
- SPE-228489: LF-DAS for dynamic well diagnosis

CHANGELOG v1.2.0 (Onda 2 — SP:I-03, SP:A-03, SP:C-03):
- thermal_coefficient_c_per_rad agora é parâmetro de construção (default 0.0028
  °C/rad, faixa da literatura 0.001–0.005 calibrável por poço), substituindo o
  valor hardcoded de 100.0 que contradizia a literatura (SPE-219546/SPE-228489)
- Novas rotas explícitas: process_lf() (LF-DAS, banda 0.05–1.0 Hz) e
  process_hf() (acústico > 1 Hz); process() mantém o comportamento legado
- Robustez LF-DAS: remoção de DC obrigatória, detector de saltos de
  unwrapping (|Δφ| > 0.8·2π) e clipping de transientes (mediana + 8·MAD),
  expostos em self.quality_flags

CHANGELOG v1.1.0:
- Decimation factor ajustado para 2000 (refresh rate ~2s conforme README)
- Adicionado parâmetro refresh_rate_target_s para controle explícito
- Melhorada documentação dos parâmetros
"""

import numpy as np
from scipy import signal as scipy_signal
from scipy.ndimage import gaussian_filter1d
from typing import Dict, List, Tuple

from alakoro.io.alakoro_spool import AlakoroPatch
from alakoro.io.dasdae import DASDAEAdapter
from alakoro.processing.advanced_processors import (
    butterworth_bandpass as cpp_bandpass,
    butterworth_highpass as cpp_highpass,
    butterworth_lowpass as cpp_lowpass,
    median_filter_1d as cpp_median,
    wavelet_denoise as cpp_wavelet_denoise,
)


class LFDASProcessor:
    """
    Extrator LF-DAS / eXDTS
    LF-DAS / eXDTS Extractor

    Converte dados DAS (Rayleigh, alta freq) em série térmica de 
    alta taxa (~2s refresh) filtrando <1 Hz.
    Converts DAS data (Rayleigh, high freq) into high-rate thermal
    series (~2s refresh) by filtering < 1 Hz.
    """

    def __init__(
        self,
        cutoff_hz: float = 1.0,
        filter_order: int = 4,
        sampling_rate_hz: float = 1000.0,
        refresh_rate_target_s: float = 2.0,
        spatial_smooth_sigma: float = 2.0,
        use_cpp_backend: bool = False,
        use_median_filter: bool = False,
        median_window_size: int = 5,
        use_wavelet_denoise: bool = False,
        wavelet_scales: list = None,
        wavelet_threshold: float = 0.5,
        thermal_coefficient_c_per_rad: float = 0.0028,
        lf_band_hz: Tuple[float, float] = (0.05, 1.0),
        hf_cutoff_hz: float = 1.0,
    ):
        """
        Args:
            cutoff_hz: Frequência de corte do filtro passa-baixa / Low-pass cutoff frequency
            filter_order: Ordem do filtro Butterworth / Butterworth filter order
            sampling_rate_hz: Taxa de amostragem original do DAS / Original DAS sampling rate
            refresh_rate_target_s: Taxa de refresh desejada (padrão: 2.0s) / Target refresh rate (default: 2.0s)
            spatial_smooth_sigma: Sigma do suavizamento espacial Gaussian / Gaussian spatial smoothing sigma
            use_cpp_backend: Se True, usa o filtro Butterworth C++20 do alakoro_core / If True, use alakoro_core C++20 Butterworth filter
            use_median_filter: Se True, aplica filtro de mediana 1D antes do Butterworth
            median_window_size: Tamanho da janela do filtro de mediana (ímpar)
            use_wavelet_denoise: Se True, aplica wavelet thresholding antes do Butterworth
            wavelet_scales: Escalas da CWT para wavelet denoise (padrão: [1,2,4])
            wavelet_threshold: Threshold para wavelet denoising
            thermal_coefficient_c_per_rad: Coeficiente de conversão fase→temperatura
                [°C/rad]. Default 0.0028 °C/rad conforme literatura LF-DAS/eXDTS
                (SPE-219546, SPE-228489); a faixa observada é 0.001–0.005 °C/rad
                e deve ser calibrada por poço. O valor anterior hardcoded (100.0)
                era fisicamente inconsistente com essa faixa.
                Phase-to-temperature conversion coefficient [°C/rad]. Default
                0.0028 °C/rad per LF-DAS/eXDTS literature; observed range
                0.001–0.005 °C/rad, calibratable per well.
            lf_band_hz: Banda do passa-faixa LF-DAS em process_lf()
                (default 0.05–1.0 Hz) / LF-DAS bandpass band for process_lf()
            hf_cutoff_hz: Frequência de corte do passa-alta em process_hf()
                (default 1.0 Hz, mantém > 1 Hz) / High-pass cutoff for process_hf()
        """
        self.cutoff_hz = cutoff_hz
        self.filter_order = filter_order
        self.sampling_rate_hz = sampling_rate_hz
        self.refresh_rate_target_s = refresh_rate_target_s
        self.spatial_smooth_sigma = spatial_smooth_sigma
        self.use_cpp_backend = use_cpp_backend
        self.use_median_filter = use_median_filter
        self.median_window_size = median_window_size
        self.use_wavelet_denoise = use_wavelet_denoise
        self.wavelet_scales = wavelet_scales if wavelet_scales is not None else [1.0, 2.0, 4.0]
        self.wavelet_threshold = wavelet_threshold

        # SP:I-03 — coeficiente térmico calibrável (literatura: ~0.0028 °C/rad)
        if thermal_coefficient_c_per_rad <= 0:
            raise ValueError("thermal_coefficient_c_per_rad deve ser > 0")
        self.thermal_coefficient_c_per_rad = float(thermal_coefficient_c_per_rad)

        # SP:A-03 — bandas LF/HF configuráveis
        nyquist = sampling_rate_hz / 2.0
        lf_low, lf_high = float(lf_band_hz[0]), float(lf_band_hz[1])
        if not (0.0 < lf_low < lf_high < nyquist):
            raise ValueError(
                f"lf_band_hz={lf_band_hz} inválido para Nyquist={nyquist} Hz; "
                "exigido 0 < low < high < Nyquist"
            )
        if not (0.0 < hf_cutoff_hz < nyquist):
            raise ValueError(
                f"hf_cutoff_hz={hf_cutoff_hz} inválido para Nyquist={nyquist} Hz"
            )
        self.lf_band_hz = (lf_low, lf_high)
        self.hf_cutoff_hz = float(hf_cutoff_hz)

        # SP:C-03 — flags de qualidade preenchidas durante o processamento
        self.quality_flags: Dict[str, object] = {
            "unwrap_jumps": [],
            "clipped_samples": 0,
        }

        # Calcular decimation factor automaticamente / Auto-calculate decimation factor
        self.decimation_factor = int(sampling_rate_hz * refresh_rate_target_s)
        if self.decimation_factor < 1:
            self.decimation_factor = 1

        normalized_cutoff = cutoff_hz / nyquist
        self.b, self.a = scipy_signal.butter(
            filter_order, normalized_cutoff, btype='low'
        )

    @property
    def refresh_rate_s(self) -> float:
        """Taxa de refresh efetiva / Effective refresh rate"""
        return self.decimation_factor / self.sampling_rate_hz

    def process(self, das_data: np.ndarray, trace_interval_s: float = 2.0) -> Dict:
        """Pipeline LF-DAS completo / Complete LF-DAS pipeline"""
        n_t, n_z = das_data.shape

        # Pré-processamento opcional com processadores avançados C++20
        working = das_data.astype(np.float64)
        if self.use_median_filter:
            patch = AlakoroPatch(
                DASDAEAdapter.array_to_patch(working, modality="das"),
                modality="das"
            )
            working = cpp_median(patch, window_size=self.median_window_size).data

        if self.use_wavelet_denoise:
            patch = AlakoroPatch(
                DASDAEAdapter.array_to_patch(working, modality="das"),
                modality="das"
            )
            working = cpp_wavelet_denoise(
                patch, scales=self.wavelet_scales,
                sample_rate_hz=self.sampling_rate_hz,
                threshold=self.wavelet_threshold
            ).data

        if self.use_cpp_backend:
            # Backend C++20: filtro Butterworth de 2ª ordem do alakoro_core
            patch = AlakoroPatch(
                DASDAEAdapter.array_to_patch(working, modality="das"),
                modality="das"
            )
            filtered_patch = cpp_lowpass(
                patch, sample_rate_hz=self.sampling_rate_hz, cutoff_hz=self.cutoff_hz
            )
            filtered = filtered_patch.data
        else:
            # Backend scipy: filtro Butterworth de ordem configurável
            filtered = np.zeros_like(working)
            for z in range(n_z):
                filtered[:, z] = scipy_signal.filtfilt(self.b, self.a, working[:, z])

        decimated = filtered[::self.decimation_factor, :]

        temperature = decimated * self.thermal_coefficient_c_per_rad

        if self.spatial_smooth_sigma > 0:
            for t in range(temperature.shape[0]):
                temperature[t, :] = gaussian_filter1d(
                    temperature[t, :], sigma=self.spatial_smooth_sigma
                )

        time_original = np.arange(n_t) * trace_interval_s
        time_decimated = time_original[::self.decimation_factor]

        method = (
            'LF-DAS Butterworth C++20 <1Hz + decimation'
            if self.use_cpp_backend
            else 'LF-DAS Butterworth IIR <1Hz + decimation'
        )
        method_pt = (
            'LF-DAS Butterworth C++20 <1Hz + decimação'
            if self.use_cpp_backend
            else 'LF-DAS Butterworth IIR <1Hz + decimação'
        )

        return {
            'temperature': temperature,
            'time_s': time_decimated,
            'n_channels': n_z,
            'refresh_rate_s': self.refresh_rate_s,
            'cutoff_hz': self.cutoff_hz,
            'metadata': {
                'method': method,
                'method_pt': method_pt,
                'original_sampling_hz': self.sampling_rate_hz,
                'decimated_sampling_hz': self.sampling_rate_hz / self.decimation_factor,
                'thermal_coefficient': self.thermal_coefficient_c_per_rad,
                'spatial_smooth_sigma': self.spatial_smooth_sigma,
                'refresh_rate_target_s': self.refresh_rate_target_s,
                'refresh_rate_actual_s': self.refresh_rate_s,
                'cpp_backend': self.use_cpp_backend,
                'median_filter': self.use_median_filter,
                'wavelet_denoise': self.use_wavelet_denoise,
            }
        }

    # ──────────────────────────────────────────────────────────────────
    # Rotas explícitas Onda 2 (SP:A-03) / Wave-2 explicit routes
    # ──────────────────────────────────────────────────────────────────

    def _filter_columns(self, working: np.ndarray, kind: str) -> np.ndarray:
        """Aplica filtro temporal por canal (scipy ou backend C++20)."""
        n_t, n_z = working.shape
        nyquist = self.sampling_rate_hz / 2.0

        if self.use_cpp_backend:
            patch = AlakoroPatch(
                DASDAEAdapter.array_to_patch(working, modality="das"),
                modality="das",
            )
            if kind == "bandpass":
                return cpp_bandpass(
                    patch,
                    sample_rate_hz=self.sampling_rate_hz,
                    low_hz=self.lf_band_hz[0],
                    high_hz=self.lf_band_hz[1],
                ).data
            return cpp_highpass(
                patch,
                sample_rate_hz=self.sampling_rate_hz,
                cutoff_hz=self.hf_cutoff_hz,
            ).data

        if kind == "bandpass":
            b, a = scipy_signal.butter(
                self.filter_order,
                [self.lf_band_hz[0] / nyquist, self.lf_band_hz[1] / nyquist],
                btype="band",
            )
        else:
            b, a = scipy_signal.butter(
                self.filter_order, self.hf_cutoff_hz / nyquist, btype="high"
            )
        filtered = np.zeros_like(working)
        for z in range(n_z):
            filtered[:, z] = scipy_signal.filtfilt(b, a, working[:, z])
        return filtered

    def _detect_unwrap_jumps(self, phase: np.ndarray) -> List[Tuple[int, int]]:
        """Detecta saltos de unwrapping: |Δφ| > 0.8·2π entre amostras adjacentes.

        Retorna lista de índices (t, z) medidos sobre np.diff(phase, axis=0),
        i.e. t ∈ [0, n_t-2]. / Returns (t, z) index pairs over the temporal
        first difference, where the phase increment exceeds 0.8·2π.
        """
        dphase = np.diff(phase, axis=0)
        hits = np.argwhere(np.abs(dphase) > 0.8 * 2.0 * np.pi)
        return [(int(t), int(z)) for t, z in hits]

    def process_lf(self, das_data: np.ndarray, trace_interval_s: float = 2.0) -> Dict:
        """
        Rota LF-DAS explícita (SP:A-03, SP:C-03) / Explicit LF-DAS route.

        Pipeline: demean obrigatório (remoção de DC) → detecção de saltos de
        unwrapping → passa-faixa na banda configurável (default 0.05–1.0 Hz)
        → decimação → conversão fase→temperatura com o coeficiente térmico.

        Pipeline: mandatory demean (DC removal) → unwrap-jump detection →
        bandpass in the configurable band (default 0.05–1.0 Hz) → decimation
        → phase-to-temperature conversion.

        Os índices de saltos ficam em self.quality_flags["unwrap_jumps"].
        """
        n_t, n_z = das_data.shape
        working = das_data.astype(np.float64)

        # (i) remoção de DC obrigatória / mandatory DC removal
        working = working - np.mean(working, axis=0, keepdims=True)

        # (ii) detector de saltos de unwrapping / unwrap-jump detector
        self.quality_flags["unwrap_jumps"] = self._detect_unwrap_jumps(working)

        filtered = self._filter_columns(working, "bandpass")
        decimated = filtered[::self.decimation_factor, :]
        temperature = decimated * self.thermal_coefficient_c_per_rad

        if self.spatial_smooth_sigma > 0:
            for t in range(temperature.shape[0]):
                temperature[t, :] = gaussian_filter1d(
                    temperature[t, :], sigma=self.spatial_smooth_sigma
                )

        time_original = np.arange(n_t) * trace_interval_s
        time_decimated = time_original[::self.decimation_factor]

        return {
            'temperature': temperature,
            'time_s': time_decimated,
            'n_channels': n_z,
            'refresh_rate_s': self.refresh_rate_s,
            'cutoff_hz': self.cutoff_hz,
            'quality_flags': {'unwrap_jumps': list(self.quality_flags["unwrap_jumps"])},
            'metadata': {
                'method': 'LF-DAS bandpass 0.05-1Hz (rota explícita process_lf)',
                'method_en': 'LF-DAS 0.05-1Hz bandpass (explicit process_lf route)',
                'route': 'lf',
                'lf_band_hz': self.lf_band_hz,
                'original_sampling_hz': self.sampling_rate_hz,
                'decimated_sampling_hz': self.sampling_rate_hz / self.decimation_factor,
                'thermal_coefficient': self.thermal_coefficient_c_per_rad,
                'spatial_smooth_sigma': self.spatial_smooth_sigma,
                'refresh_rate_actual_s': self.refresh_rate_s,
                'cpp_backend': self.use_cpp_backend,
                'n_unwrap_jumps': len(self.quality_flags["unwrap_jumps"]),
            },
        }

    def process_hf(self, das_data: np.ndarray) -> Dict:
        """
        Rota acústica HF explícita (SP:A-03, SP:C-03) / Explicit HF route.

        Pipeline: demean → clipping de transientes (amostras com
        |x| > mediana + 8·MAD são limitadas e contadas em
        self.quality_flags["clipped_samples"]) → passa-alta que remove o
        conteúdo ≤ hf_cutoff_hz (default 1.0 Hz), mantendo > 1 Hz.

        Pipeline: demean → transient clipping (samples with
        |x| > median + 8·MAD are limited and counted in
        self.quality_flags["clipped_samples"]) → high-pass removing the
        ≤ hf_cutoff_hz content (default 1.0 Hz), keeping > 1 Hz.
        """
        n_t, n_z = das_data.shape
        working = das_data.astype(np.float64)
        working = working - np.mean(working, axis=0, keepdims=True)

        # (iii) clipping de transientes HF / HF transient clipping
        median = float(np.median(working))
        mad = float(np.median(np.abs(working - median)))
        limit = median + 8.0 * mad
        over = np.abs(working) > limit
        self.quality_flags["clipped_samples"] = int(np.count_nonzero(over))
        if self.quality_flags["clipped_samples"] > 0:
            working = np.clip(working, -limit, limit)

        filtered = self._filter_columns(working, "highpass")

        return {
            'hf_data': filtered,
            'n_channels': n_z,
            'cutoff_hz': self.hf_cutoff_hz,
            'quality_flags': {'clipped_samples': self.quality_flags["clipped_samples"]},
            'metadata': {
                'method': 'HF-DAS highpass >1Hz (rota explícita process_hf)',
                'method_en': 'HF-DAS >1Hz high-pass (explicit process_hf route)',
                'route': 'hf',
                'hf_cutoff_hz': self.hf_cutoff_hz,
                'clip_limit': limit,
                'original_sampling_hz': self.sampling_rate_hz,
                'cpp_backend': self.use_cpp_backend,
            },
        }

    def compute_relative_difference(self, temperature: np.ndarray, 
                                     baseline_indices: slice = slice(0, 10)) -> np.ndarray:
        """Produto de diferença relativa contra baseline / Relative difference product against baseline"""
        baseline = np.mean(temperature[baseline_indices, :], axis=0)
        rel_diff = (temperature - baseline) / np.abs(baseline)
        return rel_diff

    def compute_dtdz(self, temperature: np.ndarray, depth: np.ndarray) -> np.ndarray:
        """Derivada térmica com profundidade (dT/dz) / Thermal derivative with depth (dT/dz)"""
        dtdz = np.zeros_like(temperature)
        dz = np.mean(np.diff(depth))
        for t in range(temperature.shape[0]):
            dtdz[t, :] = np.gradient(temperature[t, :], dz)
        return dtdz
