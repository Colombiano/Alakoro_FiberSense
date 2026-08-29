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
    cwt as _cwt,
    magnitude_spectrum as _magnitude_spectrum,
    psd as _psd,
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


__all__ = [
    "butterworth_lowpass",
    "butterworth_highpass",
    "butterworth_bandpass",
    "magnitude_spectrum",
    "psd",
    "cwt",
]
