# Serialização de Dados

O Alakoro FiberSense suporta três formatos de serialização para dados DAS/DTS/DSS:

| Formato | Camada | Caso de uso principal |
|---------|--------|----------------------|
| JSON-LD | C++20 + Python | Interoperabilidade semântica com a ontologia Alakoro |
| Protobuf | C++20 (opcional) | Comunicação de alta performance, IoT, gRPC |
| Avro | Python (`fastavro`) | Streaming enterprise (Kafka), data lakes, evolução de schema |

---

## JSON-LD

Disponível nativamente em todas as compilações:

```python
from alakoro_core import DASData

data = DASData(n_times=100, n_channels=64)
payload = data.to_jsonld()
```

O JSON-LD inclui `@context` e `@type` para integração direta com a ontologia Alakoro.

---

## Protobuf

A serialização Protobuf é implementada em C++20 usando metaprogramação (`concepts`, `if constexpr`, templates).

### Habilitando no build

```bash
pip install -e . --config-settings=cmake.define.ALAKORO_WITH_PROTOBUF=ON
```

Requisitos de sistema:
- `protobuf-compiler`
- `libprotobuf-dev`

### Uso

```python
from alakoro_core import DASData

data = DASData(n_times=100, n_channels=64)
payload = data.to_protobuf_bytes()
restored = DASData.from_protobuf_bytes(payload)
```

Também disponível via `AlakoroPatch`:

```python
from src.io.alakoro_spool import AlakoroPatch

patch = AlakoroPatch(...)
payload = patch.to_protobuf_bytes()
restored = AlakoroPatch.from_protobuf_bytes(payload, modality="das")
```

O schema Protobuf está definido em `src/cpp/proto/alakoro_sensing.proto`.

---

## Avro

A serialização Avro é implementada em Python com `fastavro`. É o formato recomendado para streaming com Kafka.

### Instalação

```bash
pip install fastavro
```

### Uso

```python
from src.io.alakoro_spool import AlakoroPatch

patch = AlakoroPatch(...)
payload = patch.to_avro_bytes(metadata={"sampling_rate_hz": 1000.0})
restored = AlakoroPatch.from_avro_bytes(payload)
```

Também é possível usar diretamente:

```python
from src.io.avro_format import serialize_avro, deserialize_avro

payload = serialize_avro(patch.data, modality="das", metadata={...})
record = deserialize_avro(payload)
```

O schema Avro está em `src/io/schemas/alakoro_sensing.avsc`.

Também é possível salvar/carregar arquivos Avro e Protobuf via `src/io/protobuf_format.py`:

```python
from src.io.protobuf_format import save_protobuf, load_protobuf

save_protobuf("patch.pb", patch)
restored = load_protobuf("patch.pb", modality="das")
```

---

## GUI

A interface gráfica (PySide6) inclui um painel unificado de serialização e streaming Kafka em `src/gui/serialization_panel.py`. A aba **🔌 Serialize/Kafka** permite:

- Exportar o patch atual para Avro ou Protobuf.
- Importar arquivos Avro/Protobuf e exibi-los no heatmap.
- Enviar patches para um tópico Kafka (`alakoro.data`).
- Conectar como consumidor Kafka e exibir automaticamente os patches recebidos.
- Configurar broker, tópicos, `group_id` e metadados PRODML.

Para abrir a GUI:

```bash
python -m src.gui.main_window
```

---

## Comparativo

| Característica | JSON-LD | Protobuf | Avro |
|----------------|---------|----------|------|
| Legibilidade humana | ✅ | ❌ | ❌ |
| Tamanho compacto | ❌ | ✅ | ✅ |
| Schema evolution | ❌ | ✅ | ✅ |
| Kafka-friendly | ❌ | ⚠️ | ✅ |
| C++20/metaprogramação | ✅ | ✅ | ❌ (Python) |
| Dependência nativa | Nenhuma | Protobuf C++ | fastavro (Python) |
