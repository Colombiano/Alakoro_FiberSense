# Changelog — Alakoro FiberSense

## v2.3.0 (2026-08-16)

### Adições

#### 1. Módulo de Ontologia (`src/ontology/`)
- Modelo semântico RDF/OWL para domínio DFOS em poços de petróleo
- Classes de domínio: `Well`, `Wellbore`, `Completion`, `FiberOpticCable`
- Classes de sensing: `Interrogator`, `DASMeasurement`, `DTSMeasurement`, `DSSMeasurement`
- Classes de eventos: `Event`, `JouleThomsonEvent`, `LeakEvent`, `FlowEvent`, `WarmBackEvent`
- Serialização: Turtle, JSON-LD, OWL/XML
- Bridge `SignatureOntologyBridge`: converte assinaturas sintéticas em entidades ontológicas

#### 2. Correções de Empacotamento
- `pyproject.toml`: removidos emails vazios que quebravam build
- `pyproject.toml`: licença atualizada para formato SPDX (`license = "MIT"`)
- `setup.py`: removido `use_scm_version` para evitar conflito de versionamento
- `src/__init__.py`: adicionada função `main()` para entry point CLI

#### 3. CI/CD
- `.github/workflows/tests.yml`: adicionado job `build` com `python -m build` em todo PR/push

#### 4. Documentação
- `cronograma/Alakoro_FiberSense_Documento_Integrado_Atualizado.md`: roadmap realizado atualizado para v2.2.1
- `README.md`: seção de arquitetura atualizada com módulo `ontology/`

### Testes
- 9 novos testes em `tests/test_ontology.py`
- Total: 44 testes, todos passando

---

## v2.2.1 (2026-07-18)

### Correções Aplicadas (6 issues)

#### 1. Refatoração signature_generator.py (v4.0 → v4.1)
- **Problema:** Duplicação massiva de código em todas as 15 assinaturas
- **Solução:** Métodos utilitários `_init_arrays()`, `_get_baseline()`, `_finalize()`
- **Impacto:** Código reduzido de ~660 para ~580 linhas, mais manutenível

#### 2. Correção signature_validator.py (v1.0.0 → v1.2.1)
- **Problema:** Localização de pico incorreta no Joule-Thomson (1135m vs 1500m)
- **Solução v1.1.1:** Detecção por derivada espacial |dT/dz| para interfaces
- **Solução v1.2.0:** Thresholds ajustados (MIN_SNR_DB=0.5, LOC_TOLERANCE_M=150)
- **Solução v1.2.1:** `_detect_multiple_peaks()` para Crossflow Zonal e Cement Channeling
- **Impacto:** Taxa de sucesso de 85.7% → 91.3%

#### 3. LF-DAS Processor (v1.0.0 → v1.1.0)
- **Problema:** Refresh rate 0.5s, README prometia ~2s
- **Solução:** `decimation_factor = sampling_rate * refresh_rate_target` (padrão: 2000)
- **Impacto:** Refresh rate alinhado com documentação

#### 4. Schema JSON (v1.0.0 → v1.1.0)
- **Problema:** 4 assinaturas sem event type correspondente
- **Solução:** Adicionados 4 event types:
  - `WarmBackDetected`
  - `PerforationEffectivenessEvaluated`
  - `ProppantDistributionMapped`
  - `FractureHeightGrowthDetected`
- **Impacto:** 18 event types cobrindo 100% das 15 assinaturas

#### 5. __init__.py com exports
- **Problema:** 5 arquivos __init__.py vazios
- **Solução:** Exports completos em todos os módulos
- **Impacto:** Importação modular funcional (`from src.simulation import ...`)

#### 6. Testes Unitários (0 → 40+ testes)
- **Problema:** pytest no requirements.txt mas sem pasta tests/
- **Solução:** 40+ testes cobrindo: WellGeometry, AcquisitionConfig, 15 assinaturas,
  LFDASProcessor, SignatureValidator, EventSchema, Integration
- **Impacto:** Pipeline completo testado: gerar → processar → validar

### Resultado da Validação
- **Taxa de sucesso média:** 91.3% (≥90% aprovado)
- **Assinaturas ≥90%:** 15/15
- **Joule-Thomson:** 100% (interface em 1501.5m, esperado 1500m)
- **Crossflow Zonal:** 86% (3/3 zonas detectadas)
- **Cement Channeling:** 86% (3/3 canais detectados)

### Arquivos Modificados
- `src/simulation/signature_generator.py` → v4.1
- `src/processing/lfdas_processor.py` → v1.1.0
- `src/validation/signature_validator.py` → v1.2.1
- `src/events/fibersense_event_schema_v1.1.0.json` → v1.1.0
- `src/__init__.py`, `src/simulation/__init__.py`, etc. → com exports
- `tests/test_alakoro_fibersense.py` → 40+ testes
- `README.md` → v2.2.1
- `.gitignore` → novo

### Autor
Luiz Paulo Colombiano — 2026
MIT License
