"""
Alakoro FiberSense — Data Loader para GUI Qt

Diálogo e funções utilitárias para carregar arquivos DFOS e detectar
formato/modalidade.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QComboBox,
    QVBoxLayout,
)

from src.gui.workers.load_worker import LoadWorker
from src.gui.format_hints import detect_format
from src.io.alakoro_spool import AlakoroPatch
from src.io.dasdae import DASDAEAdapter


def load_patch(path: str | Path, modality: str = "das") -> Optional[AlakoroPatch]:
    """
    Carrega um arquivo DFOS e retorna AlakoroPatch.

    Tenta primeiro via registry de drivers proprietários (com fallback
    DASCore/Xdas). Se falhar, tenta carregar como array NumPy simples.
    """
    path = Path(path)
    if not path.exists():
        return None

    # 1. Tentar registry de drivers (fallback automático para DASCore/Xdas)
    try:
        from src.io.drivers import read_vendor

        return read_vendor(str(path))
    except Exception:
        pass

    # 2. Tentar DASCore diretamente
    try:
        import dascore as dc

        patch = dc.read(str(path))[0]
        return DASDAEAdapter.from_dascore(patch, modality=modality)
    except Exception:
        pass

    # 3. Tentar Xdas diretamente
    try:
        from src.io.xdas_formats import read_xdas

        return read_xdas(str(path), modality=modality)
    except Exception:
        pass

    return None


class DataLoaderDialog(QDialog):
    """Diálogo de seleção de arquivo e configuração de carregamento."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Carregar Dados / Load Data")
        self.setMinimumWidth(500)
        self._patch: Optional[AlakoroPatch] = None
        self._worker_thread: Optional[QThread] = None
        self._worker: Optional[LoadWorker] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Arquivo
        file_layout = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("Selecione um arquivo ou diretório...")
        browse_btn = QPushButton("📂 Procurar...")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(self.file_edit)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)

        # Informações de formato
        form = QFormLayout()
        self.format_label = QLabel("—")
        form.addRow("Formato detectado / Detected format:", self.format_label)

        self.modality_combo = QComboBox()
        self.modality_combo.addItems(["das", "dts", "dss"])
        self.modality_combo.setCurrentText("das")
        form.addRow("Modalidade / Modality:", self.modality_combo)

        layout.addLayout(form)

        # Botões
        btn_layout = QHBoxLayout()
        self.load_btn = QPushButton("🚀 Carregar / Load")
        self.load_btn.clicked.connect(self._load)
        cancel_btn = QPushButton("Cancelar / Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.load_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status_label = QLabel("Aguardando seleção... / Waiting for selection...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar arquivo DFOS / Select DFOS file",
            "",
            "DFOS files (*.tdms *.segy *.sgy *.h5 *.hdf5 *.nc *.netcdf *.dasdae "
            "*.pkl *.pickle *.miniseed *.mseed *.exd *.*);;All files (*)",
        )
        if path:
            self.file_edit.setText(path)
            fmt = detect_format(Path(path))
            self.format_label.setText(fmt)

    def _load(self):
        path = self.file_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "Aviso / Warning", "Selecione um arquivo / Select a file")
            return

        modality = self.modality_combo.currentText()
        self.status_label.setText("Carregando... / Loading...")
        self.progress.setVisible(True)
        self.load_btn.setEnabled(False)

        self._worker_thread = QThread()
        self._worker = LoadWorker(path, modality=modality)
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.status_label.setText)
        self._worker.finished.connect(self._on_load_finished)
        self._worker.error.connect(self._on_load_error)

        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)

        self._worker_thread.start()

    def _on_load_finished(self, patch: Optional[AlakoroPatch]):
        self.progress.setVisible(False)
        self.load_btn.setEnabled(True)
        if patch is None:
            QMessageBox.critical(
                self,
                "Erro / Error",
                f"Não foi possível carregar:\n{self.file_edit.text()}\n\n"
                "Could not load the selected file.",
            )
            self.status_label.setText("Falha no carregamento / Load failed")
            return

        self._patch = patch
        self.status_label.setText(
            f"✅ Carregado: {patch.shape} / Loaded: {patch.shape}"
        )
        self.accept()

    def _on_load_error(self, message: str):
        self.progress.setVisible(False)
        self.load_btn.setEnabled(True)
        self.status_label.setText("Erro / Error")

    def patch(self) -> Optional[AlakoroPatch]:
        """Retorna o AlakoroPatch carregado após execução do diálogo."""
        return self._patch

    @staticmethod
    def get_patch(parent=None) -> Optional[AlakoroPatch]:
        """Método estático de conveniência."""
        dialog = DataLoaderDialog(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            patch = dialog.patch()
            if patch is not None and dialog.file_edit.text():
                patch.source_path = dialog.file_edit.text()
            return patch
        return None
