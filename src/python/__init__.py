"""
Alakoro_FiberSense
==================

Sistema de Processamento de Dados de Fibra Optica (DAS)
Arquitetura: Event-Driven + MVC

Autor: Luiz Paulo Colombiano
"""

__version__ = "1.0.0"
__author__ = "Luiz Paulo Colombiano"
__license__ = "MIT"

from .controllers import PipelineController, DataController, EventController
from .models import DASData, DASEvent, ProcessingConfig
from .views import DataView, EventView, DashboardView
from .events import EventBus, EventType, EventPriority
from .services import ProcessingService, DetectionService, StreamingService

__all__ = [
    "PipelineController",
    "DataController", 
    "EventController",
    "DASData",
    "DASEvent",
    "ProcessingConfig",
    "DataView",
    "EventView",
    "DashboardView",
    "EventBus",
    "EventType",
    "EventPriority",
    "ProcessingService",
    "DetectionService",
    "StreamingService",
]
