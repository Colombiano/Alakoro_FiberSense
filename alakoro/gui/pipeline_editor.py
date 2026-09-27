"""
Editor visual simples de pipeline de processamento (lista encadeada de nós).
"""

from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class PipelineEditor(QWidget):
    """Editor visual de pipeline como lista de nós."""

    pipeline_changed = Signal(list)  # lista de {action, kwargs}

    AVAILABLE_NODES = {
        "demean": {},
        "detrend": {},
        "taper": {"alpha": 0.05},
        "butterworth_lowpass": {"cutoff_hz": 100.0},
        "butterworth_highpass": {"cutoff_hz": 10.0},
        "butterworth_bandpass": {"low_hz": 10.0, "high_hz": 100.0},
        "median_filter_1d": {"window_size": 5},
        "svd_denoise": {"n_components": 5},
        "sta_lta": {"n_sta": 10, "n_lta": 50},
        "hilbert_envelope": {},
        "psd": {},
        "thermal_gradient": {},
        "geothermal_baseline_correction": {},
        "thermal_anomaly_detection": {},
        "spatial_median_filter": {"window_size": 5},
        "dts_pipeline": {},
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Adicionar nó
        add_layout = QHBoxLayout()
        add_layout.addWidget(QLabel("Adicionar nó / Add node:"))
        self.node_combo = QComboBox()
        self.node_combo.addItems(list(self.AVAILABLE_NODES.keys()))
        add_layout.addWidget(self.node_combo)
        add_btn = QPushButton("+")
        add_btn.clicked.connect(self._add_node)
        add_layout.addWidget(add_btn)
        add_layout.addStretch()
        layout.addLayout(add_layout)

        # Lista de nós
        self.node_list = QListWidget()
        self.node_list.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self.node_list)

        # Controles do nó selecionado
        self.node_controls = QGroupBox("Parâmetros do nó / Node parameters")
        self.node_controls_layout = QFormLayout(self.node_controls)
        self.param_edit = QLineEdit()
        self.param_edit.setPlaceholderText('{"cutoff_hz": 100}')
        self.param_edit.editingFinished.connect(self._update_current_node_params)
        self.node_controls_layout.addRow("JSON kwargs:", self.param_edit)
        layout.addWidget(self.node_controls)

        # Botões de reordenação e remoção
        btn_layout = QHBoxLayout()
        up_btn = QPushButton("⬆ Up")
        up_btn.clicked.connect(self._move_up)
        down_btn = QPushButton("⬇ Down")
        down_btn.clicked.connect(self._move_down)
        remove_btn = QPushButton("🗑 Remove")
        remove_btn.clicked.connect(self._remove_node)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear)
        btn_layout.addWidget(up_btn)
        btn_layout.addWidget(down_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Visualização JSON
        layout.addWidget(QLabel("Pipeline JSON:"))
        self.json_preview = QLineEdit()
        self.json_preview.setReadOnly(True)
        layout.addWidget(self.json_preview)

        self._update_json_preview()

    def _add_node(self):
        action = self.node_combo.currentText()
        kwargs = self.AVAILABLE_NODES.get(action, {}).copy()
        item = QListWidgetItem(f"{action}  →  {json.dumps(kwargs)}")
        item.setData(Qt.ItemDataRole.UserRole, {"action": action, "kwargs": kwargs})
        self.node_list.addItem(item)
        self._emit()

    def _on_selection_changed(self):
        row = self.node_list.currentRow()
        if row < 0:
            self.param_edit.clear()
            return
        data = self.node_list.item(row).data(Qt.ItemDataRole.UserRole)
        self.param_edit.setText(json.dumps(data.get("kwargs", {})))

    def _update_current_node_params(self):
        row = self.node_list.currentRow()
        if row < 0:
            return
        text = self.param_edit.text().strip()
        try:
            kwargs = json.loads(text) if text else {}
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Aviso", "JSON inválido")
            return
        item = self.node_list.item(row)
        data = item.data(Qt.ItemDataRole.UserRole)
        data["kwargs"] = kwargs
        item.setData(Qt.ItemDataRole.UserRole, data)
        item.setText(f"{data['action']}  →  {json.dumps(kwargs)}")
        self._emit()

    def _move_up(self):
        row = self.node_list.currentRow()
        if row > 0:
            item = self.node_list.takeItem(row)
            self.node_list.insertItem(row - 1, item)
            self.node_list.setCurrentRow(row - 1)
            self._emit()

    def _move_down(self):
        row = self.node_list.currentRow()
        if 0 <= row < self.node_list.count() - 1:
            item = self.node_list.takeItem(row)
            self.node_list.insertItem(row + 1, item)
            self.node_list.setCurrentRow(row + 1)
            self._emit()

    def _remove_node(self):
        row = self.node_list.currentRow()
        if row >= 0:
            self.node_list.takeItem(row)
            self._emit()

    def _clear(self):
        self.node_list.clear()
        self._emit()

    def _emit(self):
        self._update_json_preview()
        self.pipeline_changed.emit(self.get_pipeline())

    def _update_json_preview(self):
        self.json_preview.setText(json.dumps(self.get_pipeline()))

    def get_pipeline(self) -> list[dict[str, Any]]:
        pipeline = []
        for i in range(self.node_list.count()):
            data = self.node_list.item(i).data(Qt.ItemDataRole.UserRole)
            pipeline.append(data)
        return pipeline

    def set_pipeline(self, pipeline: list[dict[str, Any]]):
        self.node_list.clear()
        for step in pipeline:
            action = step.get("action", "")
            kwargs = step.get("kwargs", {})
            item = QListWidgetItem(f"{action}  →  {json.dumps(kwargs)}")
            item.setData(Qt.ItemDataRole.UserRole, {"action": action, "kwargs": kwargs})
            self.node_list.addItem(item)
        self._update_json_preview()
