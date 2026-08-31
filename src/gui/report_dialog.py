"""
Diálogo de geração de relatório automatizado HTML/PDF.
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class ReportDialog(QDialog):
    """Gera relatório automatizado a partir dos dados e metadados atuais."""

    def __init__(
        self,
        data: np.ndarray,
        modality: str,
        validation_result: dict | None,
        source_path: str,
        parent=None,
    ):
        super().__init__(parent)
        self._data = data
        self._modality = modality
        self._validation = validation_result
        self._source_path = source_path
        self.setWindowTitle("Gerar Relatório / Generate Report")
        self.setMinimumWidth(500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.title_edit = QLineEdit("Alakoro FiberSense — Relatório / Report")
        form.addRow("Título / Title:", self.title_edit)

        self.author_edit = QLineEdit("Alakoro FiberSense")
        form.addRow("Autor / Author:", self.author_edit)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        html_btn = QPushButton("Exportar HTML / Export HTML")
        html_btn.clicked.connect(self._export_html)
        pdf_btn = QPushButton("Exportar PDF / Export PDF")
        pdf_btn.clicked.connect(self._export_pdf)
        cancel_btn = QPushButton("Cancelar / Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(html_btn)
        btn_layout.addWidget(pdf_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _figure_to_base64(self) -> str:
        fig, ax = plt.subplots(figsize=(10, 5))
        vmax = np.max(np.abs(self._data))
        im = ax.imshow(
            self._data.T,
            aspect="auto",
            cmap="RdBu_r",
            origin="lower",
            vmin=-vmax,
            vmax=vmax,
        )
        ax.set_title(f"{self._modality.upper()} — {self._data.shape}")
        ax.set_xlabel("Time / Tempo")
        ax.set_ylabel("Channel / Canal")
        plt.colorbar(im, ax=ax)
        buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format="png", dpi=120)
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def _build_html(self) -> str:
        img_b64 = self._figure_to_base64()
        validation_html = ""
        if self._validation:
            passed = self._validation.get("passed", 0)
            total = self._validation.get("total", 0)
            rate = self._validation.get("success_rate", 0.0)
            validation_html = f"<h2>Validação / Validation</h2><p>{passed}/{total} passaram ({rate:.0f}%)</p><ul>"
            for test in self._validation.get("tests", []):
                status = "✅" if test.get("passed", False) else "❌"
                validation_html += f"<li>{status} {test.get('message', '')}</li>"
            validation_html += "</ul>"

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{self.title_edit.text()}</title>
    <style>
        body {{ font-family: sans-serif; margin: 2em; color: #333; }}
        h1 {{ color: #2c3e50; }}
        img {{ max-width: 100%; border: 1px solid #ccc; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
        th {{ background: #f0f0f0; }}
    </style>
</head>
<body>
    <h1>{self.title_edit.text()}</h1>
    <p><b>Autor / Author:</b> {self.author_edit.text()}</p>
    <p><b>Fonte / Source:</b> {self._source_path}</p>
    <p><b>Modalidade / Modality:</b> {self._modality.upper()}</p>
    <p><b>Shape:</b> {self._data.shape}</p>

    <h2>Visualização / Visualization</h2>
    <img src="data:image/png;base64,{img_b64}" alt="heatmap">

    {validation_html}

    <h2>Metadados / Metadata</h2>
    <pre>{json.dumps({"shape": list(self._data.shape), "dtype": str(self._data.dtype)}, indent=2)}</pre>
</body>
</html>"""

    def _export_html(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar relatório HTML", "", "HTML (*.html)"
        )
        if path:
            Path(path).write_text(self._build_html(), encoding="utf-8")
            QMessageBox.information(self, "Concluído / Done", f"Salvo em / Saved to:\n{path}")

    def _export_pdf(self):
        try:
            import weasyprint
        except ImportError:
            QMessageBox.critical(
                self,
                "Erro / Error",
                "weasyprint não instalado.\nInstale com: pip install weasyprint",
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar relatório PDF", "", "PDF (*.pdf)"
        )
        if path:
            html = self._build_html()
            weasyprint.HTML(string=html).write_pdf(path)
            QMessageBox.information(self, "Concluído / Done", f"Salvo em / Saved to:\n{path}")
