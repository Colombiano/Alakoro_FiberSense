"""
Alakoro FiberSense — Testes de Ontologia da Onda 2
Wave-2 Ontology Tests

Especialização ontológica dos 15 eventos canônicos (CL-12, IE:A-02/IE:E-03/
IE:E-04), FlowEvent estendida com campos cinemáticos (CL-04), metadados
Brillouin em Measurement (SP:B-05) e WellboreReferenceMeasurements (IE:D-05).
"""

import pytest

from alakoro.ontology import (
    OntologyModel,
    Well,
    Wellbore,
    DTSMeasurement,
    Event,
    FlowEvent,
    SlopeVelocityEvent,
    GasLiftValveEvent,
    GLVBellowRuptureEvent,
    ValveChatterEvent,
    FracScreenoutEvent,
    FracProppantDistributionEvent,
    FracHeightGrowthEvent,
    PerforationEffectivenessEvent,
    CementBondEvaluationEvent,
    ReCementingAssessmentEvent,
    CrossflowZonalEvent,
    CementChannelingEvent,
    WellboreReferenceMeasurements,
)


@pytest.fixture
def model():
    return OntologyModel()


# =============================================================================
# CL-12 — Especialização ontológica dos eventos de poço
# =============================================================================

class TestEventClassMap:
    """Os 15 códigos canônicos têm classe dedicada na ontologia."""

    def test_todos_os_codigos_canonicos_mapeados(self):
        from alakoro.ontology.inference_engine import _EVENT_CLASS_MAP

        expected = {
            "joule_thomson", "slope_velocity", "warm_back", "valve_chatter",
            "slugging_cycle", "leak_path", "glv_bellow_rupture",
            "perforation_effectiveness", "frac_screenout",
            "frac_proppant_distribution", "frac_height_growth",
            "cement_bond_evaluation", "re_cementing_assessment",
            "crossflow_zonal", "cement_channeling",
        }
        assert expected <= set(_EVENT_CLASS_MAP)

    def test_codigos_usam_classes_dedicadas(self):
        from alakoro.ontology.inference_engine import _EVENT_CLASS_MAP

        assert _EVENT_CLASS_MAP["slope_velocity"] is SlopeVelocityEvent
        assert _EVENT_CLASS_MAP["valve_chatter"] is ValveChatterEvent
        assert _EVENT_CLASS_MAP["glv_bellow_rupture"] is GLVBellowRuptureEvent
        assert _EVENT_CLASS_MAP["perforation_effectiveness"] is PerforationEffectivenessEvent
        assert _EVENT_CLASS_MAP["frac_screenout"] is FracScreenoutEvent
        assert _EVENT_CLASS_MAP["frac_proppant_distribution"] is FracProppantDistributionEvent
        assert _EVENT_CLASS_MAP["frac_height_growth"] is FracHeightGrowthEvent
        assert _EVENT_CLASS_MAP["cement_bond_evaluation"] is CementBondEvaluationEvent
        assert _EVENT_CLASS_MAP["re_cementing_assessment"] is ReCementingAssessmentEvent
        assert _EVENT_CLASS_MAP["crossflow_zonal"] is CrossflowZonalEvent
        assert _EVENT_CLASS_MAP["cement_channeling"] is CementChannelingEvent


class TestEventosEspecializados:
    """Cada classe nova instancia no padrão kwarg próprio + **kwargs e emite
    triplas próprias em Turtle/JSON-LD (padrão substring)."""

    def test_slope_velocity_event(self, model):
        event = SlopeVelocityEvent(
            apparent_velocity_ms=1.5, flow_direction="down",
            discrimination="hydraulic", confidence=0.8, depth_md=1000.0,
        )
        assert event.event_type == "slope_velocity"
        assert isinstance(event, FlowEvent)  # herda campos cinemáticos (CL-04)
        model.add(event)
        ttl = model.to_turtle()
        assert "SlopeVelocityEvent" in ttl
        assert "slope_velocity" in ttl
        assert "1.5" in ttl            # hasApparentVelocityMs
        assert "down" in ttl           # hasFlowDirection
        assert "hydraulic" in ttl      # hasDiscrimination

    def test_gas_lift_valve_event(self, model):
        event = GasLiftValveEvent(
            valve_depths_m=[950.0, 1400.0, 1850.0],
            rupture_valve_idx=1, chatter_band_hz=7.5,
            confidence=0.9, depth_md=1400.0,
        )
        assert event.event_type == "gas_lift_valve"
        model.add(event)
        ttl = model.to_turtle()
        assert "GasLiftValveEvent" in ttl
        assert "950.0" in ttl and "1850.0" in ttl   # hasValveDepthsM
        assert "1" in ttl                            # hasRuptureValveIdx
        assert "7.5" in ttl                          # hasChatterBandHz

    def test_glv_bellow_rupture_event(self, model):
        event = GLVBellowRuptureEvent(rupture_valve_idx=2, confidence=0.97,
                                      severity="Critical", depth_md=1850.0)
        assert event.event_type == "glv_bellow_rupture"
        model.add(event)
        ttl = model.to_turtle()
        assert "GLVBellowRuptureEvent" in ttl
        assert "glv_bellow_rupture" in ttl
        assert "2" in ttl  # hasRuptureValveIdx

    def test_valve_chatter_event(self, model):
        event = ValveChatterEvent(chatter_band_hz=12.0, confidence=0.7,
                                  depth_md=1400.0)
        assert event.event_type == "valve_chatter"
        model.add(event)
        ttl = model.to_turtle()
        assert "ValveChatterEvent" in ttl
        assert "valve_chatter" in ttl
        assert "12.0" in ttl  # hasChatterBandHz

    def test_frac_screenout_event(self, model):
        event = FracScreenoutEvent(confidence=0.85, depth_md=2539.0)
        assert event.event_type == "frac_screenout"
        model.add(event)
        ttl = model.to_turtle()
        assert "FracScreenoutEvent" in ttl
        assert "frac_screenout" in ttl

    def test_frac_proppant_distribution_event(self, model):
        event = FracProppantDistributionEvent(confidence=0.8, depth_md=1516.0)
        assert event.event_type == "frac_proppant_distribution"
        model.add(event)
        ttl = model.to_turtle()
        assert "FracProppantDistributionEvent" in ttl
        assert "frac_proppant_distribution" in ttl

    def test_frac_height_growth_event(self, model):
        event = FracHeightGrowthEvent(frac_height_m=87.0, confidence=0.75,
                                      depth_md=1521.0)
        assert event.event_type == "frac_height_growth"
        model.add(event)
        ttl = model.to_turtle()
        assert "FracHeightGrowthEvent" in ttl
        assert "frac_height_growth" in ttl
        assert "87.0" in ttl  # hasFracHeightM

    def test_perforation_effectiveness_event(self, model):
        event = PerforationEffectivenessEvent(confidence=0.66, depth_md=1530.0)
        assert event.event_type == "perforation_effectiveness"
        model.add(event)
        ttl = model.to_turtle()
        assert "PerforationEffectivenessEvent" in ttl
        assert "perforation_effectiveness" in ttl

    def test_cement_bond_evaluation_event(self, model):
        event = CementBondEvaluationEvent(confidence=0.4, depth_md=1500.0)
        assert event.event_type == "cement_bond_evaluation"
        model.add(event)
        ttl = model.to_turtle()
        assert "CementBondEvaluationEvent" in ttl
        assert "cement_bond_evaluation" in ttl

    def test_re_cementing_assessment_event(self, model):
        event = ReCementingAssessmentEvent(confidence=0.6, depth_md=914.0)
        assert event.event_type == "re_cementing_assessment"
        model.add(event)
        ttl = model.to_turtle()
        assert "ReCementingAssessmentEvent" in ttl
        assert "re_cementing_assessment" in ttl

    def test_crossflow_zonal_event(self, model):
        event = CrossflowZonalEvent(
            affected_depth_range_m=[1100.0, 1450.0], channel_count=6,
            confidence=0.9, depth_md=1275.0,
        )
        assert event.event_type == "crossflow_zonal"
        model.add(event)
        ttl = model.to_turtle()
        assert "CrossflowZonalEvent" in ttl
        assert "crossflow_zonal" in ttl
        assert "1100.0" in ttl and "1450.0" in ttl  # hasAffectedDepthRangeM
        assert "6" in ttl                            # hasChannelCount

    def test_cement_channeling_event(self, model):
        event = CementChannelingEvent(
            affected_depth_range_m=[900.0, 1150.0], channel_count=4,
            confidence=0.8, depth_md=1025.0,
        )
        assert event.event_type == "cement_channeling"
        model.add(event)
        ttl = model.to_turtle()
        assert "CementChannelingEvent" in ttl
        assert "cement_channeling" in ttl
        assert "900.0" in ttl and "1150.0" in ttl  # hasAffectedDepthRangeM
        assert "4" in ttl                           # hasChannelCount

    def test_jsonld_contem_classes_novas(self, model):
        model.add(SlopeVelocityEvent(apparent_velocity_ms=2.0,
                                     flow_direction="down"))
        model.add(CementChannelingEvent(affected_depth_range_m=[10.0, 20.0],
                                        channel_count=3))
        jld = model.to_jsonld()
        assert "SlopeVelocityEvent" in jld
        assert "CementChannelingEvent" in jld


class TestFlowEventEstendida:
    """CL-04: FlowEvent aceita campos cinemáticos opcionais."""

    def test_campos_cinematicos_padrao_none(self):
        event = FlowEvent(flow_rate_ms=0.8)
        assert event.flow_rate_ms == 0.8
        assert event.apparent_velocity_ms is None
        assert event.flow_direction is None
        assert event.discrimination is None

    def test_sem_campos_nao_emite_triplas(self, model):
        from alakoro.ontology.core import ALAKORO
        event = FlowEvent(flow_rate_ms=0.8)
        model.add(event)
        # As propriedades são declaradas no schema; a ausência é por-instância:
        # nenhuma tripla com o sujeito do evento.
        assert (event.uri, ALAKORO.hasApparentVelocityMs, None) not in model.graph
        assert (event.uri, ALAKORO.hasFlowDirection, None) not in model.graph
        assert (event.uri, ALAKORO.hasDiscrimination, None) not in model.graph
        assert (event.uri, ALAKORO.hasFlowRateMs, None) in model.graph

    def test_com_campos_emite_triplas(self, model):
        event = FlowEvent(apparent_velocity_ms=-1.25,
                          flow_direction="up",
                          discrimination="thermal")
        model.add(event)
        ttl = model.to_turtle()
        assert "hasApparentVelocityMs" in ttl
        assert "hasFlowDirection" in ttl
        assert "hasDiscrimination" in ttl
        assert "-1.25" in ttl
        assert "up" in ttl
        assert "thermal" in ttl


# =============================================================================
# SP:B-05 — Metadados Brillouin em Measurement (lado ontologia)
# =============================================================================

class TestMeasurementBrillouin:
    def test_campos_brillouin_em_turtle(self, model):
        dts = DTSMeasurement(
            name="DTS-Brillouin",
            brillouin_c11_mhz_per_ustrain=0.05,
            brillouin_c12_mhz_per_c=1.0,
            thermal_reference_modality="dts",
            dual_fiber_config=True,
        )
        model.add(dts)
        ttl = model.to_turtle()
        assert "hasBrillouinC11MhzPerUstrain" in ttl
        assert "hasBrillouinC12MhzPerC" in ttl
        assert "hasThermalReferenceModality" in ttl
        assert "hasDualFiberConfig" in ttl
        assert "0.05" in ttl
        assert "dts" in ttl
        assert "true" in ttl.lower()

    def test_campos_opcionais(self):
        dts = DTSMeasurement(name="DTS-default")
        assert dts.brillouin_c11_mhz_per_ustrain is None
        assert dts.brillouin_c12_mhz_per_c is None
        assert dts.thermal_reference_modality is None
        assert dts.dual_fiber_config is None


# =============================================================================
# IE:D-05 — WellboreReferenceMeasurements (lado ontologia)
# =============================================================================

class TestWellboreReferenceMeasurements:
    def test_add_gauge_com_e_sem_pressao(self):
        ref = WellboreReferenceMeasurements(name="Ref-Gauges")
        g1 = ref.add_gauge(1500.0, 85.5, pressure_bar=320.0)
        g2 = ref.add_gauge(2400.0, 97.0)
        assert len(ref.gauges) == 2
        assert g1 == {"depth_md": 1500.0, "temperature_c": 85.5,
                      "pressure_bar": 320.0}
        assert g2 == {"depth_md": 2400.0, "temperature_c": 97.0}
        assert "pressure_bar" not in g2

    def test_triplas_gauges_em_turtle(self, model):
        well = Well(name="Well-Ref")
        wellbore = Wellbore(name="WB-Ref", measured_depth_top=0.0,
                            measured_depth_bottom=3000.0)
        well.add_wellbore(wellbore)
        ref = WellboreReferenceMeasurements(name="Ref-Gauges", wellbore=wellbore)
        ref.add_gauge(1500.0, 85.5, pressure_bar=320.0)
        ref.add_gauge(2400.0, 97.0)
        model.add(ref)
        ttl = model.to_turtle()
        assert "WellboreReferenceMeasurements" in ttl
        assert "1500.0" in ttl and "2400.0" in ttl   # hasGaugeDepthMD
        assert "85.5" in ttl and "97.0" in ttl       # hasGaugeTemperatureC
        assert "320.0" in ttl                        # hasGaugePressureBar


# =============================================================================
# Registro no schema (_define_schema)
# =============================================================================

class TestRegistroSchema:
    def test_classes_eventos_registradas_no_schema(self, model):
        for cls in (
            SlopeVelocityEvent, GasLiftValveEvent, GLVBellowRuptureEvent,
            ValveChatterEvent, FracScreenoutEvent, FracProppantDistributionEvent,
            FracHeightGrowthEvent, PerforationEffectivenessEvent,
            CementBondEvaluationEvent, ReCementingAssessmentEvent,
            CrossflowZonalEvent, CementChannelingEvent,
        ):
            event = cls(name=f"inst-{cls.__name__}")
            model.add(event)
            ttl = model.to_turtle()
            assert cls.__name__ in ttl, f"{cls.__name__} não registrada no schema"

    def test_event_base_continua_funcionando(self, model):
        model.add(Event(event_type="custom", name="Evt"))
        assert "custom" in model.to_turtle()
