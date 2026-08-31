# Changelog — Alakoro FiberSense

## v2.11.0 (2026-08-30) — Evolução da GUI Desktop

### Adições

#### 1. Experiência do usuário
- Cursor sincronizado entre heatmap e perfis com coordenadas na status bar.
- Drag-and-drop de arquivos na janela principal.
- Menu de arquivos recentes com persistência via `QSettings`.
- Undo/redo de processamentos com pilha de estados limitada.
- Barra de progresso percentual nos workers.

#### 2. Visualização científica
- Aba de espectrograma STFT configurável (`SpectrogramView`).
- ROI retangular no heatmap.
- Controle de colormap (`RdBu_r`, `seismic`, `viridis`, etc.) e escala (auto, fixa, percentil 1-99).
- Perfis interativos com checkboxes, adição de tempos e visualização de média ± desvio.
- Downsampling automático para dados grandes.

#### 3. Pipelines e produtividade
- Editor visual de pipelines (`PipelineEditor`) e painel de presets JSON.
- Batch processing para aplicar presets em múltiplos arquivos.

#### 4. ML e validação
- Relatório detalhado de validação com exportação HTML.
- Máscara de anomalias sobre o heatmap com threshold ajustável.
- Wizard de treinamento simplificado (Random Forest / SVM).

#### 5. Robustez
- Carregamento de arquivos em thread separada (`LoadWorker`).
- Cache de processamentos baseado em hash dos dados e parâmetros.

#### 6. Exportação e relatórios
- Diálogo de exportação de figura configurável (tamanho, DPI, colormap).
- Geração de relatórios automatizados HTML/PDF.
- Opções Avro/Protobuf no diálogo de salvamento (stub para futura implementação).

#### 7. Qualidade
- Log persistente em `~/.alakoro/alakoro.log` com janela de visualização.
- Suporte a internacionalização via `QTranslator`.
- Testes de GUI com `pytest-qt` (`tests/test_gui.py`).

### Testes
- Total: 169 testes passando, 0 skipped.

---

## v2.10.0 (2026-08-30) — Paridade DTS/DAS e Processadores Térmicos C++20

### Adições

#### 1. Processadores térmicos C++20 (`src/cpp/include/alakoro/thermal.hpp`)
- `thermal_gradient` — gradiente dT/dz ao longo da profundidade.
- `geothermal_baseline_correction` — remoção de baseline geotérmico linear.
- `thermal_anomaly_detection` — detecção de anomalias por desvio padrão temporal.
- `spatial_median_filter` — filtro de mediana espacial ao longo da profundidade.
- `estimate_geothermal_gradient` — regressão linear do perfil geotérmico.

#### 2. Generalização dos bindings C++20 para DAS/DTS/DSS (`src/cpp/src/bindings.cpp`)
- Todas as funções avançadas expostas com variantes `_d_das` e `_d_dts`.
- DSS usa fallback para DAS enquanto não houver implementações específicas.
- Processadores térmicos expostos apenas para DTS.

#### 3. `DTSThermalProcessor` (`src/processing/dts_processor.py`)
- Pipeline completo: pré-processamento espacial/temporal, correção geotérmica,
  cálculo de gradiente, detecção de anomalias e estatísticas por canal.
- Método auxiliar `compute_thermal_front_velocity` para rastrear frentes térmicas.

#### 4. `DTSFeatureExtractor` (`src/ml/features.py`)
- Features estatísticas, espectrais, térmicas (gradiente geotérmico, dT/dz) e
  de anomalia para treinamento de modelos de ML em dados DTS.

#### 5. Validação térmica avançada (`src/validation/signature_validator.py`)
- `_check_thermal_gradient_cpp`, `_check_thermal_anomalies_cpp`,
  `_check_geothermal_baseline_cpp` usando processadores C++20.
- Ativadas em `validate_signature(..., advanced_checks=True)` quando há dados DTS.

#### 6. `advanced_processors.py` multimodal (`src/processing/advanced_processors.py`)
- Todos os wrappers Python de processadores avançados respeitam `patch.modality`.
- Mapa de dispatch `_PROCESSOR_MAP` roteia automaticamente para a implementação
  C++ correta (DAS/DTS/DSS).
- Adicionados wrappers para processadores térmicos.

#### 7. GUI Desktop (`src/gui`)
- Interface gráfica com **PySide6** (LGPL) e **PyQtGraph**.
- `DataLoaderDialog`: seleção de arquivo com detecção de formato e modalidade.
- `HeatmapView` e `ProfileView`: visualização 2D e perfis.
- Painéis de processadores: filtros, denoising, eventos, térmicos e ML.
- `ProcessingWorker` em `QThread` para não travar a UI.
- Entry point `alakoro-gui` e extra opcional `[gui]` no `pyproject.toml`.

#### 8. Testes (`tests/test_dts_processor.py`)
- 9 testes cobrindo buffer DTS, processadores térmicos C++, pipeline
  `DTSThermalProcessor`, `DTSFeatureExtractor` e validação de modalidade.

### Testes
- Total: 164 testes passando, 0 skipped.

---

## v2.9.0 (2026-08-30) — Arquitetura de plugins para drivers proprietários

### Adições

#### 1. Base de drivers de fabricantes (`src/io/drivers/base.py`)
- `BaseVendorDriver` — interface abstrata para plugins de drivers DFOS/DAS.
- Métodos: `is_available()`, `detect()`, `read()`, `metadata()`.
- O core Alakoro permanece sob licença MIT; drivers proprietários podem ser distribuídos em pacotes separados.

#### 2. Registry de plugins (`src/io/drivers/registry.py`)
- `VendorDriverRegistry` descobre drivers via entry point `alakoro.driver`.
- Detecção automática por extensão/arquivo.
- Fallback para leitores open-source Xdas e DASCore quando nenhum driver proprietário corresponder.
- Funções públicas: `read_vendor()`, `list_available_drivers()`, `detect_driver()`.

#### 3. Driver de exemplo open-source (`src/io/drivers/optional/example_vendor.py`)
- Formato hipotético `.exd` baseado em HDF5.
- Inclui `write_example_file()` para geração de fixtures de teste.
- Registrado via entry point em `pyproject.toml`.

#### 4. Testes (`tests/test_io_drivers.py`)
- Testes de API pública, registry, detecção, leitura, `vendor_hint`, fallback e descoberta por entry point mockado.

#### 5. Documentação (`docs/drivers/plugins.md`)
- Guia de arquitetura de plugins, API, registro por entry point e orientações de propriedade intelectual.

---

## v2.8.3 (2026-08-30) — Correção de bug de memória nos bindings C++

### Correções

#### 1. Use-after-free em `src/cpp/src/bindings.cpp`
- `vector_to_numpy` e `matrix_to_numpy` retornavam arrays NumPy apontando para `std::vector::data()` de objetos locais já destruídos.
- Corrigido usando `py::capsule` com deleter customizado para manter o vetor vivo enquanto o array NumPy existir.
- Impacto: elimina lixo de memória e `NaN` esporádicos em processadores como `wavelet_denoise`, `median_filter_1d`, `cwt`, `spectrogram`, `emd`, `eemd`.

#### 2. Testes
- Removido `xfail` de `test_wavelet_denoise_reduces_noise`.
- Total: 141 testes passando, 0 skipped/xfailed.

---

## v2.8.2 (2026-08-30) — Integração completa com Xdas

### Adições

#### 1. Conversão direta Alakoro ↔ Xdas (`src/io/xdas_adapter.py`)
- `alakoro_to_xdas(patch)` e `xdas_to_alakoro(da)` — conversão direta preservando `well_id`, `modality` e metadados.
- `spool_to_datacollection(spool)` e `datacollection_to_spool(dc)` — `AlakoroSpool` ↔ `xdas.DataCollection`.
- `array_to_dataarray()` / `dataarray_to_array()` — conversão de/para arrays NumPy.
- Coordenadas Xdas regulares (`SampledCoordinate`) para evitar warnings de inferência.

#### 2. Leitura/escrita de formatos Xdas (`src/io/xdas_formats.py`)
- `read_xdas(path, ...)` — lê arquivo único (`xdas.open`) ou múltiplos arquivos (`xdas.open_mfdataarray`).
- `write_xdas(obj, path, engine=...)` — salva em NetCDF, com inferência por extensão.
- `supported_xdas_formats()` — lista engines de `xdas.io`.
- Suporte a lazy loading via parâmetro `lazy`.

#### 3. Pipeline híbrido Xdas (`src/processing/hybrid_pipeline.py`)
- Novo método `.xdas(processor, ...)` para encadear processadores `xdas.signal` / `xdas.fft` (detrend, filter, hilbert, decimate, rfft, etc.) com processadores C++20 e DASCore.
- Novo método `.apply_array_xdas(...)` para processadores que retornam arrays (ex: `rfft`).

#### 4. Testes e exemplos
- `tests/test_io_xdas_formats.py`: 14 testes reais de conversão, roundtrip NetCDF, DataCollection e pipeline híbrido.
- `examples/xdas_formats.py` e `examples/xdas_hybrid_pipeline.py`.
- Notebook `notebooks/01_dasdae_integration.ipynb` unificado (DASCore + Xdas).

### Testes
- Total: 142 testes passando, 0 skipped

---

## v2.8.1 (2026-08-30) — Integração DASCore: formatos + pipeline híbrido

### Adições

#### 1. Leitura/escrita de formatos DASCore (`src/io/dascore_formats.py`)
- `read(path, ...)`: lê arquivos/diretórios suportados pelo DASCore e retorna `AlakoroPatch` ou `AlakoroSpool`.
- `write(obj, path, file_format=...)`: salva `AlakoroPatch`/`AlakoroSpool` em formatos DASCore (dasdae, pickle, etc.).
- `supported_formats()`: lista os formatos detectados em `dascore.io`.
- Conversores de conveniência: `patch_from_dascore`, `spool_from_dascore`.

#### 2. Pipeline híbrido DASCore + C++20 (`src/processing/hybrid_pipeline.py`)
- `HybridPipeline` com API fluente: `.dascore(method, ...)`, `.cpp(processor, ...)`, `.apply_array(processor, ...)`.
- Permite encadear métodos nativos do DASCore (detrend, pass_filter, decimate) com processadores avançados C++20 (median_filter_1d, wavelet_denoise, butterworth, etc.).
- Aceita `AlakoroPatch`, `Patch` DASCore ou `np.ndarray` como entrada.
- Histórico de passos (`history`) e suporte a clone.

#### 3. Testes e exemplos
- `tests/test_io_dascore_formats.py`: 13 testes cobrindo formatos, roundtrip e pipeline híbrido.
- `examples/dascore_formats.py`: demonstra leitura/escrita de múltiplos formatos.
- `examples/hybrid_pipeline.py`: demonstra pipeline fluente DASCore + C++20.
- `notebooks/01_dascore_integration.ipynb` atualizado com seções de formatos e pipeline híbrido.

### Testes
- Total: 126 testes passando, 0 skipped

---

## v2.8.0 (2026-08-29) — Fase 1/2: Biblioteca Completa de Processadores Avançados C++20

### Adições

#### 1. Detectores de eventos (`src/cpp/include/alakoro/event_detection.hpp`)
- STA/LTA (Short-Term / Long-Term Average) para detecção de chegada de eventos
- Hilbert envelope via FFT para extração de envoltória de amplitude
- Teager-Kaiser Energy Operator (TKEO) para realce de transientes

#### 2. Denoising (`src/cpp/include/alakoro/denoising.hpp`)
- Median filter 1D/2D com `std::nth_element`
- SVD/PCA denoising via método de Jacobi (sem dependências externas)
- Wavelet thresholding denoising usando CWT Morlet

#### 3. Análise tempo-frequência e propagação (`src/cpp/include/alakoro/time_frequency.hpp`)
- STFT e espectrograma com janela de Hann
- Cross-correlation entre canais adjacentes
- Magnitude squared coherence entre canais adjacentes

#### 4. Filtros adaptativos e calibração (`src/cpp/include/alakoro/adaptive.hpp`)
- Compensação aproximada de gauge length
- Filtro adaptativo LMS
- Filtro adaptativo RLS

#### 5. Decomposições avançadas (`src/cpp/include/alakoro/decomposition.hpp`)
- EMD (Empirical Mode Decomposition) com spline cúbico natural
- EEMD (Ensemble EMD) com ensemble de realizações
- NMF (Non-negative Matrix Factorization) por algoritmo multiplicativo

#### 6. Integrações
- `LFDASProcessor`: opções `use_median_filter` e `use_wavelet_denoise`
- `SignatureValidator`: checks avançados de STA/LTA e coherence

#### 7. Documentação
- `notebooks/03_advanced_processors.ipynb` atualizado com exemplos de todos os processadores

### Testes
- 21 testes em `tests/test_advanced_processors.py` cobrindo todos os processadores
- Total: 113 testes passando, 0 skipped

---

## v2.7.0 (2026-08-29) — Fase 1/2: Processadores Avançados C++20

### Adições

#### 1. Processadores Avançados em C++20 (`src/cpp/include/alakoro/`)
- `filters.hpp`: filtros Butterworth de 2ª ordem (lowpass, highpass, bandpass)
  - Templates com `Order` não-tipo e `if constexpr` para especialização
  - Cálculo de coeficientes via transformação bilinear
- `fft.hpp`: FFT, magnitude spectrum e PSD por canal
  - Implementação iterativa de radix-2 com bit-reversal
  - Uso de `std::complex`, `std::span` e `std::size_t`
- `wavelet.hpp`: Transformada Wavelet Contínua (CWT)
  - Wavelets Morlet (complexa) e Ricker (Mexican Hat)
  - Convolução circular e normalização L2
  - Suporte a dados 2D (time, channels)

#### 2. Bindings pybind11 (`src/cpp/src/bindings.cpp`)
- Expõe filtros Butterworth, magnitude spectrum, PSD e CWT para Python
- Helpers `vector_to_numpy` e `matrix_to_numpy` para conversão zero-copy/cópia controlada

#### 3. Wrappers Python (`src/processing/advanced_processors.py`)
- `butterworth_lowpass`, `butterworth_highpass`, `butterworth_bandpass`
- `magnitude_spectrum`, `psd`, `cwt`
- Operam sobre `AlakoroPatch` e retornam `AlakoroPatch` ou arrays NumPy

#### 4. Integração com processadores existentes
- `LFDASProcessor` (`src/processing/lfdas_processor.py`):
  - Novo parâmetro `use_cpp_backend` para usar filtro Butterworth C++20
  - Backend scipy permanece como padrão para compatibilidade
- `SignatureValidator` (`src/validation/signature_validator.py`):
  - Novo parâmetro `advanced_checks` para ativar validações por PSD e CWT
  - Detecta conteúdo de frequência e transientes no sinal DAS

#### 5. Notebook de exemplos
- `notebooks/03_advanced_processors.ipynb`: Butterworth, FFT/PSD, CWT, LF-DAS C++ e validação avançada

### Testes
- 8 novos testes em `tests/test_advanced_processors.py`
- 2 novos testes em `tests/test_alakoro_fibersense.py` para backend C++ e validação avançada
- Total: 93 testes passando, 0 skipped

---

## v2.6.0 (2026-08-29) — Fase 4 (parcial): Machine Learning

### Adições

#### 1. Módulo de Machine Learning (`src/ml/`)
- `data.py`: `DASDataset`, `DASDataLoader` e `split_dataset`
- `features.py`: `DASFeatureExtractor` com estatísticas, PSD, wavelet e features DAS específicas
- `models.py`: `EventCNN` (classificação), `UNet2D` (segmentação), `FlowRegressor` (fluxo)
- `train.py`: `Trainer` com early stopping, LR scheduling e checkpoints
- `eval.py`: métricas de classificação (accuracy, precision, recall, F1, ROC-AUC, PR-AUC)
- `api.py`: `predict_event`, `predict_segmentation`, `predict_flow`, `load_model_for_inference`
- `bridge.py`: `MLOntoBridge` integra predições à ontologia

#### 2. Exemplos e Notebooks
- `examples/ml_training.py`: treinamento de CNN com dados sintéticos
- `notebooks/02_ml_training.ipynb`: tutorial de treinamento

### Testes
- 10 novos testes em `tests/test_ml.py`
- Total: 83 testes passando, 0 skipped
- Dependências adicionadas: `torch`, `torchvision`, `scikit-learn`

---

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
- Total: 73 testes passando, 0 skipped
- Dependências adicionadas: `xarray`, `pandas`, `obspy`, `xdas`

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
