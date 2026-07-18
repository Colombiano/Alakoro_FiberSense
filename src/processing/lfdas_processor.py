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

CHANGELOG v1.1.0:
- Decimation factor ajustado para 2000 (refresh rate ~2s conforme README)
- Adicionado parâmetro refresh_rate_target_s para controle explícito
- Melhorada documentação dos parâmetros
"""

import numpy as np
from scipy import signal as scipy_signal
from scipy.ndimage import gaussian_filter1d
from typing import Dict


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
        spatial_smooth_sigma: float = 2.0
    ):
        """
        Args:
            cutoff_hz: Frequência de corte do filtro passa-baixa / Low-pass cutoff frequency
            filter_order: Ordem do filtro Butterworth / Butterworth filter order
            sampling_rate_hz: Taxa de amostragem original do DAS / Original DAS sampling rate
            refresh_rate_target_s: Taxa de refresh desejada (padrão: 2.0s) / Target refresh rate (default: 2.0s)
            spatial_smooth_sigma: Sigma do suavizamento espacial Gaussian / Gaussian spatial smoothing sigma
        """
        self.cutoff_hz = cutoff_hz
        self.filter_order = filter_order
        self.sampling_rate_hz = sampling_rate_hz
        self.refresh_rate_target_s = refresh_rate_target_s
        self.spatial_smooth_sigma = spatial_smooth_sigma

        # Calcular decimation factor automaticamente / Auto-calculate decimation factor
        self.decimation_factor = int(sampling_rate_hz * refresh_rate_target_s)
        if self.decimation_factor < 1:
            self.decimation_factor = 1

        nyquist = sampling_rate_hz / 2
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

        filtered = np.zeros_like(das_data)
        for z in range(n_z):
            filtered[:, z] = scipy_signal.filtfilt(self.b, self.a, das_data[:, z])

        decimated = filtered[::self.decimation_factor, :]

        thermal_coefficient = 100.0
        temperature = decimated * thermal_coefficient

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
            'metadata': {
                'method': 'LF-DAS Butterworth IIR <1Hz + decimation',
                'method_pt': 'LF-DAS Butterworth IIR <1Hz + decimação',
                'original_sampling_hz': self.sampling_rate_hz,
                'decimated_sampling_hz': self.sampling_rate_hz / self.decimation_factor,
                'thermal_coefficient': thermal_coefficient,
                'spatial_smooth_sigma': self.spatial_smooth_sigma,
                'refresh_rate_target_s': self.refresh_rate_target_s,
                'refresh_rate_actual_s': self.refresh_rate_s,
            }
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
