"""
Painel de presets de processamento: salvar/carregar e aplicar pipelines JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.gui.pipeline_editor import PipelineEditor


class PresetPanel(QWidget):
    """Painel para gerenciar presets de pipeline de processamento."""

    # Lista de (action, kwargs) a serem aplicadas em sequência
    apply_preset_requested = Signal(list)

    def __init__(self, parent=None):
        self._presets_dir = Path.home() / ".alakoro" / "presets"
        self._presets_dir.mkdir(parents=True, exist_ok=True)
        super().__init__(parent)
        self._setup_ui()
        self._refresh_preset_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()

        # Aba de editor visual
        self.editor = PipelineEditor()
        self.editor.pipeline_changed.connect(self._on_pipeline_changed)
        self.tabs.addTab(self.editor, "🧱 Editor Visual")

        # Aba de presets salvos
        presets_widget = QWidget()
        presets_layout = QVBoxLayout(presets_widget)

        presets_layout.addWidget(QLabel("Presets salvos / Saved presets:"))
        self.preset_list = QListWidget()
        self.preset_list.itemDoubleClicked.connect(self._apply_selected)
        presets_layout.addWidget(self.preset_list)

        btn_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Aplicar / Apply")
        self.apply_btn.clicked.connect(self._apply_selected)
        self.save_btn = QPushButton("Salvar atual / Save current")
        self.save_btn.clicked.connect(self._save_current)
        self.load_btn = QPushButton("Carregar arquivo / Load file")
        self.load_btn.clicked.connect(self._load_from_file)
        btn_layout.addWidget(self.apply_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.load_btn)
        presets_layout.addLayout(btn_layout)

        layout.addWidget(self.tabs)
        self.tabs.addTab(presets_widget, "📂 Presets Salvos")

        # Pipeline JSON bruto (sincronizado com editor)
        layout.addWidget(QLabel("Pipeline atual / Current pipeline (JSON):"))
        self.pipeline_edit = QLineEdit()
        self.pipeline_edit.setPlaceholderText(
            '[{"action": "demean", "kwargs": {}}, {"action": "butterworth_bandpass", "kwargs": {"low_hz": 1, "high_hz": 100}}]'
        )
        self.pipeline_edit.editingFinished.connect(self._on_json_edited)
        layout.addWidget(self.pipeline_edit)

    def _on_pipeline_changed(self, pipeline: list[dict[str, Any]]):
        self.pipeline_edit.setText(json.dumps(pipeline))

    def _on_json_edited(self):
        text = self.pipeline_edit.text().strip()
        if not text:
            return
        try:
            pipeline = json.loads(text)
            self.editor.set_pipeline(pipeline)
        except json.JSONDecodeError:
            pass

    def _refresh_preset_list(self):
        self.preset_list.clear()
        if not self._presets_dir.exists():
            return
        for path in sorted(self._presets_dir.glob("*.json")):
            self.preset_list.addItem(path.stem)

    def _preset_path(self, name: str) -> Path:
        return self._presets_dir / f"{name}.json"

    def _apply_selected(self):
        item = self.preset_list.currentItem()
        if item is None:
            QMessageBox.warning(self, "Aviso / Warning", "Selecione um preset / Select a preset")
            return
        path = self._preset_path(item.text())
        self._apply_file(path)

    def _apply_file(self, path: Path):
        try:
            pipeline = json.loads(path.read_text(encoding="utf-8"))
            self.editor.set_pipeline(pipeline)
            self.apply_preset_requested.emit(pipeline)
        except Exception as exc:
            QMessageBox.critical(self, "Erro / Error", f"Falha ao carregar preset:\n{exc}")

    def _load_from_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Carregar preset / Load preset",
            str(self._presets_dir),
            "JSON (*.json)",
        )
        if path:
            self._apply_file(Path(path))

    def _save_current(self):
        pipeline = self.editor.get_pipeline()
        if not pipeline:
            QMessageBox.warning(self, "Aviso / Warning", "Pipeline vazio / Empty pipeline")
            return

        name, ok = QInputDialog.getText(
            self, "Salvar preset / Save preset", "Nome / Name:"
        )
        if not ok or not name:
            return

        path = self._preset_path(name)
        try:
            path.write_text(json.dumps(pipeline, indent=2), encoding="utf-8")
            self._refresh_preset_list()
        except Exception as exc:
            QMessageBox.critical(self, "Erro / Error", f"Falha ao salvar:\n{exc}")
