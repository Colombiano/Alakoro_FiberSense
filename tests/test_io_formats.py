"""
Testes da Fase 2 — Escape hatches, ProdML e WITSML.
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from src.io.alakoro_spool import AlakoroPatch
from src.io.dasdae import DASDAEAdapter
from src.io.escape_hatches import (
    to_numpy,
    from_numpy,
    to_dataframe,
    from_dataframe,
    to_xarray,
    from_xarray,
)
from src.io import prodml, witsml


def _make_patch(n_t=30, n_c=5) -> AlakoroPatch:
    data = np.random.randn(n_t, n_c)
    patch = DASDAEAdapter.array_to_patch(data, modality="das")
    return AlakoroPatch(patch, well_id="W-01", modality="das")


def test_to_numpy_from_numpy():
    patch = _make_patch()
    arr = to_numpy(patch)
    assert arr.shape == patch.shape

    back = from_numpy(arr, modality="das")
    assert back.shape == patch.shape


def test_to_dataframe_from_dataframe():
    pytest.importorskip("pandas")
    patch = _make_patch()
    df = to_dataframe(patch)
    assert df.shape == patch.shape

    back = from_dataframe(df, modality="das")
    assert back.shape == patch.shape


def test_to_xarray_from_xarray():
    pytest.importorskip("xarray")
    patch = _make_patch()
    da = to_xarray(patch)
    assert da.shape == patch.shape

    back = from_xarray(da, modality="das")
    assert back.shape == patch.shape


def test_prodml_write_read():
    patch = _make_patch(n_t=20, n_c=3)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.prodml"
        prodml.write(patch, str(path), well_id="W-01")
        assert path.exists()

        back = prodml.read(str(path))
        assert back.shape == (20, 3)


def test_witsml_write_read():
    patch = _make_patch(n_t=15, n_c=2)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.witsml"
        witsml.write_log(patch, str(path), well_id="W-01", wellbore_id="WB-01")
        assert path.exists()

        back = witsml.read_log(str(path))
        assert back.shape == (15, 2)
