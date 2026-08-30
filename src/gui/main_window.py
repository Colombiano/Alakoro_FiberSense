"""
Alakoro FiberSense — GUI Principal (PySide6 + PyQtGraph)

Aplicação desktop para carregar, visualizar e processar dados DFOS.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pyqtgraph as pg
import qdarkstyle
from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.io.alakoro_spool import AlakoroPatch
from src.io.dasdae import DASDAEAdapter

from .data_loader import DataLoaderDialog, load_patch
from .processors.filter_panel import FilterPanel
from .processors.ml_panel import MLPanel
from .processors.thermal_panel import ThermalPanel
from .viewers.heatmap_view import HeatmapView
from .viewers.profile_view import ProfileView
from .workers.processing_worker import ProcessingWorker


class AlakoroMainWindow(QMainWindow):
    """Janela principal do Alakoro FiberSense."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎸 Alakoro FiberSense v2.10.0")
        self.resize(1400, 900)

        self._patch: Optional[AlakoroPatch] = None
        self._display_data: Optional[np.ndarray] = None
        self._worker_thread: Optional[QThread] = None

        self._setup_ui()
        self._setup_menu()
        self._setup_status_bar()
        self._connect_signals()

    def _setup_ui(self):
        # Widget central com splitter
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.splitter)

        # Aba de visualizadores
        self.viewer_tabs = QTabWidget()
        self.heatmap = HeatmapView()
        self.profile = ProfileView()
        self.viewer_tabs.addTab(self.heatmap, "🗺️ Heatmap")
        self.viewer_tabs.addTab(self.profile, "📈 Profiles")
        self.splitter.addWidget(self.viewer_tabs)

        # Painel lateral de processadores
        self.processor_tabs = QTabWidget()
        self.filter_panel = FilterPanel()
        self.thermal_panel = ThermalPanel()
        self.ml_panel = MLPanel()
        self.processor_tabs.addTab(self.filter_panel, "🔧 Filters")
        self.processor_tabs.addTab(self.thermal_panel, "🌡️ Thermal")
        self.processor_tabs.addTab(self.ml_panel, "🤖 ML/Validate")
        self.splitter.addWidget(self.processor_tabs)

        self.splitter.setSizes([1000, 400])

    def _setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Arquivo / File")

        open_action = file_menu.addAction("📂 Abrir / Open...")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file)

        save_action = file_menu.addAction("💾 Salvar / Save...")
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_result)

        file_menu.addSeparator()

        exit_action = file_menu.addAction("❌ Sair / Exit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

    def _setup_status_bar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Pronto / Ready")

        self.progress = QProgressBar()
        self.progress.setMaximumWidth(200)
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.status.addPermanentWidget(self.progress)

    def _connect_signals(self):
        self.filter_panel.process_requested.connect(self._run_processor)
        self.thermal_panel.process_requested.connect(self._run_processor)
        self.ml_panel.validate_requested.connect(self._run_validation)
        self.ml_panel.model_load_requested.connect(self._load_model)
        self.ml_panel.inference_requested.connect(self._run_inference)

    def _open_file(self):
        patch = DataLoaderDialog.get_patch(self)
        if patch is not None:
            self._set_patch(patch)

    def _set_patch(self, patch: AlakoroPatch):
        self._patch = patch
        self._display_data = patch.data
        self._update_viewers()
        self.status.showMessage(
            f"Loaded {patch.modality.upper()} {patch.shape}"
        )

    def _update_viewers(self):
        if self._display_data is None:
            return

        title = f"{self._patch.modality.upper()} — {self._display_data.shape}"
        self.heatmap.set_data(self._display_data, title=title)

        n_t = self._display_data.shape[0]
        times = [0, n_t // 4, n_t // 2, 3 * n_t // 4, n_t - 1]
        self.profile.set_data(self._display_data, times=times)

    def _run_processor(self, action: str, kwargs: dict):
        if self._patch is None:
            QMessageBox.warning(self, "Aviso / Warning", "Carregue dados primeiro / Load data first")
            return

        self._start_worker(action, kwargs)

    def _start_worker(self, action: str, kwargs: dict):
        if self._worker_thread is not None and self._worker_thread.isRunning():
            QMessageBox.warning(self, "Ocupado / Busy", "Um processamento já está em execução")
            return

        self.progress.setVisible(True)
        self.status.showMessage(f"Running {action}...")

        self._worker_thread = QThread()
        self._worker = ProcessingWorker(self._patch, action, kwargs)
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.progress.connect(self.status.showMessage)

        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.error.connect(self._worker_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)

        self._worker_thread.start()

    def _on_worker_finished(self, result):
        self.progress.setVisible(False)
        if isinstance(result, AlakoroPatch):
            self._patch = result
            self._display_data = result.data
            self._update_viewers()
            self.status.showMessage(f"Processamento concluído: {result.shape}")
        elif isinstance(result, np.ndarray):
            self._display_data = result
            self._update_viewers()
            self.status.showMessage(f"Resultado array: {result.shape}")
        elif isinstance(result, dict):
            # Pipeline DTS retorna dict
            if "temperature_corrected" in result:
                self._display_data = result["temperature_corrected"]
                self._update_viewers()
                self.status.showMessage(
                    f"DTS pipeline: {result['thermal_gradient'].shape}, "
                    f"anomalies={int(result['anomalies'].sum())}"
                )
            else:
                self.status.showMessage("Processamento concluído (resultado dict)")
        else:
            self.status.showMessage("Processamento concluído")

    def _on_worker_error(self, message: str):
        self.progress.setVisible(False)
        QMessageBox.critical(self, "Erro / Error", message)
        self.status.showMessage("Erro no processamento / Processing error")

    def _run_validation(self):
        if self._patch is None:
            QMessageBox.warning(self, "Aviso / Warning", "Carregue dados primeiro")
            return

        try:
            from src.simulation import AcquisitionConfig, WellGeometry
            from src.validation import SignatureValidator

            n_t, n_c = self._patch.shape
            well = WellGeometry(depth_top=0, depth_bottom=n_c, n_channels=n_c)
            acq = AcquisitionConfig(
                sampling_rate_hz=1000.0,
                trace_interval_s=2.0,
                duration_s=n_t * 2.0,
            )
            validator = SignatureValidator(well, acq)

            sig_data = {
                "signature_type": type(
                    "SigType",
                    (),
                    {"code": "CUSTOM", "pt": "Custom", "en": "Custom"},
                )(),
                "parameters": {},
                "dts": self._patch.data if self._patch.modality == "dts" else np.zeros_like(self._patch.data),
                "das": self._patch.data if self._patch.modality == "das" else np.zeros_like(self._patch.data),
            }

            result = validator.validate_signature(sig_data)
            summary = f"{result['passed']}/{result['total']} passaram ({result['success_rate']:.0f}%)"
            self.ml_panel.set_validation_summary(summary)
            self.status.showMessage(f"Validation: {summary}")
        except Exception as exc:
            QMessageBox.critical(self, "Erro / Error", f"Validation failed: {exc}")

    def _load_model(self, path: str):
        self.status.showMessage(f"Modelo carregado: {path}")
        self.ml_panel.set_inference_result("Modelo carregado / Model loaded")

    def _run_inference(self):
        self.ml_panel.set_inference_result("Inferência executada (stub) / Inference executed (stub)")
        self.status.showMessage("Inferência concluída / Inference done")

    def _save_result(self):
        if self._display_data is None:
            QMessageBox.warning(self, "Aviso / Warning", "Nenhum dado para salvar")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar resultado / Save result",
            "",
            "NetCDF (*.nc);;NumPy (*.npy);;PNG image (*.png);;CSV (*.csv)",
        )
        if not path:
            return

        try:
            suffix = path.lower()
            if suffix.endswith(".npy"):
                np.save(path, self._display_data)
            elif suffix.endswith(".csv"):
                np.savetxt(path, self._display_data, delimiter=",")
            elif suffix.endswith(".png"):
                import matplotlib.pyplot as plt
                plt.imsave(path, self._display_data.T, cmap="RdBu_r")
            elif suffix.endswith(".nc"):
                import xarray as xr
                xr.DataArray(self._display_data, dims=("time", "channel")).to_netcdf(path)
            else:
                np.save(path, self._display_data)
            self.status.showMessage(f"Salvo em / Saved to: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Erro / Error", f"Falha ao salvar: {exc}")


def main():
    """Entry point da GUI."""
    import sys

    pg.setConfigOptions(useOpenGL=True, antialias=True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside6())

    window = AlakoroMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
