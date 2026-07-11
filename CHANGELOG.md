# Changelog

Todas as mudancas notaveis neste projeto serao documentadas neste arquivo.

O formato e baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere a [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [2.1.0] - 2026-07-12

### Adicionado
- **Modulo Wavelet no Engine C++17** para analise avancada de transientes acusticos
  - CWT (Continuous Wavelet Transform) com wavelet Morlet
    - Otimizado para deteccao de transientes nao-estacionarios em DAS
    - Scalogram: visualizacao tempo-escala (superior ao espectrograma STFT)
    - Cone of Influence (COI) para identificar efeitos de borda
  - DWT (Discrete Wavelet Transform) com Daubechies-4
    - Decomposicao multi-nivel para analise multi-resolucao
  - Deteccao de transientes via CWT ridge detection
    - Mais sensivel que STFT para eventos de curta duracao
    - Identifica ridges no scalogram correspondentes a eventos acusticos
  - Wavelet Denoising com dois metodos:
    - **VisuShrink**: threshold universal com estimativa MAD de ruido
    - **SureShrink**: threshold adaptativo por nivel via SURE
  - Wavelet Power Spectrum e Scale-Averaged Power
- Novo router `/api/wavelet` com endpoints REST
  - `POST /api/wavelet/cwt` - Computa CWT completa
  - `POST /api/wavelet/scalogram` - Computa scalograma apenas
  - `POST /api/wavelet/transients` - Detecta transientes acusticos
  - `POST /api/wavelet/denoise` - Aplica denoising wavelet
  - `POST /api/wavelet/scale-average` - Power media em banda de frequencia
  - `GET /api/wavelet/info` - Capacidades e referencias do modulo wavelet
- Fallback Python puro quando engine C++ nao disponivel
  - Implementacao CWT em Python usando FFT
  - Integracao com PyWavelets para DWT/denoising
- Novos eventos no Event Bus para processamento wavelet

### Notas Tecnicas
- Wavelet Morlet escolhida por ser a melhor para sinais oscilatorios
  nao-estacionarios (Goupillaud, Grossmann & Morlet, 1984)
- A CWT supera o STFT para eventos transientes porque a localizacao
  tempo-frequencia se adapta a escala (alta frequencia = boa resolucao
  temporal; baixa frequencia = boa resolucao espectral)
- Referencias: Torrence & Compo (1998), Mallat (2008), SPE papers

## [2.0.0] - 2026-07-12

### Adicionado
- Suporte completo a DAS (Distributed Acoustic Sensing)
- Suporte completo a DTS (Distributed Temperature Sensing)
- Suporte completo a DSS (Distributed Strain Sensing)
- Modulo de simulacao com tres simuladores independentes
  - DASSimulator com eventos gaussianos, exponenciais e boxcar
  - DTSSimulator com deteccao de hotspots
  - DSSSimulator com eventos de deformacao
- Engine C++17 com bindings Python via pybind11
  - FFT Cooley-Tukey O(n log n)
  - Filtros digitais (bandpass, moving average)
  - Deteccao de anomalies
- Frontend React com dashboards especificos por tipo de sinal
  - WaterfallPlot com colormaps DAS/DTS/DSS
  - SpectrogramPlot com escala HSL
  - ProfilePlot para visualizacao de perfil
  - FrequencyPlot para analise espectral
  - SimulationPanel para configuracao de simulacoes
  - ConfigPanel para parametros do engine C++
  - AlertPanel para gerenciamento de alertas
  - StatusBar com metricas em tempo real
- Arquitetura Event-Driven com Redis Pub/Sub
  - 22 tipos de eventos
  - WebSocket para updates em tempo real
- Sistema MVC completo
  - Models: SignalData, SignalEvent, SignalAlert, ProcessingJob
  - Views: Serializadores para API
  - Controllers: SignalPipeline, AlertController, SignalStore
- Kubernetes manifests com Kustomize
  - Overlays dev e prod
  - HPA (Horizontal Pod Autoscaler)
  - DaemonSet para engine C++
  - Celery workers separados por tipo
- Docker Compose completo
- Scripts de setup, backup e restore

### Alterado
- Renomeado de FiberSense para Alakoro FiberSense
- Reestruturacao completa da arquitetura para suporte multi-sinal
- Pipeline de processamento configuravel por tipo de sinal

## [1.0.0] - 2026-07-10

### Adicionado
- Versao inicial do sistema FiberSense
- Processamento de dados DAS
- Engine C++ basica
- Frontend React inicial
- Docker configuracao basica
