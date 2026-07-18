<h1 align="center">Alakoro FiberSense v2.2.1</h1>

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

### ✨ Novidades v2.2.1 / What's New

- ✅ **15 Assinaturas Canônicas** (M15) — 6 originais + 9 novas
- ✅ **LF-DAS / eXDTS** (M1) — temperatura de alta taxa (~2s refresh)
- ✅ **Eventos Semânticos** (M12) — JSON Schema v1.1.0 (18 event types)
- ✅ **Validador v1.2.1** — detecção de múltiplos picos para crossflow zonal
- ✅ **Testes Unitários** — pytest com 40+ testes (91.3% validação)
- ✅ **PyPI** — `pip install alakoro-fibersense`
- ✅ **Docker** — `docker pull colombiano/alakoro-fibersense`
- ✅ **CI/CD** — GitHub Actions com testes, lint, build, PyPI e release
- ✅ **Documentação Bilíngue** — PT + EN em todos os módulos
- ✅ **Logo Alakoro** — Instrumento sagrado de Ogum entrelaçado com fibra óptica

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

---

### 🏗️ Arquitetura / Architecture

```
Alakoro FiberSense v2.2.1
│
├── 🟢 install/              # Modo Leigo (clique duplo)
│   ├── INSTALL_WINDOWS.bat
│   ├── INSTALL_UNIX.sh
│   └── INSTALL_GUI.py
│
├── 🔵 src/                  # Código-fonte corrigido
│   ├── simulation/          # signature_generator.py v4.1
│   ├── processing/          # lfdas_processor.py v1.1.0
│   ├── validation/          # signature_validator.py v1.2.1
│   └── events/              # schema v1.1.0 (18 event types)
│
├── 🧪 tests/                # 40+ testes pytest
├── 🐳 Dockerfile            # Container Docker
├── ⚙️ .github/workflows/    # CI/CD (testes, Docker, PyPI, release)
├── 📦 pyproject.toml        # Metadata PyPI (PEP 517/518)
├── 📦 setup.py             # Compatibilidade legacy
├── 📦 MANIFEST.in          # Arquivos extras no pacote
│
├── 🎸 docs/                 # Documentação completa
│   ├── sphinx/              # Site Sphinx (make html)
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
