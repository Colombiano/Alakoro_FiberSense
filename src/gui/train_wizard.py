"""
Wizard simplificado de treinamento de modelo ML para dados DFOS.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from PySide6.QtCore import QObject, QThread, Signal
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


class TrainWorker(QObject):
    """Treina modelo em thread separada."""

    finished = Signal(str)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, data_dir: str, model_type: str, output_path: str):
        super().__init__()
        self.data_dir = data_dir
        self.model_type = model_type
        self.output_path = output_path

    def run(self):
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.svm import SVC
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score
            import joblib

            self.progress.emit("Carregando dados / Loading data...")
            X, y = self._load_data()

            self.progress.emit("Treinando / Training...")
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            if self.model_type == "Random Forest":
                model = RandomForestClassifier(n_estimators=50, random_state=42)
            else:
                model = SVC(probability=True, random_state=42)

            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            acc = accuracy_score(y_test, y_pred)

            joblib.dump(model, self.output_path)
            self.finished.emit(f"Acurácia / Accuracy: {acc:.2%}\nSalvo em / Saved to: {self.output_path}")
        except Exception as exc:
            import traceback
            self.error.emit(traceback.format_exc())

    def _load_data(self) -> tuple[np.ndarray, np.ndarray]:
        """Carrega arquivos .npy com features e labels."""
        X_list, y_list = [], []
        for path in Path(self.data_dir).glob("*.npy"):
            arr = np.load(path)
            if arr.ndim == 1:
                X_list.append(arr)
                # Label vem do nome do arquivo antes do primeiro '_'
                label = int(path.stem.split("_")[0]) if path.stem[0].isdigit() else 0
                y_list.append(label)
        if not X_list:
            raise ValueError("Nenhum arquivo .npy encontrado na pasta")
        return np.vstack(X_list), np.array(y_list)


class TrainWizard(QDialog):
    """Wizard para treinar modelo simples a partir de features .npy."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Treinar Modelo / Train Model")
        self.setMinimumSize(600, 400)
        self._worker_thread: Optional[QThread] = None
        self._worker: Optional[TrainWorker] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        data_layout = QHBoxLayout()
        self.data_edit = QLineEdit()
        self.data_edit.setPlaceholderText("Pasta com .npy de features...")
        data_btn = QPushButton("Procurar...")
        data_btn.clicked.connect(self._browse_data)
        data_layout.addWidget(self.data_edit)
        data_layout.addWidget(data_btn)
        form.addRow("Dados / Data:", data_layout)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["Random Forest", "SVM"])
        form.addRow("Modelo / Model:", self.model_combo)

        out_layout = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Caminho para salvar .joblib...")
        out_btn = QPushButton("Procurar...")
        out_btn.clicked.connect(self._browse_output)
        out_layout.addWidget(self.output_edit)
        out_layout.addWidget(out_btn)
        form.addRow("Saída / Output:", out_layout)

        layout.addLayout(form)

        self.train_btn = QPushButton("▶ Treinar / Train")
        self.train_btn.clicked.connect(self._train)
        layout.addWidget(self.train_btn)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        layout.addWidget(QLabel("Log:"))
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)

        close_btn = QPushButton("Fechar / Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _browse_data(self):
        path = QFileDialog.getExistingDirectory(self, "Pasta de dados / Data folder")
        if path:
            self.data_edit.setText(path)

    def _browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar modelo / Save model",
            str(Path.home() / "model.joblib"),
            "Joblib (*.joblib)",
        )
        if path:
            self.output_edit.setText(path)

    def _train(self):
        data_dir = self.data_edit.text().strip()
        output_path = self.output_edit.text().strip()
        if not data_dir or not output_path:
            QMessageBox.warning(self, "Aviso / Warning", "Preencha todos os campos")
            return

        try:
            import sklearn, joblib  # noqa: F401
        except ImportError:
            QMessageBox.critical(
                self,
                "Erro / Error",
                "Instale scikit-learn e joblib:\npip install scikit-learn joblib",
            )
            return

        self.progress.setVisible(True)
        self.train_btn.setEnabled(False)
        self.log_edit.clear()

        self._worker_thread = QThread()
        self._worker = TrainWorker(data_dir, self.model_combo.currentText(), output_path)
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._log)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)

        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)

        self._worker_thread.start()

    def _log(self, message: str):
        self.log_edit.append(message)

    def _on_finished(self, message: str):
        self.progress.setVisible(False)
        self.train_btn.setEnabled(True)
        self._log(message)
        QMessageBox.information(self, "Concluído / Done", message)

    def _on_error(self, message: str):
        self.progress.setVisible(False)
        self.train_btn.setEnabled(True)
        self._log(message)
        QMessageBox.critical(self, "Erro / Error", message)
