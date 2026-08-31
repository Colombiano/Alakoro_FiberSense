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
        prodml.write(patch, str(path), well_id="W-01", wellbore_id="WB-01")
        assert path.exists()

        back = prodml.read(str(path))
        assert back.shape == (20, 3)
        assert back.well_id == "W-01"


def test_prodml_preserves_metadata():
    data = np.random.randn(10, 4)
    dc_patch = DASDAEAdapter.array_to_patch(
        data, modality="das", dt_s=0.002, dx_m=2.5, units="1/s"
    )
    patch = AlakoroPatch(dc_patch, well_id="W-99", modality="das")

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "meta.prodml"
        prodml.write(patch, str(path))
        back = prodml.read(str(path))

        assert back.modality == "das"
        assert back.shape == (10, 4)
        assert back.well_id == "W-99"
        # Valores aproximados devido a formatacao float no XML
        back_dt_s = float(back.attrs.time_step / np.timedelta64(1, "s"))
        assert abs(back_dt_s - 0.002) < 1e-6
        assert abs(back.attrs.distance_step - 2.5) < 1e-6


def test_prodml_roundtrip_data_values():
    patch = _make_patch(n_t=5, n_c=2)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "round.prodml"
        prodml.write(patch, str(path))
        back = prodml.read(str(path))
        np.testing.assert_allclose(back.data, patch.data, rtol=1e-4)


def test_witsml_write_read():
    patch = _make_patch(n_t=15, n_c=2)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.witsml"
        witsml.write_log(patch, str(path), well_id="W-01", wellbore_id="WB-01")
        assert path.exists()

        back = witsml.read_log(str(path))
        assert back.shape == (15, 2)
        assert back.well_id == "W-01"


def test_witsml_preserves_metadata():
    data = np.random.randn(8, 3)
    dc_patch = DASDAEAdapter.array_to_patch(
        data, modality="das", dt_s=0.001, dx_m=1.0, units="strain"
    )
    patch = AlakoroPatch(dc_patch, well_id="W-02", modality="das")

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "meta.witsml"
        witsml.write_log(
            patch,
            str(path),
            well_id="W-02",
            wellbore_id="WB-02",
            mnemonics=["CH0", "CH1", "CH2"],
            units=["m/s", "m/s", "m/s"],
        )
        back = witsml.read_log(str(path))

        assert back.shape == (8, 3)
        assert back.well_id == "W-02"
        assert "m / s" in str(back.attrs.data_units)


def test_witsml_roundtrip_data_values():
    patch = _make_patch(n_t=6, n_c=2)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "round.witsml"
        witsml.write_log(patch, str(path))
        back = witsml.read_log(str(path))
        # primeira coluna do WITSML e o indice de tempo; dados comecam na coluna 1
        np.testing.assert_allclose(back.data, patch.data, rtol=1e-4)
