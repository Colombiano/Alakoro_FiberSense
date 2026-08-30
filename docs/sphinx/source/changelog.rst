Changelog
=========

v2.10.0 (2026-08-30) — Paridade DTS/DAS e Processadores Térmicos C++20
-----------------------------------------------------------------------

Adições / Additions
^^^^^^^^^^^^^^^^^^^

* **Processadores térmicos C++20** (`src/cpp/include/alakoro/thermal.hpp`) —
  gradiente térmico, correção de baseline geotérmico, detecção de anomalias,
  filtro de mediana espacial e estimativa de gradiente geotérmico.
* **Bindings C++20 generalizados** (`src/cpp/src/bindings.cpp`) — variantes
  ``*_d_das`` e ``*_d_dts`` para todos os processadores avançados.
* **DTSThermalProcessor** (`src/processing/dts_processor.py`) — pipeline
  completo de processamento térmico para DTS.
* **DTSFeatureExtractor** (`src/ml/features.py`) — features estatísticas,
  espectrais, térmicas e de anomalia.
* **Validação térmica avançada** (`src/validation/signature_validator.py`) —
  checks de gradiente, anomalias e baseline geotérmico via C++20.
* **advanced_processors.py multimodal** — roteamento automático por modalidade.
* **Testes DTS** (`tests/test_dts_processor.py`) — 9 novos testes.

Resultado / Result
^^^^^^^^^^^^^^^^^^

* Total: 163 testes passando, 1 skipped.

v2.2.1 (2026-07-18)
-------------------

Correções e Melhorias / Fixes and Improvements
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* **signature_generator.py v4.1** — Refatoração, eliminação de duplicação de código
* **lfdas_processor.py v1.1.0** — Refresh rate ~2s alinhado com README
* **signature_validator.py v1.2.1** — Detecção de múltiplos picos para crossflow zonal
* **fibersense_event_schema_v1.1.0.json** — 18 event types (4 novos)
* **__init__.py** — Exports em todos os módulos
* **tests/** — 40+ testes unitários pytest
* **README.md** — Atualizado para v2.2.1

Novos Arquivos / New Files
^^^^^^^^^^^^^^^^^^^^^^^^^^

* ``install/INSTALL_WINDOWS.bat`` — Instalador Windows (modo leigo)
* ``install/INSTALL_UNIX.sh`` — Instalador macOS/Linux (modo leigo)
* ``install/INSTALL_GUI.py`` — Instalador gráfico universal (modo leigo)
* ``docs/sphinx/`` — Documentação Sphinx completa
* ``pyproject.toml`` — Metadata PyPI (PEP 517/518)
* ``Dockerfile`` — Imagem containerizada
* ``.github/workflows/`` — CI/CD (testes, Docker, PyPI, release)

Resultado / Result
^^^^^^^^^^^^^^^^^^^

* Taxa de validação: 91.3% (15/15 assinaturas ≥90%)

v2.2.0 (2026-07-18)
-------------------

* Versão inicial com 15 assinaturas canônicas
* LF-DAS / eXDTS processor
* Eventos semânticos JSON Schema v1.0.0
* Documentação bilíngue PT/EN
