"""
Alakoro FiberSense — Classes de Domínio de Petróleo
Petroleum Domain Classes

Well, Wellbore, Completion, FiberOpticCable.
"""

from rdflib import Graph, Literal, RDF, RDFS, XSD
from typing import Optional, List
from .core import AlakoroEntity, ALAKORO


class Well(AlakoroEntity):
    """Poço de petróleo / Oil or gas well."""

    _type = ALAKORO.Well

    def __init__(self, identifier: Optional[str] = None, name: Optional[str] = None,
                 operator: Optional[str] = None, field: Optional[str] = None,
                 country: Optional[str] = None, status: Optional[str] = None,
                 surface_latitude: Optional[float] = None,
                 surface_longitude: Optional[float] = None):
        super().__init__(identifier=identifier, name=name)
        self.operator = operator
        self.field = field
        self.country = country
        self.status = status
        self.surface_latitude = surface_latitude
        self.surface_longitude = surface_longitude
        self.wellbores: List["Wellbore"] = []

    def add_wellbore(self, wellbore: "Wellbore"):
        self.wellbores.append(wellbore)
        wellbore.well = self

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.operator:
            graph.add((self.uri, ALAKORO.hasOperator, Literal(self.operator)))
        if self.field:
            graph.add((self.uri, ALAKORO.hasField, Literal(self.field)))
        if self.country:
            graph.add((self.uri, ALAKORO.hasCountry, Literal(self.country)))
        if self.status:
            graph.add((self.uri, ALAKORO.hasStatus, Literal(self.status)))
        if self.surface_latitude is not None:
            graph.add((self.uri, ALAKORO.hasSurfaceLatitude, Literal(self.surface_latitude, datatype=XSD.float)))
        if self.surface_longitude is not None:
            graph.add((self.uri, ALAKORO.hasSurfaceLongitude, Literal(self.surface_longitude, datatype=XSD.float)))
        for wellbore in self.wellbores:
            wellbore._attach(graph)
            graph.add((self.uri, ALAKORO.hasWellbore, wellbore.uri))


class Wellbore(AlakoroEntity):
    """Poço perfurado / Wellbore."""

    _type = ALAKORO.Wellbore

    def __init__(self, identifier: Optional[str] = None, name: Optional[str] = None,
                 measured_depth_top: Optional[float] = None,
                 measured_depth_bottom: Optional[float] = None,
                 true_vertical_depth: Optional[float] = None,
                 status: Optional[str] = None):
        super().__init__(identifier=identifier, name=name)
        self.measured_depth_top = measured_depth_top
        self.measured_depth_bottom = measured_depth_bottom
        self.true_vertical_depth = true_vertical_depth
        self.status = status
        self.well: Optional[Well] = None
        self.completions: List["Completion"] = []
        self.cables: List["FiberOpticCable"] = []

    def add_completion(self, completion: "Completion"):
        self.completions.append(completion)
        completion.wellbore = self

    def add_cable(self, cable: "FiberOpticCable"):
        self.cables.append(cable)
        cable.wellbore = self

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.measured_depth_top is not None:
            graph.add((self.uri, ALAKORO.hasMeasuredDepthTop, Literal(self.measured_depth_top, datatype=XSD.float)))
        if self.measured_depth_bottom is not None:
            graph.add((self.uri, ALAKORO.hasMeasuredDepthBottom, Literal(self.measured_depth_bottom, datatype=XSD.float)))
        if self.true_vertical_depth is not None:
            graph.add((self.uri, ALAKORO.hasTrueVerticalDepth, Literal(self.true_vertical_depth, datatype=XSD.float)))
        if self.status:
            graph.add((self.uri, ALAKORO.hasStatus, Literal(self.status)))
        if self.well:
            graph.add((self.uri, ALAKORO.isWellboreOf, self.well.uri))
        for completion in self.completions:
            completion._attach(graph)
            graph.add((self.uri, ALAKORO.hasCompletion, completion.uri))
        for cable in self.cables:
            cable._attach(graph)
            graph.add((self.uri, ALAKORO.hasFiberOpticCable, cable.uri))


class Completion(AlakoroEntity):
    """Completão do poço / Well completion."""

    _type = ALAKORO.Completion

    def __init__(self, identifier: Optional[str] = None, name: Optional[str] = None,
                 completion_type: Optional[str] = None):
        super().__init__(identifier=identifier, name=name)
        self.completion_type = completion_type
        self.wellbore: Optional[Wellbore] = None

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.completion_type:
            graph.add((self.uri, ALAKORO.hasCompletionType, Literal(self.completion_type)))
        if self.wellbore:
            graph.add((self.uri, ALAKORO.isCompletionOf, self.wellbore.uri))


class FiberOpticCable(AlakoroEntity):
    """Cabo de fibra óptica / Fiber optic cable."""

    _type = ALAKORO.FiberOpticCable

    def __init__(self, identifier: Optional[str] = None, name: Optional[str] = None,
                 depth_top: Optional[float] = None, depth_bottom: Optional[float] = None,
                 n_channels: Optional[int] = None):
        super().__init__(identifier=identifier, name=name)
        self.depth_top = depth_top
        self.depth_bottom = depth_bottom
        self.n_channels = n_channels
        self.wellbore: Optional[Wellbore] = None

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.depth_top is not None:
            graph.add((self.uri, ALAKORO.hasDepthTop, Literal(self.depth_top, datatype=XSD.float)))
        if self.depth_bottom is not None:
            graph.add((self.uri, ALAKORO.hasDepthBottom, Literal(self.depth_bottom, datatype=XSD.float)))
        if self.n_channels is not None:
            graph.add((self.uri, ALAKORO.hasNumberOfChannels, Literal(self.n_channels, datatype=XSD.integer)))
        if self.wellbore:
            graph.add((self.uri, ALAKORO.isCableOf, self.wellbore.uri))
