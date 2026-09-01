# Auditoria Técnica — Alakoro_FiberSense vs. Estado da Arte DFOS em Poços de Petróleo

**Data:** 2026-09-01  
**Alcance:** Inspeção estática do código-fonte Python 3.9+ e C++20 do projeto `Alakoro_FiberSense`, confrontada com requisitos técnicos consolidados a partir de 21 resumos de papers e apresentações sobre DFOS em poços de petróleo.  
**Documentos de entrada:** `consolidated_requirements.md`, `inspection_checklist.md` e seis arquivos de achados em `docs/.audit_work/findings/`.  
**Saída:** `/home/guest/Alakoro_FiberSense/docs/technical_audit_das_dts_dss.md`

---

## 1. Resumo Executivo

### Contexto e objetivo
A fibra óptica distribuída (DFOS) transforma um cabo monomodo passivo em um array contínuo de milhares de sensores ao longo do poço. As modalidades principais — DAS (Rayleigh, dinâmico/direcional), DTS (Raman, absoluto/lento), DSS/Brillouin e LF-DAS/RFS (quase-estático) — são complementares e, no estado da arte, só funcionam de forma robusta quando combinadas com modelagem física e processamento na borda. O objetivo desta auditoria foi verificar, mediante inspeção de código, em que medida o Alakoro_FiberSense atende a esses requisitos de estado da arte.

### Principais conclusões
- **Arquitetura promissora, lógica ainda em proof-of-concept.** O projeto tem bons *boilerplates*: wrapper Python/C++20, enum canônico de 15 eventos, mapeamento DAS/DTS/DSS, backends de denoising variados, I/O ProdML/WITSML/DASCore/Xdas e pipeline híbrido. No entanto, a maior parte das regras de inferência ainda são heurísticas térmicas simples.
- **Fusão multimodal crítica não implementada.** Não há alinhamento temporal/espacial entre LF-DAS (~2 s) e DTS (5–10 min) e nenhum módulo de desacoplamento tensão-temperatura (T/ε) por similaridade de cosseno em janela 2D — requisitos centrais do estado da arte.
- **Coeficiente LF-DAS→temperatura fisicamente inconsistente.** `src/processing/lfdas_processor.py:146` usa `thermal_coefficient = 100.0`, enquanto a literatura indica ~0,002–0,0032 °C/rad.
- **Padrões de fraturamento ausentes.** *Heart shapes*, *blue wings*, *antennas*, *break lines* e bandas de convergência não são gerados nem detectados.
- **Backend C++ não compilado no ambiente auditado.** `alakoro_core._alakoro_core` está ausente, inviabilizando a execução dos 163 testes citados no README e prejudicando a validação dinâmica.
- **ML caixa-preta sem regras físicas.** `FlowRegressor` empilha DAS e DTS sem alinhamento de grids e sem discriminar influxo de refluxo/reinjeção por velocidade aparente.
- **Tratamento de NaN/Inf e flags de qualidade por canal insuficientes.** Os processadores e o motor podem propagar dados inválidos silenciosamente.
- **I/O funcional, mas com falhas metrológicas.** `src/io/witsml.py:280` força `data_category="das"` em todo `read_log`, descartando a modalidade real do log (DTS/DSS).
- **Testes e validação têm cobertura parcial.** O gerador cobre os 15 tipos canônicos, mas o validador não os cobre individualmente e há inconsistência no critério de aprovação (85 % vs. 90 % esperado).
- **Documentação e exemplos existem, mas carecem de unidades físicas e limitações.** Docstrings omitem unidades e justificativas para constantes mágicas.

### Nível geral de maturidade técnica
**Protótipo funcional com gaps críticos em fusão multimodal, desacoplamento T/ε, modelagem física de fraturamento/fluxo e validação de dados reais.** O código é modular e bem estruturado para desenvolvimento iterativo, mas não está pronto para deploy em poços sem correção dos itens CRITICAL/HIGH identificados.

---

## 2. Metodologia

### Corpus analisado
- **21 resumos técnicos** (fontes S01–S21) cobrindo física de fibra, aquisição, instalação, pré-processamento, fusão multimodal, interpretação, modelagem, escalabilidade e casos de campo.
- **6 arquivos de achados** produzidos por agentes do Kimi Code inspecionando código-fonte:
  1. `findings/inference_engine.md`
  2. `findings/signal_processing.md`
  3. `findings/preprocessing.md`
  4. `findings/simulation_tests.md`
  5. `findings/integration.md`
  6. `findings/ml_pipeline.md`

### Como o código foi inspecionado
A inspeção foi guiada pelo `inspection_checklist.md`, derivado dos 21 resumos. Cada item do checklist foi verificado em arquivos-fonte específicos de Python (`src/ontology/`, `src/processing/`, `src/io/`, `src/ml/`, `src/simulation/`, `src/validation/`) e C++ (`src/cpp/include/alakoro/`, `src/cpp/src/bindings.cpp`). Foram atribuídos status:
- **PASS:** requisito atendido de forma satisfatória.
- **PARTIAL:** requisito parcialmente atendido; requer melhorias.
- **FAIL:** requisito não atendido ou atendido de forma inadequada.

### Áreas inspecionadas
1. Motor de inferência e ontologia (`src/ontology/`)
2. Processamento de sinais DAS/DTS/LF-DAS (`src/processing/`)
3. Pré-processamento, filtros e denoising (`src/cpp/include/alakoro/`, `src/processing/advanced_processors.py`)
4. Simulação, validação e testes (`src/simulation/`, `src/validation/`, `tests/`)
5. Integração e padrões industriais (`src/io/`)
6. ML, features e pipeline híbrido (`src/ml/`, `src/processing/hybrid_pipeline.py`)

### Limitações da auditoria
- **Build C++ não disponível:** não foi possível executar `pytest` para confirmar os 163 testes citados no README nem verificar o comportamento dinâmico do motor C++.
- **Dados reais não foram processados:** a avaliação é baseada em inspeção estática e testes sintéticos presentes no repositório.
- **Ambiente de produção não auditado:** CI/CD, infraestrutura de borda e integração com sistemas SCADA não foram inspecionados.
- **Dependências externas:** não foi verificado se bibliotecas como DASCore/Xdas estão instaladas e compatíveis com a versão utilizada.

---

## 3. Estado da Arte DFOS em Poços de Petróleo

### Síntese das modalidades

| Modalidade | Mecanismo físico | Grandeza | Características principais |
|------------|------------------|----------|----------------------------|
| **DAS** | Rayleigh (elástico) | Fase/freq. do retroespalhamento | Relativo, direcional, alta taxa (até 40 kHz), gauge length 5–10 m típico. |
| **DTS** | Raman (inelástico) | Temperatura absoluta | Auto-referenciado, resolução 0,15–0,3 °C, refresh 5–10 min, sofre atenuação diferencial. |
| **DSS / BFS** | Brillouin | Strain + temperatura (ambíguos) | Absoluto, lento (min/ponto), requer separação T/ε por fibras tensionada/folgada ou referência térmica. |
| **LF-DAS / eXDTS** | Componente < 0,05–1 Hz do DAS | Temperatura/strain quase-estático | Refresh ~2 s, fator ~0,0028 °C/rad, mas mistura T/ε/P. |
| **RFS** | Rayleigh scanning | Strain relativo de alta resolução | ~20 cm, < 1 µε, relativo. |

### Fusão multimodal
O estado da arte converge para a **fusão ternária DAS + DTS + DSS/LF-DAS**, combinando:
- **Temperatura absoluta** (DTS) para ancorar inferências térmicas;
- **Energia acústica direcional** (DAS) para detectar fluxo, vazamentos e falhas mecânicas;
- **Velocidade aparente da frente térmica/de fluido** (`v = Δz/Δt`) para discriminar influxo produtivo de refluxo/reinjeção;
- **Strain absoluto/quase-estático** (DSS/LF-DAS) para geomecânica e fraturamento.

### Principais aplicações
- **Fraturamento hidráulico:** detecção de *heart shapes*, *blue wings*, *stress shadow*, *break lines*, FIP, geometria de fratura.
- **Perfil de produção/injeção:** inversão térmica DTS, alocação zonal via DAS+DTS.
- **Integridade de poço:** vazamentos tubo-ânulo, comunicação anular, pressão sustentada, canalização de cimento.
- **Gas lift:** detecção de GLV/SPM abertos, *chatter*, *bellow rupture*, *fallback*, *slugging*.
- **Eventos geomecânicos:** microsismicidade, *creep*, *fault slip*, subsidência.

### Gaps do estado da arte
- **DAS/LF-DAS são relativos:** exigem baseline e sensores de referência (WHT/DHT/GR/CCL).
- **Cross-sensitividade T/ε/P:** Brillouin, RFS e LF-DAS misturam temperatura, strain e pressão.
- **Acoplamento fibra-cimento-rocha** raramente conhecido; distorce amplitudes.
- **Gauge length** age como filtro passa-baixa espacial; eventos < 5–10 m não são resolvidos.
- **Direcionalidade:** fibra só mede projeção axial do campo de deformação.
- **Atenuação e hidrogênio** limitam alcance e corrompem DTS Raman em *lead-ins* longos.
- **Inversão de fluxo mal-posta:** múltiplas soluções; depende fortemente de calibração.

---

## 4. Requisitos Técnicos Consolidados

### Resumo dos requisitos mais relevantes
Os requisitos funcionais (RF) e não-funcionais (RNF) consolidados exigem:
- Suporte explícito a DAS, DTS, DSS, LF-DAS, RFS, BFS com metadados de aquisição (RF-01).
- Conversão tempo–profundidade OTDR, baseline geotérmico, gradientes e anomalias (RF-02 a RF-04).
- LF-DAS com banda < 1 Hz e refresh ~2 s (RF-05).
- Fusão multimodal com alinhamento temporal/espacial e desacoplamento T/ε (RF-06, RF-07).
- Detecção de padrões de fraturamento e eventos de integridade/produção (RF-08 a RF-13).
- Inversão térmica DTS e modelagem geomecânica validada (RF-10, RF-11).
- Flags de qualidade por canal, robustez a NaN/Inf e integração com sensores de referência (RF-15 a RF-17, RNF-05, RNF-06).
- Assinaturas canônicas sintéticas, padrões ProdML/WITSML e streaming (RF-18 a RF-20).
- Escalabilidade para TB e quicklook em horas (RNF-01 a RNF-03).

### Tabela de requisitos críticos vs. implementação no Alakoro

| ID | Requisito | Status no Alakoro | Evidência / Onde melhorar |
|----|-----------|-------------------|---------------------------|
| RF-01 | Modalidades DAS/DTS/DSS/RFS/BFS | **PARTIAL** | `advanced_processors.py` roteia DAS/DTS/DSS; C11/C12 de Brillouin ausentes; WITSML força `das`. |
| RF-02 | OTDR tempo–profundidade | **PASS** | Metadados presentes; C++ calcula gradiente térmico. |
| RF-03 | Baseline e diferenças relativas | **PARTIAL** | `DTSThermalProcessor.remove_geothermal_baseline` existe; falta gerenciamento por fase operacional. |
| RF-04 | Pré-processamento físico | **PARTIAL** | Filtros/denoising variados; ausente f-k 2D, tratamento de unwrapping, flags de qualidade. |
| RF-05 | LF-DAS < 1 Hz, refresh ~2 s | **PASS** | `LFDASProcessor` implementa cutoff 1 Hz e refresh 2 s. |
| RF-06 | Fusão multimodal | **FAIL** | `HybridPipeline` e `FlowRegressor` não alinham grids temporais/espaciais. |
| RF-07 | Desacoplamento T/ε | **FAIL** | Nenhum `decouple_strain_temperature`; fator térmico hardcoded 100.0. |
| RF-08 | Strain/strain rate e padrões de fratura | **FAIL** | Nenhum detector de heart shapes, blue wings, antennas, break lines. |
| RF-09 | Velocidade aparente e vazão | **FAIL** | `SlopeVelocityRule` calcula `dz/dt` sempre positivo; sem direção. |
| RF-10 | Inversão térmica DTS | **FAIL** | Apenas thresholds; sem modelo direto 1D + Tikhonov. |
| RF-11 | Modelagem/inversão de fraturamento | **FAIL** | Sem validação KGD/Sneddon, sem FIP, sem detecção de contato fratura-fibra. |
| RF-12 | Integridade de poço | **PARTIAL** | Regras heurísticas existem, mas mapeadas para eventos genéricos. |
| RF-13 | Produção/fluxo | **PARTIAL** | Assinaturas geradas, mas sem discriminação de influxo vs refluxo. |
| RF-15 | Correção de profundidade (GR/CCL) | **FAIL** | `Well`/`Wellbore` não têm campos GR/CCL. |
| RF-16 | Atenuação diferencial / ringing | **FAIL** | Nenhuma correção DAF ou máscara de `n_end_meters`. |
| RF-17 | Flags de qualidade por canal | **PARTIAL** | Métricas básicas em `DTSThermalProcessor`; sem SNR/coerência formal. |
| RF-18 | 15 assinaturas canônicas | **PASS** | `SignatureGenerator` implementa os 15 tipos. |
| RF-19 | ProdML/WITSML | **PARTIAL** | ProdML preserva metadados; WITSML descarta modalidade. |
| RF-20 | Streaming Avro/Kafka/MQTT | **PARTIAL** | Kafka/Avro funcional; MQTT é stub; schema Avro não carrega well/wellbore. |
| RNF-01 | Performance / edge processing | **PARTIAL** | Peças existem, mas sem pipeline orquestrado de redução. |
| RNF-05 | Robustez a ruído | **FAIL** | Sem validação NaN/Inf no motor e processadores. |
| RNF-06 | Calibração com gauges | **FAIL** | WHT/DHT/GR/CCL não integrados. |
| RNF-08 | Testabilidade | **PARTIAL** | 15 assinaturas cobertas; motor de inferência sem testes dinâmicos confirmados. |

---

## 5. Resultados da Inspeção de Código

### Resumo agregado por área

| Área | Itens | PASS | PARTIAL | FAIL | N/A | CRITICAL | HIGH |
|------|-------|------|---------|------|-----|----------|------|
| Motor de inferência / ontologia | 18 | 2 | 6 | 10 | 0 | 2 | 11 |
| Processamento de sinais | 18 | 5 | 5 | 7 | 1 | 2 | 11 |
| Pré-processamento / filtros / denoising | 9 | 2 | 3 | 2 | 2 | 0 | 4 |
| Simulação / validação / testes | 12 | 3 | 5 | 3 | 1 | 1 | 8 |
| Integração / padrões industriais | 9 | 3 | 3 | 3 | 0 | 1 | 3 |
| ML / features / pipeline híbrido | 10 | 1 | 2 | 7 | 0 | 2 | 5 |
| **Total** | **76** | **16** | **24** | **32** | **4** | **8** | **42** |

Aproximadamente **42 % dos itens inspecionados estão em FAIL**, **32 % em PARTIAL** e apenas **21 % em PASS**. Itens de severidade CRITICAL ou HIGH representam **66 %** do total.

---

### 5.1 Motor de inferência e ontologia

**Resumo dos achados:** A arquitetura é modular e promissora (wrapper Python/C++20, enum canônico, traits), mas as regras são predominantemente heurísticas térmicas simples. Faltam desacoplamento T/ε, discriminação de fluxo por velocidade aparente, inversão térmica, detecção de padrões de fraturamento, tratamento de NaN/Inf e integração com sensores de referência.

| ID | Item | Status | Severidade | Evidência | Recomendação |
|----|------|--------|------------|-----------|--------------|
| A-01 | Motor aceita DAS opcional e valida shapes | **PASS** | HIGH | `src/ontology/inference_engine.py:96-139`; binding C++ rejeita `ndim != 2`. | Manter; validar dimensões > 0. |
| A-02 | Mapeamento C++ → ontologia multimodal | **PARTIAL** | MEDIUM | `_EVENT_CLASS_MAP` cobre 15 códigos, mas só 4 têm classes especializadas; schema JSON tem 18 tipos não emitidos. | Criar subclasses para GLV, fraturamento, cimentação, etc. |
| A-03 | Separação LF/HF nas regras | **FAIL** | HIGH | `infer()` não recebe banda; regras C++ usam energia total sem filtro. | Adicionar `low_freq_band_hz`/`high_freq_band_hz` em `InferenceMetadata`. |
| A-04 | Parâmetros físicos obrigatórios | **PARTIAL** | HIGH | Metadados existem, mas `sampling_rate_hz` default 0.0 no C++ pode causar divisão por zero. | Validar `> 0` no Python e no binding C++. |
| B-05 | DSS/Brillouin com coeficientes T/ε | **PARTIAL** | MEDIUM | `DSSMeasurement` existe, mas sem C11/C12 nem estratégia de separação. | Adicionar `brillouin_c11`/`c12` e documentar ambiguidade. |
| D-03 | Desacoplamento T/ε LF-DAS/DTS | **FAIL** | CRITICAL | Função `decouple_strain_temperature` inexistente. | Implementar com janela 2D e cosine similarity (S21). |
| D-04 | Inferência ternária T + energia + velocidade | **FAIL** | HIGH | `SlopeVelocityRule` calcula velocidade escalar positiva; sem combinação física. | Criar `FlowDiscriminationRule` com banda 15–100 Hz e velocidade com sinal. |
| D-05 | Sensores de referência WHT/DHT/GR/CCL | **FAIL** | HIGH | `Well`/`Wellbore` e `Measurement` não têm campos de referência. | Estender ontologia e `InferenceMetadata`. |
| E-01 | 15 assinaturas canônicas | **PASS** | HIGH | Enum `CanonicalEvent` e `_EVENT_CLASS_MAP` cobrem os 15 tipos. | Manter; alinhar schema JSON. |
| E-02 | Padrões de fraturamento | **FAIL** | HIGH | Regras usam anomalias térmicas simples; sem heart/blue wings/antennas. | Implementar detectores morfológicos 2D. |
| E-03 | Gas lift / válvulas | **PARTIAL** | MEDIUM | Regras e traits existem, mas mapeados para `Event` genérico. | Especializar `GasLiftValveEvent`. |
| E-04 | Integridade de poço | **PARTIAL** | HIGH | Regras heurísticas existem; classes ontológicas genéricas. | Especializar eventos de integridade. |
| E-05 | Direção de fluxo | **FAIL** | HIGH | `velocity = dz/dt` sempre positivo. | Usar correlação cruzada para sinal de velocidade aparente. |
| F-01 | Inversão térmica DTS | **FAIL** | HIGH | Apenas thresholds; sem modelo direto + Tikhonov. | Implementar `invert_thermal_flow_profile`. |
| F-03 | FIP (fracture initiation pressure) | **FAIL** | MEDIUM | Nenhuma função `detect_fip`. | Adicionar piecewise linear fit em Q × P downhole. |
| F-04 | Water breakthrough ΔT/xf | **FAIL** | MEDIUM | Nenhum cálculo por fratura. | Implementar `delta_T / xf` por cluster. |
| H-02 | Testes unitários | **PARTIAL** | CRITICAL | Teste de inferência existe, mas backend C++ não compilado; 163 testes não confirmados. | Tornar build C++ parte da CI. |
| J-03 | NaN/Inf e qualidade por canal | **FAIL** | HIGH | Sem verificação `np.isfinite`; regras C++ podem propagar NaN. | Adicionar validação e `quality_flags`. |

---

### 5.2 Processamento de sinais DAS/DTS/LF-DAS

**Resumo dos achados:** Base sólida para filtros, denoising e roteamento por modalidade. Lacunas críticas em alinhamento LF-DAS/DTS, desacoplamento T/ε, correção de atenuação diferencial/ringing, tratamento de unwrapping e validação de NaN/Inf. O fator LF-DAS→temperatura (`100.0`) contradiz a literatura.

| ID | Item | Status | Severidade | Evidência | Recomendação |
|----|------|--------|------------|-----------|--------------|
| A-03 | Separação LF/HF | **PARTIAL** | HIGH | `LFDASProcessor` filtra < 1 Hz, mas sem pipeline LF/HF explícito antes da inferência. | Criar `process_lf` / `process_hf`. |
| B-01 | Roteamento DAS/DTS/DSS | **PASS** | CRITICAL | `_PROCESSOR_MAP` com chaves separadas em `advanced_processors.py:86-161`. | Manter; logar fallback DSS. |
| B-02 | LF-DAS refresh ~2 s | **PASS** | HIGH | `lfdas_processor.py:50-54` e decimação correta. | Validar Nyquist pós-decimação. |
| B-03 | Gauge length como filtro | **PARTIAL** | HIGH | `gauge_length_compensation` existe, mas é ad-hoc; simulador não modela convolução. | Usar deconvolução regularizada; integrar no simulador. |
| B-04 | Baseline geotérmico DTS | **PASS** | HIGH | `dts_processor.py:108-143` remove baseline e calcula gradiente. | Manter. |
| B-05 | DSS/Brillouin C11/C12 | **FAIL** | MEDIUM | `DSSData` existe sem coeficientes. | Adicionar metadados e documentar ambiguidade. |
| C-01 | Denoising DAS/DTS | **PASS** | HIGH | Mediana, Butterworth, wavelet, SVD, EMD/EEMD, NMF roteados. | Manter; adicionar testes Python vs C++. |
| C-02 | Filtro f-k 2D | **FAIL** | MEDIUM | Nenhuma implementação encontrada. | Implementar `fk_filter`/`dip_velocity_filter`. |
| C-03 | Tratamento unwrapping LF-DAS | **FAIL** | HIGH | Filtros opcionais; sem remoção de DC nem detector de saltos. | Adicionar DC removal, outlier detection, clipping HF. |
| C-04 | Atenuação diferencial / ringing | **FAIL** | HIGH | `DTSThermalProcessor` sem correção DAF nem máscara de `n_end_meters`. | Adicionar flags e funções C++. |
| C-05 | Flags de qualidade por canal | **PARTIAL** | MEDIUM | `mean_temperature`, `std_temperature`, `max_anomaly_score`; sem SNR/coerência. | Criar `_compute_quality_flags`. |
| D-01 | `HybridPipeline` preserva modalidade | **PASS** | HIGH | `hybrid_pipeline.py:53-75` propaga `modality` e `history`. | Adicionar guarda de modalidade em DASCore. |
| D-02 | Alinhamento LF-DAS/DTS | **FAIL** | CRITICAL | Nenhuma função de regridding/resampling. | Criar `src/processing/multimodal_alignment.py`. |
| D-03 | Desacoplamento T/ε | **FAIL** | CRITICAL | Inexistente na área de processamento. | Implementar em `LFDASProcessor` (S21). |
| F-05 | Strain/strain rate e padrões de fratura | **FAIL** | HIGH | Nenhum cálculo de strain rate nem detectores. | Adicionar `compute_strain_rate` e módulo de fraturamento. |
| J-01 | Redução de dados edge | **PARTIAL** | HIGH | Decimação e PSD existem; sem pipeline orquestrado por bandas. | Criar `DASReductionPipeline`. |
| J-03 | NaN/Inf/canais mortos | **FAIL** | HIGH | Sem verificações em processadores. | Adicionar `_validate_array` em todos os processadores. |
| I-03 | Docstrings com unidades | **PARTIAL** | LOW | Docstrings têm unidades, mas `thermal_coefficient = 100.0` sem justificativa. | Tornar configurável com default baseado na literatura. |

---

### 5.3 Pré-processamento, filtros e denoising

**Resumo dos achados:** C++20 bem estruturado com boa cobertura de técnicas clássicas. Faltam filtro f-k 2D, validação de NaN/Inf, pipeline de redução edge, compensação rigorosa de gauge length e funções de conveniência LF/HF.

| ID | Item | Status | Severidade | Evidência | Recomendação |
|----|------|--------|------------|-----------|--------------|
| A-03 | Separação LF/HF | **PARTIAL** | HIGH | Filtros configuráveis, mas sem funções de conveniência. | Criar `extract_lfdas`/`extract_hf_das`. |
| B-01 | Roteamento DAS/DTS/DSS | **PASS** | CRITICAL | `_PROCESSOR_MAP` separado; fallback documentado. | Manter; adicionar warnings no fallback. |
| B-03 | Gauge length | **PARTIAL** | HIGH | `gauge_length_compensation` é aproximação ad-hoc. | Deconvolução regularizada e metadados. |
| C-01 | Denoising | **PASS** | HIGH | Todas as técnicas implementadas em C++ e expostas. | Manter; adicionar bandstop/notch. |
| C-02 | Filtro f-k 2D | **FAIL** | MEDIUM | Não implementado. | Adicionar em `filters.hpp` ou `fk_filter.hpp`. |
| C-03 | Unwrapping LF-DAS | **N/A** | HIGH | Fora do escopo dos arquivos inspecionados. | Avaliar em inspeção dedicada. |
| C-04 | Atenuação/ringing DTS | **N/A** | HIGH | Fora do escopo; `thermal.hpp` não implementa. | Avaliar em inspeção dedicada. |
| C-05 | Flags de qualidade | **N/A** | MEDIUM | Fora do escopo; peças individuais existem. | Integrar em processadores térmicos. |
| J-01 | Redução edge | **PARTIAL** | HIGH | FFT, STFT, decimate existem; sem orquestração. | Criar `das_reduction_pipeline`. |
| J-03 | NaN/Inf | **FAIL** | HIGH | Sem verificações iniciais em filtros/denoising. | Adicionar `std::isfinite` e máscaras. |

---

### 5.4 Simulação, validação e testes

**Resumo dos achados:** O gerador cobre as 15 assinaturas canônicas, mas não reproduz padrões físicos específicos de fraturamento nem modela gauge length. O validador é genérico e não cobre individualmente todos os 15 tipos. Testes de inferência e robustez são insuficientes; backend C++ não compilado.

| ID | Item | Status | Severidade | Evidência | Recomendação |
|----|------|--------|------------|-----------|--------------|
| E-01 | 15 assinaturas canônicas | **PASS** | HIGH | `signature_generator.py:37-52` e 15 métodos `generate_*`. | Manter; propagar `SurveyPhaseType`. |
| E-02 | Padrões de fraturamento | **FAIL** | HIGH | Anomalias térmicas genéricas; sem heart/blue wings/antennas. | Implementar geradores e validadores de forma. |
| E-03 | Gas lift / válvulas | **PASS** | MEDIUM | `generate_valve_chatter`, `generate_glv_bellow_rupture`. | Reforçar distinção chatter vs rupture no validador. |
| E-04 | Integridade de poço | **PASS** | HIGH | Leak path, channeling, crossflow presentes. | Adicionar check de direção em crossflow. |
| B-03 | Gauge length no simulador | **FAIL** | HIGH | `gauge_length_m` declarado, mas sem convolução espacial. | Aplicar suavização gaussiana proporcional a gauge length. |
| F-05 | Strain/strain rate | **FAIL** | HIGH | Nenhum cálculo de strain rate nem reversão pós-shut-in. | Adicionar derivada temporal e detectores. |
| H-01 | Validador dos 15 tipos | **PARTIAL** | HIGH | Vários tipos caem no mesmo ramo genérico. | Expandir ramos específicos; uniformizar ≥ 90 %. |
| H-02 | Testes unitários | **PARTIAL** | CRITICAL | Sem testes de inferência, ML, streaming, advanced processors. | Expandir cobertura e CI. |
| H-03 | Benchmarks de campo | **N/A** | MEDIUM | Nenhum notebook/caso de campo nos arquivos inspecionados. | Verificar `docs/`/`examples/`/`notebooks/`. |
| H-04 | Robustez NaN/Inf/SNR | **PARTIAL** | HIGH | Verifica ausência de NaN/Inf nas saídas; não injeta dados corruptos. | Adicionar testes de dados corruptos. |
| I-03 | Docstrings | **PARTIAL** | LOW | Unidades inconsistentes; constantes sem justificativa. | Padronizar docstrings Google/NumPy. |
| J-03 | NaN/Inf/canais mortos | **PARTIAL** | HIGH | Gerador não valida entradas nem emite flags. | Adicionar validação e flags de qualidade. |

---

### 5.5 Integração e padrões industriais

**Resumo dos achados:** ProdML e a ponte Energistics funcionam bem. WITSML descarta modalidade do log. Faltam sensores de referência, correção de atenuação/ringing, metadados de deploy e limites mecânicos do cabo. MQTT é stub.

| ID | Item | Status | Severidade | Evidência | Recomendação |
|----|------|--------|------------|-----------|--------------|
| G-01 | WITSML namespaces 1.3.1.1 / 1.4.1.1 | **PASS** | MEDIUM | `witsml.py:40-71` detecta namespaces; read/write implementados. | Permitir escolha de namespace de saída. |
| G-02 | ProdML metadados | **PASS** | MEDIUM | `prodml.py:169-225` preserva sampling, gauge length, modality, well/wellbore. | Inferir `sampling_rate_hz` de `time_step`. |
| G-03 | Energistics bridge | **PASS** | LOW | Conversões bidirecionais implementadas. | Garantir atribuição controlada de metadados extras. |
| J-02 | Streaming Kafka/Avro/MQTT | **PARTIAL** | MEDIUM | Kafka/Avro funcional; MQTT stub; schema sem well/wellbore. | Implementar MQTT ou documentar como experimental; adicionar well/wellbore ao schema. |
| B-01 | Roteamento modalidade no I/O | **PARTIAL** | CRITICAL | `witsml.py:280` hardcoded `data_category="das"`. | Inferir/receber `modality` em `read_log`. |
| B-03 | Gauge length no WITSML | **PARTIAL** | HIGH | ProdML lê/escrita gauge length; WITSML não. | Adicionar gauge length em WITSML Log. |
| D-05 | Sensores de referência | **FAIL** | HIGH | `Well`/`Wellbore` sem WHT/DHT/GR/CCL. | Estender `WellboreReference`/`SensingAcquisition`. |
| C-04 | Atenuação/ringing no I/O | **FAIL** | HIGH | Nenhum flag de modo de aquisição nem máscara. | Adicionar `acquisition_mode`, `daf_correction_enabled`, `end_mask_m`. |
| J-04 | Metadados de deploy e limites mecânicos | **FAIL** | MEDIUM | Nenhum campo de slickline/e-line/CT, OD, temp, collapse, tension. | Estender `SensingAcquisition`/`AlakoroPatch`; validar jarring. |

---

### 5.6 ML, features e pipeline híbrido

**Resumo dos achados:** Estrutura modular inicial funcional, mas com fragilidades críticas: fusão DAS+DTS sem alinhamento, sem desacoplamento T/ε, sem regras físicas de discriminação de influxo, sem tratamento de NaN/Inf e com taxa de amostragem hardcoded nas features espectrais.

| ID | Item | Status | Severidade | Evidência | Recomendação |
|----|------|--------|------------|-----------|--------------|
| D-01 | `HybridPipeline` preserva modalidade | **PARTIAL** | HIGH | Preserva metadados, mas guarda de dimensionalidade só em `xdas()`. | Adicionar guarda em `dascore()` e `cpp()`. |
| D-02 | Alinhamento DAS+DTS | **FAIL** | CRITICAL | `models.py:174` e `api.py:115` fazem `np.stack` sem interpolação. | Implementar `src/ml/fusion.py` com regridding. |
| D-03 | Desacoplamento T/ε | **FAIL** | CRITICAL | Inexistente. | Criar `src/ml/decoupling.py` (S21). |
| D-04 | Inferência ternária T + energia + velocidade | **FAIL** | HIGH | `FlowRegressor` é CNN/MLP caixa-preta. | Adicionar camada híbrida física pós-modelo. |
| E-05 | Direção de fluxo | **FAIL** | HIGH | `features.py:104-126` calcula correlação adjacente sem sinal/unidades. | Estimar `v = Δz/Δt` com sinal. |
| F-04 | Water breakthrough ΔT/xf | **FAIL** | MEDIUM | Nenhum cálculo. | Adicionar feature `delta_T_over_xf`. |
| H-02 | Testes ML | **PARTIAL** | CRITICAL | `tests/test_ml.py` cobre shapes/treinamento, mas não robustez física. | Expandir com NaN/Inf, shapes distintos, metadados. |
| I-02 | Exemplos | **PASS** | MEDIUM | `examples/ml_training.py`, `hybrid_pipeline.py`. | Adicionar exemplo de fusão DAS+DTS com alinhamento. |
| I-03 | Docstrings com unidades | **FAIL** | LOW | `fs=1.0` hardcoded sem explicação; unidades omitidas. | Revisar docstrings. |
| J-03 | NaN/Inf | **FAIL** | HIGH | Sem verificações em features, dataset, treinador. | Inserir validações e flags. |

---

## 6. Gaps Críticos e Riscos

### Lista priorizada

| # | Gap / Risco | Justificativa técnica | Impacto operacional |
|---|-------------|----------------------|---------------------|
| 1 | **Fusão multimodal sem alinhamento espacial/temporal** (`D-02`) | LF-DAS e DTS têm grids distintos; empilhar arrays diretamente é fisicamente incorreto. | Predições de vazão/temperatura com erros de ordem de magnitude; falsos positivos de produção. |
| 2 | **Ausência de desacoplamento tensão-temperatura** (`D-03`) | LF-DAS mede deformação equivalente misturando T/ε/P; sem separação, eventos geomecânicos são confundidos com transientes térmicos. | Interpretação errada de fraturamento e perfil térmico; decisões de completação baseadas em dados ambíguos. |
| 3 | **Fator LF-DAS→temperatura hardcoded e fisicamente inconsistente** (`I-03` em signal_processing) | `thermal_coefficient = 100.0` vs. ~0,0028 °C/rad da literatura. | Temperaturas absolutas incorretas; calibração térmica inválida. |
| 4 | **Backend C++ não compilado / testes não confirmados** (`H-02`) | `alakoro_core._alakoro_core` ausente; 163 testes do README não verificáveis. | Risco de regressões não detectadas; impossibilidade de validar o motor em produção. |
| 5 | **Tratamento insuficiente de NaN/Inf e qualidade por canal** (`J-03`) | Dados reais de poço contêm canais mortos, ringing e atenuação; sem flags, o sistema pode falhar silenciosamente. | Decisões operacionais baseadas em inferências de confiança desconhecida. |
| 6 | **Inferência sem discriminação de influxo vs refluxo** (`D-04`, `E-05`) | Velocidade aparente é escalar positiva; não há regras ternárias. | Refluxo/reinjeção classificados como produção ativa. |
| 7 | **Padrões de fraturamento não implementados** (`E-02`, `F-05`) | Estado da arte usa heart shapes, blue wings, antennas, bandas de convergência. | Subdetecção de *fracture hits*, reativação de fraturas e geometria de fratura. |
| 8 | **WITSML força `data_category="das"`** (`B-01` em integration) | Descarta modalidade real do log (DTS/DSS). | Erros metrológicos na ingestão; processamento DTS como DAS. |
| 9 | **Atenuação diferencial e ringing não tratados** (`C-04`) | Corrompem a razão térmica Raman e contaminam o final da fibra. | Temperaturas distorcidas nas regiões mais profundas/longas. |
| 10 | **Inversão térmica e modelagem física ausentes** (`F-01`, `F-02`, `F-03`) | Apenas thresholds; sem modelo direto 1D, regularização Tikhonov, validação KGD/Sneddon, FIP. | Vazões absolutas incertas; modelos geomecânicos não validáveis. |

---

## 7. Recomendações e Roadmap

### Quick wins (0–4 semanas)
1. **Corrigir `witsml.read_log`** (`src/io/witsml.py:280`) para não forçar `data_category="das"`; inferir ou receber `modality` do log.
2. **Tornar `thermal_coefficient` configurável** em `src/processing/lfdas_processor.py:146`, com default baseado na literatura (~0,0028 °C/rad) e calibração local via gauges.
3. **Validar `sampling_rate_hz > 0`** no wrapper Python e no binding C++ para evitar divisão por zero.
4. **Adicionar verificações `np.isfinite`** em `InferenceEngine.infer` e nos processadores Python; propagar `quality_flags`.
5. **Uniformizar critério de aprovação dos testes** para ≥ 90 % (`tests/test_alakoro_fibersense.py:233,260`).
6. **Alinhar JSON Schema** com os 15 tipos canônicos emitidos pelo motor C++.

### Médio prazo (1–3 meses)
1. **Implementar alinhamento temporal/espacial LF-DAS/DTS** em `src/processing/multimodal_alignment.py` (ou `src/ml/fusion.py`): interpolação, regridding e sincronização de `depth_step_m`/`time_s`.
2. **Implementar desacoplamento T/ε** em `src/processing/lfdas_processor.py` ou `src/ml/decoupling.py`: regra `Δε_M = Δε_E − C·ΔT` com regressão robusta de `C` e cosine similarity em janela 2D (S21).
3. **Adicionar correção de atenuação diferencial e máscara de ringing** em `DTSThermalProcessor` (`src/processing/dts_processor.py`) e nos leitores/escritores ProdML.
4. **Implementar discriminação de influxo/refluxo**: `FlowDiscriminationRule` usando anomalia térmica + energia acústica 15–100 Hz + velocidade aparente com sinal.
5. **Adicionar sensores de referência** (`wht_temp`, `dht_temp`, `bottomhole_pressure`, `gr_ccl_depths`) à ontologia e ao I/O Energistics.
6. **Implementar detectores de padrões de fraturamento** em `src/processing/advanced_processors.py`/`src/ontology/inference_engine.py`: heart shapes, blue wings, antennas, break lines, bandas de convergência.
7. **Expandir testes de robustez** com NaN/Inf, baixo SNR, ringing, canais mortos e shapes incompatíveis.
8. **Finalizar MQTT** ou documentar como experimental; adicionar `well_id`/`wellbore_id` ao schema Avro.

### Longo prazo (3–6 meses)
1. **Inversão térmica DTS** com modelo direto 1D, termo fonte por intervalo perfurado e regularização Tikhonov (`src/processing/dts_processor.py` ou módulo dedicado).
2. **Modelagem geomecânica acoplada fluxo-geomecânica** para fraturamento, com validação contra KGD/Sneddon.
3. **FIP e water breakthrough** (`detect_fip`, `delta_T_over_xf`) integrados ao motor de inferência.
4. **Pipeline de redução edge** orquestrado (`DASReductionPipeline`) para reduzir ~TB para GB/MB com extração de energia por bandas e metadados de fator de redução.
5. **Compensação rigorosa de gauge length** via deconvolução regularizada e integração no simulador.
6. **ML híbrido físico-guidado** com camada de regras pós-modelo para reduzir falsos positivos.
7. **Benchmarks de campo** em notebooks (`docs/`/`examples/`) para Culzean, White Tiger, Neuquén, Trident, Montney.
8. **CI/CD com build C++** e execução completa dos testes em ambiente controlado.

### Roadmap sugerido

| Trimestre | Foco principal | Entregáveis |
|-----------|----------------|-------------|
| **T1** | Correções críticas de I/O, calibração e robustez | WITSML modality fix; `thermal_coefficient` configurável; NaN/Inf checks; CI com build C++; testes ≥ 90 %. |
| **T2** | Fusão multimodal e desacoplamento T/ε | `multimodal_alignment.py`; `decouple_strain_temperature`; correção DAF + ringing; sensores de referência. |
| **T3** | Física de fraturamento/fluxo e ML híbrido | Detectores de padrões de fratura; `FlowDiscriminationRule`; `FlowRegressor` com regras físicas; `DASReductionPipeline`. |
| **T4** | Modelagem avançada e validação de campo | Inversão térmica 1D; validação KGD/Sneddon; FIP; water breakthrough; notebooks de benchmarks. |

---

## 8. Conclusão

O **Alakoro_FiberSense** é um protótipo funcional e arquitetonicamente promissor para processamento e inferência DFOS em poços de petróleo. Ele já entrega uma estrutura modular com backends Python e C++20, suporte a múltiplos formatos industriais (ProdML, WITSML, DASCore, Xdas), geração das 15 assinaturas canônicas e uma variedade de filtros/denoising. Esses são alicerces sólidos.

No entanto, a auditoria revela **gaps críticos** que impedem o uso em dados reais de poço sem intervenção manual significativa:
- A **fusão multimodal** ainda não existe de fato: LF-DAS e DTS não são alinhados, não há desacoplamento T/ε e o ML empilha arrays sem regras físicas.
- A **modelagem física** de fraturamento, fluxo e inversão térmica está em estágio de *proof-of-concept* heurístico.
- A **robustez a dados reais** (NaN/Inf, canais mortos, ringing, atenuação, acoplamento) é insuficiente.
- O **backend C++ não foi compilado no ambiente auditado**, o que impede a validação dinâmica do motor.

A recomendação geral é tratar os itens CRITICAL e HIGH do T1/T2 antes de qualquer campo piloto. Com as correções propostas, o Alakoro_FiberSense pode evoluir de protótipo para uma plataforma de DFOS tecnicamente competitiva com o estado da arte.

---

## 9. Referências e Anexos

### Papers/apresentações analisados (fontes S01–S21)
Os 21 resumos estão em `docs/.audit_work/summaries/` e são detalhados em `consolidated_requirements.md`:

| Código | Título / Fonte |
|--------|----------------|
| S01 | Assessing Geological Deformation Across Spatial and Temporal Scales Using Distributed Fiber Optic Sensing |
| S02 | Characterization of low-frequency DAS signals in hydraulic fracturing — A coupled flow-geomechanical simulation approach |
| S03 | Clipping Oilfield Services — 27/06/2026 |
| S04 | Fibra Óptica em Minifrac (DOC-20260701-WA0006) |
| S05 | Fibra Ótica em Poços de Petróleo (DOC-20260716-WA0003) |
| S06 | Estimation of Temperature Profiles using Low-Frequency Distributed Acoustic Sensing from In-Well Measurements |
| S07 | Evolution mechanism of optical fiber strain induced by multi-fracture growth during fracturing in horizontal wells |
| S08 | Expro Well Surveillance and Optimization (May 2026) |
| S09 | Fibra ótica em poços de petróleo: primeiras considerações (markdown) |
| S10 | Fibra ótica em poços de petróleo: primeiras considerações (txt) |
| S11 | Govind P. Agrawal — Fiber-Optic Communication Systems, 4th ed. (2010) |
| S12 | Optical Fibre-Based Sensors for Oil and Gas Applications (MDPI Sensors 2021) |
| S13 | SPE-0324-0069-JPT — Slickline DFOS in Culzean HPHT gas well |
| S14 | SPE-212919-MS — Sustained Annulus Pressure (Neuquén) |
| S15 | SPE-219546-MS — White Tiger gas lift DFOS |
| S16 | SPE-228489-MS — DFOS-Based Fracture Evaluation and Rate Distribution |
| S17 | DTS inversion for flow profile in gas-water bifasic MFHW |
| S18 | Energies 2022 review — Research Progress of DFOS in HF and production monitoring |
| S19 | Filtering Strategies for Deformation-Rate DAS (MDPI 2022) |
| S20 | Gas production profiling using DAS and DTS (2026) |
| S21 | Improved Strain–Temperature Decoupling Method for LF-DAS/DTS (2026) |

### Arquivos de trabalho gerados
- `docs/.audit_work/consolidated_requirements.md`
- `docs/.audit_work/inspection_checklist.md`
- `docs/.audit_work/findings/inference_engine.md`
- `docs/.audit_work/findings/signal_processing.md`
- `docs/.audit_work/findings/preprocessing.md`
- `docs/.audit_work/findings/simulation_tests.md`
- `docs/.audit_work/findings/integration.md`
- `docs/.audit_work/findings/ml_pipeline.md`
- `docs/technical_audit_das_dts_dss.md` (este relatório)

### Principais caminhos de código citados
- `src/ontology/inference_engine.py`
- `src/ontology/sensing.py`
- `src/ontology/events.py`
- `src/ontology/petroleum.py`
- `src/processing/advanced_processors.py`
- `src/processing/lfdas_processor.py`
- `src/processing/dts_processor.py`
- `src/processing/hybrid_pipeline.py`
- `src/simulation/signature_generator.py`
- `src/validation/signature_validator.py`
- `src/io/witsml.py`
- `src/io/prodml.py`
- `src/io/energistics_bridge.py`
- `src/io/streaming.py`
- `src/io/schemas/alakoro_sensing.avsc`
- `src/ml/features.py`
- `src/ml/models.py`
- `src/ml/api.py`
- `src/cpp/include/alakoro/inference_engine.hpp`
- `src/cpp/include/alakoro/thermal.hpp`
- `src/cpp/include/alakoro/filters.hpp`
- `src/cpp/include/alakoro/denoising.hpp`
- `src/cpp/include/alakoro/adaptive.hpp`
- `src/cpp/src/bindings.cpp`
- `tests/test_inference_engine.py`
- `tests/test_alakoro_fibersense.py`
- `tests/test_ml.py`
