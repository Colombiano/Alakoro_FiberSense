<div align="center">

# 🔱 Alakoro FiberSense

**Advanced Signal Processing Platform for Distributed Fiber Optic Sensing**

*Plataforma Avançada de Processamento de Sinais para Sensoriamento de Fibra Óptica Distribuída*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![C++](https://img.shields.io/badge/C++-17-00599C?logo=c%2B%2B&logoColor=white)](https://isocpp.org)
[![pybind11](https://img.shields.io/badge/pybind11-2.11-2980B9?logo=python&logoColor=white)](https://pybind11.readthedocs.io)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178C6?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Kustomize-326CE5?logo=kubernetes&logoColor=white)](https://kubernetes.io)
[![Celery](https://img.shields.io/badge/Celery-5.3-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![WebSocket](https://img.shields.io/badge/WebSocket-Real--time-010101?logo=socket.io&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
[![Prometheus](https://img.shields.io/badge/Prometheus-Monitoring-E6522C?logo=prometheus&logoColor=white)](https://prometheus.io)
[![CMake](https://img.shields.io/badge/CMake-3.20+-064F8C?logo=cmake&logoColor=white)](https://cmake.org)

**Version:** `2.1.0` | **License:** MIT

</div>

---

## 🔱 What is Alakorô? | O que é Alakorô?

**[EN]** **Alakorô** is a sacred instrument from the worship of the **Orixá Ogum** — the Yoruba deity of war, iron, and paths. It is formed by two **hand-forged iron bells** joined by a chain. Alakorô is used to invoke the deity, repel negative energies, and **open paths**.

Just as the Alakorô reveals what is hidden through the sound of its bells, the **Alakoro FiberSense** platform reveals what is hidden beneath the earth through fiber optic sensing — detecting acoustic, thermal, and strain signals invisible to the naked eye.

**[PT]** **Alakorô** é um instrumento sagrado do culto do **Orixá Ogum** — a divindade iorubá da guerra, do ferro e dos caminhos. É formado por **dois sinos de ferro forjado** unidos por uma corrente. O Alakorô é utilizado para invocar a divindade, afastar energias negativas e **abrir caminhos**.

Assim como o Alakorô revela o que está oculto através do som de seus sinos, a plataforma **Alakoro FiberSense** revela o que está oculto sob a terra através do sensoriamento de fibra óptica — detectando sinais acústicos, térmicos e de deformação invisíveis aos olhos.

---

## 📡 Overview | Visão Geral

**[EN]** Alakoro FiberSense is a high-performance platform for processing, analyzing, and simulating distributed fiber optic sensing data. It supports three sensing modalities — **DAS** (Distributed Acoustic Sensing), **DTS** (Distributed Temperature Sensing), and **DSS** (Distributed Strain Sensing) — with a modular architecture powered by a C++17 compute engine, event-driven backend, and real-time React frontend.

**Key differentiator:** Wavelet transform module (CWT with Morlet wavelet) for acoustic transient detection, as recommended by SPE technical papers for superior time-frequency localization of non-stationary signals.

**[PT]** Alakoro FiberSense é uma plataforma de alta performance para processamento, análise e simulação de dados de sensoriamento de fibra óptica distribuída. Suporta três modalidades — **DAS** (Distributed Acoustic Sensing), **DTS** (Distributed Temperature Sensing) e **DSS** (Distributed Strain Sensing) — com arquitetura modular baseada em engine de computação C++17, backend event-driven e frontend React em tempo real.

**Diferencial:** Módulo de transformada wavelet (CWT com wavelet Morlet) para detecção de transientes acústicos, conforme recomendado em papers técnicos da SPE por sua superior localização tempo-frequência de sinais não-estacionários.

---

## 📐 Architecture | Arquitetura

```
Alakoro_FiberSense/
├── backend/                    # FastAPI + Event-Driven Architecture
│   ├── app/
│   │   ├── core/               # Config, Redis Pub/Sub, Events
│   │   ├── routers/            # REST API (DAS, DTS, DSS, Wavelet, Sim, Export)
│   │   ├── simulation/         # DAS / DTS / DSS Simulators
│   │   ├── models.py           # MVC Models
│   │   ├── views.py            # API Serializers
│   │   └── controllers.py      # Processing Logic
│   ├── engine/                 # C++17 Engine + pybind11
│   │   ├── src/
│   │   │   ├── signal_processor.h/cpp    # FFT, Filters, Spectrogram
│   │   │   ├── wavelet_transforms.h/cpp  # CWT, DWT, Denoising ⭐ NEW
│   │   │   └── fiber_types.h             # Data Structures
│   │   ├── py_bindings.cpp     # Python Bindings
│   │   └── CMakeLists.txt
│   └── Dockerfile
├── frontend/                   # React 18 + TypeScript + TailwindCSS
│   ├── src/components/         # Dashboard, Plots, Panels
│   └── Dockerfile
├── k8s/                        # Kubernetes (Kustomize: dev/prod)
├── scripts/                    # setup.sh, backup.sh, restore.sh
└── docker-compose.yml
```

---

## 🛰️ Supported Signal Types | Tipos de Sinal Suportados

| Type / Tipo | Description / Descrição | Applications / Aplicações |
|-------------|------------------------|---------------------------|
| **DAS** | Distributed Acoustic Sensing / Sensoriamento Acústico Distribuído | Well monitoring, hydraulic fracturing / Monitoramento de poços, fraturamento hidráulico |
| **DTS** | Distributed Temperature Sensing / Sensoriamento Térmico Distribuído | Leak detection, pipelines / Detecção de vazamentos, dutos |
| **DSS** | Distributed Strain Sensing / Sensoriamento de Deformação Distribuído | Structural monitoring, dams / Monitoramento estrutural, barragens |

---

## ⚡ Features | Funcionalidades

### Signal Processing / Processamento de Sinais
- **C++17 Compute Engine** — FFT Cooley-Tukey O(n log n), digital filters, anomaly detection
- **Wavelet Transforms (v2.1.0)** — CWT Morlet scalogram, ridge-based transient detection, DWT db4 denoising
- **Multi-Signal Pipeline** — Dedicated processing pipelines for DAS, DTS, and DSS

### Simulation / Simulação
- **DAS Simulator** — Synthetic acoustic data with configurable Gaussian, exponential, and boxcar events
- **DTS Simulator** — Temperature profiles with hotspot detection
- **DSS Simulator** — Strain data with deformation events

### Real-Time & Visualization / Tempo Real e Visualização
- **Event-Driven Architecture** — Redis Pub/Sub with 25+ event types
- **WebSocket** — Live updates to the React dashboard
- **Canvas-Based Plots** — Waterfall, spectrogram, profile, frequency, and scalogram views

### Infrastructure / Infraestrutura
- **Docker Compose** — Full stack with Redis, Backend, Frontend, Celery, Prometheus
- **Kubernetes** — Kustomize overlays (dev/prod), HPA, DaemonSet for C++ engine

---

## 🌊 Wavelet Module | Módulo Wavelet (v2.1.0)

**[EN]** The wavelet module implements **Continuous Wavelet Transform (CWT)** with the **Morlet wavelet** — the optimal basis for oscillatory, non-stationary signals like DAS acoustic transients. Unlike STFT (Short-Time Fourier Transform) which uses a fixed window, CWT adapts its time-frequency localization to scale: high frequencies get good time resolution, low frequencies get good spectral resolution.

**Capabilities:**
- `cwt()` — Full CWT with complex coefficients and scalogram
- `scalogram()` — Fast scalogram computation only
- `detect_transients()` — Ridge detection for transient acoustic events
- `denoise()` — VisuShrink (MAD-based universal threshold)
- `denoise_sure()` — SureShrink (Stein's Unbiased Risk Estimate)
- `cone_of_influence()` — Edge effect marking
- `scale_average_power()` — Band-limited wavelet power

**References:** Torrence & Compo (1998), Mallat (2008), SPE papers on wavelet-based DAS transient detection.

**[PT]** O módulo wavelet implementa a **Transformada Wavelet Contínua (CWT)** com a **wavelet Morlet** — a base ótima para sinais oscilatórios não-estacionários como transientes acústicos DAS. Diferente do STFT (Short-Time Fourier Transform) que usa janela fixa, a CWT adapta sua localização tempo-frequência à escala: altas frequências têm boa resolução temporal, baixas frequências têm boa resolução espectral.

**Capacidades:**
- `cwt()` — CWT completa com coeficientes complexos e scalograma
- `scalogram()` — Computação rápida de scalograma apenas
- `detect_transients()` — Detecção de ridges para eventos transientes acústicos
- `denoise()` — VisuShrink (threshold universal com estimativa MAD)
- `denoise_sure()` — SureShrink (Stein's Unbiased Risk Estimate)
- `cone_of_influence()` — Marcação de efeitos de borda
- `scale_average_power()` — Potência wavelet em banda limitada

**Referências:** Torrence & Compo (1998), Mallat (2008), papers da SPE sobre detecção de transientes DAS baseada em wavelets.

---

## 🚀 Quick Start | Início Rápido

### Prerequisites / Pré-requisitos

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 20+ |
| C++ Compiler | GCC 7+ / Clang 5+ (C++17) |
| CMake | 3.20+ |
| Redis | 7+ |
| Docker & Docker Compose | Latest |

### Option 1: Docker Compose (Recommended) | Opção 1: Docker Compose (Recomendado)

```bash
git clone https://github.com/Colombiano/Alakoro_FiberSense.git
cd Alakoro_FiberSense
docker-compose up -d
```

Access / Acesse:
- **Frontend:** http://localhost:5173
- **API Docs:** http://localhost:8000/docs
- **WebSocket:** ws://localhost:8000/ws

### Option 2: Local Development | Opção 2: Desenvolvimento Local

```bash
# 1. Clone
git clone https://github.com/Colombiano/Alakoro_FiberSense.git
cd Alakoro_FiberSense

# 2. Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# 3. Start Redis
docker run -d -p 6379:6379 --name redis redis:7-alpine

# 4. Start Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 5. Start Frontend (new terminal)
cd frontend
npm run dev
```

---

## 📡 API Endpoints

### DAS, DTS, DSS
```
POST /api/das/process/{signal_id}      # Process DAS data
POST /api/dts/process/{signal_id}      # Process DTS data
POST /api/dss/process/{signal_id}      # Process DSS data
GET  /api/dts/hotspots/{signal_id}     # Detect hotspots
GET  /api/dss/events/{signal_id}       # Strain events
```

### Wavelet ⭐
```
POST /api/wavelet/cwt                  # CWT with Morlet wavelet
POST /api/wavelet/scalogram            # Scalogram only (faster)
POST /api/wavelet/transients           # Transient detection via ridges
POST /api/wavelet/denoise              # Wavelet denoising
POST /api/wavelet/scale-average        # Scale-averaged power
GET  /api/wavelet/info                 # Wavelet capabilities
```

### Simulation
```
POST /api/simulation/das               # Simulate DAS data
POST /api/simulation/dts               # Simulate DTS data
POST /api/simulation/dss               # Simulate DSS data
GET  /api/simulation/templates         # Simulation templates
```

### Upload & Export
```
POST /api/upload/                      # Upload file (HDF5, SEG-Y, TDMS, CSV, NPY)
GET  /api/export/{id}?format=hdf5      # Export to HDF5
GET  /api/export/{id}?format=csv       # Export to CSV
GET  /api/export/{id}?format=netcdf    # Export to NetCDF
```

---

## 🍴 Creating a Fork | Como Criar um Fork

**[EN]** Want to contribute or build your own version? Here's how to fork Alakoro FiberSense:

**[PT]** Quer contribuir ou construir sua própria versão? Veja como fazer um fork do Alakoro FiberSense:

### Step 1: Fork on GitHub | Passo 1: Fork no GitHub

Click the **"Fork"** button at the top right of the repository page:

Clique no botão **"Fork"** no canto superior direito da página do repositório:

> https://github.com/Colombiano/Alakoro_FiberSense → **Fork**

### Step 2: Clone Your Fork | Passo 2: Clone seu Fork

```bash
# Replace 'YOUR_USERNAME' with your GitHub username
# Substitua 'YOUR_USERNAME' pelo seu usuário do GitHub
git clone https://github.com/YOUR_USERNAME/Alakoro_FiberSense.git
cd Alakoro_FiberSense

# Add upstream remote to sync with original
# Adicione o remote upstream para sincronizar com o original
git remote add upstream https://github.com/Colombiano/Alakoro_FiberSense.git
git remote -v
```

### Step 3: Sync with Original | Passo 3: Sincronize com o Original

```bash
# Fetch updates from upstream
# Busque atualizações do upstream
git fetch upstream

# Merge updates into your main branch
# Mescle as atualizações na sua branch main
git checkout main
git merge upstream/main

# Push to your fork
# Envie para seu fork
git push origin main
```

### Step 4: Create a Branch | Passo 4: Crie uma Branch

```bash
git checkout -b feature/your-feature-name
# Make your changes
# Faça suas alterações
git add .
git commit -m "feat: your feature description"
git push origin feature/your-feature-name
```

### Step 5: Pull Request | Passo 5: Pull Request

Open a Pull Request on GitHub to merge your changes into the original repository.

Abra um Pull Request no GitHub para mesclar suas alterações no repositório original.

---

## 🤝 Contributing | Contribuindo

**[EN]** Contributions are welcome! Areas of interest:
- New wavelet families (Paul, DOG) for the CWT module
- Additional signal processing algorithms
- Frontend visualization improvements
- Kubernetes deployment optimizations
- Documentation translations

**[PT]** Contribuições são bem-vindas! Áreas de interesse:
- Novas famílias de wavelets (Paul, DOG) para o módulo CWT
- Algoritmos adicionais de processamento de sinais
- Melhorias na visualização do frontend
- Otimizações de deployment Kubernetes
- Traduções da documentação

---

## 🛠️ Why C++17? | Por que C++17?

**[EN]** This project deliberately uses **C++17** for the compute engine:

1. **Universal compatibility** — supported by GCC 7+, Clang 5+, MSVC 2017+
2. **pybind11** — native, mature support for C++17 Python bindings
3. **HPC/Corporate environments** — many production systems use conservative Linux distributions (RHEL, CentOS) with older toolchains
4. **For numerical computing** — C++17 already offers all necessary features: `constexpr`, lambdas, `auto`, `std::optional`, structured bindings, `std::variant`
5. **C++20/23** — bring `concepts`, `ranges`, `modules`, but the gain for numerical processing is marginal. Upgrading to C++20 is simple (one line change in `CMakeLists.txt`) if needed

**[PT]** Este projeto usa deliberadamente **C++17** para o engine de computação:

1. **Compatibilidade universal** — suportado por GCC 7+, Clang 5+, MSVC 2017+
2. **pybind11** — suporte nativo e maduro para bindings Python com C++17
3. **Ambientes HPC/Corporativos** — muitos sistemas de produção usam distribuições Linux conservadoras (RHEL, CentOS) com toolchains mais antigos
4. **Para computação numérica** — C++17 já oferece todas as features necessárias: `constexpr`, lambdas, `auto`, `std::optional`, structured bindings, `std::variant`
5. **C++20/23** — trazem `concepts`, `ranges`, `modules`, mas o ganho para processamento numérico é marginal. A atualização para C++20 é simples (mudança de uma linha no `CMakeLists.txt`) se necessário

---

## ☸️ Kubernetes Deployment | Deploy Kubernetes

```bash
# Development / Desenvolvimento
kubectl apply -k k8s/overlays/dev/

# Production / Produção
kubectl apply -k k8s/overlays/prod/
```

---

## 👤 Author | Autor

**Luiz Paulo Colombiano**

[![GitHub](https://img.shields.io/badge/GitHub-@Colombiano-181717?logo=github&logoColor=white)](https://github.com/Colombiano)

---

## 📄 License | Licença

MIT — see [LICENSE](LICENSE) for details | veja [LICENSE](LICENSE) para detalhes.

---

<div align="center">

*"Como o Alakorô abre caminhos, a ciência revela o que está oculto."*

*"As the Alakorô opens paths, science reveals what is hidden."*

🔱

</div>
