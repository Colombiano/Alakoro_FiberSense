# Streaming Kafka + Avro (Estilo Equinor)

Este documento descreve como usar o Alakoro FiberSense para streaming de dados DAS/DTS/DSS via Apache Kafka, usando Avro como formato de serialização e PRODML para handshake de metadados.

## Arquitetura

```
+---------------+      Avro       +----------------+
|  Alakoro      | --------------> |  Kafka Topic   |
|  Producer     |  alakoro.data   |  alakoro.data  |
+---------------+                 +----------------+
       |                                   |
       | JSON PRODML                       | Avro
       v                                   v
+---------------+                 +----------------+
|  Kafka Topic  |                 |  Alakoro       |
|alakoro.profile|                 |  Consumer      |
+---------------+                 +----------------+
```

- **`alakoro.data`**: mensagens binárias Avro contendo patches de dados.
- **`alakoro.profile`**: mensagens JSON com metadados da aquisição no formato PRODML (`DASAcquisitionProfile`).

O handshake PRODML garante que o consumidor receba as informações de configuração (sampling rate, gauge length, resolução espacial) antes de processar os dados brutos.

## Requisitos

```bash
pip install fastavro kafka-python
```

## Produtor

```python
from src.io.alakoro_spool import AlakoroPatch
from src.io.streaming import KafkaStreamDriver

patch = AlakoroPatch(...)

profile = {
    "well_id": "W-01",
    "wellbore_id": "WB-01",
    "sampling_rate_hz": 1000.0,
    "spatial_resolution_m": 1.0,
    "gauge_length_m": 10.0,
}

driver = KafkaStreamDriver("localhost:9092")
with driver:
    driver.connect(profile=profile)
    driver.produce(patch, key="W-01-001")
```

## Consumidor

```python
from src.io.streaming import KafkaStreamDriver
from src.io.alakoro_spool import AlakoroPatch

driver = KafkaStreamDriver("localhost:9092")
with driver:
    driver.connect()
    for item in driver.stream():
        if isinstance(item, AlakoroPatch):
            print(f"Patch recebido: {item.shape}")
        elif isinstance(item, dict) and item.get("profileType") == "DASAcquisitionProfile":
            print(f"Perfil recebido: {item['profile']}")
```

## Exemplo standalone

Sem um broker Kafka disponível, execute o exemplo standalone:

```bash
python examples/kafka_avro_demo.py --mode standalone
```

Com broker real:

```bash
# terminal 1
python examples/kafka_avro_demo.py --mode consumer --bootstrap-servers localhost:9092

# terminal 2
python examples/kafka_avro_demo.py --mode producer --bootstrap-servers localhost:9092
```

## GUI

O painel **🔌 Serialize/Kafka** na interface gráfica do Alakoro (PySide6) permite usar o streaming Kafka sem escrever código:

- Configure `bootstrap_servers`, tópicos de dados/perfil e `group_id`.
- Envie o patch atual como produtor (`alakoro.data`).
- Conecte-se como consumidor e visualize automaticamente os patches recebidos.
- Acompanhe mensagens e eventos em log dedicado.

O worker Kafka roda em thread separada (`src/gui/workers/kafka_worker.py`) para não travar a interface.

Para abrir:

```bash
python -m src.gui.main_window
```

## Referência

- SPE-205405-MS: *A Real-Time Fiber Optical System for...* (Equinor)
- [Apache Avro](https://avro.apache.org/)
- [Apache Kafka](https://kafka.apache.org/)
