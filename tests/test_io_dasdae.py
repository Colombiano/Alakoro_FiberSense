"""
Testes da Fase 2 — Integração DASDAE (DASCore/Xdas).
"""

import numpy as np
import pytest

import dascore as dc
from dascore import Patch

from src.io.alakoro_spool import AlakoroPatch, AlakoroSpool
from src.io.dasdae import (
    DASDAEAdapter,
    alakoro_to_dascore,
    dascore_to_alakoro,
)


def _make_patch(n_t=50, n_c=10, modality="das") -> AlakoroPatch:
    data = np.random.randn(n_t, n_c)
    patch = DASDAEAdapter.array_to_patch(data, modality=modality)
    return AlakoroPatch(patch, well_id="W-01", modality=modality)


def test_alakoro_patch_properties():
    patch = _make_patch()
    assert patch.shape == (50, 10)
    assert patch.modality == "das"
    assert patch.well_id == "W-01"


def test_alakoro_patch_decimate():
    patch = _make_patch(n_t=100, n_c=10)
    dec = patch.decimate(2, dimension="time")
    assert dec.shape == (50, 10)


def test_alakoro_patch_detrend():
    data = np.linspace(0, 10, 100)[:, None].repeat(5, axis=1)
    patch = DASDAEAdapter.array_to_patch(data, modality="das")
    alakoro = AlakoroPatch(patch, well_id="W-01", modality="das")
    detrended = alakoro.detrend(dimension="time", type_="linear")
    assert detrended.data.shape == (100, 5)
    assert abs(detrended.data.mean()) < 1e-6


def test_alakoro_patch_select():
    patch = _make_patch(n_t=100, n_c=10)
    # Seleciona metade das amostras usando índices (samples=True)
    sub = patch.select(time=(0, 50), samples=True)
    assert sub.shape[0] <= 100


def test_alakoro_spool_iteration_and_indexing():
    patches = [_make_patch() for _ in range(3)]
    spool = AlakoroSpool(patches)
    assert len(spool) == 3
    assert spool[0].shape == (50, 10)
    assert len(list(spool)) == 3


def test_alakoro_spool_map():
    spool = AlakoroSpool([_make_patch(n_t=100, n_c=5) for _ in range(2)])
    result = spool.map(lambda p: p.detrend())
    assert len(result) == 2


def test_alakoro_spool_chunk():
    spool = AlakoroSpool([_make_patch(n_t=120, n_c=5)])
    chunked = spool.chunk(time=50, overlap=0)
    assert len(chunked) >= 2


def test_dasdae_array_to_patch_roundtrip():
    data = np.random.randn(100, 8)
    patch = DASDAEAdapter.array_to_patch(data, dt_s=1.0, dx_m=2.0)
    arr = DASDAEAdapter.patch_to_array(patch)

    assert arr["data"].shape == (100, 8)
    assert arr["dt_s"] == 1.0
    assert arr["dx_m"] == 2.0


def test_dasdae_to_dascore_from_dascore():
    patch = _make_patch()
    dc_patch = alakoro_to_dascore(patch)
    assert isinstance(dc_patch, Patch)

    back = dascore_to_alakoro(dc_patch, well_id="W-01")
    assert isinstance(back, AlakoroPatch)
    assert back.shape == patch.shape


def test_alakoro_spool_to_dascore():
    spool = AlakoroSpool([_make_patch() for _ in range(2)])
    dc_spool = spool.to_dascore()
    assert len(list(dc_spool)) == 2


def test_xdas_conversion_via_adapter():
    from src.io.xdas_adapter import alakoro_to_xdas, xdas_to_alakoro

    patch = _make_patch()
    da = alakoro_to_xdas(patch)
    back = xdas_to_alakoro(da, well_id="W-01")
    assert isinstance(back, AlakoroPatch)
    assert back.shape == patch.shape
    assert back.well_id == "W-01"
