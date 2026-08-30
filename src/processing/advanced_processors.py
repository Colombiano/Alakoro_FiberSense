"""
Alakoro FiberSense — Processadores Avançados

Wrappers Python de conveniência para processadores C++20:
  - Filtros Butterworth (lowpass, highpass, bandpass)
  - FFT / magnitude spectrum / PSD
  - CWT wavelet (Morlet, Ricker)

Também fornece funções que operam diretamente sobre AlakoroPatch.
"""

from __future__ import annotations

from typing import List, Optional, Union

import numpy as np

from alakoro_core import (
    DASData,
    butterworth_bandpass as _butterworth_bandpass,
    butterworth_highpass as _butterworth_highpass,
    butterworth_lowpass as _butterworth_lowpass,
    coherence as _coherence,
    cross_correlation as _cross_correlation,
    cwt as _cwt,
    hilbert_envelope as _hilbert_envelope,
    magnitude_spectrum as _magnitude_spectrum,
    median_filter_1d as _median_filter_1d,
    median_filter_2d as _median_filter_2d,
    psd as _psd,
    spectrogram as _spectrogram,
    svd_denoise as _svd_denoise,
    sta_lta as _sta_lta,
    teager_kaiser as _teager_kaiser,
    wavelet_denoise as _wavelet_denoise,
)

from src.io.alakoro_spool import AlakoroPatch


def _patch_to_dasdata(patch: AlakoroPatch) -> DASData:
    """Converte AlakoroPatch para DASData C++ (double)."""
    data = patch.data.astype(np.float64)
    das = DASData(n_times=data.shape[0], n_channels=data.shape[1])
    arr = np.array(das, copy=False)
    arr[:, :] = data
    return das


def _dasdata_to_array(das: DASData) -> np.ndarray:
    """Retorna cópia dos dados de DASData."""
    return np.array(das, copy=True)


def butterworth_lowpass(patch: AlakoroPatch,
                        sample_rate_hz: float,
                        cutoff_hz: float) -> AlakoroPatch:
    """Aplica filtro passa-baixa Butterworth de 2ª ordem."""
    das = _patch_to_dasdata(patch)
    _butterworth_lowpass(das, sample_rate_hz, cutoff_hz)
    from src.io.dasdae import DASDAEAdapter
    new_patch = DASDAEAdapter.array_to_patch(
        _dasdata_to_array(das), modality=patch.modality
    )
    return AlakoroPatch(new_patch, well_id=patch.well_id, modality=patch.modality)


def butterworth_highpass(patch: AlakoroPatch,
                         sample_rate_hz: float,
                         cutoff_hz: float) -> AlakoroPatch:
    """Aplica filtro passa-alta Butterworth de 2ª ordem."""
    das = _patch_to_dasdata(patch)
    _butterworth_highpass(das, sample_rate_hz, cutoff_hz)
    from src.io.dasdae import DASDAEAdapter
    new_patch = DASDAEAdapter.array_to_patch(
        _dasdata_to_array(das), modality=patch.modality
    )
    return AlakoroPatch(new_patch, well_id=patch.well_id, modality=patch.modality)


def butterworth_bandpass(patch: AlakoroPatch,
                         sample_rate_hz: float,
                         low_hz: float,
                         high_hz: float) -> AlakoroPatch:
    """Aplica filtro passa-faixa Butterworth de 2ª ordem."""
    das = _patch_to_dasdata(patch)
    _butterworth_bandpass(das, sample_rate_hz, low_hz, high_hz)
    from src.io.dasdae import DASDAEAdapter
    new_patch = DASDAEAdapter.array_to_patch(
        _dasdata_to_array(das), modality=patch.modality
    )
    return AlakoroPatch(new_patch, well_id=patch.well_id, modality=patch.modality)


def magnitude_spectrum(patch: AlakoroPatch) -> np.ndarray:
    """
    Calcula magnitude do espectro por canal.

    Retorna array de shape (n_freq, n_channels), onde n_freq = n_times/2 + 1.
    """
    das = _patch_to_dasdata(patch)
    return _magnitude_spectrum(das)


def psd(patch: AlakoroPatch, sample_rate_hz: float) -> np.ndarray:
    """
    Calcula densidade espectral de potência por canal.

    Retorna array de shape (n_freq, n_channels).
    """
    das = _patch_to_dasdata(patch)
    return _psd(das, sample_rate_hz)


def cwt(patch: AlakoroPatch,
        scales: List[float],
        sample_rate_hz: float,
        wavelet: str = "morlet") -> List[np.ndarray]:
    """
    Calcula CWT para cada canal.

    Retorna lista de arrays com shape (n_scales, n_times).
    """
    das = _patch_to_dasdata(patch)
    return _cwt(das, scales, sample_rate_hz, wavelet)


def sta_lta(patch: AlakoroPatch,
            n_sta: int,
            n_lta: int) -> np.ndarray:
    """
    Calcula razão STA/LTA para cada canal.

    Retorna array 1D flat com shape (n_valid * n_channels,).
    """
    das = _patch_to_dasdata(patch)
    return _sta_lta(das, n_sta, n_lta)


def hilbert_envelope(patch: AlakoroPatch) -> np.ndarray:
    """
    Calcula a envoltória de Hilbert para cada canal.

    Retorna array 1D flat com shape (n_times * n_channels,).
    """
    das = _patch_to_dasdata(patch)
    return _hilbert_envelope(das)


def teager_kaiser(patch: AlakoroPatch) -> np.ndarray:
    """
    Calcula o operador de energia de Teager-Kaiser para cada canal.

    Retorna array 1D flat com shape (n_times * n_channels,).
    """
    das = _patch_to_dasdata(patch)
    return _teager_kaiser(das)


def median_filter_1d(patch: AlakoroPatch, window_size: int) -> AlakoroPatch:
    """Aplica filtro de mediana 1D por canal."""
    das = _patch_to_dasdata(patch)
    filtered = _median_filter_1d(das, window_size)
    from src.io.dasdae import DASDAEAdapter
    new_patch = DASDAEAdapter.array_to_patch(
        filtered.reshape(das.n_times, das.n_channels), modality=patch.modality
    )
    return AlakoroPatch(new_patch, well_id=patch.well_id, modality=patch.modality)


def median_filter_2d(patch: AlakoroPatch,
                     window_t: int,
                     window_c: int) -> AlakoroPatch:
    """Aplica filtro de mediana 2D (tempo x canais)."""
    das = _patch_to_dasdata(patch)
    filtered = _median_filter_2d(das, window_t, window_c)
    from src.io.dasdae import DASDAEAdapter
    new_patch = DASDAEAdapter.array_to_patch(
        filtered.reshape(das.n_times, das.n_channels), modality=patch.modality
    )
    return AlakoroPatch(new_patch, well_id=patch.well_id, modality=patch.modality)


def svd_denoise(patch: AlakoroPatch, n_components: int) -> AlakoroPatch:
    """Denoising por SVD/PCA mantendo n_components componentes principais."""
    das = _patch_to_dasdata(patch)
    denoised = _svd_denoise(das, n_components)
    from src.io.dasdae import DASDAEAdapter
    new_patch = DASDAEAdapter.array_to_patch(
        denoised.reshape(das.n_times, das.n_channels), modality=patch.modality
    )
    return AlakoroPatch(new_patch, well_id=patch.well_id, modality=patch.modality)


def wavelet_denoise(patch: AlakoroPatch,
                    scales: List[float],
                    sample_rate_hz: float,
                    threshold: float,
                    rule: str = "soft") -> AlakoroPatch:
    """Denoising por thresholding de coeficientes wavelet (Morlet)."""
    das = _patch_to_dasdata(patch)
    denoised = _wavelet_denoise(das, scales, sample_rate_hz, threshold, rule)
    from src.io.dasdae import DASDAEAdapter
    new_patch = DASDAEAdapter.array_to_patch(
        denoised.reshape(das.n_times, das.n_channels), modality=patch.modality
    )
    return AlakoroPatch(new_patch, well_id=patch.well_id, modality=patch.modality)


def spectrogram(patch: AlakoroPatch,
                window_size: int,
                hop_size: int,
                n_fft: int) -> List[np.ndarray]:
    """
    Calcula o espectrograma para cada canal.

    Retorna lista de arrays com shape (n_frames, n_freq).
    """
    das = _patch_to_dasdata(patch)
    return _spectrogram(das, window_size, hop_size, n_fft)


def cross_correlation_channels(patch: AlakoroPatch, max_lag: int) -> np.ndarray:
    """
    Calcula correlação cruzada entre canais adjacentes.

    Retorna array de shape (n_channels, 2*max_lag+1).
    """
    das = _patch_to_dasdata(patch)
    return _cross_correlation(das, max_lag)


def coherence_channels(patch: AlakoroPatch,
                       window_size: int,
                       hop_size: int,
                       n_fft: int) -> np.ndarray:
    """
    Calcula magnitude squared coherence entre canais adjacentes.

    Retorna array de shape (n_channels, n_fft/2+1).
    """
    das = _patch_to_dasdata(patch)
    return _coherence(das, window_size, hop_size, n_fft)


__all__ = [
    "butterworth_lowpass",
    "butterworth_highpass",
    "butterworth_bandpass",
    "magnitude_spectrum",
    "psd",
    "cwt",
    "sta_lta",
    "hilbert_envelope",
    "teager_kaiser",
    "median_filter_1d",
    "median_filter_2d",
    "svd_denoise",
    "wavelet_denoise",
    "spectrogram",
    "cross_correlation_channels",
    "coherence_channels",
]
