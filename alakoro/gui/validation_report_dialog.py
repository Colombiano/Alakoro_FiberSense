"""
Diálogo de relatório detalhado de validação de assinaturas.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)


class ValidationReportDialog(QDialog):
    """Exibe o relatório detalhado de validação com exportação HTML."""

    def __init__(self, result: dict, parent=None):
        super().__init__(parent)
        self._result = result
        self.setWindowTitle("Relatório de Validação / Validation Report")
        self.setMinimumSize(700, 500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        summary = self._result.get("summary", "")
        passed = self._result.get("passed", 0)
        total = self._result.get("total", 0)
        rate = self._result.get("success_rate", 0.0)

        layout.addWidget(QLabel(f"<b>{summary}</b>" if summary else f"<b>{passed}/{total} passaram ({rate:.0f}%)</b>"))

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Status", "Mensagem / Message", "Detalhes / Details"])

        tests = self._result.get("tests", [])
        self.table.setRowCount(len(tests))
        for i, test in enumerate(tests):
            status = "✅" if test.get("passed", False) else "❌"
            self.table.setItem(i, 0, QTableWidgetItem(status))
            self.table.setItem(i, 1, QTableWidgetItem(test.get("message", "")))
            details = test.get("details", "")
            if not isinstance(details, str):
                details = str(details)
            self.table.setItem(i, 2, QTableWidgetItem(details))

        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # JSON bruto
        layout.addWidget(QLabel("JSON completo / Full JSON:"))
        self.json_edit = QTextEdit()
        import json
        self.json_edit.setPlainText(json.dumps(self._result, indent=2, default=str))
        self.json_edit.setMaximumHeight(150)
        layout.addWidget(self.json_edit)

        btn_layout = QHBoxLayout()
        export_html_btn = QPushButton("Exportar HTML / Export HTML")
        export_html_btn.clicked.connect(self._export_html)
        close_btn = QPushButton("Fechar / Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(export_html_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _export_html(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar relatório / Save report",
            "",
            "HTML (*.html);;Todos os arquivos (*)",
        )
        if not path:
            return

        html = self._to_html()
        Path(path).write_text(html, encoding="utf-8")

    def _to_html(self) -> str:
        passed = self._result.get("passed", 0)
        total = self._result.get("total", 0)
        rate = self._result.get("success_rate", 0.0)
        summary = self._result.get("summary", f"{passed}/{total} passaram ({rate:.0f}%)")

        rows = ""
        for test in self._result.get("tests", []):
            status = "✅ PASS" if test.get("passed", False) else "❌ FAIL"
            rows += f"<tr><td>{status}</td><td>{test.get('message', '')}</td><td>{test.get('details', '')}</td></tr>"

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Alakoro Validation Report</title>
    <style>
        body {{ font-family: sans-serif; margin: 2em; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
        th {{ background: #f0f0f0; }}
    </style>
</head>
<body>
    <h1>Alakoro FiberSense — Validation Report</h1>
    <h2>{summary}</h2>
    <table>
        <tr><th>Status</th><th>Message</th><th>Details</th></tr>
        {rows}
    </table>
</body>
</html>"""
