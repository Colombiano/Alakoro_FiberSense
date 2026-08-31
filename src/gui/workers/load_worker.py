"""
Worker de carregamento de arquivos DFOS em background.
"""

from __future__ import annotations

import traceback
from typing import Optional

from PySide6.QtCore import QObject, Signal

from src.io.alakoro_spool import AlakoroPatch


class LoadWorker(QObject):
    """Carrega um arquivo DFOS em thread separada."""

    finished = Signal(object)  # AlakoroPatch ou None
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, path: str, modality: str = "das"):
        super().__init__()
        self.path = path
        self.modality = modality

    def run(self):
        try:
            from src.gui.data_loader import load_patch
            self.progress.emit("Carregando arquivo... / Loading file...")
            patch = load_patch(self.path, modality=self.modality)
            if patch is not None:
                patch.source_path = self.path
            self.finished.emit(patch)
        except Exception as exc:
            tb = traceback.format_exc()
            self.error.emit(f"Error loading file: {exc}\n{tb}")
            self.finished.emit(None)
