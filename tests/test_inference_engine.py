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


def _infer(generator, signature):
    """Helper para executar inferência sobre uma assinatura."""
    engine = InferenceEngine()
    return engine.infer_from_signature(signature)


class TestJouleThomsonInference:
    def test_detect_joule_thomson(self, generator):
        events = _infer(generator, generator.generate_joule_thomson(interface_depth=1500.0))
        codes = [e.event_type for e in events]
        assert "joule_thomson" in codes, f"Esperado joule_thomson, obtido {codes}"
        jt_event = next(e for e in events if e.event_type == "joule_thomson")
        assert 1400.0 <= jt_event.depth_md <= 1600.0
        assert jt_event.confidence > 0.3


class TestSlopeVelocityInference:
    def test_detect_slope_velocity(self, generator):
        events = _infer(generator, generator.generate_slope_velocity(flow_start_depth=1000.0))
        codes = [e.event_type for e in events]
        assert "slope_velocity" in codes, f"Esperado slope_velocity, obtido {codes}"


class TestWarmBackInference:
    def test_detect_warm_back(self, generator):
        events = _infer(generator, generator.generate_warm_back(injection_depths=[1200.0, 1500.0]))
        codes = [e.event_type for e in events]
        assert "warm_back" in codes, f"Esperado warm_back, obtido {codes}"


class TestValveChatterInference:
    def test_detect_valve_chatter(self, generator):
        events = _infer(generator, generator.generate_valve_chatter(valve_depth=1400.0))
        codes = [e.event_type for e in events]
        assert "valve_chatter" in codes, f"Esperado valve_chatter, obtido {codes}"


class TestSluggingCycleInference:
    def test_detect_slugging_cycle(self, generator):
        events = _infer(generator, generator.generate_slugging_cycle())
        codes = [e.event_type for e in events]
        assert "slugging_cycle" in codes, f"Esperado slugging_cycle, obtido {codes}"


class TestLeakPathInference:
    def test_detect_leak_path(self, generator):
        events = _infer(generator, generator.generate_leak_path(leak_depth=1914.0))
        codes = [e.event_type for e in events]
        assert "leak_path" in codes, f"Esperado leak_path, obtido {codes}"


class TestGlvBellowRuptureInference:
    def test_detect_glv_bellow_rupture(self, generator):
        events = _infer(generator, generator.generate_glv_bellow_rupture())
        codes = [e.event_type for e in events]
        assert "glv_bellow_rupture" in codes, f"Esperado glv_bellow_rupture, obtido {codes}"


class TestPerforationEffectivenessInference:
    def test_detect_perforation_effectiveness(self, generator):
        events = _infer(generator, generator.generate_perforation_effectiveness())
        codes = [e.event_type for e in events]
        assert "perforation_effectiveness" in codes, f"Esperado perforation_effectiveness, obtido {codes}"


class TestFracScreenoutInference:
    def test_detect_frac_screenout(self, generator):
        events = _infer(generator, generator.generate_frac_screenout(perf_depth=2000.0))
        codes = [e.event_type for e in events]
        assert "frac_screenout" in codes, f"Esperado frac_screenout, obtido {codes}"


class TestFracProppantDistributionInference:
    def test_detect_frac_proppant_distribution(self, generator):
        events = _infer(generator, generator.generate_frac_proppant_distribution())
        codes = [e.event_type for e in events]
        assert "frac_proppant_distribution" in codes, f"Esperado frac_proppant_distribution, obtido {codes}"


class TestFracHeightGrowthInference:
    def test_detect_frac_height_growth(self, generator):
        events = _infer(generator, generator.generate_frac_height_growth())
        codes = [e.event_type for e in events]
        assert "frac_height_growth" in codes, f"Esperado frac_height_growth, obtido {codes}"


class TestCementBondEvaluationInference:
    def test_detect_cement_bond_evaluation(self, generator):
        events = _infer(generator, generator.generate_cement_bond_evaluation())
        codes = [e.event_type for e in events]
        assert "cement_bond_evaluation" in codes, f"Esperado cement_bond_evaluation, obtido {codes}"


class TestReCementingAssessmentInference:
    def test_detect_re_cementing_assessment(self, generator):
        events = _infer(generator, generator.generate_re_cementing_assessment())
        codes = [e.event_type for e in events]
        assert "re_cementing_assessment" in codes, f"Esperado re_cementing_assessment, obtido {codes}"


class TestCrossflowZonalInference:
    def test_detect_crossflow_zonal(self, generator):
        events = _infer(generator, generator.generate_crossflow_zonal())
        codes = [e.event_type for e in events]
        assert "crossflow_zonal" in codes, f"Esperado crossflow_zonal, obtido {codes}"


class TestCementChannelingInference:
    def test_detect_cement_channeling(self, generator):
        events = _infer(generator, generator.generate_cement_channeling())
        codes = [e.event_type for e in events]
        assert "cement_channeling" in codes, f"Esperado cement_channeling, obtido {codes}"


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

    def test_all_canonical_events_at_least_once(self, generator):
        """Gera todas as 15 assinaturas e verifica se cada evento é detectado
        pelo menos uma vez ao longo de todas as inferências."""
        generators = [
            generator.generate_joule_thomson,
            generator.generate_slope_velocity,
            generator.generate_warm_back,
            generator.generate_valve_chatter,
            generator.generate_slugging_cycle,
            generator.generate_leak_path,
            generator.generate_glv_bellow_rupture,
            generator.generate_perforation_effectiveness,
            generator.generate_frac_screenout,
            generator.generate_frac_proppant_distribution,
            generator.generate_frac_height_growth,
            generator.generate_cement_bond_evaluation,
            generator.generate_re_cementing_assessment,
            generator.generate_crossflow_zonal,
            generator.generate_cement_channeling,
        ]
        detected = set()
        for gen_func in generators:
            events = _infer(generator, gen_func())
            detected.update(e.event_type for e in events)

        expected = {
            "joule_thomson", "slope_velocity", "warm_back", "valve_chatter",
            "slugging_cycle", "leak_path", "glv_bellow_rupture",
            "perforation_effectiveness", "frac_screenout", "frac_proppant_distribution",
            "frac_height_growth", "cement_bond_evaluation", "re_cementing_assessment",
            "crossflow_zonal", "cement_channeling",
        }
        missing = expected - detected
        assert not missing, f"Eventos nao detectados em nenhuma assinatura: {missing}"
