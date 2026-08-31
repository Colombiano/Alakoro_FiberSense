"""
Alakoro FiberSense — Worker Qt para streaming Kafka

Executa KafkaStreamDriver em thread separada para nao travar a GUI.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.io.alakoro_spool import AlakoroPatch
from src.io.streaming import KafkaStreamDriver


class KafkaConsumerWorker(QObject):
    """
    Worker que consome mensagens de um topico Kafka e emite patches/profiles.

    Sinais:
        patch_received(AlakoroPatch): novo patch de dados recebido.
        profile_received(dict): perfil PRODML recebido.
        error(str): mensagem de erro.
        connected(): conexao estabelecida.
        disconnected(): conexao encerrada.
        message_count_updated(int): numero de mensagens processadas.
    """

    patch_received = Signal(object)
    profile_received = Signal(dict)
    error = Signal(str)
    connected = Signal()
    disconnected = Signal()
    message_count_updated = Signal(int)

    def __init__(
        self,
        bootstrap_servers: str,
        topic_data: str = "alakoro.data",
        topic_profile: str = "alakoro.profile",
        group_id: str = "alakoro-gui",
        modality: str = "das",
        profile: dict | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._bootstrap_servers = bootstrap_servers
        self._topic_data = topic_data
        self._topic_profile = topic_profile
        self._group_id = group_id
        self._modality = modality
        self._profile = profile or {}
        self._driver: KafkaStreamDriver | None = None
        self._running = False
        self._message_count = 0

    def run(self):
        """Inicia o loop de consumo. Deve ser executado em uma QThread."""
        self._running = True
        self._message_count = 0
        try:
            self._driver = KafkaStreamDriver(
                bootstrap_servers=self._bootstrap_servers,
                topic_data=self._topic_data,
                topic_profile=self._topic_profile,
                group_id=self._group_id,
                modality=self._modality,
            )
            self._driver.connect(profile=self._profile)
            self.connected.emit()

            for msg in self._driver.stream():
                if not self._running:
                    break

                self._message_count += 1
                self.message_count_updated.emit(self._message_count)

                if isinstance(msg, AlakoroPatch):
                    self.patch_received.emit(msg)
                elif isinstance(msg, dict):
                    if "error" in msg:
                        self.error.emit(str(msg["error"]))
                    else:
                        self.profile_received.emit(msg)
                else:
                    self.error.emit(f"Mensagem desconhecida: {type(msg)}")

        except Exception as exc:  # pragma: no cover
            self.error.emit(f"Kafka worker error: {exc}")
        finally:
            if self._driver is not None:
                self._driver.close()
                self._driver = None
            self.disconnected.emit()

    def stop(self):
        """Solicita parada do worker."""
        self._running = False
        if self._driver is not None:
            self._driver.close()
