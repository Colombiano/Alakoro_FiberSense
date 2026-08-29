"""
Testes dos processadores avançados C++20 (Butterworth, FFT, CWT).
"""

import math

import numpy as np
import pytest

from alakoro_core import DASData, butterworth_bandpass, butterworth_highpass, butterworth_lowpass, cwt, psd

from src.io.alakoro_spool import AlakoroPatch
from src.io.dasdae import DASDAEAdapter
from src.processing.advanced_processors import (
    butterworth_bandpass as py_bandpass,
    butterworth_highpass as py_highpass,
    butterworth_lowpass as py_lowpass,
    cwt as py_cwt,
    psd as py_psd,
)


def _make_das(n_t=256, n_c=8):
    data = np.random.randn(n_t, n_c).astype(np.float64)
    das = DASData(n_times=n_t, n_channels=n_c)
    arr = np.array(das, copy=False)
    arr[:, :] = data
    return das


def _make_patch(n_t=256, n_c=8):
    data = np.random.randn(n_t, n_c).astype(np.float64)
    patch = DASDAEAdapter.array_to_patch(data, modality="das")
    return AlakoroPatch(patch, modality="das")


def test_butterworth_lowpass_does_not_change_shape():
    das = _make_das(256, 8)
    butterworth_lowpass(das, sample_rate_hz=1000.0, cutoff_hz=100.0)
    arr = np.array(das, copy=True)
    assert arr.shape == (256, 8)


def test_butterworth_highpass_removes_dc():
    das = _make_das(256, 4)
    arr = np.array(das, copy=False)
    arr[:, :] = arr[:, :] + 10.0  # adiciona componente DC

    butterworth_highpass(das, sample_rate_hz=1000.0, cutoff_hz=10.0)

    filtered = np.array(das, copy=True)
    # Após highpass, a média deve ser próxima de zero
    assert abs(filtered.mean()) < 5.0


def test_butterworth_bandpass():
    das = _make_das(256, 4)
    butterworth_bandpass(das, sample_rate_hz=1000.0, low_hz=10.0, high_hz=100.0)
    arr = np.array(das, copy=True)
    assert arr.shape == (256, 4)
    assert np.all(np.isfinite(arr))


def test_psd_shape():
    das = _make_das(256, 4)
    spec = psd(das, sample_rate_hz=1000.0)
    assert spec.ndim == 1
    assert spec.size == 129 * 4  # n_freq = n_times/2 + 1 = 129
    assert np.all(spec >= 0)


def test_cwt():
    das = _make_das(128, 2)
    scales = [1.0, 2.0, 4.0]
    coefs = cwt(das, scales, sample_rate_hz=1000.0, wavelet="morlet")
    assert len(coefs) == 2  # um por canal
    assert coefs[0].shape == (3, 128)  # (n_scales, n_times)
    assert np.all(np.isfinite(coefs[0]))


def test_python_wrappers_lowpass():
    patch = _make_patch(128, 4)
    filtered = py_lowpass(patch, sample_rate_hz=1000.0, cutoff_hz=100.0)
    assert filtered.shape == (128, 4)


def test_python_wrappers_psd():
    patch = _make_patch(128, 4)
    spec = py_psd(patch, sample_rate_hz=1000.0)
    assert spec.ndim == 1
    assert spec.size == 65 * 4


def test_python_wrappers_cwt():
    patch = _make_patch(64, 2)
    scales = [1.0, 2.0]
    coefs = py_cwt(patch, scales, sample_rate_hz=1000.0, wavelet="morlet")
    assert len(coefs) == 2
    assert coefs[0].shape == (2, 64)
