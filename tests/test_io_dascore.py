"""
Alakoro FiberSense — Testes de Integração DASCore
DASCore Integration Tests
"""

import pytest
import numpy as np

from src.io.dascore import alakoro_to_patch, patch_to_alakoro
from src.simulation import SignatureGenerator, WellGeometry, AcquisitionConfig


@pytest.fixture
def sample_signature():
    well = WellGeometry(depth_top=0, depth_bottom=3000, n_channels=300)
    acq = AcquisitionConfig(sampling_rate_hz=1000, trace_interval_s=2.0, duration_s=60)
    gen = SignatureGenerator(well, acq)
    sig = gen.generate_joule_thomson(interface_depth=1500.0)
    return sig


class TestDASCoreConversion:
    def test_alakoro_to_patch_shape(self, sample_signature):
        das = sample_signature["das"]
        patch = alakoro_to_patch(das, modality="DAS")
        assert patch.data.shape == das.shape

    def test_patch_to_alakoro_roundtrip(self, sample_signature):
        das = sample_signature["das"]
        patch = alakoro_to_patch(das, modality="DAS")
        result = patch_to_alakoro(patch)
        assert result["data"].shape == das.shape
        assert np.allclose(result["data"], das)

    def test_dts_conversion(self, sample_signature):
        dts = sample_signature["dts"]
        patch = alakoro_to_patch(dts, modality="DTS", units="degC")
        result = patch_to_alakoro(patch)
        assert result["modality"].lower() == "dts"
        assert np.allclose(result["data"], dts)
