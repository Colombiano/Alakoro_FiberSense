"""
Módulo de Processamento / Processing Module
"""

from . import multimodal_alignment
from .dts_processor import DTSThermalProcessor
from .hybrid_pipeline import HybridPipeline
from .lfdas_processor import LFDASProcessor

__all__ = ['HybridPipeline', 'LFDASProcessor', 'DTSThermalProcessor', 'multimodal_alignment']
