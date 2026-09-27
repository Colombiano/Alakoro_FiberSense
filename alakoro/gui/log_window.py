"""
Janela de log persistente da GUI.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


LOG_DIR = Path.home() / ".alakoro"
LOG_FILE = LOG_DIR / "alakoro.log"


def setup_logging() -> logging.Logger:
    """Configura logger que escreve em arquivo e também pode ser exibido na GUI."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("alakoro.gui")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


class LogWindow(QDialog):
    """Janela de log com níveis INFO, WARNING, ERROR."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Log do Alakoro / Alakoro Log")
        self.setMinimumSize(700, 400)
        self._setup_ui()
        self._load_log()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)

        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("Atualizar / Refresh")
        refresh_btn.clicked.connect(self._load_log)
        clear_btn = QPushButton("Limpar / Clear")
        clear_btn.clicked.connect(self._clear_log)
        close_btn = QPushButton("Fechar / Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _load_log(self):
        if LOG_FILE.exists():
            self.log_edit.setPlainText(LOG_FILE.read_text(encoding="utf-8"))
            scrollbar = self.log_edit.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        else:
            self.log_edit.setPlainText("Nenhum log encontrado / No log found")

    def _clear_log(self):
        if LOG_FILE.exists():
            LOG_FILE.write_text("", encoding="utf-8")
        self._load_log()


def log_message(level: str, message: str):
    """Registra mensagem no logger e no arquivo."""
    logger = setup_logging()
    level = level.upper()
    if level == "DEBUG":
        logger.debug(message)
    elif level == "INFO":
        logger.info(message)
    elif level == "WARNING":
        logger.warning(message)
    elif level == "ERROR":
        logger.error(message)
    else:
        logger.info(message)
