"""
Testes para serializacao Avro de AlakoroPatch.
"""

import numpy as np
import pytest

from src.io.alakoro_spool import AlakoroPatch
from src.io.avro_format import deserialize_avro, serialize_avro

try:
    import fastavro

    HAS_FASTAVRO = True
except ImportError:
    HAS_FASTAVRO = False


def _make_patch(modality="das"):
    import dascore as dc
    from dascore.core.attrs import PatchAttrs

    n_t, n_c = 20, 8
    data = np.random.randn(n_t, n_c).astype(np.float64)
    patch = dc.Patch(
        data=data,
        coords={
            "time": (np.arange(n_t) * 1e9).astype("timedelta64[ns]"),
            "distance": np.arange(n_c) * 2.0,
        },
        dims=("time", "distance"),
        attrs=PatchAttrs(
            data_category=modality,
            data_units="1/s",
            time_step=np.timedelta64(1_000_000_000, "ns"),
            distance_step=2.0,
        ),
    )
    return AlakoroPatch(patch, modality=modality)


@pytest.mark.skipif(not HAS_FASTAVRO, reason="fastavro not installed")
def test_serialize_avro_bytes():
    patch = _make_patch("das")
    payload = patch.to_avro_bytes(
        metadata={
            "sampling_rate_hz": 1000.0,
            "spatial_resolution_m": 2.0,
            "gauge_length_m": 10.0,
        }
    )
    assert isinstance(payload, bytes)
    assert len(payload) > 0


@pytest.mark.skipif(not HAS_FASTAVRO, reason="fastavro not installed")
def test_avro_roundtrip():
    patch = _make_patch("dts")
    payload = patch.to_avro_bytes(
        metadata={
            "sampling_rate_hz": 500.0,
            "spatial_resolution_m": 1.0,
            "gauge_length_m": 5.0,
            "units": "degC",
            "start_time": "2026-08-31T12:00:00Z",
        }
    )

    restored = AlakoroPatch.from_avro_bytes(payload)
    assert restored.modality == "dts"
    assert restored.shape == patch.shape
    assert np.allclose(restored.data, patch.data)


@pytest.mark.skipif(not HAS_FASTAVRO, reason="fastavro not installed")
def test_avro_all_modalities():
    for modality in ["das", "dts", "dss"]:
        patch = _make_patch(modality)
        payload = patch.to_avro_bytes()
        restored = AlakoroPatch.from_avro_bytes(payload)
        assert restored.modality == modality
        assert np.allclose(restored.data, patch.data)


@pytest.mark.skipif(not HAS_FASTAVRO, reason="fastavro not installed")
def test_avro_dtype_float32():
    import dascore as dc
    from dascore.core.attrs import PatchAttrs

    n_t, n_c = 5, 4
    data = np.random.randn(n_t, n_c).astype(np.float32)
    patch = dc.Patch(
        data=data,
        coords={
            "time": (np.arange(n_t) * 1e9).astype("timedelta64[ns]"),
            "distance": np.arange(n_c),
        },
        dims=("time", "distance"),
        attrs=PatchAttrs(data_category="das", data_units="1/s"),
    )
    alakoro_patch = AlakoroPatch(patch)
    payload = alakoro_patch.to_avro_bytes()
    record = deserialize_avro(payload)
    assert record["dtype"] == "float32"
    assert np.allclose(record["array"], data)
