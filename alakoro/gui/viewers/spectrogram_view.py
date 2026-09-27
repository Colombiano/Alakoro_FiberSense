"""
Visualizador de espectrograma para dados DAS/DTS usando PyQtGraph.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class SpectrogramView(QWidget):
    """Widget de espectrograma STFT para um canal selecionado."""

    def __init__(self, parent=None):
        self._data: np.ndarray | None = None
        self._sample_rate_hz: float = 1000.0
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Controles
        controls = QGroupBox("STFT Settings")
        form = QFormLayout(controls)

        self.channel_spin = QSpinBox()
        self.channel_spin.setRange(0, 0)
        self.channel_spin.setValue(0)
        self.channel_spin.valueChanged.connect(self._compute)

        self.window_spin = QSpinBox()
        self.window_spin.setRange(16, 4096)
        self.window_spin.setValue(256)
        self.window_spin.setSingleStep(16)
        self.window_spin.valueChanged.connect(self._compute)

        self.overlap_spin = QSpinBox()
        self.overlap_spin.setRange(0, 2048)
        self.overlap_spin.setValue(128)
        self.overlap_spin.setSingleStep(16)
        self.overlap_spin.valueChanged.connect(self._compute)

        self.nfft_spin = QSpinBox()
        self.nfft_spin.setRange(16, 4096)
        self.nfft_spin.setValue(256)
        self.nfft_spin.setSingleStep(16)
        self.nfft_spin.valueChanged.connect(self._compute)

        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel("Channel:"))
        hlayout.addWidget(self.channel_spin)
        hlayout.addWidget(QLabel("Window:"))
        hlayout.addWidget(self.window_spin)
        hlayout.addWidget(QLabel("Overlap:"))
        hlayout.addWidget(self.overlap_spin)
        hlayout.addWidget(QLabel("NFFT:"))
        hlayout.addWidget(self.nfft_spin)
        hlayout.addStretch()

        self.compute_btn = QPushButton("Compute / Atualizar")
        self.compute_btn.clicked.connect(self._compute)
        hlayout.addWidget(self.compute_btn)

        layout.addLayout(hlayout)

        # Plot
        self.graphics_layout = pg.GraphicsLayoutWidget()
        layout.addWidget(self.graphics_layout)

        self.plot_item = self.graphics_layout.addPlot(row=0, col=0)
        self.plot_item.setLabel("bottom", "Tempo / Time (samples)")
        self.plot_item.setLabel("left", "Frequência / Frequency (Hz)")

        self.image_item = pg.ImageItem()
        self.plot_item.addItem(self.image_item)

        self.colorbar = pg.ColorBarItem(interactive=False, orientation="vertical")
        self.colorbar.setImageItem(self.image_item)
        self.graphics_layout.addItem(self.colorbar, row=0, col=1)

    def set_data(self, data: np.ndarray, sample_rate_hz: float = 1000.0):
        """
        Define os dados 2D (time, channels).

        Args:
            data: Array 2D.
            sample_rate_hz: Taxa de amostragem em Hz.
        """
        if data.ndim != 2:
            raise ValueError("SpectrogramView espera array 2D")
        self._data = data
        self._sample_rate_hz = sample_rate_hz
        self.channel_spin.setRange(0, data.shape[1] - 1)
        self.channel_spin.setValue(min(self.channel_spin.value(), data.shape[1] - 1))
        self._compute()

    def _compute(self):
        if self._data is None:
            return

        channel = self.channel_spin.value()
        nperseg = self.window_spin.value()
        noverlap = self.overlap_spin.value()
        nfft = self.nfft_spin.value()

        if noverlap >= nperseg:
            noverlap = nperseg - 1
            self.overlap_spin.setValue(noverlap)

        try:
            from scipy.signal import stft

            f, t, Zxx = stft(
                self._data[:, channel],
                fs=self._sample_rate_hz,
                nperseg=nperseg,
                noverlap=noverlap,
                nfft=nfft,
            )
            magnitude = np.abs(Zxx)
            self.image_item.setImage(magnitude.T, autoLevels=True)

            # Ajusta eixos
            self.plot_item.setTitle(f"Espectrograma — Canal / Channel {channel}")
        except Exception as exc:
            self.plot_item.setTitle(f"Erro / Error: {exc}")

    def clear(self):
        self.image_item.clear()
        self._data = None
