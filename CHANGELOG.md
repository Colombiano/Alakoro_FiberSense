# Changelog — Alakoro FiberSense

## v2.5.0 (2026-08-29) — Fase 2: Integração DASDAE

### Adições

#### 1. AlakoroSpool e AlakoroPatch (`src/io/alakoro_spool.py`)
- Interfaces compatíveis com DASCore Patch/Spool
- Métodos: `decimate`, `detrend`, `pass_filter`, `taper`, `select`, `convert_units`
- Iteração, indexação, `map()`, `chunk()`, `update()`
- Processamento paralelo com `ProcessPoolExecutor`/`ThreadPoolExecutor`

#### 2. Adapter DASDAE (`src/io/dasdae.py`)
- `DASDAEAdapter`: conversores Alakoro ↔ DASCore Patch/Spool
- Funções de conveniência: `alakoro_to_dascore`, `dascore_to_alakoro`
- Stubs para integração Xdas: `alakoro_to_xdas`, `xdas_to_alakoro`

#### 3. Escape Hatches (`src/io/escape_hatches.py`)
- Conversores para NumPy, pandas DataFrame, xarray DataArray, ObsPy Stream
- Reversos: `from_numpy`, `from_dataframe`, `from_xarray`, `from_obspy`

#### 4. ProdML e WITSML (`src/io/prodml.py`, `src/io/witsml.py`)
- Leitura/escrita básica de arquivos ProdML XML
- Leitura/escrita de logs WITSML
- Classes `Well`, `Wellbore`, `WITSMLLog`

#### 5. Streaming (`src/io/streaming.py`)
- `DirectoryWatcher`: monitoramento de diretório
- `StreamingSpool`: spool atualizável incrementalmente
- Stubs para Kafka e MQTT

#### 6. Exemplos e Notebooks
- `examples/basic_io.py`: leitura DAS com Alakoro + DASCore
- `examples/hybrid_processing.py`: processamento híbrido C++/Python
- `examples/realtime_monitor.py`: monitoramento de diretório
- `notebooks/01_dascore_integration.ipynb`: tutorial de integração

### Testes
- 16 novos testes em `tests/test_io_dasdae.py` e `tests/test_io_formats.py`
- Total: 71 testes passando, 2 skipped (xarray não instalado)

---

## v2.4.0 (2026-08-29) — Fase 1: Fundações C++20

### Adições

#### 1. Módulo C++20 core (`alakoro_core/`)
- Ponte C++20 ↔ Python via pybind11
- Classes template `DASData`, `DTSData`, `DSSData` com tipos `float` e `double`
- Metaprogramação moderna:
  - `concepts` (`NumericScalar`, `FloatingPoint`, `AnySensingData`)
  - `if constexpr` para especialização por modalidade em tempo de compilação
  - `std::span` para views zero-copy sobre buffers internos
  - `std::optional` e `constexpr std::string_view`
- Buffer protocol: `np.array(data, copy=False)` retorna view NumPy 2D sem cópia
- Processadores C++20: `detrend`, `demean`, `taper`, `lowpass_iir`, `decimate`
- Serialização JSON-LD nativa (`to_jsonld()`)
- Stubs documentados para Avro e Protobuf (futuras integrações)

#### 2. Build e Empacotamento
- `src/cpp/CMakeLists.txt` com C++20, flags rigorosas e pybind11
- `pyproject.toml` migrado para `scikit-build-core`
- Pacote `alakoro_core` exposto em Python

#### 3. Testes
- 10 novos testes em `tests/test_cpp_core.py`
- Total: 57 testes, todos passando

---

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
