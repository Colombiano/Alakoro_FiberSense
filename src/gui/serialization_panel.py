"""
Alakoro FiberSense — Painel de Serializacao e Streaming Kafka

Painel unificado para exportar/importar dados nos formatos Avro e Protobuf e
para conectar a um broker Kafka (producer/consumer).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.io.alakoro_spool import AlakoroPatch

from .workers.kafka_worker import KafkaConsumerWorker


class SerializationPanel(QWidget):
    """
    Painel lateral de serializacao Avro/Protobuf + streaming Kafka.

    Sinais:
        import_patch_requested(AlakoroPatch): patch importado deve ser exibido.
        status_message_requested(str): mensagem para a status bar.
        log_requested(str, str): (level, message) para o log.
    """

    import_patch_requested = Signal(object)
    status_message_requested = Signal(str)
    log_requested = Signal(str, str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._patch: Optional[AlakoroPatch] = None

        # Thread Kafka
        self._kafka_thread: Optional[QThread] = None
        self._kafka_worker: Optional[KafkaConsumerWorker] = None

        self._setup_ui()
        self._connect_signals()
        self._refresh_availability()

    # ─── UI ───

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.tabs = QTabWidget()
        self._setup_export_tab()
        self._setup_import_tab()
        self._setup_kafka_tab()
        layout.addWidget(self.tabs)

    def _setup_export_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group = QGroupBox("Exportar / Export")
        form = QFormLayout(group)

        self.export_format = QComboBox()
        self.export_format.addItems(["Avro", "Protobuf"])
        form.addRow("Formato / Format:", self.export_format)

        self.export_info = QLabel("Nenhum patch carregado / No patch loaded")
        self.export_info.setWordWrap(True)
        form.addRow(self.export_info)

        self.export_btn = QPushButton("💾 Exportar patch atual / Export current patch")
        form.addRow(self.export_btn)

        layout.addWidget(group)
        layout.addStretch()
        self.tabs.addTab(tab, "📤 Exportar")

    def _setup_import_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group = QGroupBox("Importar / Import")
        form = QFormLayout(group)

        self.import_btn = QPushButton("📂 Importar arquivo / Import file")
        form.addRow(self.import_btn)

        self.import_info = QLabel("Nenhum arquivo importado / No file imported")
        self.import_info.setWordWrap(True)
        form.addRow(self.import_info)

        layout.addWidget(group)
        layout.addStretch()
        self.tabs.addTab(tab, "📥 Importar")

    def _setup_kafka_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Configuracao
        config_group = QGroupBox("Configuracao / Configuration")
        config_form = QFormLayout(config_group)

        self.kafka_bootstrap = QLineEdit("localhost:9092")
        config_form.addRow("Bootstrap servers:", self.kafka_bootstrap)

        self.kafka_topic_data = QLineEdit("alakoro.data")
        config_form.addRow("Topico dados / Data topic:", self.kafka_topic_data)

        self.kafka_topic_profile = QLineEdit("alakoro.profile")
        config_form.addRow("Topico perfil / Profile topic:", self.kafka_topic_profile)

        self.kafka_group_id = QLineEdit("alakoro-gui")
        config_form.addRow("Group ID:", self.kafka_group_id)

        self.kafka_modality = QComboBox()
        self.kafka_modality.addItems(["das", "dts", "dss"])
        config_form.addRow("Modalidade / Modality:", self.kafka_modality)

        layout.addWidget(config_group)

        # Producer
        producer_group = QGroupBox("Producer")
        producer_form = QFormLayout(producer_group)

        self.producer_well_id = QLineEdit("W-01")
        producer_form.addRow("Well ID:", self.producer_well_id)

        self.producer_sampling_rate = QLineEdit("1000.0")
        producer_form.addRow("Sampling rate (Hz):", self.producer_sampling_rate)

        self.producer_gauge_length = QLineEdit("10.0")
        producer_form.addRow("Gauge length (m):", self.producer_gauge_length)

        self.producer_btn = QPushButton("🚀 Enviar patch atual / Send current patch")
        producer_form.addRow(self.producer_btn)

        layout.addWidget(producer_group)

        # Consumer
        consumer_group = QGroupBox("Consumer")
        consumer_layout = QVBoxLayout(consumer_group)

        btn_layout = QHBoxLayout()
        self.consumer_connect_btn = QPushButton("▶ Conectar / Connect")
        self.consumer_disconnect_btn = QPushButton("⏹ Desconectar / Disconnect")
        self.consumer_disconnect_btn.setEnabled(False)
        btn_layout.addWidget(self.consumer_connect_btn)
        btn_layout.addWidget(self.consumer_disconnect_btn)
        consumer_layout.addLayout(btn_layout)

        self.consumer_auto_display = QCheckBox("Auto-exibir / Auto-display")
        self.consumer_auto_display.setChecked(True)
        consumer_layout.addWidget(self.consumer_auto_display)

        self.consumer_counter = QLabel("Mensagens / Messages: 0")
        consumer_layout.addWidget(self.consumer_counter)

        layout.addWidget(consumer_group)

        # Log
        log_group = QGroupBox("Log Kafka")
        log_layout = QVBoxLayout(log_group)
        self.kafka_log = QPlainTextEdit()
        self.kafka_log.setReadOnly(True)
        self.kafka_log.setMaximumBlockCount(200)
        log_layout.addWidget(self.kafka_log)
        layout.addWidget(log_group)

        layout.addStretch()
        self.tabs.addTab(tab, "🔌 Kafka")

    def _connect_signals(self):
        self.export_btn.clicked.connect(self._export_patch)
        self.import_btn.clicked.connect(self._import_file)
        self.producer_btn.clicked.connect(self._produce_patch)
        self.consumer_connect_btn.clicked.connect(self._connect_kafka)
        self.consumer_disconnect_btn.clicked.connect(self._disconnect_kafka)

    # ─── Patch corrente ───

    def set_patch(self, patch: Optional[AlakoroPatch]):
        """Atualiza o patch corrente usado para export/produce."""
        self._patch = patch
        self._refresh_availability()

    # ─── Helpers ───

    def _refresh_availability(self):
        has_patch = self._patch is not None
        self.export_btn.setEnabled(has_patch)
        self.producer_btn.setEnabled(has_patch)

        if has_patch:
            self.export_info.setText(
                f"Shape: {self._patch.shape}\n"
                f"Modalidade / Modality: {self._patch.modality.upper()}"
            )
        else:
            self.export_info.setText("Nenhum patch carregado / No patch loaded")

    def _log(self, level: str, message: str):
        self.log_requested.emit(level, message)
        self.kafka_log.appendPlainText(f"[{level.upper()}] {message}")

    def _status(self, message: str):
        self.status_message_requested.emit(message)

    def _avro_available(self) -> bool:
        try:
            from src.io.avro_format import _HAS_FASTAVRO

            return _HAS_FASTAVRO
        except Exception:  # pragma: no cover
            return False

    def _protobuf_available(self) -> bool:
        try:
            from src.io.protobuf_format import _has_protobuf_core

            return _has_protobuf_core()
        except Exception:  # pragma: no cover
            return False

    # ─── Exportar ───

    def _export_patch(self):
        if self._patch is None:
            QMessageBox.warning(self, "Aviso / Warning", "Carregue dados primeiro / Load data first")
            return

        fmt = self.export_format.currentText()
        if fmt == "Avro" and not self._avro_available():
            QMessageBox.information(
                self,
                "Info",
                "fastavro nao esta instalado.\nfastavro is not installed.",
            )
            return
        if fmt == "Protobuf" and not self._protobuf_available():
            QMessageBox.information(
                self,
                "Info",
                "Extensao Protobuf nao disponivel.\nProtobuf extension not available.",
            )
            return

        filters = {
            "Avro": "Avro (*.avro)",
            "Protobuf": "Protobuf (*.pb *.protobuf)",
        }
        path, _ = QFileDialog.getSaveFileName(
            self,
            f"Exportar {fmt} / Export {fmt}",
            "",
            filters[fmt],
        )
        if not path:
            return
        self._export_patch_to(path)

    def _export_patch_to(self, path: str):
        """Exporta o patch corrente para o caminho especificado (usado em testes)."""
        fmt = self.export_format.currentText()
        try:
            if fmt == "Avro":
                from src.io.avro_format import write_avro

                payload = self._patch.to_avro_bytes()
                write_avro(path, [payload])
                size = Path(path).stat().st_size
            else:
                from src.io.protobuf_format import save_protobuf

                save_protobuf(path, self._patch)
                size = Path(path).stat().st_size

            self._status(f"Exportado / Exported: {path} ({size} bytes)")
            self._log("info", f"Exportado {fmt}: {path} ({size} bytes)")
        except Exception as exc:
            QMessageBox.critical(self, "Erro / Error", f"Falha ao exportar / Export failed:\n{exc}")
            self._log("error", f"Exportacao {fmt} falhou: {exc}")

    # ─── Importar ───

    def _import_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Importar arquivo / Import file",
            "",
            "Avro/Protobuf (*.avro *.pb *.protobuf);;Todos / All (*)",
        )
        if not path:
            return
        self._import_file_from(path)

    def _import_file_from(self, path: str):
        """Importa um arquivo a partir do caminho especificado (usado em testes)."""
        suffix = Path(path).suffix.lower()
        try:
            if suffix == ".avro":
                patch = self._import_avro(path)
            elif suffix in (".pb", ".protobuf"):
                patch = self._import_protobuf(path)
            else:
                # Tenta detectar pelo conteudo: Avro comeca com varint
                content = Path(path).read_bytes()
                if content[:1] == b"\x4f":
                    patch = self._import_avro(path)
                else:
                    patch = self._import_protobuf(path)

            self.import_info.setText(
                f"Shape: {patch.shape}\n"
                f"Modalidade / Modality: {patch.modality.upper()}"
            )
            self.import_patch_requested.emit(patch)
            self._status(f"Importado / Imported: {path}")
            self._log("info", f"Importado: {path} -> {patch}")
        except Exception as exc:
            QMessageBox.critical(self, "Erro / Error", f"Falha ao importar / Import failed:\n{exc}")
            self._log("error", f"Importacao falhou: {exc}")

    def _import_avro(self, path: str) -> AlakoroPatch:
        from src.io.avro_format import read_avro

        records = read_avro(path)
        if not records:
            raise ValueError("Arquivo Avro vazio / Empty Avro file")
        record = records[0]
        return AlakoroPatch.from_array(
            record["array"],
            modality=record["modality"].lower(),
            dt_s=1.0 / record["metadata"].get("sampling_rate_hz", 1.0)
            if record["metadata"].get("sampling_rate_hz", 0) > 0
            else 1.0,
            dx_m=record["metadata"].get("spatial_resolution_m", 1.0)
            if record["metadata"].get("spatial_resolution_m", 0) > 0
            else 1.0,
            units=record["metadata"].get("units", "1/s"),
        )

    def _import_protobuf(self, path: str) -> AlakoroPatch:
        from src.io.protobuf_format import load_protobuf

        return load_protobuf(path, modality="das")

    # ─── Kafka Producer ───

    def _produce_patch(self):
        if self._patch is None:
            QMessageBox.warning(self, "Aviso / Warning", "Carregue dados primeiro / Load data first")
            return

        try:
            from kafka import KafkaProducer
            from src.io.avro_format import serialize_avro
        except ImportError as exc:
            QMessageBox.information(
                self,
                "Info",
                f"Dependencia nao instalada / Dependency missing:\n{exc}",
            )
            return

        try:
            producer = KafkaProducer(
                bootstrap_servers=self.kafka_bootstrap.text(),
                value_serializer=lambda v: v,
            )
            payload = serialize_avro(self._patch, modality=self._patch.modality)
            producer.send(
                self.kafka_topic_data.text(),
                key=self.producer_well_id.text().encode("utf-8"),
                value=payload,
            )
            producer.flush()
            producer.close()

            self._status("Patch enviado para Kafka / Patch sent to Kafka")
            self._log("info", f"Produzido: {self._patch.shape} -> {self.kafka_topic_data.text()}")
        except Exception as exc:
            QMessageBox.critical(self, "Erro / Error", f"Falha ao enviar / Send failed:\n{exc}")
            self._log("error", f"Producer Kafka falhou: {exc}")

    # ─── Kafka Consumer ───

    def _connect_kafka(self):
        if self._kafka_thread is not None and self._kafka_thread.isRunning():
            QMessageBox.information(self, "Info", "Consumer ja conectado / Consumer already connected")
            return

        try:
            import kafka  # noqa: F401
        except ImportError as exc:
            QMessageBox.information(
                self,
                "Info",
                f"kafka-python nao instalado.\nkafka-python is not installed:\n{exc}",
            )
            return

        profile = {
            "well_id": self.producer_well_id.text() or "W-01",
            "sampling_rate_hz": float(self.producer_sampling_rate.text() or 1000.0),
            "gauge_length_m": float(self.producer_gauge_length.text() or 10.0),
        }

        self._kafka_thread = QThread()
        self._kafka_worker = KafkaConsumerWorker(
            bootstrap_servers=self.kafka_bootstrap.text(),
            topic_data=self.kafka_topic_data.text(),
            topic_profile=self.kafka_topic_profile.text(),
            group_id=self.kafka_group_id.text(),
            modality=self.kafka_modality.currentText(),
            profile=profile,
        )
        self._kafka_worker.moveToThread(self._kafka_thread)

        self._kafka_thread.started.connect(self._kafka_worker.run)
        self._kafka_worker.patch_received.connect(self._on_kafka_patch)
        self._kafka_worker.profile_received.connect(self._on_kafka_profile)
        self._kafka_worker.error.connect(self._on_kafka_error)
        self._kafka_worker.connected.connect(self._on_kafka_connected)
        self._kafka_worker.disconnected.connect(self._on_kafka_disconnected)
        self._kafka_worker.message_count_updated.connect(self._on_kafka_count)

        self._kafka_worker.connected.connect(self._kafka_thread.quit)
        self._kafka_worker.disconnected.connect(self._kafka_thread.quit)
        self._kafka_worker.finished = self._kafka_thread.finished  # type: ignore

        self._kafka_thread.start()

        self.consumer_connect_btn.setEnabled(False)
        self.consumer_disconnect_btn.setEnabled(True)
        self._status("Conectando ao Kafka / Connecting to Kafka...")

    def _disconnect_kafka(self):
        if self._kafka_worker is not None:
            self._kafka_worker.stop()
        if self._kafka_thread is not None and self._kafka_thread.isRunning():
            self._kafka_thread.quit()
            self._kafka_thread.wait(3000)

        self.consumer_connect_btn.setEnabled(True)
        self.consumer_disconnect_btn.setEnabled(False)
        self._status("Desconectado do Kafka / Disconnected from Kafka")

    def _on_kafka_patch(self, patch: AlakoroPatch):
        self._log("info", f"Patch recebido: {patch}")
        if self.consumer_auto_display.isChecked():
            self.import_patch_requested.emit(patch)

    def _on_kafka_profile(self, profile: dict):
        self._log("info", f"Perfil PRODML recebido: {profile}")

    def _on_kafka_error(self, message: str):
        self._log("error", message)

    def _on_kafka_connected(self):
        self._status("Kafka conectado / Kafka connected")
        self._log("info", "Conectado ao Kafka / Connected to Kafka")

    def _on_kafka_disconnected(self):
        self._status("Kafka desconectado / Kafka disconnected")
        self._log("info", "Desconectado do Kafka / Disconnected from Kafka")
        self.consumer_connect_btn.setEnabled(True)
        self.consumer_disconnect_btn.setEnabled(False)

    def _on_kafka_count(self, count: int):
        self.consumer_counter.setText(f"Mensagens / Messages: {count}")

    def stop_kafka(self):
        """Chamado pela janela principal no closeEvent."""
        self._disconnect_kafka()
