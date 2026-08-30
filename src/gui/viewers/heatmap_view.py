"""
Visualizador de mapa de calor 2D para dados DAS/DTS/DSS usando PyQtGraph.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget


class HeatmapView(QWidget):
    """Widget de mapa de calor 2D (time x distance/depth)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel("bottom", "Tempo / Time")
        self.plot_widget.setLabel("left", "Distância/Profundidade / Distance/Depth")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        self.image_item = pg.ImageItem()
        self.plot_widget.addItem(self.image_item)

        self.colorbar = pg.ColorBarItem(interactive=False)
        self.colorbar.setImageItem(self.image_item)
        self.colorbar.setOrientation("right")

        layout.addWidget(self.plot_widget)

    def set_data(self, data: np.ndarray, title: str = "Heatmap"):
        """
        Atualiza o heatmap com dados 2D.

        Args:
            data: Array 2D (time, channels).
            title: Título opcional.
        """
        if data.ndim != 2:
            raise ValueError("HeatmapView espera array 2D")

        # Transpor para (channels, time) porque ImageItem espera (linhas, colunas)
        # e a origem é no canto inferior esquerdo por padrão.
        self.image_item.setImage(data.T, autoLevels=True)
        self.plot_widget.setTitle(title)

    def clear(self):
        self.image_item.clear()
