<h1 align="center">Alakoro FiberSense v2.11.0</h1>

<p align="center">
  <strong>Plataforma Open-Source Multi-Modal para DFOS em Poços de Petróleo</strong><br/>
  <strong>Open-Source Multi-Modal Platform for DFOS in Oil & Gas Wells</strong>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"/></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python 3.9+"/></a>
  <a href="https://pypi.org/project/alakoro-fibersense/"><img src="https://img.shields.io/pypi/v/alakoro-fibersense.svg" alt="PyPI"/></a>
  <a href="https://pypi.org/project/alakoro-fibersense/"><img src="https://img.shields.io/pypi/dm/alakoro-fibersense.svg" alt="Downloads"/></a>
  <img src="https://github.com/Colombiano/Alakoro_FiberSense/actions/workflows/tests.yml/badge.svg" alt="Tests"/>
  <img src="https://img.shields.io/docker/pulls/colombiano/alakoro-fibersense" alt="Docker"/>
</p>

---

### 🎯 Visão Geral / Overview

O **Alakoro FiberSense** é uma plataforma **full-stack open-source** para processamento, simulação e interpretação de dados de **fibra óptica distribuída (DFOS)** — DAS, DTS e DSS — em operações de poço de petróleo e gás.

**Alakoro FiberSense** is an **open-source full-stack** platform for processing, simulating, and interpreting **distributed fiber optic sensing (DFOS)** data — DAS, DTS, and DSS — in oil and gas well operations.

> 🎸 **Alakoro** é o instrumento sagrado de **Ogum**, Orixá do ferro, tecnologia e inovação. Este projeto une a força ancestral do Alakoro com a precisão da fibra óptica distribuída.
> **Alakoro** is the sacred instrument of **Ogum**, the Orisha of iron, technology, and innovation. This project unites the ancestral force of the Alakoro with the precision of distributed fiber optic sensing.

---

### 🚀 Instalação em 10 Segundos / 10-Second Install

```bash
pip install alakoro-fibersense
```

> **É só isso.** Nada de ZIP, git clone, ou scripts. Funciona em Windows, macOS, Linux, Colab, Jupyter — qualquer lugar com Python.
> **That's it.** No ZIP, no git clone, no scripts. Works on Windows, macOS, Linux, Colab, Jupyter — anywhere with Python.

---

### 🎮 Escolha Seu Modo / Choose Your Mode

| 🟢 **MODO LEIGO** | 🔵 **MODO GEEK** |
|:---:|:---:|
| **Clique e pronto!** | **Git, terminal, Docker** |
| Para quem não quer saber de código | Para quem curte linha de comando |
| For those who don't want to deal with code | For terminal lovers |
| [📖 Ver guia](INSTALL.md#-modo-leigo--click--ready) | [📖 Ver guia](INSTALL.md#-modo-geek--git-terminal-docker) |

---

### ✨ Novidades v2.11.0 / What's New in v2.11.0

- ✅ **Interface Gráfica Desktop** (`src/gui`) — PySide6 + PyQtGraph: drag-and-drop, undo/redo, heatmap 2D com ROI/colormap, perfis interativos, espectrograma STFT, presets/batch, relatórios HTML/PDF, log persistente e i18n
- ✅ **Paridade DTS/DAS** — todos os processadores avançados C++20 agora suportam DAS e DTS (`*_d_das` / `*_d_dts`); DSS com fallback básico
- ✅ **Processadores Térmicos C++20** (`alakoro_core`) — `thermal_gradient_d`, `geothermal_baseline_correction_d`, `thermal_anomaly_detection_d`, `spatial_median_filter_d`
- ✅ **DTSThermalProcessor** (`src/processing/dts_processor.py`) — pipeline completo de limpeza, correção geotérmica, gradiente dT/dz, detecção de anomalias e velocidade de frente térmica
- ✅ **DTSFeatureExtractor** (`src/ml/features.py`) — features estatísticas, espectrais, térmicas e de anomalia para ML em DTS
- ✅ **Validação Térmica Avançada** (`src/validation/signature_validator.py`) — checks de gradiente, anomalias e baseline geotérmico via C++20
- ✅ **Arquitetura de Plugins para Drivers Proprietários** (`src/io/drivers`) — `BaseVendorDriver`, `VendorDriverRegistry` com descoberta via entry point `alakoro.driver`, fallback para DASCore/Xdas e driver de exemplo `.exd`
- ✅ **Biblioteca Completa de Processadores Avançados C++20** (`alakoro_core`) — Butterworth, FFT/PSD, CWT, STA/LTA, Hilbert, TKEO, median/SVD/wavelet denoising, STFT, cross-correlation, coherence, gauge compensation, LMS/RLS, EMD/EEMD, NMF
- ✅ **Machine Learning** (`src/ml`) — CNN, U-Net, regressor; Trainer; métricas; API de inferência
- ✅ **C++20 Core** (`alakoro_core`) — DASData, DTSData, DSSData com pybind11 e metaprogramação moderna
- ✅ **Integração Nativa com DASCore** — `AlakoroPatch`/`AlakoroSpool` compatíveis; leitura/escrita de formatos DASCore (dasdae, pickle, tdms, segy, febus, optodas, etc.); pipeline híbrido DASCore + C++20
- ✅ **Integração Nativa com Xdas** — conversão direta `AlakoroPatch ↔ xdas.DataArray` e `AlakoroSpool ↔ xdas.DataCollection`; leitura/escrita NetCDF; pipeline híbrido Xdas + C++20
- ✅ **Escape Hatches** — NumPy, pandas, xarray, ObsPy
- ✅ **ProdML/WITSML** — leitura/escrita básica de arquivos Energistics
- ✅ **Streaming** — monitoramento de diretório e stubs Kafka/MQTT
- ✅ **15 Assinaturas Canônicas** (M15) — 6 originais + 9 novas
- ✅ **LF-DAS / eXDTS** (M1) — temperatura de alta taxa (~2s refresh)
- ✅ **Ontologia** (`src/ontology`) — modelo RDF/OWL + bridge com assinaturas
- ✅ **Testes Unitários** — pytest com 163 testes passando
- ✅ **PyPI** — `pip install alakoro-fibersense`
- ✅ **CI/CD** — GitHub Actions com testes, lint, build C++, PyPI e release
- ✅ **Documentação Bilíngue** — PT + EN em todos os módulos

---

### 🧪 Uso Rápido / Quick Start

```python
from src.simulation import SignatureGenerator, WellGeometry, AcquisitionConfig
from src.processing import LFDASProcessor
from src.validation import SignatureValidator

well = WellGeometry(depth_top=0, depth_bottom=3000, n_channels=3000)
acq = AcquisitionConfig(sampling_rate_hz=1000, trace_interval_s=2.0, duration_s=3600)

gen = SignatureGenerator(well, acq)
jt = gen.generate_joule_thomson(interface_depth=1500.0)

lfdas = LFDASProcessor(cutoff_hz=1.0, refresh_rate_target_s=2.0)
result = lfdas.process(jt['das'], trace_interval_s=2.0)

validator = SignatureValidator(well, acq)
validation = validator.validate_signature(jt, result)
print(f"✅ {validation['passed']}/{validation['total']} passaram ({validation['success_rate']:.0f}%)")
```

#### 🌡️ Processamento Térmico DTS / DTS Thermal Processing

```python
import numpy as np
from src.processing import DTSThermalProcessor

# temperature: array (n_times, n_channels) em °C
temperature = np.random.randn(1000, 300) * 0.1 + 20.0

proc = DTSThermalProcessor(
    depth_step_m=1.0,
    surface_temp=20.0,
    geothermal_gradient=0.03,
    spatial_median_window=5,
    anomaly_threshold_sigma=3.0,
    use_cpp_backend=True,
)
result = proc.process(temperature)

print(result['thermal_gradient'].shape)  # (1000, 300)
print(result['anomalies'].sum())         # número de amostras anômalas
```

---

### 🔌 Drivers Proprietários / Vendor Drivers

O Alakoro v2.9.0 introduz uma arquitetura de **plugins opcionais para drivers de fabricantes** DFOS/DAS. O core permanece MIT; drivers comerciais são distribuídos em pacotes separados e registrados via entry point `alakoro.driver`.

**Alakoro v2.9.0 introduces an optional plugin architecture for DFOS/DAS vendor drivers.** The core stays MIT; commercial drivers live in separate packages and register via the `alakoro.driver` entry point.

```python
from src.io.drivers import read_vendor, list_available_drivers, detect_driver

# Lista drivers disponíveis / List available drivers
print(list_available_drivers())

# Detecta o driver adequado / Detect the right driver
print(detect_driver("/dados/poco.exd"))

# Lê com fallback automático para DASCore/Xdas / Read with automatic DASCore/Xdas fallback
patch = read_vendor("/dados/poco.exd")

# Força um driver específico / Force a specific driver
patch = read_vendor("/dados/poco.bin", vendor_hint="meu_fabricante")
```

> 📖 Veja o guia completo em [docs/drivers/plugins.md](docs/drivers/plugins.md).
> 📖 See the full guide at [docs/drivers/plugins.md](docs/drivers/plugins.md).

---

### 🖥️ Interface Gráfica Desktop / Desktop GUI

O Alakoro v2.11.0 inclui uma **GUI desktop nativa** construída com **PySide6** (licença LGPL) e **PyQtGraph** para visualização científica de alta performance.

**Alakoro v2.11.0 includes a native desktop GUI** built with **PySide6** (LGPL license) and **PyQtGraph** for high-performance scientific visualization.

```bash
# Instalar com dependências da GUI / Install with GUI dependencies
pip install alakoro-fibersense[gui]

# Launch
alakoro-gui
```

Funcionalidades / Features:
- 📂 Carregamento de arquivos com detecção automática de formato (DASCore/Xdas/drivers)
- 🖱️ Drag-and-drop e arquivos recentes
- ↩️ Undo/redo de processamentos
- 🗺️ Mapa de calor 2D com ROI, colormap e escala configuráveis
- 📈 Perfis interativos (seleção de tempos, média ± desvio)
- 📊 Espectrograma STFT por canal
- 🔧 Painel de processadores: Butterworth, detrend/demean/taper, median/SVD denoising, STA/LTA, PSD
- 🌡️ Painel térmico DTS: gradiente, baseline geotérmico, anomalias, pipeline completo
- 🤖 Validação de assinaturas, relatório detalhado, máscara de anomalias e inferência ML
- 🎓 Wizard de treinamento de modelos (Random Forest/SVM)
- 🧱 Editor visual de pipelines e presets JSON
- 🔄 Batch processing em pastas
- 💾 Exportação para NetCDF, NumPy, PNG, CSV, Avro, Protobuf
- 📊 Exportação de figuras configuráveis e relatórios HTML/PDF
- 📝 Log persistente em `~/.alakoro/alakoro.log`

> A GUI roda em thread separada para não travar a interface durante processamentos C++20.

---

### 📂 Leitura de Dados / Reading Data

```python
# Via DASCore / Via DASCore
from src.io.dascore_formats import read as read_dascore
spool = read_dascore("/dados/poco_tdms/")

# Via Xdas / Via Xdas
from src.io.xdas_formats import read_xdas
patch = read_xdas("/dados/poco.nc")

# Conversão direta / Direct conversion
from src.io.xdas_adapter import alakoro_to_xdas, xdas_to_alakoro
xda = alakoro_to_xdas(patch)
patch_back = xdas_to_alakoro(xda)
```

---

### 📦 Instalação por Plataforma / Install by Platform

#### 🟢 Modo Leigo / Easy Mode
```bash
# Windows: clique duplo em / double-click:
install/INSTALL_WINDOWS.bat

# macOS/Linux:
bash install/INSTALL_UNIX.sh

# Interface gráfica (todos os sistemas) / GUI (all systems):
python install/INSTALL_GUI.py
```

#### 🔵 Modo Geek / Geek Mode
```bash
# Via pip (recomendado) / Via pip (recommended)
pip install alakoro-fibersense

# Via Git / Via Git
git clone https://github.com/Colombiano/Alakoro_FiberSense.git
cd Alakoro_FiberSense
pip install -r requirements.txt

# Via Docker / Via Docker
docker pull colombiano/alakoro-fibersense:latest
docker run -it --rm colombiano/alakoro-fibersense:latest
```

#### 🐍 Google Colab / Jupyter Notebook
```python
# Em uma célula / In a cell:
!pip install alakoro-fibersense

from src.simulation import SignatureGenerator, WellGeometry, AcquisitionConfig
# ... pronto! / ... ready!
```

---

### 📚 Documentação / Documentation

| Documento | Descrição |
|-----------|-----------|
| [INSTALL.md](INSTALL.md) | Guia de instalação completo / Complete installation guide |
| [USER_GUIDE.md](USER_GUIDE.md) | Guia do usuário com exemplos / User guide with examples |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Como contribuir / How to contribute |
| [CHANGELOG.md](CHANGELOG.md) | Histórico de versões / Version history |
| [LICENSE](LICENSE) | MIT License |
| [cronograma/Alakoro_FiberSense_Documento_Integrado_Atualizado.md](cronograma/Alakoro_FiberSense_Documento_Integrado_Atualizado.md) | Cronograma e roadmap atualizado / Updated roadmap |

---

### 🏗️ Arquitetura / Architecture

```
Alakoro FiberSense v2.9.0
│
├── 🟢 install/              # Modo Leigo (clique duplo / double-click)
│   ├── INSTALL_WINDOWS.bat
│   ├── INSTALL_UNIX.sh
│   └── INSTALL_GUI.py
│
├── 🔵 src/                  # Código-fonte principal / Main source code
│   ├── simulation/          # Geração de assinaturas e geometria de poço
│   ├── processing/          # LF-DAS, processadores avançados e pipelines híbridos
│   ├── validation/          # Validação de assinaturas canônicas
│   ├── events/              # Schema de eventos (JSON-LD / RDF)
│   ├── ontology/            # Modelo semântico RDF/OWL + bridge com assinaturas
│   ├── io/                  # Entrada/saída de dados
│   │   ├── dascore.py / dascore_formats.py  # Integração DASCore
│   │   ├── xdas_adapter.py / xdas_formats.py # Integração Xdas
│   │   ├── drivers/         # Plugins de drivers proprietários (MIT-safe)
│   │   │   ├── base.py      # BaseVendorDriver
│   │   │   ├── registry.py  # Descoberta por entry point + fallback
│   │   │   └── optional/    # Drivers opcionais embarcados (ex: example_vendor)
│   │   ├── prodml.py / witsml.py             # Formatos Energistics
│   │   └── streaming.py     # Streaming de diretórios / stubs Kafka/MQTT
│   └── ml/                  # Machine Learning (CNN, U-Net, regressor, trainer)
│
├── 🧪 tests/                # 154+ testes pytest
├── 🐳 Dockerfile            # Container Docker
├── ⚙️ .github/workflows/    # CI/CD (testes, Docker, PyPI, release)
├── 📦 pyproject.toml        # Metadata PyPI (PEP 517/518) + entry points
├── 📦 setup.py             # Compatibilidade legacy
├── 📦 MANIFEST.in          # Arquivos extras no pacote
│
├── 🎸 docs/                 # Documentação completa
│   ├── sphinx/              # Site Sphinx (make html)
│   ├── drivers/             # Guia de plugins para drivers proprietários
│   ├── architecture/        # Documentação de arquitetura
│   ├── Alakoro_Demo.ipynb   # Notebook Jupyter interativo
│   └── alakoro_logo.png     # Logo (Alakoro + Fibra Óptica)
│
└── 📚 docs/                 # Documentação bilíngue PT/EN
    ├── README.md
    ├── INSTALL.md
    ├── USER_GUIDE.md
    ├── CONTRIBUTING.md
    ├── CHANGELOG.md
    └── LICENSE
```

---

### 🤝 Contribuindo / Contributing

Veja [CONTRIBUTING.md](CONTRIBUTING.md) para detalhes.
See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---


### 📄 Licença / License

[MIT License](LICENSE) — Luiz Paulo Colombiano, 2026
