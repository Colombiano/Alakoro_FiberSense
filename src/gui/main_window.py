"""
Alakoro FiberSense — GUI Principal (PySide6 + PyQtGraph)

Aplicação desktop para carregar, visualizar e processar dados DFOS.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Optional

import numpy as np
import pyqtgraph as pg
import qdarkstyle
from PySide6.QtCore import QSettings, QThread, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.io.alakoro_spool import AlakoroPatch
from src.io.dasdae import DASDAEAdapter

from .batch_dialog import BatchDialog
from .data_loader import DataLoaderDialog, load_patch
from .export_figure_dialog import ExportFigureDialog
from .i18n import install_translators
from .log_window import LogWindow, log_message
from .report_dialog import ReportDialog
from .processors.filter_panel import FilterPanel
from .processors.ml_panel import MLPanel
from .processors.preset_panel import PresetPanel
from .processors.thermal_panel import ThermalPanel
from .viewers.heatmap_view import HeatmapView
from .viewers.profile_view import ProfileView
from .viewers.spectrogram_view import SpectrogramView
from .workers.processing_worker import ProcessingWorker


class AlakoroMainWindow(QMainWindow):
    """Janela principal do Alakoro FiberSense."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎸 Alakoro FiberSense v2.11.0")
        self.resize(1400, 900)

        self._patch: Optional[AlakoroPatch] = None
        self._display_data: Optional[np.ndarray] = None
        self._worker_thread: Optional[QThread] = None

        # Undo/redo de processamentos
        self._history: list[tuple[AlakoroPatch, np.ndarray]] = []
        self._history_index: int = -1
        self._max_history = 10

        # Fila de processamento para presets/batch
        self._pending_pipeline: list[dict] = []

        # Último resultado de validação para relatório
        self._last_validation_result: dict | None = None

        # Persistência de arquivos recentes
        self._settings = QSettings("Alakoro", "FiberSense")
        self._recent_files: list[str] = []

        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_status_bar()
        self._connect_signals()
        self._load_recent_files()

        # Habilitar drag-and-drop
        self.setAcceptDrops(True)

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
        self.spectrogram = SpectrogramView()
        self.viewer_tabs.addTab(self.heatmap, "🗺️ Heatmap")
        self.viewer_tabs.addTab(self.profile, "📈 Profiles")
        self.viewer_tabs.addTab(self.spectrogram, "📊 Spectrogram")
        self.splitter.addWidget(self.viewer_tabs)

        # Painel lateral de processadores
        self.processor_tabs = QTabWidget()
        self.filter_panel = FilterPanel()
        self.thermal_panel = ThermalPanel()
        self.ml_panel = MLPanel()
        self.preset_panel = PresetPanel()
        self.processor_tabs.addTab(self.filter_panel, "🔧 Filters")
        self.processor_tabs.addTab(self.thermal_panel, "🌡️ Thermal")
        self.processor_tabs.addTab(self.ml_panel, "🤖 ML/Validate")
        self.processor_tabs.addTab(self.preset_panel, "📋 Presets")
        self.splitter.addWidget(self.processor_tabs)

        self.splitter.setSizes([1000, 400])

    def _setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Arquivo / File")

        open_action = file_menu.addAction("📂 Abrir / Open...")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file)

        self._recent_menu = file_menu.addMenu("🕘 Recentes / Recent")
        self._update_recent_menu()

        save_action = file_menu.addAction("💾 Salvar / Save...")
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_result)

        batch_action = file_menu.addAction("🔄 Batch Processing...")
        batch_action.triggered.connect(self._open_batch_dialog)

        export_fig_action = file_menu.addAction("📊 Exportar Figura / Export Figure...")
        export_fig_action.triggered.connect(self._open_export_figure_dialog)

        report_action = file_menu.addAction("📄 Gerar Relatório / Generate Report...")
        report_action.triggered.connect(self._open_report_dialog)

        file_menu.addSeparator()

        exit_action = file_menu.addAction("❌ Sair / Exit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

        # Menu Ajuda / Help
        help_menu = menubar.addMenu("Ajuda / Help")
        log_action = help_menu.addAction("📝 Ver Log / View Log")
        log_action.triggered.connect(self._open_log_window)

        # Menu Editar / Edit
        edit_menu = menubar.addMenu("Editar / Edit")

        self._undo_action = edit_menu.addAction("↩ Desfazer / Undo")
        self._undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self._undo_action.triggered.connect(self._undo)
        self._undo_action.setEnabled(False)

        self._redo_action = edit_menu.addAction("↪ Refazer / Redo")
        self._redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self._redo_action.triggered.connect(self._redo)
        self._redo_action.setEnabled(False)

    def _setup_toolbar(self):
        toolbar = QToolBar("Principal / Main")
        self.addToolBar(toolbar)

        open_btn = toolbar.addAction("📂 Abrir")
        open_btn.triggered.connect(self._open_file)

        save_btn = toolbar.addAction("💾 Salvar")
        save_btn.triggered.connect(self._save_result)

        toolbar.addSeparator()

        undo_btn = toolbar.addAction("↩ Desfazer")
        undo_btn.triggered.connect(self._undo)
        self._undo_tool_action = undo_btn

        redo_btn = toolbar.addAction("↪ Refazer")
        redo_btn.triggered.connect(self._redo)
        self._redo_tool_action = redo_btn

        self._update_undo_redo_actions()

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
        self.ml_panel.mask_requested.connect(self._apply_anomaly_mask)
        self.ml_panel.report_requested.connect(self._show_validation_report)
        self.preset_panel.apply_preset_requested.connect(self._run_preset_pipeline)

        # Cursor sincronizado entre visualizadores
        self.heatmap.cursor_moved.connect(self._on_heatmap_cursor_moved)
        self.heatmap.cursor_clicked.connect(self._on_heatmap_cursor_clicked)
        self.heatmap.roi_changed.connect(self._on_heatmap_roi_changed)

    def _open_file(self):
        patch = DataLoaderDialog.get_patch(self)
        if patch is not None:
            log_message("info", f"Arquivo aberto / File opened: {getattr(patch, 'source_path', '')}")
            self._set_patch(patch)

    def _open_log_window(self):
        dialog = LogWindow(self)
        dialog.exec()

    def _open_batch_dialog(self):
        dialog = BatchDialog(self)
        dialog.exec()

    def _open_export_figure_dialog(self):
        if self._display_data is None:
            QMessageBox.warning(self, "Aviso / Warning", "Nenhum dado para exportar")
            return
        title = self._patch.modality.upper() if self._patch else "Alakoro"
        dialog = ExportFigureDialog(self._display_data, title=title, parent=self)
        dialog.exec()

    def _open_report_dialog(self):
        if self._display_data is None:
            QMessageBox.warning(self, "Aviso / Warning", "Nenhum dado para relatório")
            return
        modality = self._patch.modality if self._patch else "unknown"
        source = getattr(self._patch, "source_path", "")
        dialog = ReportDialog(
            self._display_data,
            modality,
            self._last_validation_result,
            source,
            parent=self,
        )
        dialog.exec()

    def _open_recent_file(self, path: str):
        patch = load_patch(path)
        if patch is not None:
            self._set_patch(patch)
        else:
            QMessageBox.critical(self, "Erro / Error", f"Não foi possível carregar:\n{path}")
            self._remove_recent_file(path)

    def _set_patch(self, patch: AlakoroPatch):
        self._patch = patch
        self._display_data = patch.data
        self._history.clear()
        self._history_index = -1
        self._update_undo_redo_actions()
        self._update_viewers()
        self._add_recent_file(patch.source_path if hasattr(patch, "source_path") else "")
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

        # Taxa de amostragem padrão; idealmente extrair do patch
        fs = getattr(self._patch, "sample_rate_hz", 1000.0)
        self.spectrogram.set_data(self._display_data, sample_rate_hz=fs)

    def _on_heatmap_cursor_moved(self, t: int, c: int, amp: float):
        modality = self._patch.modality.upper() if self._patch else "—"
        self.status.showMessage(
            f"{modality} | t={t}, ch={c}, amp={amp:.4f}"
        )

    def _on_heatmap_cursor_clicked(self, t: int, c: int):
        """Clicar no heatmap fixa o perfil no tempo selecionado."""
        if self._display_data is None:
            return
        self.profile.set_data(self._display_data, times=[t])
        self.status.showMessage(f"Perfil fixado no tempo / Profile pinned at time: t={t}")

    def _on_heatmap_roi_changed(self, x0: int, y0: int, x1: int, y1: int):
        """Atualiza status com a região selecionada pelo ROI."""
        self.status.showMessage(
            f"ROI: t=[{x0}:{x1}], ch=[{y0}:{y1}] "
            f"({x1 - x0} x {y1 - y0})"
        )

    # ── Drag-and-drop ──
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            patch = load_patch(path)
            if patch is not None:
                self._set_patch(patch)
            else:
                QMessageBox.critical(self, "Erro / Error", f"Não foi possível carregar:\n{path}")

    # ── Recent files ──
    def _load_recent_files(self):
        self._recent_files = self._settings.value("recentFiles", []) or []
        if isinstance(self._recent_files, str):
            self._recent_files = [self._recent_files]
        self._recent_files = [f for f in self._recent_files if Path(f).exists()]
        self._update_recent_menu()

    def _add_recent_file(self, path: str):
        if not path or not Path(path).exists():
            return
        if path in self._recent_files:
            self._recent_files.remove(path)
        self._recent_files.insert(0, path)
        self._recent_files = self._recent_files[:10]
        self._settings.setValue("recentFiles", self._recent_files)
        self._update_recent_menu()

    def _remove_recent_file(self, path: str):
        if path in self._recent_files:
            self._recent_files.remove(path)
            self._settings.setValue("recentFiles", self._recent_files)
            self._update_recent_menu()

    def _update_recent_menu(self):
        self._recent_menu.clear()
        if not self._recent_files:
            action = self._recent_menu.addAction("Nenhum arquivo recente / No recent files")
            action.setEnabled(False)
            return
        for path in self._recent_files:
            action = self._recent_menu.addAction(Path(path).name)
            action.setToolTip(path)
            action.triggered.connect(lambda checked, p=path: self._open_recent_file(p))
        self._recent_menu.addSeparator()
        clear_action = self._recent_menu.addAction("Limpar / Clear")
        clear_action.triggered.connect(self._clear_recent_files)

    def _clear_recent_files(self):
        self._recent_files.clear()
        self._settings.setValue("recentFiles", self._recent_files)
        self._update_recent_menu()

    # ── Undo/Redo ──
    def _push_history(self):
        """Salva estado atual do patch e dados de exibição."""
        if self._patch is None:
            return
        # Remove estados à frente do índice atual (após um undo + novo processamento)
        self._history = self._history[: self._history_index + 1]
        self._history.append((copy.deepcopy(self._patch), self._display_data.copy()))
        if len(self._history) > self._max_history:
            self._history.pop(0)
        self._history_index = len(self._history) - 1
        self._update_undo_redo_actions()

    def _undo(self):
        if self._history_index > 0:
            self._history_index -= 1
            self._restore_history()

    def _redo(self):
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self._restore_history()

    def _restore_history(self):
        patch, data = self._history[self._history_index]
        self._patch = copy.deepcopy(patch)
        self._display_data = data.copy()
        self._update_viewers()
        self._update_undo_redo_actions()
        self.status.showMessage(f"Histórico / History: {self._history_index + 1}/{len(self._history)}")

    def _update_undo_redo_actions(self):
        can_undo = self._history_index > 0
        can_redo = self._history_index < len(self._history) - 1
        self._undo_action.setEnabled(can_undo)
        self._redo_action.setEnabled(can_redo)
        self._undo_tool_action.setEnabled(can_undo)
        self._redo_tool_action.setEnabled(can_redo)

    def _run_processor(self, action: str, kwargs: dict):
        if self._patch is None:
            QMessageBox.warning(self, "Aviso / Warning", "Carregue dados primeiro / Load data first")
            return

        # Salva estado atual antes de processar
        self._push_history()
        self._start_worker(action, kwargs)

    def _run_preset_pipeline(self, pipeline: list[dict]):
        if self._patch is None:
            QMessageBox.warning(self, "Aviso / Warning", "Carregue dados primeiro / Load data first")
            return
        if not pipeline:
            return

        # Salva estado inicial
        self._push_history()
        self._pending_pipeline = list(pipeline)
        first = self._pending_pipeline.pop(0)
        self._start_worker(first.get("action", ""), first.get("kwargs", {}))

    def _run_next_in_pipeline(self):
        if self._pending_pipeline:
            next_step = self._pending_pipeline.pop(0)
            self._start_worker(next_step.get("action", ""), next_step.get("kwargs", {}))

    def _start_worker(self, action: str, kwargs: dict):
        if self._worker_thread is not None and self._worker_thread.isRunning():
            QMessageBox.warning(self, "Ocupado / Busy", "Um processamento já está em execução")
            return

        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.status.showMessage(f"Running {action}...")

        self._worker_thread = QThread()
        self._worker = ProcessingWorker(self._patch, action, kwargs)
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.progress.connect(self.status.showMessage)
        self._worker.progress_percent.connect(self.progress.setValue)

        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.error.connect(self._worker_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)

        self._worker_thread.start()

    def _on_worker_finished(self, result):
        self.progress.setVisible(False)
        source_path = getattr(self._patch, "source_path", None)

        if isinstance(result, AlakoroPatch):
            self._patch = result
            if source_path and not getattr(self._patch, "source_path", None):
                self._patch.source_path = source_path
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

        self._update_undo_redo_actions()

        # Continua pipeline se houver próximos passos
        if self._pending_pipeline:
            self._run_next_in_pipeline()
            return

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
            self._last_validation_result = result
            summary = f"{result['passed']}/{result['total']} passaram ({result['success_rate']:.0f}%)"
            self.ml_panel.set_validation_summary(summary)
            self.status.showMessage(f"Validation: {summary}")
        except Exception as exc:
            QMessageBox.critical(self, "Erro / Error", f"Validation failed: {exc}")

    def _apply_anomaly_mask(self, threshold: float):
        if self._display_data is None:
            QMessageBox.warning(self, "Aviso / Warning", "Carregue dados primeiro")
            return
        # Stub: máscara baseada em percentil de amplitude
        q = np.quantile(np.abs(self._display_data), threshold)
        mask = (np.abs(self._display_data) > q).astype(np.float32)
        self.heatmap.set_overlay(mask)
        count = int(mask.sum())
        self.ml_panel.set_inference_result(
            f"Máscara aplicada: {count} pixels acima do threshold / Mask applied: {count} pixels above threshold"
        )
        self.status.showMessage(f"Overlay: {count} pixels | threshold={threshold:.2f}")

    def _show_validation_report(self):
        if self._last_validation_result is None:
            QMessageBox.information(self, "Info", "Execute a validação primeiro / Run validation first")
            return
        from src.gui.validation_report_dialog import ValidationReportDialog
        dialog = ValidationReportDialog(self._last_validation_result, self)
        dialog.exec()

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
            "NetCDF (*.nc);;NumPy (*.npy);;PNG image (*.png);;CSV (*.csv);;Avro (*.avro);;Protobuf (*.protobuf *.pb)",
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
            elif suffix.endswith(".avro"):
                self._save_avro(path)
            elif suffix.endswith(".protobuf") or suffix.endswith(".pb"):
                self._save_protobuf(path)
            else:
                np.save(path, self._display_data)
            self.status.showMessage(f"Salvo em / Saved to: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Erro / Error", f"Falha ao salvar: {exc}")

    def _save_avro(self, path: str):
        """Salva em Avro se o módulo estiver disponível."""
        try:
            from src.io.avro_format import save_avro
            save_avro(path, self._display_data)
        except ImportError:
            QMessageBox.information(
                self,
                "Info",
                "Serialização Avro ainda não implementada.\n"
                "Compile com -DALAKORO_WITH_AVRO=ON ou implemente src/io/avro_format.py",
            )
            raise RuntimeError("Avro não disponível")

    def _save_protobuf(self, path: str):
        """Salva em Protobuf se o módulo estiver disponível."""
        try:
            from src.io.protobuf_format import save_protobuf
            save_protobuf(path, self._display_data)
        except ImportError:
            QMessageBox.information(
                self,
                "Info",
                "Serialização Protobuf ainda não implementada.\n"
                "Compile com -DALAKORO_WITH_PROTOBUF=ON ou implemente src/io/protobuf_format.py",
            )
            raise RuntimeError("Protobuf não disponível")


def main():
    """Entry point da GUI."""
    import sys

    pg.setConfigOptions(useOpenGL=False, antialias=True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside6())

    install_translators(app)

    window = AlakoroMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
