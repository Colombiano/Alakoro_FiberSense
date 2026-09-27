"""
Diálogo para exportar figura científica configurável.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)


class ExportFigureDialog(QDialog):
    """Exporta heatmap/perfil com tamanho, DPI e colormap configuráveis."""

    def __init__(self, data: np.ndarray, title: str = "Alakoro Plot", parent=None):
        super().__init__(parent)
        self._data = data
        self._title = title
        self.setWindowTitle("Exportar Figura / Export Figure")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.width_spin = QSpinBox()
        self.width_spin.setRange(2, 32)
        self.width_spin.setValue(10)
        form.addRow("Width (in):", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(2, 32)
        self.height_spin.setValue(6)
        form.addRow("Height (in):", self.height_spin)

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(150)
        form.addRow("DPI:", self.dpi_spin)

        self.cmap_combo = QComboBox()
        self.cmap_combo.addItems(["RdBu_r", "seismic", "viridis", "plasma", "inferno", "magma"])
        form.addRow("Colormap:", self.cmap_combo)

        self.title_edit = QLineEdit(self._title)
        form.addRow("Title:", self.title_edit)

        self.kind_combo = QComboBox()
        self.kind_combo.addItems(["heatmap", "profile"])
        form.addRow("Kind:", self.kind_combo)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        export_btn = QPushButton("Exportar / Export")
        export_btn.clicked.connect(self._export)
        cancel_btn = QPushButton("Cancelar / Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(export_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar figura / Save figure",
            "",
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg);;JPEG (*.jpg *.jpeg)",
        )
        if not path:
            return

        try:
            fig, ax = plt.subplots(
                figsize=(self.width_spin.value(), self.height_spin.value()),
                dpi=self.dpi_spin.value(),
            )
            kind = self.kind_combo.currentText()
            cmap = self.cmap_combo.currentText()

            if kind == "heatmap":
                im = ax.imshow(self._data.T, aspect="auto", cmap=cmap, origin="lower")
                ax.set_xlabel("Time / Tempo")
                ax.set_ylabel("Channel / Canal")
                plt.colorbar(im, ax=ax)
            else:
                n_t = self._data.shape[0]
                for t in [0, n_t // 2, n_t - 1]:
                    ax.plot(self._data[t, :], label=f"t={t}")
                ax.set_xlabel("Channel / Canal")
                ax.set_ylabel("Amplitude")
                ax.legend()

            ax.set_title(self.title_edit.text())
            fig.tight_layout()
            fig.savefig(path, dpi=self.dpi_spin.value())
            plt.close(fig)
            QMessageBox.information(self, "Concluído / Done", f"Salvo em / Saved to:\n{path}")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Erro / Error", f"Falha ao exportar:\n{exc}")
