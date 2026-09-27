"""
Visualizador de mapa de calor 2D para dados DAS/DTS/DSS usando PyQtGraph.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class HeatmapView(QWidget):
    """Widget de mapa de calor 2D (time x distance/depth)."""

    # (time_index, channel_index, amplitude)
    cursor_moved = Signal(int, int, float)
    # (time_index, channel_index)
    cursor_clicked = Signal(int, int)
    # (x0, y0, x1, y1) em índices de dados
    roi_changed = Signal(int, int, int, int)

    # Colormaps suportados pelo pyqtgraph (nomes de arquivo em colors/maps)
    _COLORMAPS = {
        "RdBu_r": pg.colormap.get("CET-R4"),
        "seismic": pg.colormap.get("CET-D1"),
        "viridis": pg.colormap.get("viridis"),
        "plasma": pg.colormap.get("plasma"),
        "inferno": pg.colormap.get("inferno"),
        "magma": pg.colormap.get("magma"),
    }

    def __init__(self, parent=None):
        self._data: np.ndarray | None = None
        self._levels: tuple[float, float] | None = None
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Controles de visualização
        controls = QGroupBox("Display")
        controls_layout = QHBoxLayout(controls)

        controls_layout.addWidget(QLabel("Colormap:"))
        self.cmap_combo = QComboBox()
        self.cmap_combo.addItems(["RdBu_r", "seismic", "viridis", "plasma", "inferno", "magma"])
        self.cmap_combo.setCurrentText("RdBu_r")
        self.cmap_combo.currentTextChanged.connect(self._update_colormap)
        controls_layout.addWidget(self.cmap_combo)

        controls_layout.addWidget(QLabel("Scale:"))
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["Auto", "Fixed", "Percentile 1-99"])
        self.scale_combo.currentTextChanged.connect(self._update_levels)
        controls_layout.addWidget(self.scale_combo)

        self.reset_btn = QPushButton("Reset ROI")
        self.reset_btn.clicked.connect(self._reset_roi)
        controls_layout.addWidget(self.reset_btn)
        controls_layout.addStretch()

        layout.addWidget(controls)

        # Plot
        self.graphics_layout = pg.GraphicsLayoutWidget()
        layout.addWidget(self.graphics_layout)

        self.plot_item = self.graphics_layout.addPlot(row=0, col=0)
        self.plot_item.setLabel("bottom", "Tempo / Time")
        self.plot_item.setLabel("left", "Distância/Profundidade / Distance/Depth")
        self.plot_item.showGrid(x=True, y=True, alpha=0.3)

        self.image_item = pg.ImageItem()
        self.plot_item.addItem(self.image_item)

        # Overlay para máscara de inferência/anomalias
        self.overlay_item = pg.ImageItem()
        self.overlay_item.setOpacity(0.5)
        self.plot_item.addItem(self.overlay_item)

        self.colorbar = pg.ColorBarItem(interactive=False, orientation="vertical")
        self.colorbar.setImageItem(self.image_item)
        self.graphics_layout.addItem(self.colorbar, row=0, col=1)

        # ROI retangular
        self.roi = pg.RectROI(
            [0, 0],
            [10, 10],
            pen=pg.mkPen("y", width=2),
            removable=True,
        )
        self.roi.sigRegionChanged.connect(self._on_roi_changed)
        self.plot_item.addItem(self.roi)
        self.roi.hide()

        # Proxy para eventos de mouse
        self._proxy = pg.SignalProxy(
            self.plot_item.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_mouse_moved,
        )
        self.plot_item.scene().sigMouseClicked.connect(self._on_mouse_clicked)

        self._update_colormap()

    def set_data(self, data: np.ndarray, title: str = "Heatmap"):
        """
        Atualiza o heatmap com dados 2D.

        Aplica downsampling automático se os dados forem muito grandes
        para manter a interface responsiva.

        Args:
            data: Array 2D (time, channels).
            title: Título opcional.
        """
        if data.ndim != 2:
            raise ValueError("HeatmapView espera array 2D")

        self._data = data
        display_data = self._downsample_if_needed(data)

        # Transpor para (channels, time) porque ImageItem espera (linhas, colunas)
        self.image_item.setImage(display_data.T, autoLevels=True)

        if display_data is not data:
            title += f" (downsampled {data.shape} → {display_data.shape})"
        self.plot_item.setTitle(title)
        self._update_levels()

        # Reset ROI para o tamanho dos dados
        n_t, n_c = data.shape
        self.roi.setPos([0, 0], finish=False)
        self.roi.setSize([max(1, n_t // 4), max(1, n_c // 4)], finish=False)
        self.roi.show()

    def _downsample_if_needed(self, data: np.ndarray, max_pixels: int = 2_000_000) -> np.ndarray:
        """Reduz dados grandes para visualização interativa."""
        n_t, n_c = data.shape
        total = n_t * n_c
        if total <= max_pixels:
            return data

        factor = int(np.ceil(np.sqrt(total / max_pixels)))
        new_t = max(1, n_t // factor)
        new_c = max(1, n_c // factor)
        step_t = max(1, n_t // new_t)
        step_c = max(1, n_c // new_c)
        return data[::step_t, ::step_c]

    def _update_colormap(self):
        name = self.cmap_combo.currentText()
        cmap = self._COLORMAPS.get(name)
        if cmap is not None:
            self.image_item.setColorMap(cmap)
            self.colorbar.setColorMap(cmap)

    def _update_levels(self):
        if self._data is None:
            return
        scale = self.scale_combo.currentText()
        if scale == "Auto":
            self.image_item.setLevels(None)
            self.colorbar.setLevels(None)
        elif scale == "Fixed":
            if self._levels is None:
                vmax = np.max(np.abs(self._data))
                self._levels = (-vmax, vmax)
            self.image_item.setLevels(self._levels)
            self.colorbar.setLevels(self._levels)
        elif scale == "Percentile 1-99":
            low, high = np.percentile(self._data, [1, 99])
            self.image_item.setLevels((low, high))
            self.colorbar.setLevels((low, high))

    def _reset_roi(self):
        if self._data is None:
            return
        n_t, n_c = self._data.shape
        self.roi.setPos([0, 0], finish=False)
        self.roi.setSize([n_t, n_c], finish=False)
        self.roi_changed.emit(0, 0, n_t, n_c)

    def _on_roi_changed(self):
        if self._data is None:
            return
        pos = self.roi.pos()
        size = self.roi.size()
        x0 = int(round(pos.x()))
        y0 = int(round(pos.y()))
        x1 = int(round(x0 + size.x()))
        y1 = int(round(y0 + size.y()))
        n_t, n_c = self._data.shape
        x0, x1 = max(0, x0), min(n_t, x1)
        y0, y1 = max(0, y0), min(n_c, y1)
        self.roi_changed.emit(x0, y0, x1, y1)

    def _map_scene_to_data(self, pos) -> tuple[int, int] | None:
        """Converte coordenadas da cena para índices (time, channel)."""
        if self._data is None:
            return None
        mapped = self.plot_item.vb.mapSceneToView(pos)
        n_t, n_c = self._data.shape
        t = int(round(mapped.x()))
        c = int(round(mapped.y()))
        if 0 <= t < n_t and 0 <= c < n_c:
            return t, c
        return None

    def _on_mouse_moved(self, event):
        pos = event[0]
        mapped = self._map_scene_to_data(pos)
        if mapped is not None:
            t, c = mapped
            amp = float(self._data[t, c])
            self.cursor_moved.emit(t, c, amp)

    def _on_mouse_clicked(self, event):
        mapped = self._map_scene_to_data(event.scenePos())
        if mapped is not None:
            self.cursor_clicked.emit(*mapped)

    def set_overlay(self, mask: np.ndarray | None, color: tuple = (255, 0, 0, 150)):
        """
        Sobrepõe uma máscara 2D (time, channels) ao heatmap.

        Args:
            mask: Array 2D binário ou contínuo. None limpa o overlay.
            color: Cor RGBA do overlay.
        """
        if mask is None or self._data is None:
            self.overlay_item.clear()
            return
        if mask.shape != self._data.shape:
            raise ValueError(f"Máscara deve ter shape {self._data.shape}, recebido {mask.shape}")

        # Cria imagem RGBA
        rgba = np.zeros((*mask.T.shape, 4), dtype=np.uint8)
        rgba[..., 0] = color[0]
        rgba[..., 1] = color[1]
        rgba[..., 2] = color[2]
        rgba[..., 3] = (np.clip(mask.T, 0, 1) * color[3]).astype(np.uint8)
        self.overlay_item.setImage(rgba)

    def clear(self):
        self.image_item.clear()
        self.overlay_item.clear()
        self._data = None
