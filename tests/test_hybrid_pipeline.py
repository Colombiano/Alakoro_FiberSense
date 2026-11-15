"""
Alakoro FiberSense — Testes do HybridPipeline
HybridPipeline Tests

Foca nas guardas de dimensionalidade (CL-02): ramos dascore() e cpp() devem
rejeitar saídas que não sejam 2D (time, distance), como já fazia xdas().
"""

import numpy as np
import pytest
from dascore import Patch

from alakoro.io.alakoro_spool import AlakoroPatch
from alakoro.io.dasdae import DASDAEAdapter
from alakoro.processing.hybrid_pipeline import HybridPipeline


def _patch(data=None):
    data = np.random.default_rng(0).normal(size=(16, 8)) if data is None else data
    return AlakoroPatch(
        DASDAEAdapter.array_to_patch(data, modality="das"),
        modality="das",
    )


def _patch_3d():
    p3 = Patch(
        data=np.zeros((2, 3, 4)),
        coords={"a": [0, 1], "b": [0, 1, 2], "c": [0, 1, 2, 3]},
        dims=("a", "b", "c"),
    )
    return AlakoroPatch(p3, modality="das")


class TestDascoreBranch:
    def test_dascore_keeps_2d(self):
        out = HybridPipeline(_patch()).dascore(
            "detrend", dim="time", type="linear"
        ).to_numpy()
        assert out.shape == (16, 8)

    def test_dascore_dimensional_guard(self, monkeypatch):
        """Saída não-2D do DASCore deve levantar ValueError."""
        def fake_3d(self):
            return Patch(
                data=np.zeros((2, 3, 4)),
                coords={"a": [0, 1], "b": [0, 1, 2], "c": [0, 1, 2, 3]},
                dims=("a", "b", "c"),
            )

        monkeypatch.setattr(Patch, "to_3d_test", fake_3d, raising=False)
        with pytest.raises(ValueError, match="dimensionality"):
            HybridPipeline(_patch()).dascore("to_3d_test")


class TestCppBranch:
    def test_cpp_keeps_2d(self):
        out = HybridPipeline(_patch()).cpp("median_filter_1d", window_size=3).to_numpy()
        assert out.shape == (16, 8)

    def test_cpp_dimensional_guard_alakoro_patch(self, monkeypatch):
        """Processador C++ que devolve AlakoroPatch 3D deve levantar ValueError."""
        import alakoro.processing.advanced_processors as adv

        def fake_processor(patch, **kwargs):
            return _patch_3d()

        monkeypatch.setattr(adv, "fake_3d_proc", fake_processor, raising=False)
        with pytest.raises(ValueError, match="dimensionality"):
            HybridPipeline(_patch()).cpp("fake_3d_proc")

    def test_cpp_dimensional_guard_patch(self, monkeypatch):
        """Processador C++ que devolve Patch 3D puro também é rejeitado."""
        import alakoro.processing.advanced_processors as adv

        def fake_processor(patch, **kwargs):
            return _patch_3d().patch

        monkeypatch.setattr(adv, "fake_3d_proc", fake_processor, raising=False)
        with pytest.raises(ValueError, match="dimensionality"):
            HybridPipeline(_patch()).cpp("fake_3d_proc")
