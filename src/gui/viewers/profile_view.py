"""
Visualizador de perfis (traces) em tempos selecionados usando PyQtGraph.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget


class ProfileView(QWidget):
    """Widget de perfis de amplitude vs distance/depth em tempos selecionados."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel("bottom", "Distância/Profundidade / Distance/Depth")
        self.plot_widget.setLabel("left", "Amplitude")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend()

        layout.addWidget(self.plot_widget)

    def set_data(self, data: np.ndarray, times: list[int] | None = None,
                 depth: np.ndarray | None = None):
        """
        Plota perfis em tempos selecionados.

        Args:
            data: Array 2D (time, channels).
            times: Índices de tempo a plotar. Se None, plota primeiro, meio e fim.
            depth: Vetor de profundidade/distância. Se None, usa índices.
        """
        self.plot_widget.clear()
        self.plot_widget.addLegend()

        n_t, n_c = data.shape
        if times is None:
            times = [0, n_t // 2, n_t - 1]

        x = depth if depth is not None else np.arange(n_c)

        colors = ["y", "c", "m", "g", "r", "b", "w"]
        for i, t in enumerate(times):
            if 0 <= t < n_t:
                pen = pg.mkPen(color=colors[i % len(colors)], width=2)
                self.plot_widget.plot(
                    x, data[t, :],
                    pen=pen,
                    name=f"t={t}"
                )

        self.plot_widget.setTitle("Perfis de Amplitude / Amplitude Profiles")

    def clear(self):
        self.plot_widget.clear()
