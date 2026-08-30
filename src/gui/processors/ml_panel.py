"""
Painel de Machine Learning: validação de assinaturas e inferência.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class MLPanel(QWidget):
    """Painel de validação de assinaturas e inferência ML."""

    validate_requested = Signal()
    model_load_requested = Signal(str)
    inference_requested = Signal()

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

        self.inference_result = QLabel("—")
        self.inference_result.setWordWrap(True)
        inf_layout.addRow(self.inference_result)

        layout.addWidget(inf_group)
        layout.addStretch()

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

    def set_validation_summary(self, text: str):
        self.validation_summary.setText(text)

    def set_inference_result(self, text: str):
        self.inference_result.setText(text)
