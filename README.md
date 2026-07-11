# Alakoro FiberSense

> **Sistema Avancado de Processamento de Dados de Fibra Otica (DAS)**
> 
> Arquitetura Event-Driven + MVC | C++ de Alto Desempenho | Python Flexivel

---

## Sobre

**Alakoro FiberSense** e um sistema completo para processamento, analise e deteccao de eventos em dados de **Distributed Acoustic Sensing (DAS)** de fibra otica. Desenvolvido para aplicacoes em **monitoramento de pocos de petroleo**, **seguranca de infraestruturas** e **geofisica**.

O nome **Alakoro** e uma homenagem a rica heranca cultural, combinando tecnologia de ponta com identidade.

---

## Caracteristicas

- **Processamento de Alto Desempenho**: Nucleo em C++17 com bindings Python via pybind11
- **Arquitetura Event-Driven**: Comunicacao assincrona entre componentes via Event Bus
- **Padrao MVC**: Separacao clara entre Modelos, Views e Controllers
- **Multiplos Formatos**: Suporte a Silixa HDF5, OptaSense TDMS, Febus H5 e formato raw
- **Deteccao em Tempo Real**: Deteccao e classificacao de eventos em streaming
- **Containerizacao**: Docker e Docker Compose prontos para deploy
- **API REST**: Interface web para controle e monitoramento
- **Visualizacao**: Dashboard interativo e plots de dados DAS

---

## Arquitetura

```
Alakoro_FiberSense/
|
|-- src/
|   |-- cpp/                    # Nucleo C++ de alto desempenho
|   |   |-- core/               # Processamento de sinais
|   |   |-- bindings/           # Bindings pybind11
|   |   |-- include/alakoro/    # Headers
|   |
|   |-- python/                 # Framework Python
|       |-- models/             # Modelos MVC (Dados, Eventos, Config)
|       |-- views/              # Views MVC (Visualizacao)
|       |-- controllers/        # Controllers MVC (Pipeline)
|       |-- services/           # Logica de negocio
|       |-- events/             # Event Bus (Arquitetura Event-Driven)
|
|-- docker/                     # Containerizacao
|-- config/                     # Configuracoes
|-- tests/                      # Testes
|-- docs/                       # Documentacao
```

---

## Instalacao

### Requisitos

- Python 3.9+
- CMake 3.14+
- Eigen3
- Compilador C++17 (gcc/clang)

### Instalacao Local

```bash
# Clone o repositorio
git clone https://github.com/Colombiano/Alakoro_FiberSense.git
cd Alakoro_FiberSense

# Cria ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instala dependencias
pip install -r requirements.txt

# Compila bindings C++
mkdir build && cd build
cmake ..
make -j$(nproc)
cd ..

# Instala pacote
pip install -e .
```

### Docker

```bash
# Inicia todos os servicos
docker-compose -f docker/docker-compose.yml up -d

# Ou build manual
docker build -f docker/Dockerfile -t alakoro-fibersense .
docker run -p 8000:8000 alakoro-fibersense
```

---

## Uso Rapido

### Processamento de Arquivo

```python
from alakoro_fibersense import PipelineController, PipelineConfig

# Configura pipeline
config = PipelineConfig()
config.processing.detection_threshold = 15.0

# Cria e executa
pipeline = PipelineController(config)
pipeline.initialize()

# Processa arquivo
result = pipeline.run("./data/raw/dados_das.h5")

# Resultados
print(f"Frames processados: {result.num_frames}")
print(f"Eventos detectados: {result.metadata.custom_fields.get('num_events', 0)}")
```

### Streaming em Tempo Real

```python
from alakoro_fibersense import StreamingService

# Inicia streaming
stream = StreamingService(buffer_size=100)
stream.on_frame = lambda frame: print(f"Frame {frame.frame_number} recebido")
stream.start("tcp://192.168.1.100:5000")

# Processa...
import time
time.sleep(60)

# Para
stream.stop()
```

### Deteccao de Eventos

```python
from alakoro_fibersense import DetectionService, DASFrame
from alakoro_fibersense.models import DASMetadata
import numpy as np

# Cria frame de exemplo
data = np.random.randn(1000, 100) * 0.01
# Adiciona sinal simulado
for ch in range(40, 60):
    data[:, ch] += 0.5 * np.sin(2 * np.pi * 50 * np.arange(1000) / 1000)

frame = DASFrame(
    data=data,
    timestamp=0.0,
    frame_number=0,
    metadata=DASMetadata(temporal_sampling=1000.0)
)

# Detecta eventos
detector = DetectionService()
events = detector.detect_events(frame)

for event in events:
    print(f"Evento: {event.classification.value}")
    print(f"  Canais: {event.channel_start}-{event.channel_end}")
    print(f"  SNR: {event.snr:.1f} dB")
    print(f"  Confidencia: {event.confidence:.2f}")
```

### Visualizacao

```python
from alakoro_fibersense.views import DataView

view = DataView()

# Waterfall plot
view.plot_waterfall(data, sample_rate=1000, spatial_sampling=1.0)

# Espectrograma
view.plot_spectrogram(data[:, 0], sample_rate=1000)

# Multiplos canais
view.plot_multiple_channels(data, channels=[0, 25, 50, 75])
```

---

## API REST

O sistema inclui uma API REST para controle remoto:

```bash
# Inicia servidor
uvicorn src.python.api:app --host 0.0.0.0 --port 8000

# Endpoints:
# GET  /status         - Status do sistema
# POST /pipeline/run   - Executa pipeline
# GET  /events         - Lista eventos detectados
# GET  /data           - Dados processados
# WS   /ws/stream      - WebSocket para streaming
```

---

## Testes

```bash
# Testes Python
pytest tests/python -v

# Testes C++
cd build && ctest --output-on-failure

# Com cobertura
pytest tests/python --cov=src/python --cov-report=html
```

---

## Configuracao

O sistema usa arquivos YAML para configuracao:

```yaml
# config/custom.yaml
pipeline:
  stages: [decode, calibrate, filter, detect]
  
processing:
  filter_type: "bandpass"
  low_cutoff: 1.0
  high_cutoff: 500.0
  detection_threshold: 10.0
```

---

## Performance

| Operacao          | Python Puro | C++ (pybind11) | Speedup |
|-------------------|-------------|----------------|---------|
| FFT (1M samples)  | 120 ms      | 15 ms          | 8x      |
| Filtro FIR        | 85 ms       | 12 ms          | 7x      |
| STFT              | 200 ms      | 35 ms          | 5.7x    |
| Deteccao          | 150 ms      | 25 ms          | 6x      |

---

## Contribuicao

Contribuicoes sao bem-vindas! Por favor:

1. Fork o repositorio
2. Crie uma branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudancas (`git commit -am 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

---

## Licenca

Este projeto esta licenciado sob a licenca MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## Autor

**Luiz Paulo Colombiano**
- GitHub: [@Colombiano](https://github.com/Colombiano)
- Localizacao: Salvador, Bahia, Brasil

---

## Agradecimentos

- Inspirado nas tecnologias DAS da industria de petroleo
- Desenvolvido com apoio da comunidade open-source
- Eigen3, pybind11, FastAPI e todas as dependencias

---

<p align="center">
  <strong>Alakoro FiberSense</strong> - Processamento Inteligente de Dados de Fibra Otica
  <br>
  <em>Sarava!</em>
</p>
