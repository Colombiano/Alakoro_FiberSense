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
import numpy as np

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


# ─── Integrações Kafka/MQTT ───

class KafkaStreamDriver:
    """
    Driver de streaming Kafka + Avro no estilo Equinor.

    Arquitetura:
      - Tópico de dados: mensagens Avro com patches DAS/DTS/DSS.
      - Tópico de perfil (handshake PRODML): JSON com metadados da aquisicao.

    Ao conectar, o driver publica um DASAcquisitionProfile no tópico de perfil
    e passa a consumir o tópico de dados.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        topic_data: str = "alakoro.data",
        topic_profile: str = "alakoro.profile",
        group_id: str = "alakoro-consumer",
        modality: str = "das",
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic_data = topic_data
        self.topic_profile = topic_profile
        self.group_id = group_id
        self.modality = modality.lower()
        self._consumer = None
        self._producer = None

    def _check_dependencies(self):
        try:
            from kafka import KafkaConsumer, KafkaProducer
        except ImportError as exc:
            raise ImportError(
                "Kafka streaming requires kafka-python. "
                "Install it with: pip install kafka-python"
            ) from exc
        return KafkaConsumer, KafkaProducer

    def connect(self, profile: Optional[dict] = None, timeout_ms: int = 10000):
        """
        Conecta ao Kafka e realiza handshake PRODML.

        Args:
            profile: dicionario com metadados da aquisicao (DASAcquisitionProfile).
                Se None, usa valores padrao.
            timeout_ms: timeout para operacoes de handshake.
        """
        KafkaConsumer, KafkaProducer = self._check_dependencies()

        self._consumer = KafkaConsumer(
            self.topic_data,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset="latest",
            consumer_timeout_ms=timeout_ms,
        )
        self._producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: v.encode("utf-8") if isinstance(v, str) else v,
        )

        # Handshake PRODML: publica perfil de aquisicao
        self.publish_profile(profile or {})

        # Subscreve tambem o topico de perfil para receber perfis de produtores
        self._consumer.subscribe([self.topic_data, self.topic_profile])

        return self

    def publish_profile(self, profile: dict) -> None:
        """Publica um DASAcquisitionProfile no topico de perfil."""
        if self._producer is None:
            raise RuntimeError("KafkaStreamDriver not connected. Call connect() first.")

        import json

        full_profile = {
            "profileType": "DASAcquisitionProfile",
            "version": "2.0",
            "modality": self.modality,
            "producer": "Alakoro FiberSense",
            "profile": profile,
        }
        self._producer.send(
            self.topic_profile,
            json.dumps(full_profile).encode("utf-8"),
        )
        self._producer.flush()

    def produce(self, patch, key: Optional[str] = None) -> None:
        """Publica um AlakoroPatch serializado em Avro no topico de dados."""
        if self._producer is None:
            raise RuntimeError("KafkaStreamDriver not connected. Call connect() first.")

        from .avro_format import serialize_avro

        payload = serialize_avro(patch, modality=self.modality)
        self._producer.send(
            self.topic_data,
            key=key.encode("utf-8") if key else None,
            value=payload,
        )
        self._producer.flush()

    def stream(self):
        """
        Iterador de patches recebidos do Kafka.

        Yields:
            AlakoroPatch para mensagens de dados Avro.
            dict para mensagens de perfil PRODML.
        """
        if self._consumer is None:
            raise RuntimeError("KafkaStreamDriver not connected. Call connect() first.")

        import json

        from .alakoro_spool import AlakoroPatch
        from .avro_format import deserialize_avro

        for msg in self._consumer:
            if msg.topic == self.topic_profile:
                try:
                    yield json.loads(msg.value.decode("utf-8"))
                except Exception:
                    yield {"raw": msg.value}
                continue

            try:
                record = deserialize_avro(msg.value)
                arr = record["array"]
                modality = record["modality"].lower()
                meta = record["metadata"]

                n_t, n_c = arr.shape
                dt_s = 1.0 / meta["sampling_rate_hz"] if meta["sampling_rate_hz"] > 0 else 1.0
                dx_m = meta["spatial_resolution_m"] if meta["spatial_resolution_m"] > 0 else 1.0

                import dascore as dc
                from dascore.core.attrs import PatchAttrs

                patch = dc.Patch(
                    data=arr,
                    coords={
                        "time": (np.arange(n_t) * dt_s * 1e9).astype("timedelta64[ns]"),
                        "distance": np.arange(n_c) * dx_m,
                    },
                    dims=("time", "distance"),
                    attrs=PatchAttrs(
                        data_category=modality,
                        data_units=meta["units"],
                        time_step=np.timedelta64(int(dt_s * 1e9), "ns"),
                        distance_step=dx_m,
                    ),
                )
                yield AlakoroPatch(patch, modality=modality)
            except Exception as exc:
                # Em caso de erro no parse, yield mensagem bruta para nao parar o stream
                yield {"error": str(exc), "raw": msg.value}

    def close(self) -> None:
        """Fecha conexoes Kafka."""
        if self._consumer is not None:
            self._consumer.close()
            self._consumer = None
        if self._producer is not None:
            self._producer.close()
            self._producer = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class MQTTStreamDriver:
    """
    Driver de streaming MQTT (stub/minimo).

    Requer paho-mqtt para implementacao completa.
    """

    def __init__(self, host: str, port: int = 1883, topic: str = "#"):
        self.host = host
        self.port = port
        self.topic = topic
        self._client = None

    def connect(self):
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise ImportError(
                "MQTT streaming requires paho-mqtt. "
                "Install it with: pip install paho-mqtt"
            ) from exc

        self._client = mqtt.Client()
        self._client.connect(self.host, self.port)
        return self

    def subscribe(self, callback):
        if self._client is None:
            raise RuntimeError("MQTTStreamDriver not connected.")
        self._client.on_message = callback
        self._client.subscribe(self.topic)
        self._client.loop_start()

    def close(self):
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
