# 📦 Guia de Instalação / Installation Guide

**Alakoro FiberSense v2.2.1** — Escolha seu modo / Choose your mode:

---

## 🟢 MODO LEIGO — Clique e Pronto! / Click & Ready!

> **Para quem não quer saber de código.**
> **For those who don't want to deal with code.**

### Windows
1. Baixe o ZIP do projeto / Download the project ZIP
2. Extraia em qualquer pasta / Extract to any folder
3. **Clique duplo** em `install/INSTALL_WINDOWS.bat` / **Double-click** `install/INSTALL_WINDOWS.bat`
4. Pronto! Um atalho `Alakoro_FiberSense.bat` será criado / Done! A shortcut will be created

### macOS / Linux
1. Baixe e extraia o ZIP / Download and extract the ZIP
2. Abra o Terminal na pasta / Open Terminal in the folder
3. Execute: `bash install/INSTALL_UNIX.sh`
4. Pronto! Use `./Alakoro_FiberSense.sh` / Done! Use `./Alakoro_FiberSense.sh`

### Interface Gráfica (todos os sistemas) / GUI (all systems)
```bash
python install/INSTALL_GUI.py
```
Ou clique duplo no arquivo / Or double-click the file.

---

## 🔵 MODO GEEK — Git, Terminal, Docker

> **Para quem curte linha de comando.**
> **For terminal lovers.**

### Via Git (recomendado) / Via Git (recommended)
```bash
git clone https://github.com/Colombiano/Alakoro_FiberSense.git
cd Alakoro_FiberSense
pip install -r requirements.txt
pytest tests/ -v
```

### Via Docker
```bash
# Pull da imagem oficial / Pull official image
docker pull colombiano/alakoro-fibersense:latest

# Executar container / Run container
docker run -it --rm colombiano/alakoro-fibersense:latest

# Ou build local / Or local build
docker build -t alakoro-fibersense .
docker run -it --rm alakoro-fibersense
```

### Via pip (em breve) / Via pip (coming soon)
```bash
pip install alakoro-fibersense
```

---

## 🧪 Verificando a Instalação / Verifying Installation

```python
from src.simulation import SignatureGenerator, WellGeometry, AcquisitionConfig
from src.validation import SignatureValidator
from src.processing import LFDASProcessor

well = WellGeometry(depth_top=0, depth_bottom=3000, n_channels=3000)
acq = AcquisitionConfig(sampling_rate_hz=1000, trace_interval_s=2.0, duration_s=3600)

gen = SignatureGenerator(well, acq)
jt = gen.generate_joule_thomson(interface_depth=1500.0)

print(f"✅ Alakoro FiberSense v2.2.1 pronto! / ready!")
print(f"   Assinatura gerada: {jt['signature_type'].pt}")
print(f"   DTS shape: {jt['dts'].shape}")
```

---

## ❓ Problemas Comuns / Common Issues

| Problema / Problem | Solução / Solution |
|-------------------|-------------------|
| "Python não encontrado" / "Python not found" | Instale Python 3.9+ e marque "Add to PATH" / Install Python 3.9+ and check "Add to PATH" |
| "Permission denied" no macOS/Linux | Execute: `chmod +x install/INSTALL_UNIX.sh` |
| Erro no tkinter (GUI) | Windows: já vem com Python. macOS: `brew install python-tk`. Linux: `sudo apt install python3-tk` |
| Dependências falham | Atualize pip: `pip install --upgrade pip` |

---

## 📞 Suporte / Support

- 🐛 Issues: [github.com/Colombiano/Alakoro_FiberSense/issues](https://github.com/Colombiano/Alakoro_FiberSense/issues)
- 📧 Email: seu_email@exemplo.com
- 📖 Documentação: README.md
