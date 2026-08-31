"""
Alakoro FiberSense — Testes do InferenceEngine C++20
InferenceEngine Tests

Prova de conceito: garantir que o motor de inferência canônica consegue
detectar eventos sintéticos gerados pelo SignatureGenerator.
"""

import pytest
import numpy as np

from alakoro_core import (
    InferenceResult,
    InferenceMetadata,
    CanonicalInferenceEngine,
)
from src.ontology import InferenceEngine, infer_events
from src.simulation import SignatureGenerator, WellGeometry, AcquisitionConfig


@pytest.fixture
def generator():
    """Fixture com geometria e aquisição enxuta para testes rápidos."""
    well = WellGeometry(depth_top=0, depth_bottom=3000, n_channels=3000)
    acq = AcquisitionConfig(sampling_rate_hz=1000, trace_interval_s=2.0, duration_s=120)
    return SignatureGenerator(well, acq)


class TestCppBindings:
    """Testa diretamente as classes expostas via pybind11."""

    def test_inference_metadata_default(self):
        meta = InferenceMetadata()
        assert meta.sampling_rate_hz == 0.0
        assert meta.depth_step_m == 1.0
        assert meta.surface_temp_c == 20.0
        assert meta.geo_gradient_cpm == 0.03

    def test_canonical_engine_import(self):
        engine = CanonicalInferenceEngine()
        assert engine is not None

    def test_inference_result_repr(self):
        engine = CanonicalInferenceEngine()
        dts = np.zeros((10, 100), dtype=np.float64)
        meta = InferenceMetadata()
        meta.sampling_rate_hz = 1000.0
        meta.depth_step_m = 1.0
        results = engine.infer(dts, None, meta)
        assert isinstance(results, list)


class TestJouleThomsonInference:
    """Valida detecção do evento Joule-Thomson."""

    def test_detect_joule_thomson(self, generator):
        signature = generator.generate_joule_thomson(interface_depth=1500.0)
        engine = InferenceEngine()
        events = engine.infer_from_signature(signature)

        codes = [e.event_type for e in events]
        assert "joule_thomson" in codes, f"Esperado joule_thomson, obtido {codes}"

        jt_event = next(e for e in events if e.event_type == "joule_thomson")
        assert 1400.0 <= jt_event.depth_md <= 1600.0
        assert jt_event.confidence > 0.3


class TestWarmBackInference:
    """Valida detecção de Warm-Back."""

    def test_detect_warm_back(self, generator):
        signature = generator.generate_warm_back(injection_depths=[1200.0, 1500.0])
        events = infer_events(
            signature["dts"],
            signature["das"],
            sampling_rate_hz=generator.acq.sampling_rate_hz,
            depth_step_m=generator.acq.spatial_resolution_m,
        )
        codes = [e.event_type for e in events]
        assert "warm_back" in codes, f"Esperado warm_back, obtido {codes}"


class TestLeakPathInference:
    """Valida detecção de caminho de vazamento."""

    def test_detect_leak_path(self, generator):
        signature = generator.generate_leak_path(leak_depth=1914.0)
        engine = InferenceEngine()
        events = engine.infer_from_signature(signature)
        codes = [e.event_type for e in events]
        assert "leak_path" in codes, f"Esperado leak_path, obtido {codes}"


class TestValveChatterInference:
    """Valida detecção de valve chatter via DAS."""

    def test_detect_valve_chatter(self, generator):
        signature = generator.generate_valve_chatter(valve_depth=1400.0)
        events = infer_events(
            signature["dts"],
            signature["das"],
            sampling_rate_hz=generator.acq.sampling_rate_hz,
            depth_step_m=generator.acq.spatial_resolution_m,
        )
        codes = [e.event_type for e in events]
        assert "valve_chatter" in codes, f"Esperado valve_chatter, obtido {codes}"


class TestFracScreenoutInference:
    """Valida detecção de screen-out."""

    def test_detect_frac_screenout(self, generator):
        signature = generator.generate_frac_screenout(perf_depth=2000.0)
        engine = InferenceEngine()
        events = engine.infer_from_signature(signature)
        codes = [e.event_type for e in events]
        assert "frac_screenout" in codes, f"Esperado frac_screenout, obtido {codes}"


class TestEngineRobustness:
    """Testa robustez a entradas degeneradas."""

    def test_empty_das_optional(self, generator):
        signature = generator.generate_joule_thomson()
        engine = InferenceEngine()
        events = engine.infer(signature["dts"])
        assert isinstance(events, list)

    def test_wrong_shape_raises(self, generator):
        dts = np.zeros((10, 100), dtype=np.float64)
        das = np.zeros((10, 50), dtype=np.float64)
        with pytest.raises(ValueError):
            infer_events(dts, das)
