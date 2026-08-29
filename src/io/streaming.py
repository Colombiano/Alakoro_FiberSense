"""
Alakoro FiberSense — Streaming em tempo real

Componentes básicos para processamento contínuo de dados DAS/DTS/DSS:
- Monitoramento de diretório para novos arquivos
- AlakoroSpool.update() incremental
- Arquitetura preparada para Kafka/MQTT (stub)
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

import dascore as dc

from .alakoro_spool import AlakoroSpool


class DirectoryWatcher:
    """
    Monitora um diretório por novos arquivos e dispara callbacks.
    """

    def __init__(self, path: str | Path,
                 callback: Callable[[Path], None],
                 interval_s: float = 5.0,
                 pattern: str = "*.h5"):
        self.path = Path(path)
        self.callback = callback
        self.interval_s = interval_s
        self.pattern = pattern
        self._known = set(self._collect_files())
        self._running = False

    def _collect_files(self) -> set:
        return {p for p in self.path.glob(self.pattern) if p.is_file()}

    def start(self, timeout_s: Optional[float] = None):
        """Inicia monitoramento bloqueante."""
        self._running = True
        start = time.time()
        while self._running:
            current = self._collect_files()
            new = current - self._known
            for p in sorted(new):
                self.callback(p)
            self._known = current

            if timeout_s and (time.time() - start) > timeout_s:
                break
            time.sleep(self.interval_s)

    def stop(self):
        """Para o monitoramento."""
        self._running = False


class StreamingSpool:
    """
    Spool que pode ser atualizado incrementalmente com novos dados.
    """

    def __init__(self, base_path: str | Path, modality: str = "das"):
        self.base_path = Path(base_path)
        self.modality = modality
        self.spool = AlakoroSpool([])
        self._watcher: Optional[DirectoryWatcher] = None

    def load_existing(self) -> "StreamingSpool":
        """Carrega todos os arquivos existentes no diretório base."""
        spool = AlakoroSpool.from_directory(self.base_path, modality=self.modality)
        self.spool = spool
        return self

    def update(self) -> "StreamingSpool":
        """Recarrega diretório e atualiza spool."""
        new_spool = AlakoroSpool.from_directory(self.base_path, modality=self.modality)
        self.spool = self.spool.update(list(new_spool))
        return self

    def watch(self, interval_s: float = 5.0, pattern: str = "*.h5"):
        """Inicia watcher em segundo plano (não bloqueante)."""
        def on_new(path: Path):
            new_spool = AlakoroSpool.from_directory(path.parent, modality=self.modality)
            self.spool = self.spool.update(list(new_spool))

        self._watcher = DirectoryWatcher(
            self.base_path, on_new, interval_s=interval_s, pattern=pattern
        )
        return self._watcher


# ─── Stubs para futuras integrações Kafka/MQTT ───

class KafkaStreamDriver:
    """Stub para consumer Kafka + Avro (Equinor-style)."""

    def __init__(self, bootstrap_servers: str, topic: str):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic

    def connect(self):
        raise NotImplementedError(
            "Kafka streaming requires kafka-python and avro. "
            "Install dependencies and implement consumer loop."
        )


class MQTTStreamDriver:
    """Stub para subscriber MQTT."""

    def __init__(self, host: str, port: int = 1883, topic: str = "#"):
        self.host = host
        self.port = port
        self.topic = topic

    def connect(self):
        raise NotImplementedError(
            "MQTT streaming requires paho-mqtt. "
            "Install dependency and implement subscriber loop."
        )
