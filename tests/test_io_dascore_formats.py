"""
Alakoro FiberSense — Testes de integração DASCore: formatos + pipeline híbrido
"""

import tempfile
from pathlib import Path

import dascore as dc
import numpy as np
import pytest
from dascore import Patch
from dascore.core.attrs import PatchAttrs

from src.io.dascore_formats import (
    read,
    write,
    supported_formats,
    patch_from_dascore,
    spool_from_dascore,
)
from src.io.dasdae import DASDAEAdapter
from src.io.alakoro_spool import AlakoroPatch, AlakoroSpool
from src.processing.hybrid_pipeline import HybridPipeline


@pytest.fixture
def sample_dascore_patch():
    """Patch DASCore sintético para roundtrip."""
    n_t, n_z = 64, 8
    data = np.random.default_rng(42).standard_normal((n_t, n_z))
    time = (np.arange(n_t) * 1_000_000_000).astype("timedelta64[ns]")
    distance = np.arange(n_z) * 2.0
    attrs = PatchAttrs(
        data_category="das",
        data_units="1/s",
        time_step=np.timedelta64(int(1e9), "ns"),
        distance_step=2.0,
    )
    return Patch(
        data=data,
        coords={"time": time, "distance": distance},
        dims=("time", "distance"),
        attrs=attrs,
    )


@pytest.fixture
def sample_alakoro_patch(sample_dascore_patch):
    return patch_from_dascore(sample_dascore_patch, well_id="W-01", modality="das")


class TestDASCoreFormatSupport:
    def test_supported_formats_returns_non_empty_list(self):
        formats = supported_formats()
        assert isinstance(formats, list)
        assert len(formats) > 0
        assert "dasdae" in formats
        assert "pickle" in formats

    def test_patch_from_dascore_preserves_shape_and_metadata(self, sample_dascore_patch):
        patch = patch_from_dascore(sample_dascore_patch, well_id="W-01", modality="das")
        assert patch.shape == sample_dascore_patch.data.shape
        assert patch.well_id == "W-01"
        assert patch.modality == "das"
        assert patch.attrs.data_category == "das"

    def test_spool_from_dascore_preserves_contents(self, sample_dascore_patch):
        spool = dc.spool([sample_dascore_patch, sample_dascore_patch])
        alakoro_spool = spool_from_dascore(spool, well_id="W-02", modality="dts")
        assert len(alakoro_spool) == 2
        assert alakoro_spool[0].well_id == "W-02"
        assert alakoro_spool[0].modality == "dts"


class TestDASCoreReadWrite:
    @pytest.mark.parametrize("file_format", ["dasdae", "pickle"])
    def test_write_and_read_alakoro_patch(self, sample_alakoro_patch, file_format):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / f"roundtrip.{file_format}"
            write(sample_alakoro_patch, path)
            assert path.exists()

            back = read(path, well_id="W-01")
            assert isinstance(back, AlakoroPatch)
            assert back.shape == sample_alakoro_patch.shape
            assert back.well_id == "W-01"
            assert back.modality == "das"
            np.testing.assert_allclose(back.data, sample_alakoro_patch.data)

    def test_write_and_read_alakoro_spool(self, sample_alakoro_patch):
        # Pickle é o formato que preserva múltiplos patches em spool;
        # DASDAE pode colapsar/concatenar patches ao ler.
        spool = AlakoroSpool([sample_alakoro_patch, sample_alakoro_patch])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spool.pickle"
            write(spool, path)
            assert path.exists()

            back = read(path, well_id="W-01")
            assert isinstance(back, AlakoroSpool)
            assert len(back) == 2
            assert back[0].shape == sample_alakoro_patch.shape

    def test_write_infers_format_from_extension(self, sample_alakoro_patch):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inferred.dasdae"
            write(sample_alakoro_patch, path)
            assert path.exists()

    def test_read_nonexistent_path_raises(self):
        with pytest.raises(FileNotFoundError):
            read("/nonexistent/path/file.dasdae")


class TestHybridPipeline:
    def test_pipeline_with_dascore_and_cpp(self, sample_alakoro_patch):
        pipeline = (
            HybridPipeline(sample_alakoro_patch)
            .dascore("detrend", dim="time", type="linear")
            .cpp("median_filter_1d", window_size=5)
        )
        result = pipeline.to_patch()
        assert isinstance(result, AlakoroPatch)
        assert result.shape == sample_alakoro_patch.shape
        assert result.well_id == sample_alakoro_patch.well_id
        assert "dascore.detrend" in pipeline.history

    def test_pipeline_from_numpy(self):
        data = np.random.default_rng(7).standard_normal((64, 8))
        result = (
            HybridPipeline(data, well_id="W-03", modality="das")
            .dascore("detrend", dim="time", type="linear")
            .cpp("median_filter_1d", window_size=5)
            .to_patch()
        )
        assert result.shape == (64, 8)
        assert result.well_id == "W-03"

    def test_pipeline_apply_array_returns_numpy(self):
        data = np.random.default_rng(9).standard_normal((128, 8))
        psd = (
            HybridPipeline(data, modality="das")
            .apply_array("psd", sample_rate_hz=1000.0)
        )
        assert isinstance(psd, np.ndarray)
        assert psd.size > 0

    def test_pipeline_history_tracks_steps(self):
        data = np.random.default_rng(11).standard_normal((32, 4))
        pipeline = (
            HybridPipeline(data, modality="das")
            .dascore("detrend", dim="time", type="linear")
            .cpp("median_filter_1d", window_size=3)
        )
        assert pipeline.history == ["dascore.detrend", "cpp.median_filter_1d"]

    def test_pipeline_clone_preserves_state(self):
        data = np.random.default_rng(13).standard_normal((32, 4))
        p1 = HybridPipeline(data, modality="das").dascore("detrend", dim="time", type="linear")
        p2 = p1.clone()
        assert p1.history == p2.history
        assert p1.to_patch().shape == p2.to_patch().shape
