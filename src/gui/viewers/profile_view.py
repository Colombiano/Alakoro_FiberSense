"""
Visualizador de perfis (traces) em tempos selecionados usando PyQtGraph.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ProfileView(QWidget):
    """Widget de perfis de amplitude vs distance/depth em tempos selecionados."""

    # Emitido quando um tempo da lista é selecionado
    time_selected = Signal(int)

    def __init__(self, parent=None):
        self._data: np.ndarray | None = None
        self._depth: np.ndarray | None = None
        self._time_labels: list[str] = []
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Controles
        controls = QHBoxLayout()

        controls.addWidget(QLabel("Add time:"))
        self.time_spin = QSpinBox()
        self.time_spin.setRange(0, 0)
        controls.addWidget(self.time_spin)

        self.add_btn = QPushButton("+")
        self.add_btn.clicked.connect(self._add_current_time)
        controls.addWidget(self.add_btn)

        self.mean_cb = QCheckBox("Mean ± std")
        self.mean_cb.setChecked(False)
        self.mean_cb.stateChanged.connect(self._replot)
        controls.addWidget(self.mean_cb)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_times)
        controls.addWidget(self.clear_btn)

        controls.addStretch()
        layout.addLayout(controls)

        # Lista de tempos selecionados
        self.time_list = QListWidget()
        self.time_list.setMaximumHeight(120)
        self.time_list.itemChanged.connect(self._replot)
        layout.addWidget(self.time_list)

        # Plot
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
        self._data = data
        self._depth = depth if depth is not None else np.arange(data.shape[1])

        n_t = data.shape[0]
        self.time_spin.setRange(0, n_t - 1)

        self.time_list.clear()
        if times is None:
            times = [0, n_t // 2, n_t - 1]

        for t in times:
            self._add_time_item(t)

        self._replot()

    def _add_time_item(self, t: int):
        item = QListWidgetItem(f"t={t}")
        item.setData(256, t)  # role UserRole
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked)
        item.setSelected(True)
        self.time_list.addItem(item)

    def _add_current_time(self):
        t = self.time_spin.value()
        self._add_time_item(t)
        self._replot()

    def _clear_times(self):
        self.time_list.clear()
        self._replot()

    def _get_checked_times(self) -> list[int]:
        times = []
        for i in range(self.time_list.count()):
            item = self.time_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                times.append(item.data(256))
        return times

    def _replot(self):
        self.plot_widget.clear()
        self.plot_widget.addLegend()

        if self._data is None:
            return

        checked_times = self._get_checked_times()
        x = self._depth

        colors = ["y", "c", "m", "g", "r", "b", "w"]

        if self.mean_cb.isChecked() and len(checked_times) > 0:
            subset = self._data[checked_times, :]
            mean = subset.mean(axis=0)
            std = subset.std(axis=0)
            self.plot_widget.plot(
                x, mean,
                pen=pg.mkPen("w", width=2),
                name="Mean",
            )
            upper = mean + std
            lower = mean - std
            fill = pg.FillBetweenItem(
                pg.PlotDataItem(x, upper),
                pg.PlotDataItem(x, lower),
                brush=(255, 255, 255, 40),
            )
            self.plot_widget.addItem(fill)

        for i, t in enumerate(checked_times):
            if 0 <= t < self._data.shape[0]:
                pen = pg.mkPen(color=colors[i % len(colors)], width=2)
                self.plot_widget.plot(
                    x, self._data[t, :],
                    pen=pen,
                    name=f"t={t}",
                )

        self.plot_widget.setTitle("Perfis de Amplitude / Amplitude Profiles")

    def clear(self):
        self.plot_widget.clear()
        self._data = None
        self._depth = None
        self.time_list.clear()
