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
                 recommendation: Optional[str] = None):
        super().__init__(identifier=identifier, name=name)
        self.event_type = event_type
        self.timestamp = timestamp
        self.depth_md = depth_md
        self.confidence = confidence
        self.severity = severity
        self.recommendation = recommendation
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
    """Evento de fluxo / Flow event."""

    _type = ALAKORO.FlowEvent

    def __init__(self, flow_rate_ms: Optional[float] = None, **kwargs):
        kwargs.setdefault("event_type", "VelocityEstimate")
        kwargs.setdefault("name", "Flow Velocity Estimate")
        super().__init__(**kwargs)
        self.flow_rate_ms = flow_rate_ms

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.flow_rate_ms is not None:
            graph.add((self.uri, ALAKORO.hasFlowRateMs, Literal(self.flow_rate_ms, datatype=XSD.float)))


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
                 abertura_ue: Optional[float] = None, **kwargs):
        kwargs.setdefault("event_type", "CrackPropagation")
        kwargs.setdefault("name", "Propagação de Fissura")
        super().__init__(**kwargs)
        self.posicao_fissura_m = posicao_fissura_m
        self.abertura_ue = abertura_ue

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.posicao_fissura_m is not None:
            graph.add((self.uri, ALAKORO.hasPosicaoFissuraM,
                       Literal(self.posicao_fissura_m, datatype=XSD.float)))
        if self.abertura_ue is not None:
            graph.add((self.uri, ALAKORO.hasAberturaUe, Literal(self.abertura_ue, datatype=XSD.float)))


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
