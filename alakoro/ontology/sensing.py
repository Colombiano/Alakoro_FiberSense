"""
Alakoro FiberSense — Classes de Sensing
Sensing Classes

Interrogator, DASMeasurement, DTSMeasurement, DSSMeasurement.
"""

from rdflib import Graph, Literal, RDF, RDFS, XSD
from datetime import datetime
from typing import Optional
from .core import AlakoroEntity, ALAKORO
from .petroleum import Wellbore, FiberOpticCable


class Interrogator(AlakoroEntity):
    """Interrogador de fibra óptica / Fiber optic interrogator."""

    _type = ALAKORO.Interrogator

    def __init__(self, identifier: Optional[str] = None, name: Optional[str] = None,
                 manufacturer: Optional[str] = None, model: Optional[str] = None,
                 max_channels: Optional[int] = None,
                 sampling_rate_hz: Optional[float] = None):
        super().__init__(identifier=identifier, name=name)
        self.manufacturer = manufacturer
        self.model = model
        self.max_channels = max_channels
        self.sampling_rate_hz = sampling_rate_hz

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.manufacturer:
            graph.add((self.uri, ALAKORO.hasManufacturer, Literal(self.manufacturer)))
        if self.model:
            graph.add((self.uri, ALAKORO.hasModel, Literal(self.model)))
        if self.max_channels is not None:
            graph.add((self.uri, ALAKORO.hasMaxChannels, Literal(self.max_channels, datatype=XSD.integer)))
        if self.sampling_rate_hz is not None:
            graph.add((self.uri, ALAKORO.hasSamplingRateHz, Literal(self.sampling_rate_hz, datatype=XSD.float)))


class Measurement(AlakoroEntity):
    """Medição DFOS base / Base DFOS measurement."""

    _type = ALAKORO.Measurement

    def __init__(self, identifier: Optional[str] = None, name: Optional[str] = None,
                 modality: Optional[str] = None,
                 start_time: Optional[datetime] = None,
                 end_time: Optional[datetime] = None,
                 sampling_rate_hz: Optional[float] = None,
                 spatial_resolution_m: Optional[float] = None,
                 gauge_length_m: Optional[float] = None,
                 n_channels: Optional[int] = None,
                 n_time_samples: Optional[int] = None,
                 brillouin_c11_mhz_per_ustrain: Optional[float] = None,
                 brillouin_c12_mhz_per_c: Optional[float] = None,
                 thermal_reference_modality: Optional[str] = None,
                 dual_fiber_config: Optional[bool] = None):
        super().__init__(identifier=identifier, name=name)
        self.modality = modality
        self.start_time = start_time
        self.end_time = end_time
        self.sampling_rate_hz = sampling_rate_hz
        self.spatial_resolution_m = spatial_resolution_m
        self.gauge_length_m = gauge_length_m
        self.n_channels = n_channels
        self.n_time_samples = n_time_samples
        # Metadados Brillouin / Brillouin metadata (SP:B-05, lado ontologia):
        # espelham os novos campos de AcquisitionMetadata do núcleo C++.
        # mirror the new AcquisitionMetadata fields of the C++ core.
        self.brillouin_c11_mhz_per_ustrain = brillouin_c11_mhz_per_ustrain
        self.brillouin_c12_mhz_per_c = brillouin_c12_mhz_per_c
        self.thermal_reference_modality = thermal_reference_modality
        self.dual_fiber_config = dual_fiber_config
        self.wellbore: Optional[Wellbore] = None
        self.cable: Optional[FiberOpticCable] = None
        self.interrogator: Optional[Interrogator] = None

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.modality:
            graph.add((self.uri, ALAKORO.hasModality, Literal(self.modality)))
        if self.start_time:
            graph.add((self.uri, ALAKORO.hasStartTime, Literal(self.start_time.isoformat(), datatype=XSD.dateTime)))
        if self.end_time:
            graph.add((self.uri, ALAKORO.hasEndTime, Literal(self.end_time.isoformat(), datatype=XSD.dateTime)))
        if self.sampling_rate_hz is not None:
            graph.add((self.uri, ALAKORO.hasSamplingRateHz, Literal(self.sampling_rate_hz, datatype=XSD.float)))
        if self.spatial_resolution_m is not None:
            graph.add((self.uri, ALAKORO.hasSpatialResolutionM, Literal(self.spatial_resolution_m, datatype=XSD.float)))
        if self.gauge_length_m is not None:
            graph.add((self.uri, ALAKORO.hasGaugeLengthM, Literal(self.gauge_length_m, datatype=XSD.float)))
        if self.n_channels is not None:
            graph.add((self.uri, ALAKORO.hasNumberOfChannels, Literal(self.n_channels, datatype=XSD.integer)))
        if self.n_time_samples is not None:
            graph.add((self.uri, ALAKORO.hasNumberOfTimeSamples, Literal(self.n_time_samples, datatype=XSD.integer)))
        if self.brillouin_c11_mhz_per_ustrain is not None:
            graph.add((self.uri, ALAKORO.hasBrillouinC11MhzPerUstrain,
                       Literal(self.brillouin_c11_mhz_per_ustrain, datatype=XSD.float)))
        if self.brillouin_c12_mhz_per_c is not None:
            graph.add((self.uri, ALAKORO.hasBrillouinC12MhzPerC,
                       Literal(self.brillouin_c12_mhz_per_c, datatype=XSD.float)))
        if self.thermal_reference_modality:
            graph.add((self.uri, ALAKORO.hasThermalReferenceModality,
                       Literal(self.thermal_reference_modality)))
        if self.dual_fiber_config is not None:
            graph.add((self.uri, ALAKORO.hasDualFiberConfig,
                       Literal(self.dual_fiber_config, datatype=XSD.boolean)))
        if self.wellbore:
            graph.add((self.uri, ALAKORO.measuredIn, self.wellbore.uri))
        if self.cable:
            graph.add((self.uri, ALAKORO.measuredWithCable, self.cable.uri))
        if self.interrogator:
            graph.add((self.uri, ALAKORO.measuredWithInterrogator, self.interrogator.uri))


class DASMeasurement(Measurement):
    """Medição DAS / DAS measurement."""

    _type = ALAKORO.DASMeasurement

    def __init__(self, **kwargs):
        kwargs.setdefault("modality", "DAS")
        super().__init__(**kwargs)


class DTSMeasurement(Measurement):
    """Medição DTS / DTS measurement."""

    _type = ALAKORO.DTSMeasurement

    def __init__(self, **kwargs):
        kwargs.setdefault("modality", "DTS")
        super().__init__(**kwargs)


class DSSMeasurement(Measurement):
    """Medição DSS / DSS measurement."""

    _type = ALAKORO.DSSMeasurement

    def __init__(self, **kwargs):
        kwargs.setdefault("modality", "DSS")
        super().__init__(**kwargs)
