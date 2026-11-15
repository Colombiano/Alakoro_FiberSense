"""
Alakoro FiberSense — Módulo de Ontologia
Semantic Ontology Module

Autor/Author: Luiz Paulo Colombiano
Licença/License: MIT

Modelo semântico RDF/OWL para poços, equipamentos, medições DFOS,
eventos detectados a partir de dados de fibra óptica e estruturas
monitoradas (MSE: edifícios antigos).
"""

from .core import ALAKORO, OntologyModel, AlakoroEntity
from .petroleum import Well, Wellbore, Completion, FiberOpticCable
from .sensing import Interrogator, DASMeasurement, DTSMeasurement, DSSMeasurement
from .events import (
    Event,
    JouleThomsonEvent,
    LeakEvent,
    FlowEvent,
    WarmBackEvent,
    PropagacaoFissuraEvento,
    AberturaFissuraTermicaEvento,
    EventoAcusticoFissura,
    AnomaliaTermicaEvento,
    DanoModalEvento,
    RecalqueEvento,
)
from .estruturas import (
    Estrutura,
    EdificioEclesiastico,
    ElementoEstrutural,
    Alvenaria,
    Fundacao,
    TorreSineira,
    Cobertura,
    Abobada,
    Fissura,
    InstalacaoFibra,
)
from .bridge import SignatureOntologyBridge
from .inference_engine import InferenceEngine, infer_events

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
    "PropagacaoFissuraEvento",
    "AberturaFissuraTermicaEvento",
    "EventoAcusticoFissura",
    "AnomaliaTermicaEvento",
    "DanoModalEvento",
    "RecalqueEvento",
    "Estrutura",
    "EdificioEclesiastico",
    "ElementoEstrutural",
    "Alvenaria",
    "Fundacao",
    "TorreSineira",
    "Cobertura",
    "Abobada",
    "Fissura",
    "InstalacaoFibra",
    "SignatureOntologyBridge",
    "InferenceEngine",
    "infer_events",
]
