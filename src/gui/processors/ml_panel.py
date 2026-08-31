"""
Painel de Machine Learning: validação de assinaturas, inferência e máscaras.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from src.gui.train_wizard import TrainWizard


class MLPanel(QWidget):
    """Painel de validação de assinaturas e inferência ML."""

    validate_requested = Signal()
    model_load_requested = Signal(str)
    inference_requested = Signal()
    mask_requested = Signal(float)  # threshold
    report_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # ── Validação de assinaturas ──
        val_group = QGroupBox("Signature Validation")
        val_layout = QVBoxLayout(val_group)

        self.validate_btn = QPushButton("🧪 Run SignatureValidator")
        self.validate_btn.clicked.connect(self.validate_requested.emit)
        val_layout.addWidget(self.validate_btn)

        self.report_btn = QPushButton("📋 View Validation Report")
        self.report_btn.clicked.connect(self.report_requested.emit)
        self.report_btn.setEnabled(False)
        val_layout.addWidget(self.report_btn)

        self.validation_summary = QLabel("—")
        self.validation_summary.setWordWrap(True)
        val_layout.addWidget(self.validation_summary)

        layout.addWidget(val_group)

        # ── Inferência ML ──
        inf_group = QGroupBox("ML Inference")
        inf_layout = QFormLayout(inf_group)

        model_layout = QHBoxLayout()
        self.model_path_edit = QLineEdit()
        self.model_path_edit.setPlaceholderText("Select model file...")
        model_browse = QPushButton("Browse...")
        model_browse.clicked.connect(self._browse_model)
        model_layout.addWidget(self.model_path_edit)
        model_layout.addWidget(model_browse)
        inf_layout.addRow("Model:", model_layout)

        self.load_model_btn = QPushButton("Load Model")
        self.load_model_btn.clicked.connect(self._load_model)
        inf_layout.addRow(self.load_model_btn)

        self.inference_btn = QPushButton("Run Inference")
        self.inference_btn.setEnabled(False)
        self.inference_btn.clicked.connect(self.inference_requested.emit)
        inf_layout.addRow(self.inference_btn)

        self.train_btn = QPushButton("🎓 Train Model Wizard")
        self.train_btn.clicked.connect(self._open_train_wizard)
        inf_layout.addRow(self.train_btn)

        self.inference_result = QLabel("—")
        self.inference_result.setWordWrap(True)
        inf_layout.addRow(self.inference_result)

        layout.addWidget(inf_group)

        # ── Máscara de anomalias ──
        mask_group = QGroupBox("Anomaly Mask")
        mask_layout = QVBoxLayout(mask_group)

        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Threshold:"))
        self.threshold_slider = QSlider()
        self.threshold_slider.setOrientation(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(50)
        self.threshold_slider.valueChanged.connect(self._update_threshold_label)
        slider_layout.addWidget(self.threshold_slider)
        self.threshold_label = QLabel("0.50")
        slider_layout.addWidget(self.threshold_label)
        mask_layout.addLayout(slider_layout)

        self.mask_btn = QPushButton("Apply Amplitude Mask")
        self.mask_btn.clicked.connect(self._request_mask)
        mask_layout.addWidget(self.mask_btn)

        layout.addWidget(mask_group)
        layout.addStretch()

    def _update_threshold_label(self, value: int):
        self.threshold_label.setText(f"{value / 100.0:.2f}")

    def _request_mask(self):
        threshold = self.threshold_slider.value() / 100.0
        self.mask_requested.emit(threshold)

    def _browse_model(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ML model",
            "",
            "Model files (*.pth *.pt *.pkl *.joblib *.onnx);;All files (*)",
        )
        if path:
            self.model_path_edit.setText(path)

    def _load_model(self):
        path = self.model_path_edit.text().strip()
        if path and Path(path).exists():
            self.model_load_requested.emit(path)
            self.inference_btn.setEnabled(True)

    def _open_train_wizard(self):
        wizard = TrainWizard(self)
        wizard.exec()

    def set_validation_summary(self, text: str):
        self.validation_summary.setText(text)
        self.report_btn.setEnabled(True)

    def set_inference_result(self, text: str):
        self.inference_result.setText(text)
