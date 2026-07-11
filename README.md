# Alakoro FiberSense

Sistema avancado de processamento, analise e simulacao de dados de fibra otica distribuida, com suporte a DAS (Distributed Acoustic Sensing), DTS (Distributed Temperature Sensing) e DSS (Distributed Strain Sensing).

## Arquitetura

```
Alakoro_FiberSense/
├── backend/           # FastAPI + Event-Driven + C++ Engine
│   ├── app/           # Aplicacao principal (MVC)
│   │   ├── core/      # Configuracoes, eventos, Redis
│   │   ├── routers/   # Endpoints REST (DAS, DTS, DSS, simulacao, export, wavelet)
│   │   ├── simulation/# Simuladores DAS, DTS, DSS
│   │   ├── models.py  # Modelos MVC
│   │   ├── views.py   # Serializadores
│   │   └── controllers.py # Logica de processamento
│   ├── engine/        # Engine C++17 com pybind11
│   │   ├── src/
│   │   │   ├── signal_processor.h/cpp  # FFT, filtros, spectrogram
│   │   │   ├── wavelet_transforms.h/cpp # CWT, DWT, denoising
│   │   │   └── fiber_types.h           # Tipos e structs
│   │   └── py_bindings.cpp            # Bindings Python
│   └── Dockerfile
├── frontend/          # React + TypeScript + TailwindCSS
│   ├── src/components/# Dashboard, plots, paineis
│   └── Dockerfile
├── k8s/               # Kubernetes manifests (Kustomize)
├── scripts/           # Scripts de setup, backup, restore
└── docker-compose.yml # Orchestracao local
```

## Tecnologias

- **Backend**: FastAPI, Redis Pub/Sub, Celery, WebSocket
- **Engine**: C++17, pybind11, FFT Cooley-Tukey, filtros digitais, **Wavelet Transforms (CWT/DWT)**
- **Frontend**: React 18, TypeScript, TailwindCSS, Canvas API
- **Infra**: Docker, Kubernetes (Kustomize), Prometheus

## Tipos de Sinal Suportados

| Tipo | Descricao | Aplicacoes |
|------|-----------|------------|
| DAS | Acustico distribuido | Monitoramento de pocos, fraturamento hidraulico |
| DTS | Temperatura distribuida | Deteccao de vazamentos, pipelines |
| DSS | Deformacao distribuida | Monitoramento estrutural, pontes, barragens |

## Modulo de Simulacao

O sistema inclui tres simuladores independentes:

- **DASSimulator**: Gera dados acusticos sinteticos com eventos configuraveis (gaussianos, exponenciais, boxcar)
- **DTSSimulator**: Simula perfis de temperatura com deteccao de hotspots
- **DSSSimulator**: Gera dados de strain com eventos de deformacao

## Modulo Wavelet (CWT/DWT)

Sistema avancado de analise wavelet para deteccao de transientes acusticos em DAS:

- **CWT (Continuous Wavelet Transform)** com wavelet Morlet
  - Scalogram: visualizacao tempo-escala superior ao espectrograma STFT
  - Deteccao de transientes via ridge detection no scalogram
  - Cone of Influence (COI) para identificar efeitos de borda
- **DWT (Discrete Wavelet Transform)** com Daubechies-4
  - Decomposicao multi-nivel para denoising e extracao de caracteristicas
- **Wavelet Denoising** com dois metodos:
  - **VisuShrink**: threshold universal com estimativa robusta MAD
  - **SureShrink**: threshold adaptativo por nivel via SURE
- **Wavelet Power Spectrum** e power media em banda de frequencia

A wavelet Morlet foi escolhida por ser a melhor base para sinais oscilatorios
nao-estacionarios, conforme papers da SPE sobre deteccao de transientes em DAS.
A CWT supera o STFT para eventos transientes porque a localizacao tempo-frequencia
se adapta a escala: alta frequencia -> boa resolucao temporal; baixa frequencia ->
boa resolucao espectral.

Referencias:
- Torrence & Compo (1998) - A Practical Guide to Wavelet Analysis
- Mallat (2008) - A Wavelet Tour of Signal Processing
- SPE papers on wavelet-based DAS transient detection

## Instalacao

### Requisitos

- Python 3.11+
- Node.js 20+
- C++17 compiler (g++ ou clang++)
- CMake 3.20+
- Redis 7+

### Quick Start

```bash
# Clone o repositorio
git clone https://github.com/Colombiano/Alakoro_FiberSense.git
cd Alakoro_FiberSense

# Execute o setup
chmod +x scripts/setup.sh
./scripts/setup.sh

# Inicie com Docker Compose
docker-compose up -d

# Ou inicie localmente:
# Backend
cd backend
pip install -r requirements.txt
python setup_engine.py
cd app && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (novo terminal)
cd frontend
npm install
npm run dev
```

### Acesso

- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs
- WebSocket: ws://localhost:8000/ws

## API Endpoints

### DAS
- `POST /api/das/process` - Processar dados DAS
- `GET /api/das/status` - Status do processamento

### DTS
- `POST /api/dts/process` - Processar dados DTS
- `GET /api/dts/hotspots` - Detectar hotspots

### DSS
- `POST /api/dss/process` - Processar dados DSS
- `GET /api/dss/events` - Eventos de strain

### Simulacao
- `POST /api/simulation/das` - Simular dados DAS
- `POST /api/simulation/dts` - Simular dados DTS
- `POST /api/simulation/dss` - Simular dados DSS
- `GET /api/simulation/templates` - Templates de simulacao

### Wavelet
- `POST /api/wavelet/cwt` - CWT com wavelet Morlet (scalogram + coeficientes)
- `POST /api/wavelet/scalogram` - Scalogram apenas (mais rapido)
- `POST /api/wavelet/transients` - Deteccao de transientes via ridge detection
- `POST /api/wavelet/denoise` - Denoising wavelet (VisuShrink/SureShrink)
- `POST /api/wavelet/scale-average` - Power media em banda de frequencia
- `GET /api/wavelet/info` - Capacidades e referencias do modulo wavelet

### Upload
- `POST /api/upload` - Upload de arquivo (HDF5, SEG-Y, TDMS)

### Export
- `GET /api/export/{signal_id}?format=hdf5` - Exportar para HDF5
- `GET /api/export/{signal_id}?format=csv` - Exportar para CSV
- `GET /api/export/{signal_id}?format=netcdf` - Exportar para NetCDF

## Desenvolvimento

### Estrutura MVC

- **Models**: `SignalData`, `SignalEvent`, `SignalAlert`, `ProcessingJob`, `FiberParams`
- **Views**: Serializadores para API (`SignalDataView`, `AnalysisResultView`, etc.)
- **Controllers**: `SignalPipeline`, `AlertController`, `SignalStore`

### Eventos (Redis Pub/Sub)

| Evento | Descricao |
|--------|-----------|
| das.raw_received | Dados DAS brutos recebidos |
| das.processing.completed | Processamento DAS finalizado |
| dts.raw_received | DTS brutos recebidos |
| dts.hotspot.detected | Hotspot detectado |
| dss.raw_received | DSS brutos recebidos |
| dss.event.detected | Evento de strain detectado |
| wavelet.cwt.completed | CWT finalizada |
| wavelet.transient.detected | Transiente detectado via CWT |
| simulation.started | Simulacao iniciada |
| simulation.completed | Simulacao finalizada |
| alert.triggered | Alerta disparado |
| ws.update | Atualizacao WebSocket |

## Sobre a Versao C++17

O projeto usa **C++17** deliberadamente. As razoes sao:

1. **Compatibilidade universal**: C++17 e suportado por GCC 7+, Clang 5+, MSVC 2017+
2. **pybind11**: Tem suporte nativo e maduro para C++17
3. **Ambientes HPC/Corporativos**: Muitos sistemas de producao usam distribuicoes Linux
   conservadoras (RHEL, CentOS) com toolchains mais antigos
4. **Para computacao numerica**: C++17 ja oferece todas as features necessarias
   (`constexpr`, lambdas, `auto`, `std::optional`, structured bindings, `std::variant`)
5. **C++20/23**: Trazem `concepts`, `ranges`, `modules`, mas o ganho para processamento
   numerico e marginal. Se houver necessidade, a atualizacao para C++20 e simples
   (mudanca de uma linha no CMakeLists.txt)

## Kubernetes

```bash
# Deploy no ambiente de desenvolvimento
kubectl apply -k k8s/overlays/dev/

# Deploy em producao
kubectl apply -k k8s/overlays/prod/
```

## Licenca

MIT - Veja [LICENSE](LICENSE) para detalhes.

## Autor

Luiz Paulo Colombiano - [@Colombiano](https://github.com/Colombiano)
