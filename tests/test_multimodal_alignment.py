"""
Alakoro FiberSense — Testes de Alinhamento Multimodal LF-DAS/DTS
Multimodal Alignment Tests

Cobre: no-op em grades iguais, interpolação em grades defasadas,
ValueError em shapes/grades incompatíveis e round-trip de unidades/metadados.
"""

import numpy as np
import pytest

from alakoro.processing.multimodal_alignment import (
    AlignedData,
    align_lfdas_dts,
    regrid_to_common,
)


def _dict(data, time, depth, units="degC", metadata=None):
    out = {"data": data, "time": time, "depth": depth, "units": units}
    if metadata:
        out["metadata"] = metadata
    return out


class TestAlignLfdasDts:
    def test_same_grid_is_noop(self):
        """Grades idênticas: dados preservados sem interpolação."""
        rng = np.random.default_rng(0)
        das = rng.normal(size=(30, 12))
        dts = rng.normal(size=(30, 12))
        time = np.arange(30) * 2.0
        depth = np.arange(12) * 1.0
        aligned = align_lfdas_dts(
            _dict(das, time, depth), _dict(dts, time, depth)
        )
        assert isinstance(aligned, AlignedData)
        assert aligned.shape == (30, 12)
        assert np.array_equal(aligned.time, time)
        assert np.array_equal(aligned.depth, depth)
        assert np.array_equal(aligned.data["lfdas"], das)
        assert np.array_equal(aligned.data["dts"], dts)

    def test_offset_time_grids_interpolate_correctly(self):
        """Grade temporal defasada em meio passo: interpolação linear exata."""
        # f(t, z) = t + z: interpolação linear reproduz o valor exato.
        time_a = np.arange(10) * 2.0
        time_b = np.arange(10) * 2.0 + 1.0  # defasado em 1s (meio passo)
        depth = np.arange(5) * 1.0
        da = time_a[:, None] + depth[None, :]
        db = time_b[:, None] + depth[None, :]
        aligned = align_lfdas_dts(_dict(da, time_a, depth), _dict(db, time_b, depth))
        # Grade comum = mais grosseira contida na sobreposição [1, 17].
        # Ambas têm o mesmo espaçamento; a escolhida é a do LF-DAS (primeiro).
        common_t = aligned.time
        expected = common_t[:, None] + depth[None, :]
        assert np.allclose(aligned.data["lfdas"], expected, atol=1e-12)
        assert np.allclose(aligned.data["dts"], expected, atol=1e-12)

    def test_coarser_grid_wins(self):
        """Alinhamento usa a grade mais grosseira de cada eixo."""
        das = np.ones((40, 16))
        dts = np.ones((10, 4)) * 2.0
        aligned = align_lfdas_dts(
            _dict(das, np.arange(40) * 1.0, np.arange(16) * 0.5),
            _dict(dts, np.arange(10) * 4.0, np.arange(4) * 2.0),
        )
        assert aligned.time.size == 10
        assert aligned.depth.size == 4
        assert aligned.shape == (10, 4)
        assert np.allclose(aligned.data["lfdas"], 1.0)
        assert np.allclose(aligned.data["dts"], 2.0)

    def test_units_and_metadata_roundtrip(self):
        """Unidades e metadados de cada entrada sobrevivem ao alinhamento."""
        meta_das = {"method": "LF-DAS Butterworth", "cutoff_hz": 1.0}
        meta_dts = {"method": "DTS calibrated", "probe": "Raman"}
        aligned = align_lfdas_dts(
            _dict(np.ones((8, 6)), np.arange(8) * 2.0, np.arange(6),
                  units="degC", metadata=meta_das),
            _dict(np.ones((8, 6)) * 3, np.arange(8) * 2.0, np.arange(6),
                  units="degC", metadata=meta_dts),
        )
        assert aligned.units == {"lfdas": "degC", "dts": "degC"}
        assert aligned.attrs["lfdas"]["cutoff_hz"] == 1.0
        assert aligned.attrs["dts"]["probe"] == "Raman"

    def test_incompatible_shapes_raise(self):
        """Dimensões diferentes sem sobreposição recuperável → ValueError."""
        with pytest.raises(ValueError, match="does not match"):
            align_lfdas_dts(
                _dict(np.ones((10, 6)), np.arange(10), np.arange(6)),
                _dict(np.ones((10, 6)), np.arange(10), np.arange(5)),
            )

    def test_no_overlap_raises(self):
        """Eixos sem sobreposição são incompatíveis de forma irrecuperável."""
        with pytest.raises(ValueError, match="no overlap"):
            align_lfdas_dts(
                _dict(np.ones((10, 6)), np.arange(10) * 1.0, np.arange(6) * 1.0),
                _dict(np.ones((10, 6)), np.arange(10) * 1.0 + 1000.0,
                      np.arange(6) * 1.0),
            )

    def test_unsupported_method_raises(self):
        with pytest.raises(ValueError, match="method"):
            align_lfdas_dts(
                _dict(np.ones((4, 4)), np.arange(4), np.arange(4)),
                _dict(np.ones((4, 4)), np.arange(4), np.arange(4)),
                method="nearest",
            )

    def test_plain_arrays_use_implicit_grid(self):
        """np.ndarray 2D puro usa grade inteira implícita."""
        das = np.ones((8, 6))
        dts = np.ones((8, 6)) * 2
        aligned = align_lfdas_dts(das, dts)
        assert aligned.shape == (8, 6)
        assert np.array_equal(aligned.data["lfdas"], das)

    def test_1d_data_raises(self):
        with pytest.raises(ValueError, match="2D"):
            align_lfdas_dts(
                _dict(np.ones(10), np.arange(10), np.arange(10)),
                _dict(np.ones((10, 10)), np.arange(10), np.arange(10)),
            )


class TestRegridToCommon:
    def test_linear_interpolation(self):
        arrays = {
            "a": (np.array([0.0, 1.0, 2.0]), np.array([0.0, 1.0, 2.0])),
            "b": (np.array([10.0, 20.0]), np.array([0.0, 2.0])),
        }
        out = regrid_to_common(arrays, np.array([0.0, 1.0, 2.0]))
        assert np.allclose(out["a"], [0.0, 1.0, 2.0])
        assert np.allclose(out["b"], [10.0, 15.0, 20.0])

    def test_mismatched_pair_raises(self):
        with pytest.raises(ValueError, match="shapes differ"):
            regrid_to_common({"a": (np.ones(3), np.ones(4))}, np.arange(3.0))

    def test_2d_values_raise(self):
        with pytest.raises(ValueError, match="1D"):
            regrid_to_common({"a": (np.ones((3, 3)), np.ones(3))}, np.arange(3.0))

    def test_unsupported_method_raises(self):
        with pytest.raises(ValueError, match="method"):
            regrid_to_common({"a": (np.ones(3), np.ones(3))}, np.ones(3),
                             method="cubic")
