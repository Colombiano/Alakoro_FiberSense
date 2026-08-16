"""
Alakoro FiberSense — Módulo de Ontologia
Semantic Ontology Module

Autor/Author: Luiz Paulo Colombiano
Licença/License: MIT

Modelo semântico RDF/OWL para poços, equipamentos, medições DFOS
e eventos detectados a partir de dados de fibra óptica.
"""

from .core import ALAKORO, OntologyModel, AlakoroEntity
from .petroleum import Well, Wellbore, Completion, FiberOpticCable
from .sensing import Interrogator, DASMeasurement, DTSMeasurement, DSSMeasurement
from .events import Event, JouleThomsonEvent, LeakEvent, FlowEvent, WarmBackEvent
from .bridge import SignatureOntologyBridge

__all__ = [
    "ALAKORO",
    "OntologyModel",
    "AlakoroEntity",
    "Well",
    "Wellbore",
    "Completion",
    "FiberOpticCable",
    "Interrogator",
    "DASMeasurement",
    "DTSMeasurement",
    "DSSMeasurement",
    "Event",
    "JouleThomsonEvent",
    "LeakEvent",
    "FlowEvent",
    "WarmBackEvent",
    "SignatureOntologyBridge",
]
