# Changelog

Todas as mudancas notaveis neste projeto serao documentadas neste arquivo.

O formato e baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere a [Semantic Versioning](https://semver.org/lang/pt-BR/).

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
