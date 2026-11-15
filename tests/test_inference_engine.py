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
from alakoro.ontology import InferenceEngine, infer_events
from alakoro.ontology.events import FlowEvent
from alakoro.ontology.inference_engine import _resolve_sampling_rate_hz
from alakoro.simulation import SignatureGenerator, WellGeometry, AcquisitionConfig


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


# =============================================================================
# CL-11 — Validações e placeholders do motor de inferência
# =============================================================================

class TestSamplingRateValidation:
    """IE:A-04: sampling_rate_hz <= 0 deve ser rejeitado (Python e C++)."""

    def test_python_wrapper_rejects_zero(self, generator):
        signature = generator.generate_joule_thomson()
        engine = InferenceEngine()
        with pytest.raises(ValueError, match="sampling_rate_hz"):
            engine.infer(signature["dts"], signature["das"], sampling_rate_hz=0.0)

    def test_python_wrapper_rejects_negative(self, generator):
        signature = generator.generate_joule_thomson()
        engine = InferenceEngine()
        with pytest.raises(ValueError, match="sampling_rate_hz"):
            engine.infer(signature["dts"], sampling_rate_hz=-100.0)

    def test_cpp_wrapper_rejects_default_zero(self, generator):
        """InferenceMetadata default é 0.0: o C++ deve levantar ValueError."""
        engine = CanonicalInferenceEngine()
        meta = InferenceMetadata()  # sampling_rate_hz == 0.0
        dts = np.zeros((10, 100), dtype=np.float64)
        with pytest.raises(ValueError, match="sampling_rate_hz"):
            engine.infer(dts, None, meta)


class TestSamplingRateDerivation:
    """infer_from_signature deriva fs de parameters/acq; fallback 1000 Hz."""

    def test_from_parameters_sampling_rate(self, generator):
        signature = generator.generate_joule_thomson()
        signature["parameters"] = dict(
            signature["parameters"], sampling_rate_hz=500.0
        )
        engine = InferenceEngine()
        events = engine.infer_from_signature(signature)
        assert isinstance(events, list)

    def test_resolve_from_parameters(self):
        assert _resolve_sampling_rate_hz(
            {"parameters": {"sampling_rate_hz": 500.0}}) == 500.0

    def test_resolve_from_trace_interval(self):
        assert _resolve_sampling_rate_hz(
            {"parameters": {"trace_interval_s": 4.0}}) == 0.25

    def test_resolve_from_acq_object(self):
        acq = AcquisitionConfig(sampling_rate_hz=250.0)
        assert _resolve_sampling_rate_hz({"acq": acq}) == 250.0

    def test_resolve_fallback_is_1000(self, generator):
        signature = generator.generate_joule_thomson()
        assert _resolve_sampling_rate_hz(signature) == 1000.0


class TestCriticalSeverity:
    """GLV bellow rupture com confiança > 0.95 emite severity Critical
    (única condição Critical do motor, prevista no JSON Schema v1.1.0)."""

    def test_glv_bellow_rupture_critical(self, generator):
        events = _infer(generator, generator.generate_glv_bellow_rupture())
        glv = next(e for e in events if e.event_type == "glv_bellow_rupture")
        assert glv.confidence > 0.95
        assert glv.severity == "Critical"


class TestFlowEventNoFakeFlowRate:
    """FlowEvent não deve usar confidence como placeholder de flow_rate_ms."""

    def test_flow_event_flow_rate_is_none(self, generator):
        events = _infer(generator, generator.generate_slope_velocity())
        flow = next(e for e in events if e.event_type == "slope_velocity")
        assert isinstance(flow, FlowEvent)
        assert flow.flow_rate_ms is None
        assert 0.0 <= flow.confidence <= 1.0


# =============================================================================
# Onda 2 — CL-08 bandas LF/HF, CL-04 cinemática, IE:J-03 quality_flags,
# CL-03 wrapper de desacoplamento
# =============================================================================

from types import SimpleNamespace

from alakoro.ontology.events import SlopeVelocityEvent
from alakoro.ontology.inference_engine import (
    _decouple_fallback,
    _result_to_event,
)

# Campo DAS LF lento e determinístico: pulso gaussiano (σ_t = 0.4 s)
# deslocando-se a +20 m/s. Usado para exercitar o condicionamento CL-08
# (bandas padrão 0.05–1 Hz) e os campos cinemáticos CL-04.
_LF_FS = 100.0
_LF_N_T = 2000
_LF_N_Z = 100


def _lf_moving_field(velocidade_ms=20.0, seed=3):
    rng = np.random.default_rng(seed)
    t = np.arange(_LF_N_T) / _LF_FS
    z = np.arange(_LF_N_Z, dtype=float)
    dt = t[:, None] - (z / velocidade_ms)[None, :]
    return np.exp(-0.5 * (dt / 0.4) ** 2) + rng.normal(0.0, 0.01, (_LF_N_T, _LF_N_Z))


def _das_hydraulic_case():
    """Cenário hidráulico determinístico (espelha TestVelocidadeEDiscriminacao
    de test_cpp_wave2): anomalia térmica + energia 15–100 Hz + evento móvel
    coerente com velocidade > 0."""
    fs, n_t, n_z = 1000.0, 4000, 200
    rng = np.random.default_rng(5)
    t = np.arange(n_t) / fs
    z = np.arange(n_z, dtype=float)
    dt = t[:, None] - (z / 50.0)[None, :]
    forma = np.exp(-0.5 * (dt / 0.02) ** 2) * np.sin(2.0 * np.pi * 80.0 * dt)
    das = forma + rng.normal(0.0, 0.02, (n_t, n_z))
    tom = 0.5 * np.sin(2.0 * np.pi * 30.0 * t)
    das[:, 60:140] += tom[:, None]
    dts = np.full((n_t, n_z), 60.0)
    dts[:, 80:120] += 8.0
    return dts, das, fs


class TestBandParametersCL08:
    """CL-08 (lado Python): bandas LF-DAS e hidráulica repassadas ao C++."""

    def test_metadata_reflete_bandas(self, generator, monkeypatch):
        captured = {}

        class _SpyEngine(CanonicalInferenceEngine):
            def infer(self, dts, das, meta):
                captured["low"] = meta.low_freq_band_hz
                captured["high"] = meta.high_freq_band_hz
                captured["dlow"] = meta.discrim_low_freq_hz
                captured["dhigh"] = meta.discrim_high_freq_hz
                captured["apply"] = meta.apply_band_filter
                return super().infer(dts, das, meta)

        monkeypatch.setattr(
            "alakoro.ontology.inference_engine.CanonicalInferenceEngine", _SpyEngine)
        signature = generator.generate_joule_thomson()
        engine = InferenceEngine()
        events = engine.infer(
            signature["dts"], signature["das"], sampling_rate_hz=1000.0,
            low_freq_band_hz=0.1, high_freq_band_hz=0.5,
            discrim_low_freq_hz=20.0, discrim_high_freq_hz=80.0,
            apply_band_filter=False,
        )
        assert captured["low"] == 0.1
        assert captured["high"] == 0.5
        assert captured["dlow"] == 20.0
        assert captured["dhigh"] == 80.0
        assert captured["apply"] is False
        assert isinstance(events, list)

    def test_defaults_canonicos_forwarded(self, generator, monkeypatch):
        captured = {}

        class _SpyEngine(CanonicalInferenceEngine):
            def infer(self, dts, das, meta):
                captured.update(low=meta.low_freq_band_hz, high=meta.high_freq_band_hz,
                                dlow=meta.discrim_low_freq_hz,
                                dhigh=meta.discrim_high_freq_hz,
                                apply=meta.apply_band_filter)
                return super().infer(dts, das, meta)

        monkeypatch.setattr(
            "alakoro.ontology.inference_engine.CanonicalInferenceEngine", _SpyEngine)
        signature = generator.generate_joule_thomson()
        engine = InferenceEngine()
        engine.infer(signature["dts"], sampling_rate_hz=1000.0)
        # Defaults do contrato C++ (InferenceMetadata).
        assert captured == {"low": 0.05, "high": 1.0, "dlow": 15.0,
                            "dhigh": 100.0, "apply": True}

    def test_bandas_invalidas_rejeitadas(self, generator):
        signature = generator.generate_joule_thomson()
        engine = InferenceEngine()
        with pytest.raises(ValueError, match="LF band"):
            engine.infer(signature["dts"], sampling_rate_hz=1000.0,
                         high_freq_band_hz=0.01)  # high <= low
        with pytest.raises(ValueError, match="discrimination band"):
            engine.infer(signature["dts"], sampling_rate_hz=1000.0,
                         discrim_low_freq_hz=-1.0)

    def test_apply_band_filter_muda_resultado(self):
        """O condicionamento LF (CL-08) altera a estimativa de velocidade."""
        engine = InferenceEngine()
        dts = np.zeros((_LF_N_T, _LF_N_Z))
        das = _lf_moving_field()

        off = {e.event_type: e for e in engine.infer(
            dts, das, sampling_rate_hz=_LF_FS, apply_band_filter=False)}
        on = {e.event_type: e for e in engine.infer(
            dts, das, sampling_rate_hz=_LF_FS, apply_band_filter=True)}

        sv_off = off.get("slope_velocity")
        assert sv_off is not None, "sem filtro LF o evento móvel deve ser detectado"
        assert np.isfinite(sv_off.apparent_velocity_ms)
        assert sv_off.apparent_velocity_ms == pytest.approx(20.0, rel=0.25)

        sv_on = on.get("slope_velocity")
        # O filtro altera o resultado: suprime o evento ou muda a velocidade.
        if sv_on is not None:
            assert (not np.isfinite(sv_on.apparent_velocity_ms)
                    or sv_on.apparent_velocity_ms != pytest.approx(
                        sv_off.apparent_velocity_ms))


class TestKinematicFieldsCL04:
    """CL-04: campos cinemáticos do InferenceResult → ontologia."""

    def test_slope_velocity_event_campos(self):
        engine = InferenceEngine()
        dts = np.zeros((_LF_N_T, _LF_N_Z))
        events = engine.infer(dts, _lf_moving_field(),
                              sampling_rate_hz=_LF_FS, apply_band_filter=False)
        sv = next(e for e in events if e.event_type == "slope_velocity")
        assert isinstance(sv, SlopeVelocityEvent)
        assert isinstance(sv, FlowEvent)
        assert np.isfinite(sv.apparent_velocity_ms)
        assert sv.apparent_velocity_ms == pytest.approx(20.0, rel=0.25)
        assert sv.flow_direction == "down"
        assert sv.flow_rate_ms is None  # nunca usar confidence como proxy

    def test_flow_discrimination_mapeado_para_flow_event(self):
        engine = InferenceEngine()
        dts, das, fs = _das_hydraulic_case()
        events = engine.infer(dts, das, sampling_rate_hz=fs,
                              apply_band_filter=False)
        fd = next(e for e in events if e.event_type == "flow_discrimination")
        assert type(fd) is FlowEvent  # código flow_discrimination → FlowEvent
        assert fd.discrimination == "hydraulic"
        assert fd.flow_direction == "down"
        assert fd.apparent_velocity_ms > 0.0

    def test_nan_vira_none_em_result_to_event(self):
        stub = SimpleNamespace(
            event_type="slope_velocity", event_label_pt="Rastreamento",
            event_label_en="Slope Tracking", confidence=0.9, depth_md=100.0,
            severity="Medium", recommendation="Investigar",
            apparent_velocity_ms=float("nan"), flow_direction="undetermined",
            discrimination="none",
        )
        event = _result_to_event(stub)
        assert isinstance(event, SlopeVelocityEvent)
        assert event.apparent_velocity_ms is None  # NaN → None
        assert event.flow_direction == "undetermined"
        assert event.discrimination == "none"

    def test_eventos_sem_campo_cinematico_nao_recebem_flow(self):
        # Regras térmicas não são FlowEvent: campos cinemáticos ausentes.
        engine = InferenceEngine()
        dts, das, fs = _das_hydraulic_case()
        events = engine.infer(dts, das, sampling_rate_hz=fs,
                              apply_band_filter=False)
        jt = next(e for e in events if e.event_type == "joule_thomson")
        assert type(jt) is not FlowEvent
        assert not hasattr(jt, "apparent_velocity_ms")


class TestQualityFlagsIEJ03:
    """IE:J-03: validação de entrada, sanitização e quality_flags."""

    def test_dados_limpos_zero_invalidos(self, generator):
        signature = generator.generate_joule_thomson()
        engine = InferenceEngine()
        engine.infer(signature["dts"], signature["das"], sampling_rate_hz=1000.0)
        assert engine.quality_flags["canais_invalidos"] == 0
        assert set(engine.quality_flags) == {"canais_invalidos", "canais_mortos"}

    def test_canal_com_nan_contabilizado(self, generator):
        signature = generator.generate_joule_thomson()
        dts = np.array(signature["dts"], dtype=np.float64)
        dts[:, 10] = np.nan
        engine = InferenceEngine()
        events = engine.infer(dts, signature["das"], sampling_rate_hz=1000.0)
        assert isinstance(events, list)  # não quebra com NaN sanitizado
        assert engine.quality_flags["canais_invalidos"] == 1

    def test_inf_sanitizado_para_nan(self, generator):
        signature = generator.generate_joule_thomson()
        dts = np.array(signature["dts"], dtype=np.float64)
        dts[:, 5] = np.inf
        das = np.array(signature["das"], dtype=np.float64)
        das[:, 7] = -np.inf
        engine = InferenceEngine()
        events = engine.infer(dts, das, sampling_rate_hz=1000.0)
        assert isinstance(events, list)
        assert engine.quality_flags["canais_invalidos"] == 2

    def test_canal_morto_constante(self, generator):
        signature = generator.generate_joule_thomson()
        dts = np.array(signature["dts"], dtype=np.float64)
        dts[:, 20] = 60.0  # canal constante (variância nula)
        engine = InferenceEngine()
        engine.infer(dts, signature["das"], sampling_rate_hz=1000.0)
        assert engine.quality_flags["canais_mortos"] >= 1


class TestDecoupleWrapperCL03:
    """CL-03 (lado Python): wrapper decouple_strain_temperature."""

    @staticmethod
    def _campo_acoplado(n_t=120, n_z=40, coeficiente=-2800.0, seed=1):
        rng = np.random.default_rng(seed)
        base = 20.0 + 8.0 * np.sin(2.0 * np.pi * np.arange(n_t) / n_t)
        T = base[:, None] + rng.normal(0.0, 0.02, (n_t, n_z))
        sinal = np.zeros((n_t, n_z))
        sinal[60:70, 20:25] = 500.0
        dtemp = T - T[0, :]
        strain = sinal + coeficiente * dtemp + rng.normal(0.0, 2.0, (n_t, n_z))
        return strain, T, sinal

    def test_wrapper_contrato_cpp(self):
        strain, T, sinal = self._campo_acoplado()
        engine = InferenceEngine()
        out = engine.decouple_strain_temperature(strain, T, 24, 12, True)
        assert set(out) == {"decoupled", "coefficient_map",
                            "global_coefficient", "constrained"}
        assert np.asarray(out["decoupled"]).shape == strain.shape
        # O binding C++ devolve coefficient_map achatado; o wrapper reshapeia.
        assert np.asarray(out["coefficient_map"]).shape == strain.shape
        assert out["global_coefficient"] == pytest.approx(-2800.0, rel=0.05)
        cm = np.asarray(out["coefficient_map"])
        assert np.nanmedian(cm[5:, :]) == pytest.approx(-2800.0, rel=0.10)
        assert np.abs(np.asarray(out["decoupled"])[60:70, 20:25] - 500.0).max() < 60.0

    def test_fallback_consistente_com_cpp(self):
        strain, T, _ = self._campo_acoplado()
        engine = InferenceEngine()
        out_cpp = engine.decouple_strain_temperature(strain, T, 24, 12, True)
        out_fb = _decouple_fallback(strain, T, 24, 12, True)
        assert set(out_fb) == set(out_cpp)
        assert np.asarray(out_fb["decoupled"]).shape == strain.shape
        assert np.asarray(out_fb["coefficient_map"]).shape == strain.shape
        assert out_fb["global_coefficient"] == pytest.approx(-2800.0, rel=0.10)
        assert out_fb["global_coefficient"] == pytest.approx(
            out_cpp["global_coefficient"], rel=0.10)
        corr = np.corrcoef(np.asarray(out_cpp["decoupled"]).ravel(),
                           np.asarray(out_fb["decoupled"]).ravel())[0, 1]
        assert corr > 0.99

    def test_fallback_restricao_cs(self):
        rng = np.random.default_rng(2)
        n_t, n_z = 120, 40
        base = 20.0 + 8.0 * np.sin(2.0 * np.pi * np.arange(n_t) / n_t)
        T = base[:, None] + rng.normal(0.0, 0.02, (n_t, n_z))
        dtemp = T - T[0, :]
        strain = 500.0 * dtemp + rng.normal(0.0, 2.0, (n_t, n_z))  # C > 0 espúrio
        out = _decouple_fallback(strain, T, 24, 12, True)
        assert out["constrained"] is True
        assert np.asarray(out["coefficient_map"]).max() <= 1e-6

    def test_janela_invalida_rejeitada(self):
        strain, T, _ = self._campo_acoplado()
        engine = InferenceEngine()
        with pytest.raises(ValueError, match=">= 8"):
            engine.decouple_strain_temperature(strain, T, 4, 12)

    def test_shapes_incompativeis_rejeitados(self):
        strain, T, _ = self._campo_acoplado()
        engine = InferenceEngine()
        with pytest.raises(ValueError, match="same shape"):
            engine.decouple_strain_temperature(strain, T[:, :30])
