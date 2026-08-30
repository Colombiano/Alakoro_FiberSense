"""
Painel de processadores de sinal (filtros, denoising, detecção de eventos).
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class FilterPanel(QWidget):
    """Painel de filtros e processadores avançados."""

    # Sinal: (nome_da_acao, kwargs)
    process_requested = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # ── Filtros Butterworth ──
        bw_group = QGroupBox("Butterworth")
        bw_form = QFormLayout(bw_group)

        self.fs_spin = QDoubleSpinBox()
        self.fs_spin.setRange(0.1, 1_000_000.0)
        self.fs_spin.setValue(1000.0)
        self.fs_spin.setSuffix(" Hz")
        bw_form.addRow("Fs:", self.fs_spin)

        self.cutoff_spin = QDoubleSpinBox()
        self.cutoff_spin.setRange(0.01, 500_000.0)
        self.cutoff_spin.setValue(100.0)
        self.cutoff_spin.setSuffix(" Hz")
        bw_form.addRow("Cutoff:", self.cutoff_spin)

        self.low_hz_spin = QDoubleSpinBox()
        self.low_hz_spin.setRange(0.01, 500_000.0)
        self.low_hz_spin.setValue(10.0)
        self.low_hz_spin.setSuffix(" Hz")
        bw_form.addRow("Low:", self.low_hz_spin)

        self.high_hz_spin = QDoubleSpinBox()
        self.high_hz_spin.setRange(0.01, 500_000.0)
        self.high_hz_spin.setValue(100.0)
        self.high_hz_spin.setSuffix(" Hz")
        bw_form.addRow("High:", self.high_hz_spin)

        bw_btns = QHBoxLayout()
        for name, action in [
            ("Lowpass", "butterworth_lowpass"),
            ("Highpass", "butterworth_highpass"),
            ("Bandpass", "butterworth_bandpass"),
        ]:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, a=action: self._request_butterworth(a))
            bw_btns.addWidget(btn)
        bw_form.addRow(bw_btns)

        layout.addWidget(bw_group)

        # ── Pré-processamento básico ──
        basic_group = QGroupBox("Basic Preprocessing")
        basic_layout = QHBoxLayout(basic_group)
        for name, action in [
            ("Detrend", "detrend"),
            ("Demean", "demean"),
            ("Taper", "taper"),
        ]:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, a=action: self.process_requested.emit(a, {}))
            basic_layout.addWidget(btn)
        layout.addWidget(basic_group)

        # ── Denoising ──
        denoise_group = QGroupBox("Denoising")
        denoise_form = QFormLayout(denoise_group)

        self.median1d_spin = QSpinBox()
        self.median1d_spin.setRange(3, 101)
        self.median1d_spin.setValue(5)
        self.median1d_spin.setSingleStep(2)
        denoise_form.addRow("Median 1D window:", self.median1d_spin)

        median1d_btn = QPushButton("Apply Median 1D")
        median1d_btn.clicked.connect(self._request_median1d)
        denoise_form.addRow(median1d_btn)

        self.svd_spin = QSpinBox()
        self.svd_spin.setRange(1, 100)
        self.svd_spin.setValue(5)
        denoise_form.addRow("SVD components:", self.svd_spin)

        svd_btn = QPushButton("Apply SVD Denoise")
        svd_btn.clicked.connect(self._request_svd)
        denoise_form.addRow(svd_btn)

        layout.addWidget(denoise_group)

        # ── Event Detection ──
        event_group = QGroupBox("Event Detection")
        event_layout = QVBoxLayout(event_group)

        sta_layout = QHBoxLayout()
        self.n_sta_spin = QSpinBox()
        self.n_sta_spin.setRange(2, 1000)
        self.n_sta_spin.setValue(10)
        self.n_lta_spin = QSpinBox()
        self.n_lta_spin.setRange(2, 10000)
        self.n_lta_spin.setValue(50)
        sta_layout.addWidget(QLabel("STA:"))
        sta_layout.addWidget(self.n_sta_spin)
        sta_layout.addWidget(QLabel("LTA:"))
        sta_layout.addWidget(self.n_lta_spin)
        event_layout.addLayout(sta_layout)

        sta_btn = QPushButton("Compute STA/LTA")
        sta_btn.clicked.connect(self._request_sta_lta)
        event_layout.addWidget(sta_btn)

        for name, action in [
            ("Hilbert Envelope", "hilbert_envelope"),
            ("PSD", "psd"),
        ]:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, a=action: self._request_simple(a))
            event_layout.addWidget(btn)

        layout.addWidget(event_group)
        layout.addStretch()

    def _request_butterworth(self, action: str):
        kwargs = {
            "sample_rate_hz": self.fs_spin.value(),
        }
        if action == "butterworth_lowpass":
            kwargs["cutoff_hz"] = self.cutoff_spin.value()
        elif action == "butterworth_highpass":
            kwargs["cutoff_hz"] = self.cutoff_spin.value()
        elif action == "butterworth_bandpass":
            kwargs["low_hz"] = self.low_hz_spin.value()
            kwargs["high_hz"] = self.high_hz_spin.value()
        self.process_requested.emit(action, kwargs)

    def _request_median1d(self):
        self.process_requested.emit("median_filter_1d", {"window_size": self.median1d_spin.value()})

    def _request_svd(self):
        self.process_requested.emit("svd_denoise", {"n_components": self.svd_spin.value()})

    def _request_sta_lta(self):
        self.process_requested.emit("sta_lta", {
            "n_sta": self.n_sta_spin.value(),
            "n_lta": self.n_lta_spin.value(),
        })

    def _request_simple(self, action: str):
        if action == "psd":
            kwargs = {"sample_rate_hz": self.fs_spin.value()}
        else:
            kwargs = {}
        self.process_requested.emit(action, kwargs)
