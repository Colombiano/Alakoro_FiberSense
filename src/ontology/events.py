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
