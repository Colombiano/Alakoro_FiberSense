"""
Exemplo: Streaming Kafka + Avro no estilo Equinor.

Este script demonstra como publicar e consumir patches Alakoro via Kafka
usando serializacao Avro. O handshake PRODML publica metadados da
aquisicao em um topico separado antes do envio dos dados brutos.

Requisitos:
    pip install fastavro kafka-python

Para rodar com um broker real (ex: Kafka local em localhost:9092):
    # terminal 1
    python examples/kafka_avro_demo.py --mode consumer

    # terminal 2
    python examples/kafka_avro_demo.py --mode producer

Sem broker, o script usa um modo standalone com mock para demonstrar a
serializacao/deserializacao.
"""

from __future__ import annotations

import argparse
import json
import time
from unittest.mock import MagicMock

import numpy as np

import dascore as dc
from dascore.core.attrs import PatchAttrs

from src.io.alakoro_spool import AlakoroPatch
from src.io.streaming import KafkaStreamDriver


def make_example_patch(n_times: int = 50, n_channels: int = 16) -> AlakoroPatch:
    """Cria um patch sintetico DAS para o exemplo."""
    t = np.linspace(0, 1, n_times)
    x = np.linspace(0, n_channels - 1, n_channels)
    data = np.sin(2 * np.pi * 5 * t[:, None]) * np.cos(0.3 * x[None, :])
    data += 0.1 * np.random.randn(n_times, n_channels)

    patch = dc.Patch(
        data=data.astype(np.float64),
        coords={
            "time": (np.arange(n_times) * 0.02 * 1e9).astype("timedelta64[ns]"),
            "distance": np.arange(n_channels) * 2.0,
        },
        dims=("time", "distance"),
        attrs=PatchAttrs(
            data_category="das",
            data_units="1/s",
            time_step=np.timedelta64(int(0.02 * 1e9), "ns"),
            distance_step=2.0,
        ),
    )
    return AlakoroPatch(patch, well_id="demo-well-01", modality="das")


def run_producer(bootstrap_servers: str = "localhost:9092", n_messages: int = 10):
    """Publica patches sinteticos no Kafka."""
    driver = KafkaStreamDriver(
        bootstrap_servers=bootstrap_servers,
        topic_data="alakoro.demo.data",
        topic_profile="alakoro.demo.profile",
        group_id="alakoro-demo-producer",
    )

    profile = {
        "well_id": "demo-well-01",
        "wellbore_id": "WB-01",
        "sampling_rate_hz": 50.0,
        "spatial_resolution_m": 2.0,
        "gauge_length_m": 10.0,
        "n_channels": 16,
    }

    with driver:
        driver.connect(profile=profile)
        print(f"[produtor] conectado a {bootstrap_servers}")
        print(f"[produtor] perfil PRODML publicado: {json.dumps(profile, indent=2)}")

        for i in range(n_messages):
            patch = make_example_patch()
            driver.produce(patch, key=f"msg-{i:04d}")
            print(f"[produtor] enviado msg-{i:04d} shape={patch.shape}")
            time.sleep(0.5)


def run_consumer(bootstrap_servers: str = "localhost:9092", timeout_s: float = 30.0):
    """Consum patches do Kafka e imprime estatisticas."""
    driver = KafkaStreamDriver(
        bootstrap_servers=bootstrap_servers,
        topic_data="alakoro.demo.data",
        topic_profile="alakoro.demo.profile",
        group_id="alakoro-demo-consumer",
    )

    with driver:
        driver.connect()
        print(f"[consumidor] conectado a {bootstrap_servers}")

        start = time.time()
        count = 0
        for item in driver.stream():
            if isinstance(item, AlakoroPatch):
                count += 1
                print(
                    f"[consumidor] recebido patch {count}: "
                    f"shape={item.shape}, modality={item.modality}, "
                    f"mean={item.data.mean():.4f}, std={item.data.std():.4f}"
                )
            elif isinstance(item, dict) and "profileType" in item:
                print(f"[consumidor] perfil PRODML recebido: {item['profileType']}")
            else:
                print(f"[consumidor] mensagem ignorada: {item}")

            if time.time() - start > timeout_s:
                print("[consumidor] timeout atingido")
                break


def run_standalone():
    """Demonstracao sem broker Kafka: serializa, simula stream e desserializa."""
    print("[standalone] demonstracao sem broker Kafka")
    patch = make_example_patch()

    # 1. Serializa para Avro
    payload = patch.to_avro_bytes(
        metadata={
            "sampling_rate_hz": 50.0,
            "spatial_resolution_m": 2.0,
            "gauge_length_m": 10.0,
            "units": "1/s",
            "start_time": "2026-08-31T12:00:00Z",
        }
    )
    print(f"[standalone] Avro payload size: {len(payload)} bytes")

    # 2. Simula uma mensagem Kafka
    msg = MagicMock()
    msg.topic = "alakoro.demo.data"
    msg.value = payload

    # 3. Driver mock para consumo
    driver = KafkaStreamDriver("mock:9092")
    mock_consumer = MagicMock()
    mock_consumer.__iter__ = MagicMock(return_value=iter([msg]))
    driver._consumer = mock_consumer

    for item in driver.stream():
        if isinstance(item, AlakoroPatch):
            print(
                f"[standalone] patch reconstruido: shape={item.shape}, "
                f"modality={item.modality}, allclose={np.allclose(item.data, patch.data)}"
            )
        else:
            print(f"[standalone] erro: {item}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kafka + Avro demo for Alakoro")
    parser.add_argument(
        "--mode",
        choices=["producer", "consumer", "standalone"],
        default="standalone",
        help="Modo de execucao",
    )
    parser.add_argument("--bootstrap-servers", default="localhost:9092")
    parser.add_argument("--n-messages", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    if args.mode == "producer":
        run_producer(args.bootstrap_servers, args.n_messages)
    elif args.mode == "consumer":
        run_consumer(args.bootstrap_servers, args.timeout)
    else:
        run_standalone()
