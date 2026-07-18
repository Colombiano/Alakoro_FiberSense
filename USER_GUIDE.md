# 📖 Guia do Usuário / User Guide

**Alakoro FiberSense v2.2.1**

---

## 🎯 O que é o Alakoro FiberSense? / What is Alakoro FiberSense?

O **Alakoro FiberSense** é uma plataforma **open-source** para processamento, simulação e interpretação de dados de **fibra óptica distribuída (DFOS)** — DAS, DTS e DSS — em operações de poço de petróleo e gás.

**Alakoro FiberSense** is an **open-source** platform for processing, simulating, and interpreting **distributed fiber optic sensing (DFOS)** data — DAS, DTS, and DSS — in oil and gas well operations.

---

## 🚀 Primeiros Passos / Quick Start

### 1. Gerar uma Assinatura / Generate a Signature

```python
from src.simulation import SignatureGenerator, WellGeometry, AcquisitionConfig

# Configurar o poço / Configure the well
well = WellGeometry(depth_top=0, depth_bottom=3000, n_channels=3000)
acq = AcquisitionConfig(sampling_rate_hz=1000, trace_interval_s=2.0, duration_s=3600)

# Criar gerador / Create generator
gen = SignatureGenerator(well, acq)

# Gerar assinatura Joule-Thomson / Generate Joule-Thomson signature
jt = gen.generate_joule_thomson(interface_depth=1500.0)

print(f"📝 Assinatura: {jt['signature_type'].pt}")
print(f"   Dados DTS: {jt['dts'].shape}")
print(f"   Dados DAS: {jt['das'].shape}")
```

### 2. Processar com LF-DAS / Process with LF-DAS

```python
from src.processing import LFDASProcessor

lfdas = LFDASProcessor(cutoff_hz=1.0, refresh_rate_target_s=2.0)
result = lfdas.process(jt['das'], trace_interval_s=2.0)

print(f"🌡️ Temperatura extraída: {result['temperature'].shape}")
print(f"   Refresh rate: {result['refresh_rate_s']:.1f}s")
```

### 3. Validar a Assinatura / Validate the Signature

```python
from src.validation import SignatureValidator

validator = SignatureValidator(well, acq)
validation = validator.validate_signature(jt, result)

print(f"✅ Validação: {validation['passed']}/{validation['total']} passaram")
print(f"   Taxa de sucesso: {validation['success_rate']:.0f}%")
```

---

## 📋 As 15 Assinaturas Canônicas / The 15 Canonical Signatures

| # | Código | Nome (PT) | Nome (EN) | Uso |
|---|--------|-----------|-----------|-----|
| 1 | `dipolo_thermal_jt` | Dipolo Térmico Joule-Thomson | Joule-Thomson Thermal Dipole | Interface gás/óleo |
| 2 | `slope_velocity_tracking` | Rastreamento de Inclinação | Slope Tracking | Velocidade de fluxo |
| 3 | `warm_back_recovery` | Recuperação Térmica | Warm-Back | Avaliação de injeção |
| 4 | `valve_chatter_multipointing` | Chatter de Válvula | Valve Chatter | Diagnóstico de GLV |
| 5 | `slugging_cyclic` | Ciclo de Slugging | Slugging Cycle | Instabilidade de produção |
| 6 | `leak_path_tubing_annulus` | Vazamento Tubing↔Ânulo | Leak Path | Detecção de vazamento |
| 7 | `glv_bellow_rupture` | Fole Furado GLV | GLV Bellow Rupture | Falha de válvula |
| 8 | `perforation_effectiveness` | Efetividade de Canhoneio | Perforation Effectiveness | Avaliação de perfurações |
| 9 | `frac_screenout` | Embuchamento de Fratura | Fracture Screen-out | Fraturamento hidráulico |
| 10 | `frac_proppant_distribution` | Distribuição de Propante | Proppant Distribution | Mapeamento de propante |
| 11 | `frac_height_growth` | Crescimento de Altura | Fracture Height Growth | Controle de fratura |
| 12 | `cement_bond_evaluation` | Avaliação de Cimentação | Cement Bond Evaluation | Qualidade de cimentação |
| 13 | `re_cementing_assessment` | Avaliação de Recimentação | Re-Cementing Assessment | Reparo de cimentação |
| 14 | `crossflow_zonal` | Fluxo Cruzado Zonal | Zonal Crossflow | Comunicação entre zonas |
| 15 | `cement_channeling` | Canalização de Cimento | Cement Channeling | Canais no cimento |

---

## 🧪 Executar Testes / Run Tests

```bash
# Todos os testes / All tests
pytest tests/ -v

# Apenas assinaturas / Only signatures
pytest tests/test_alakoro_fibersense.py::TestSignatures -v

# Apenas LF-DAS / Only LF-DAS
pytest tests/test_alakoro_fibersense.py::TestLFDASProcessor -v

# Com cobertura / With coverage
pytest tests/ --cov=src --cov-report=html
```

---

## 🐳 Docker

```bash
# Build
docker build -t alakoro-fibersense .

# Run interativo / Interactive run
docker run -it --rm alakoro-fibersense

# Run com volume para dados / Run with data volume
docker run -it --rm -v $(pwd)/dados:/app/dados alakoro-fibersense
```

---

## 📚 Leitura Recomendada / Further Reading

- [README.md](README.md) — Visão geral / Overview
- [INSTALL.md](INSTALL.md) — Guia de instalação / Installation guide
- [CHANGELOG.md](CHANGELOG.md) — Histórico de versões / Version history
- SPE-219546: eXDTS (Expro)
- SPE-228489: LF-DAS for dynamic well diagnosis
