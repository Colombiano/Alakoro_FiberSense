"""
Alakoro FiberSense — Testes de integração Xdas
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest
import xdas

from src.io.alakoro_spool import AlakoroPatch, AlakoroSpool
from src.io.dasdae import DASDAEAdapter
from src.io.xdas_adapter import (
    alakoro_to_xdas,
    array_to_dataarray,
    dataarray_to_array,
    datacollection_to_spool,
    spool_to_datacollection,
    xdas_to_alakoro,
)
from src.io.xdas_formats import (
    read_xdas,
    write_xdas,
    supported_xdas_formats,
)
from src.processing.hybrid_pipeline import HybridPipeline


@pytest.fixture
def sample_alakoro_patch():
    n_t, n_z = 64, 8
    data = np.random.default_rng(42).standard_normal((n_t, n_z))
    patch = DASDAEAdapter.array_to_patch(data, dt_s=1.0, dx_m=2.0, modality="das")
    return AlakoroPatch(patch, well_id="W-01", modality="das")


class TestXdasAdapter:
    def test_array_to_dataarray_shape_and_attrs(self):
        data = np.random.default_rng(1).standard_normal((32, 4))
        da = array_to_dataarray(data, dt_s=0.5, dx_m=1.0, modality="dts", well_id="W-02")
        assert da.shape == (32, 4)
        assert da.attrs["data_category"] == "dts"
        assert da.attrs["well_id"] == "W-02"

    def test_dataarray_to_array_roundtrip(self):
        data = np.random.default_rng(2).standard_normal((32, 4))
        da = array_to_dataarray(data, dt_s=1.0, dx_m=2.0)
        arr = dataarray_to_array(da)
        assert arr["data"].shape == (32, 4)
        assert arr["dt_s"] == 1.0
        assert arr["dx_m"] == 2.0

    def test_alakoro_to_xdas_preserves_metadata(self, sample_alakoro_patch):
        da = alakoro_to_xdas(sample_alakoro_patch)
        assert da.shape == sample_alakoro_patch.shape
        assert da.attrs["well_id"] == "W-01"
        assert da.attrs["data_category"] == "das"

    def test_xdas_to_alakoro_roundtrip(self, sample_alakoro_patch):
        da = alakoro_to_xdas(sample_alakoro_patch)
        back = xdas_to_alakoro(da)
        assert back.shape == sample_alakoro_patch.shape
        assert back.well_id == "W-01"
        assert back.modality == "das"
        np.testing.assert_allclose(back.data, sample_alakoro_patch.data)

    def test_spool_to_datacollection_and_back(self, sample_alakoro_patch):
        spool = AlakoroSpool([sample_alakoro_patch, sample_alakoro_patch])
        collection = spool_to_datacollection(spool)
        assert len(collection) == 2
        assert all(isinstance(v, xdas.DataArray) for v in collection.values())

        back = datacollection_to_spool(collection)
        assert len(back) == 2
        assert back[0].shape == sample_alakoro_patch.shape


class TestXdasFormats:
    def test_supported_xdas_formats_returns_list(self):
        formats = supported_xdas_formats()
        assert isinstance(formats, list)
        assert len(formats) > 0
        assert "xdas" in formats

    def test_write_and_read_xdas_netcdf(self, sample_alakoro_patch):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.nc"
            write_xdas(sample_alakoro_patch, path)
            assert path.exists()

            back = read_xdas(path, well_id="W-01")
            assert isinstance(back, AlakoroPatch)
            assert back.shape == sample_alakoro_patch.shape
            assert back.well_id == "W-01"
            np.testing.assert_allclose(back.data, sample_alakoro_patch.data)

    def test_read_multiple_files(self, sample_alakoro_patch):
        with tempfile.TemporaryDirectory() as tmp:
            p1 = Path(tmp) / "p1.nc"
            p2 = Path(tmp) / "p2.nc"
            write_xdas(sample_alakoro_patch, p1)
            write_xdas(sample_alakoro_patch, p2)

            back = read_xdas([p1, p2], well_id="W-01")
            assert isinstance(back, AlakoroPatch)
            assert back.shape[0] == 2 * sample_alakoro_patch.shape[0]

    def test_read_nonexistent_path_raises(self):
        with pytest.raises(FileNotFoundError):
            read_xdas("/nonexistent/path/file.nc")


class TestHybridPipelineXdas:
    def test_pipeline_xdas_detrend(self, sample_alakoro_patch):
        pipeline = (
            HybridPipeline(sample_alakoro_patch)
            .xdas("detrend", dim="time", type="linear")
        )
        result = pipeline.to_patch()
        assert result.shape == sample_alakoro_patch.shape
        assert "xdas.detrend" in pipeline.history

    def test_pipeline_xdas_filter(self, sample_alakoro_patch):
        pipeline = (
            HybridPipeline(sample_alakoro_patch)
            .xdas("detrend", dim="time", type="linear")
            .xdas("filter", freq=0.2, dim="time", btype="lowpass")
        )
        result = pipeline.to_patch()
        assert result.shape == sample_alakoro_patch.shape

    def test_pipeline_hybrid_xdas_then_cpp(self, sample_alakoro_patch):
        pipeline = (
            HybridPipeline(sample_alakoro_patch)
            .xdas("detrend", dim="time", type="linear")
            .cpp("median_filter_1d", window_size=5)
            .xdas("filter", freq=0.2, dim="time", btype="lowpass")
        )
        result = pipeline.to_patch()
        assert result.shape == sample_alakoro_patch.shape
        assert pipeline.history == [
            "xdas.detrend",
            "cpp.median_filter_1d",
            "xdas.filter",
        ]

    def test_apply_array_xdas(self):
        data = np.random.default_rng(3).standard_normal((64, 4))
        spec = HybridPipeline(data, modality="das").apply_array_xdas("rfft")
        assert isinstance(spec, xdas.DataArray)
        assert spec.size > 0

    def test_xdas_unknown_processor_raises(self, sample_alakoro_patch):
        with pytest.raises(AttributeError):
            HybridPipeline(sample_alakoro_patch).xdas("nonexistent_processor")
