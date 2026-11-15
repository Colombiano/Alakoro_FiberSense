"""
Alakoro FiberSense — Classes de Eventos
Event Classes

Eventos semânticos alinhados ao JSON Schema v1.1.0.
"""

from rdflib import Graph, Literal, RDF, RDFS, XSD
from datetime import datetime
from typing import Optional
from .core import AlakoroEntity, ALAKORO
from .sensing import Measurement


class Event(AlakoroEntity):
    """Evento detectado / Detected event."""

    _type = ALAKORO.Event

    def __init__(self, identifier: Optional[str] = None, name: Optional[str] = None,
                 event_type: Optional[str] = None,
                 timestamp: Optional[datetime] = None,
                 depth_md: Optional[float] = None,
                 confidence: Optional[float] = None,
                 severity: Optional[str] = None,
                 recommendation: Optional[str] = None,
                 correlation_id: Optional[str] = None):
        super().__init__(identifier=identifier, name=name)
        self.event_type = event_type
        self.timestamp = timestamp
        self.depth_md = depth_md
        self.confidence = confidence
        self.severity = severity
        self.recommendation = recommendation
        self.correlation_id = correlation_id
        self.measurements: list[Measurement] = []

    def add_measurement(self, measurement: Measurement):
        self.measurements.append(measurement)

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.event_type:
            graph.add((self.uri, ALAKORO.hasEventType, Literal(self.event_type)))
        if self.timestamp:
            graph.add((self.uri, ALAKORO.hasTimestamp, Literal(self.timestamp.isoformat(), datatype=XSD.dateTime)))
        if self.depth_md is not None:
            graph.add((self.uri, ALAKORO.hasDepthMD, Literal(self.depth_md, datatype=XSD.float)))
        if self.confidence is not None:
            graph.add((self.uri, ALAKORO.hasConfidence, Literal(self.confidence, datatype=XSD.float)))
        if self.severity:
            graph.add((self.uri, ALAKORO.hasSeverity, Literal(self.severity)))
        if self.recommendation:
            graph.add((self.uri, ALAKORO.hasRecommendation, Literal(self.recommendation)))
        if self.correlation_id:
            graph.add((self.uri, ALAKORO.hasCorrelationId, Literal(self.correlation_id)))
        for measurement in self.measurements:
            measurement._attach(graph)
            graph.add((self.uri, ALAKORO.detectedIn, measurement.uri))


class JouleThomsonEvent(Event):
    """Evento de dipolo térmico Joule-Thomson."""

    _type = ALAKORO.JouleThomsonEvent

    def __init__(self, interface_depth: Optional[float] = None, **kwargs):
        kwargs.setdefault("event_type", "JouleThomsonSignature")
        kwargs.setdefault("name", "Joule-Thomson Thermal Dipole")
        super().__init__(**kwargs)
        self.interface_depth = interface_depth

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.interface_depth is not None:
            graph.add((self.uri, ALAKORO.hasInterfaceDepth, Literal(self.interface_depth, datatype=XSD.float)))


class LeakEvent(Event):
    """Evento de vazamento / Leak event."""

    _type = ALAKORO.LeakEvent

    def __init__(self, leak_depth: Optional[float] = None, **kwargs):
        kwargs.setdefault("event_type", "LeakDetected")
        kwargs.setdefault("name", "Leak Detection")
        super().__init__(**kwargs)
        self.leak_depth = leak_depth

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.leak_depth is not None:
            graph.add((self.uri, ALAKORO.hasLeakDepth, Literal(self.leak_depth, datatype=XSD.float)))


class FlowEvent(Event):
    """Evento de fluxo / Flow event.

    Campos cinemáticos (CL-04): apparent_velocity_ms, flow_direction e
    discrimination vêm do InferenceResult do motor C++ (regras SlopeVelocity
    e FlowDiscrimination). ``apparent_velocity_ms`` usa a convenção de sinal
    do motor: + = descendente (z crescente com a profundidade MD); None =
    indeterminada (NaN no resultado C++). ``discrimination`` é a
    classificação ternária da FlowDiscriminationRule
    ("hydraulic" | "thermal" | "inconclusive"); "none" = não aplicável.

    Kinematic fields (CL-04): apparent_velocity_ms, flow_direction and
    discrimination come from the C++ InferenceResult. Sign convention:
    + = descending; None = undetermined (NaN in the C++ result).
    """

    _type = ALAKORO.FlowEvent

    def __init__(self, flow_rate_ms: Optional[float] = None,
                 apparent_velocity_ms: Optional[float] = None,
                 flow_direction: Optional[str] = None,
                 discrimination: Optional[str] = None,
                 **kwargs):
        kwargs.setdefault("event_type", "VelocityEstimate")
        kwargs.setdefault("name", "Flow Velocity Estimate")
        super().__init__(**kwargs)
        self.flow_rate_ms = flow_rate_ms
        self.apparent_velocity_ms = apparent_velocity_ms
        self.flow_direction = flow_direction
        self.discrimination = discrimination

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.flow_rate_ms is not None:
            graph.add((self.uri, ALAKORO.hasFlowRateMs, Literal(self.flow_rate_ms, datatype=XSD.float)))
        if self.apparent_velocity_ms is not None:
            graph.add((self.uri, ALAKORO.hasApparentVelocityMs,
                       Literal(self.apparent_velocity_ms, datatype=XSD.float)))
        if self.flow_direction:
            graph.add((self.uri, ALAKORO.hasFlowDirection, Literal(self.flow_direction)))
        if self.discrimination:
            graph.add((self.uri, ALAKORO.hasDiscrimination, Literal(self.discrimination)))


class WarmBackEvent(Event):
    """Evento de recuperação térmica / Warm-back event."""

    _type = ALAKORO.WarmBackEvent

    def __init__(self, injection_depths: Optional[list] = None, **kwargs):
        kwargs.setdefault("event_type", "WarmBackDetected")
        kwargs.setdefault("name", "Warm-Back Recovery")
        super().__init__(**kwargs)
        self.injection_depths = injection_depths or []

    def _attach(self, graph: Graph):
        super()._attach(graph)
        for depth in self.injection_depths:
            graph.add((self.uri, ALAKORO.hasInjectionDepth, Literal(depth, datatype=XSD.float)))


class PropagacaoFissuraEvento(Event):
    """Evento de propagação/abertura de fissura (DSS) / Crack propagation event (DSS)."""

    _type = ALAKORO.PropagacaoFissuraEvento

    def __init__(self, posicao_fissura_m: Optional[float] = None,
                 abertura_ue: Optional[float] = None,
                 taxa_ue_dia: Optional[float] = None, **kwargs):
        kwargs.setdefault("event_type", "CrackPropagation")
        kwargs.setdefault("name", "Propagação de Fissura")
        super().__init__(**kwargs)
        self.posicao_fissura_m = posicao_fissura_m
        self.abertura_ue = abertura_ue
        self.taxa_ue_dia = taxa_ue_dia

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.posicao_fissura_m is not None:
            graph.add((self.uri, ALAKORO.hasPosicaoFissuraM,
                       Literal(self.posicao_fissura_m, datatype=XSD.float)))
        if self.abertura_ue is not None:
            graph.add((self.uri, ALAKORO.hasAberturaUe, Literal(self.abertura_ue, datatype=XSD.float)))
        if self.taxa_ue_dia is not None:
            graph.add((self.uri, ALAKORO.hasTaxaUeDia,
                       Literal(self.taxa_ue_dia, datatype=XSD.float)))


class AberturaFissuraTermicaEvento(Event):
    """Evento de abertura/fecho térmico de fissura / Thermally driven crack opening event."""

    _type = ALAKORO.AberturaFissuraTermicaEvento

    def __init__(self, posicao_m: Optional[float] = None,
                 variacao_termica_c: Optional[float] = None, **kwargs):
        kwargs.setdefault("event_type", "ThermalCrackOpening")
        kwargs.setdefault("name", "Abertura Térmica de Fissura")
        super().__init__(**kwargs)
        self.posicao_m = posicao_m
        self.variacao_termica_c = variacao_termica_c

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.posicao_m is not None:
            graph.add((self.uri, ALAKORO.hasPosicaoM, Literal(self.posicao_m, datatype=XSD.float)))
        if self.variacao_termica_c is not None:
            graph.add((self.uri, ALAKORO.hasVariacaoTermicaC,
                       Literal(self.variacao_termica_c, datatype=XSD.float)))


class EventoAcusticoFissura(Event):
    """Evento acústico de fissura (DAS) / Crack acoustic emission event (DAS)."""

    _type = ALAKORO.EventoAcusticoFissura

    def __init__(self, posicao_m: Optional[float] = None, energia: Optional[float] = None,
                 taxa_eventos_h: Optional[float] = None, **kwargs):
        kwargs.setdefault("event_type", "CrackAcousticEmission")
        kwargs.setdefault("name", "Emissão Acústica de Fissura")
        super().__init__(**kwargs)
        self.posicao_m = posicao_m
        self.energia = energia
        self.taxa_eventos_h = taxa_eventos_h

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.posicao_m is not None:
            graph.add((self.uri, ALAKORO.hasPosicaoM, Literal(self.posicao_m, datatype=XSD.float)))
        if self.energia is not None:
            graph.add((self.uri, ALAKORO.hasEnergia, Literal(self.energia, datatype=XSD.float)))
        if self.taxa_eventos_h is not None:
            graph.add((self.uri, ALAKORO.hasTaxaEventosH, Literal(self.taxa_eventos_h, datatype=XSD.float)))


class AnomaliaTermicaEvento(Event):
    """Evento de anomalia térmica local (DTS) / Local thermal anomaly event (DTS)."""

    _type = ALAKORO.AnomaliaTermicaEvento

    def __init__(self, posicao_m: Optional[float] = None,
                 offset_k: Optional[float] = None, **kwargs):
        kwargs.setdefault("event_type", "ThermalAnomaly")
        kwargs.setdefault("name", "Anomalia Térmica")
        super().__init__(**kwargs)
        self.posicao_m = posicao_m
        self.offset_k = offset_k

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.posicao_m is not None:
            graph.add((self.uri, ALAKORO.hasPosicaoM, Literal(self.posicao_m, datatype=XSD.float)))
        if self.offset_k is not None:
            graph.add((self.uri, ALAKORO.hasOffsetK, Literal(self.offset_k, datatype=XSD.float)))


class DanoModalEvento(Event):
    """Evento de dano modal em torres de alvenaria / Modal damage event in masonry towers.

    O dano estrutural reduz a frequência fundamental f1 (tipicamente 0,5–3%)
    e alarga o espectro (Hubbard 2021); a variação relativa monitorada
    alimenta severidade e confiança.
    """

    _type = ALAKORO.DanoModalEvento

    def __init__(self, frequencia_hz: Optional[float] = None,
                 variacao_relativa_pct: Optional[float] = None, **kwargs):
        kwargs.setdefault("event_type", "ModalDamage")
        kwargs.setdefault("name", "Dano Modal")
        super().__init__(**kwargs)
        self.frequencia_hz = frequencia_hz
        self.variacao_relativa_pct = variacao_relativa_pct

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.frequencia_hz is not None:
            graph.add((self.uri, ALAKORO.hasFrequenciaHz,
                       Literal(self.frequencia_hz, datatype=XSD.float)))
        if self.variacao_relativa_pct is not None:
            graph.add((self.uri, ALAKORO.hasVariacaoRelativaPct,
                       Literal(self.variacao_relativa_pct, datatype=XSD.float)))


class RecalqueEvento(Event):
    """Evento de recalque diferencial / Differential settlement event."""

    _type = ALAKORO.RecalqueEvento

    def __init__(self, taxa_ue_dia: Optional[float] = None,
                 posicao_m: Optional[float] = None, **kwargs):
        kwargs.setdefault("event_type", "DifferentialSettlement")
        kwargs.setdefault("name", "Recalque Diferencial")
        super().__init__(**kwargs)
        self.taxa_ue_dia = taxa_ue_dia
        self.posicao_m = posicao_m

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.taxa_ue_dia is not None:
            graph.add((self.uri, ALAKORO.hasTaxaUeDia, Literal(self.taxa_ue_dia, datatype=XSD.float)))
        if self.posicao_m is not None:
            graph.add((self.uri, ALAKORO.hasPosicaoM, Literal(self.posicao_m, datatype=XSD.float)))


# =============================================================================
# Onda 2 (auditoria técnica) — Especialização ontológica dos eventos de poço
# Wave 2 — Ontological specialization of well events (CL-12, IE:A-02)
# =============================================================================

class SlopeVelocityEvent(FlowEvent):
    """Evento de velocidade por rastreamento de inclinação / Slope velocity event.

    Subclasse de FlowEvent (CL-04): acrescenta a velocidade aparente COM SINAL
    estimada por correlação cruzada das envoltórias (ou rastreio de frente),
    a direção do fluxo e a discriminação ternária propagada pelo motor.

    Subclass of FlowEvent (CL-04): adds the signed apparent velocity from
    envelope cross-correlation (or front tracking), the flow direction and
    the ternary discrimination propagated by the engine.
    """

    _type = ALAKORO.SlopeVelocityEvent

    def __init__(self, **kwargs):
        kwargs.setdefault("event_type", "slope_velocity")
        kwargs.setdefault("name", "Slope Tracking (Velocity)")
        super().__init__(**kwargs)


class GasLiftValveEvent(Event):
    """Evento de válvula de gás lift / Gas lift valve event.

    Evento de domínio composto (audit IE:E-03): consolida o inventário de
    válvulas (valve_depths_m), o índice da válvula com fole rompido
    (rupture_valve_idx) e a banda de chatter característica
    (chatter_band_hz). Não é emitido diretamente pelo motor C++ — é
    instanciado por consumidores de domínio que agregam os resultados
    "glv_bellow_rupture" e "valve_chatter".

    Domain-level composite event (audit IE:E-03): consolidates the valve
    inventory (valve_depths_m), the ruptured-valve index (rupture_valve_idx)
    and the characteristic chatter band (chatter_band_hz). Not emitted
    directly by the C++ engine — instantiated by domain consumers that
    aggregate "glv_bellow_rupture" and "valve_chatter" results.
    """

    _type = ALAKORO.GasLiftValveEvent

    def __init__(self, valve_depths_m: Optional[list] = None,
                 rupture_valve_idx: Optional[int] = None,
                 chatter_band_hz: Optional[float] = None, **kwargs):
        kwargs.setdefault("event_type", "gas_lift_valve")
        kwargs.setdefault("name", "Gas Lift Valve")
        super().__init__(**kwargs)
        self.valve_depths_m = valve_depths_m or []
        self.rupture_valve_idx = rupture_valve_idx
        self.chatter_band_hz = chatter_band_hz

    def _attach(self, graph: Graph):
        super()._attach(graph)
        for depth in self.valve_depths_m:
            graph.add((self.uri, ALAKORO.hasValveDepthsM,
                       Literal(depth, datatype=XSD.float)))
        if self.rupture_valve_idx is not None:
            graph.add((self.uri, ALAKORO.hasRuptureValveIdx,
                       Literal(self.rupture_valve_idx, datatype=XSD.integer)))
        if self.chatter_band_hz is not None:
            graph.add((self.uri, ALAKORO.hasChatterBandHz,
                       Literal(self.chatter_band_hz, datatype=XSD.float)))


class GLVBellowRuptureEvent(Event):
    """Evento de fole rompido de válvula de gás lift / GLV bellow rupture event."""

    _type = ALAKORO.GLVBellowRuptureEvent

    def __init__(self, rupture_valve_idx: Optional[int] = None, **kwargs):
        kwargs.setdefault("event_type", "glv_bellow_rupture")
        kwargs.setdefault("name", "Gas Lift Valve Bellow Rupture")
        super().__init__(**kwargs)
        self.rupture_valve_idx = rupture_valve_idx

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.rupture_valve_idx is not None:
            graph.add((self.uri, ALAKORO.hasRuptureValveIdx,
                       Literal(self.rupture_valve_idx, datatype=XSD.integer)))


class ValveChatterEvent(Event):
    """Evento de chatter/multipointing de válvula / Valve chatter event."""

    _type = ALAKORO.ValveChatterEvent

    def __init__(self, chatter_band_hz: Optional[float] = None, **kwargs):
        kwargs.setdefault("event_type", "valve_chatter")
        kwargs.setdefault("name", "Valve Chatter/Multipointing")
        super().__init__(**kwargs)
        self.chatter_band_hz = chatter_band_hz

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.chatter_band_hz is not None:
            graph.add((self.uri, ALAKORO.hasChatterBandHz,
                       Literal(self.chatter_band_hz, datatype=XSD.float)))


class FracScreenoutEvent(Event):
    """Evento de embuchamento de fratura (screen-out) / Fracture screen-out event."""

    _type = ALAKORO.FracScreenoutEvent

    def __init__(self, **kwargs):
        kwargs.setdefault("event_type", "frac_screenout")
        kwargs.setdefault("name", "Fracture Screen-out")
        super().__init__(**kwargs)


class FracProppantDistributionEvent(Event):
    """Evento de distribuição de propante / Proppant distribution event."""

    _type = ALAKORO.FracProppantDistributionEvent

    def __init__(self, **kwargs):
        kwargs.setdefault("event_type", "frac_proppant_distribution")
        kwargs.setdefault("name", "Proppant Distribution")
        super().__init__(**kwargs)


class FracHeightGrowthEvent(Event):
    """Evento de crescimento de altura de fratura / Fracture height growth event."""

    _type = ALAKORO.FracHeightGrowthEvent

    def __init__(self, frac_height_m: Optional[float] = None, **kwargs):
        kwargs.setdefault("event_type", "frac_height_growth")
        kwargs.setdefault("name", "Fracture Height Growth")
        super().__init__(**kwargs)
        self.frac_height_m = frac_height_m

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.frac_height_m is not None:
            graph.add((self.uri, ALAKORO.hasFracHeightM,
                       Literal(self.frac_height_m, datatype=XSD.float)))


class PerforationEffectivenessEvent(Event):
    """Evento de efetividade de canhoneio / Perforation effectiveness event."""

    _type = ALAKORO.PerforationEffectivenessEvent

    def __init__(self, **kwargs):
        kwargs.setdefault("event_type", "perforation_effectiveness")
        kwargs.setdefault("name", "Perforation Effectiveness")
        super().__init__(**kwargs)


class CementBondEvaluationEvent(Event):
    """Evento de avaliação de cimentação (CBL/VDL) / Cement bond evaluation event."""

    _type = ALAKORO.CementBondEvaluationEvent

    def __init__(self, **kwargs):
        kwargs.setdefault("event_type", "cement_bond_evaluation")
        kwargs.setdefault("name", "Cement Bond Evaluation (CBL/VDL)")
        super().__init__(**kwargs)


class ReCementingAssessmentEvent(Event):
    """Evento de avaliação de recimentação / Re-cementing assessment event."""

    _type = ALAKORO.ReCementingAssessmentEvent

    def __init__(self, **kwargs):
        kwargs.setdefault("event_type", "re_cementing_assessment")
        kwargs.setdefault("name", "Re-Cementing Assessment")
        super().__init__(**kwargs)


class CrossflowZonalEvent(Event):
    """Evento de fluxo cruzado zonal / Zonal crossflow event.

    ``affected_depth_range_m`` é a lista [topo, fundo] (m MD) do intervalo
    com comunicação entre zonas. ``channel_count`` conta os canais térmicos
    alternados (picos positivos + vales negativos) que sustentam o evento.

    ``affected_depth_range_m`` is the [top, bottom] list (m MD) of the
    crossflowing interval. ``channel_count`` counts the alternating thermal
    channels supporting the event.
    """

    _type = ALAKORO.CrossflowZonalEvent

    def __init__(self, affected_depth_range_m: Optional[list] = None,
                 channel_count: Optional[int] = None, **kwargs):
        kwargs.setdefault("event_type", "crossflow_zonal")
        kwargs.setdefault("name", "Zonal Crossflow")
        super().__init__(**kwargs)
        self.affected_depth_range_m = affected_depth_range_m or []
        self.channel_count = channel_count

    def _attach(self, graph: Graph):
        super()._attach(graph)
        for depth in self.affected_depth_range_m:
            graph.add((self.uri, ALAKORO.hasAffectedDepthRangeM,
                       Literal(depth, datatype=XSD.float)))
        if self.channel_count is not None:
            graph.add((self.uri, ALAKORO.hasChannelCount,
                       Literal(self.channel_count, datatype=XSD.integer)))


class CementChannelingEvent(Event):
    """Evento de canalização de cimento / Cement channeling event.

    Mesma modelagem de intervalo de CrossflowZonalEvent: faixa [topo, fundo]
    afetada e número de canais estreitos no perfil térmico.

    Same interval modelling as CrossflowZonalEvent: [top, bottom] affected
    range and number of narrow channels in the thermal profile.
    """

    _type = ALAKORO.CementChannelingEvent

    def __init__(self, affected_depth_range_m: Optional[list] = None,
                 channel_count: Optional[int] = None, **kwargs):
        kwargs.setdefault("event_type", "cement_channeling")
        kwargs.setdefault("name", "Cement Channeling")
        super().__init__(**kwargs)
        self.affected_depth_range_m = affected_depth_range_m or []
        self.channel_count = channel_count

    def _attach(self, graph: Graph):
        super()._attach(graph)
        for depth in self.affected_depth_range_m:
            graph.add((self.uri, ALAKORO.hasAffectedDepthRangeM,
                       Literal(depth, datatype=XSD.float)))
        if self.channel_count is not None:
            graph.add((self.uri, ALAKORO.hasChannelCount,
                       Literal(self.channel_count, datatype=XSD.integer)))
