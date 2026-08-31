"""
Diálogo de processamento em lote (batch) de arquivos DFOS.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from src.gui.format_hints import _EXTENSION_HINTS
from src.gui.workers.batch_worker import BatchWorker


class BatchDialog(QDialog):
    """Diálogo para configurar e executar batch processing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Processamento em Lote / Batch Processing")
        self.setMinimumSize(700, 500)
        self._worker_thread: Optional[QThread] = None
        self._worker: Optional[BatchWorker] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        # Pasta de entrada
        input_layout = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Selecione a pasta com os arquivos...")
        input_btn = QPushButton("Procurar...")
        input_btn.clicked.connect(self._browse_input)
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(input_btn)
        form.addRow("Pasta de entrada / Input folder:", input_layout)

        # Pasta de saída
        output_layout = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Selecione a pasta de saída...")
        output_btn = QPushButton("Procurar...")
        output_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(output_btn)
        form.addRow("Pasta de saída / Output folder:", output_layout)

        # Preset
        preset_layout = QHBoxLayout()
        self.preset_edit = QLineEdit()
        self.preset_edit.setPlaceholderText("Selecione o preset JSON...")
        preset_btn = QPushButton("Procurar...")
        preset_btn.clicked.connect(self._browse_preset)
        preset_layout.addWidget(self.preset_edit)
        preset_layout.addWidget(preset_btn)
        form.addRow("Preset / Pipeline JSON:", preset_layout)

        # Formato de exportação
        self.format_combo = QComboBox()
        self.format_combo.addItems(["nc", "npy", "csv", "png"])
        form.addRow("Formato de exportação / Export format:", self.format_combo)

        layout.addLayout(form)

        # Botões
        btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("▶ Executar / Run")
        self.run_btn.clicked.connect(self._run)
        self.cancel_btn = QPushButton("Cancelar / Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_run_btn = QPushButton("⏹ Parar / Stop")
        self.cancel_run_btn.setEnabled(False)
        self.cancel_run_btn.clicked.connect(self._cancel)
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.cancel_run_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        # Progresso
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        # Log
        layout.addWidget(QLabel("Log:"))
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)

    def _browse_input(self):
        path = QFileDialog.getExistingDirectory(self, "Pasta de entrada / Input folder")
        if path:
            self.input_edit.setText(path)
            if not self.output_edit.text():
                self.output_edit.setText(str(Path(path) / "output"))

    def _browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "Pasta de saída / Output folder")
        if path:
            self.output_edit.setText(path)

    def _browse_preset(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar preset / Select preset",
            str(Path.home() / ".alakoro" / "presets"),
            "JSON (*.json)",
        )
        if path:
            self.preset_edit.setText(path)

    def _log(self, message: str):
        self.log_edit.append(message)

    def _run(self):
        input_dir = self.input_edit.text().strip()
        output_dir = self.output_edit.text().strip()
        preset_path = self.preset_edit.text().strip()

        if not input_dir or not output_dir or not preset_path:
            QMessageBox.warning(self, "Aviso / Warning", "Preencha todos os campos / Fill all fields")
            return

        try:
            pipeline = json.loads(Path(preset_path).read_text(encoding="utf-8"))
        except Exception as exc:
            QMessageBox.critical(self, "Erro / Error", f"Preset inválido:\n{exc}")
            return

        # Coleta arquivos compatíveis
        extensions = set(_EXTENSION_HINTS.keys()) | {".nc", ".npy", ".csv", ".dasdae"}
        files = [
            str(p) for p in Path(input_dir).iterdir()
            if p.is_file() and p.suffix.lower() in extensions
        ]
        files.sort()

        if not files:
            QMessageBox.warning(self, "Aviso / Warning", "Nenhum arquivo compatível encontrado")
            return

        self._log(f"Iniciando batch com {len(files)} arquivos...")
        self.run_btn.setEnabled(False)
        self.cancel_run_btn.setEnabled(True)
        self.progress.setValue(0)

        self._worker_thread = QThread()
        self._worker = BatchWorker(
            files,
            pipeline,
            output_dir,
            export_format=self.format_combo.currentText(),
        )
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.file_started.connect(lambda p: self._log(f"Processando / Processing: {Path(p).name}"))
        self._worker.file_finished.connect(self._on_file_finished)
        self._worker.file_error.connect(self._on_file_error)
        self._worker.progress_percent.connect(self.progress.setValue)
        self._worker.finished.connect(self._on_finished)

        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)

        self._worker_thread.start()

    def _on_file_finished(self, path: str, out_path: str):
        self._log(f"✅ Concluído / Done: {Path(path).name} → {out_path}")

    def _on_file_error(self, path: str, message: str):
        self._log(f"❌ Erro / Error: {Path(path).name}\n{message}")

    def _on_finished(self):
        self._log("Batch finalizado / Batch finished")
        self.run_btn.setEnabled(True)
        self.cancel_run_btn.setEnabled(False)

    def _cancel(self):
        if self._worker is not None:
            self._worker.cancel()
            self._log("Cancelamento solicitado / Cancellation requested")
