"""
Alakoro FiberSense — GUI Desktop (PySide6 + PyQtGraph)
"""

from .flow_analysis import JanelaAnaliseFluxo
from .main_window import AlakoroMainWindow, main

__all__ = ["AlakoroMainWindow", "JanelaAnaliseFluxo", "main"]
