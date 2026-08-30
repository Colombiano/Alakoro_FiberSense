Alakoro FiberSense
==================

**Plataforma Open-Source Multi-Modal para DFOS em Poços de Petróleo**
**Open-Source Multi-Modal Platform for DFOS in Oil & Gas Wells**

.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
   :target: https://opensource.org/licenses/MIT
   :alt: License: MIT

.. image:: https://img.shields.io/badge/python-3.9+-blue.svg
   :target: https://www.python.org/downloads/
   :alt: Python 3.9+

.. image:: https://img.shields.io/pypi/v/alakoro-fibersense.svg
   :target: https://pypi.org/project/alakoro-fibersense/
   :alt: PyPI

.. toctree::
   :maxdepth: 2
   :caption: Conteúdo / Contents:

   install
   user_guide
   api_reference
   signatures
   changelog
   contributing

Visão Geral / Overview
----------------------

O **Alakoro FiberSense** é uma plataforma **full-stack open-source** para processamento, simulação e interpretação de dados de **fibra óptica distribuída (DFOS)** — DAS, DTS e DSS — em operações de poço de petróleo e gás.

**Alakoro FiberSense** is an **open-source full-stack** platform for processing, simulating, and interpreting **distributed fiber optic sensing (DFOS)** data — DAS, DTS, and DSS — in oil and gas well operations.

Características / Features
--------------------------

- **Paridade DTS/DAS** — processadores avançados C++20 para DAS e DTS
- **Processadores Térmicos C++20** — gradiente, baseline geotérmico, anomalias, mediana espacial
- **DTSThermalProcessor** — pipeline completo de processamento térmico
- **15 Assinaturas Canônicas** (M15) — 6 originais + 9 novas
- **LF-DAS / eXDTS** (M1) — temperatura de alta taxa (~2s refresh)
- **Eventos Semânticos** (M12) — JSON Schema v1.1.0 (18 event types)
- **Validador v1.2.1** — detecção de múltiplos picos + validações térmicas C++20
- **GUI Desktop** — PySide6 + PyQtGraph (`alakoro-gui`)
- **Testes Unitários** — pytest com 164 testes passando
- **PyPI** — ``pip install alakoro-fibersense``
- **Docker** — imagem oficial disponível
- **Documentação Bilíngue** — PT + EN

Instalação Rápida / Quick Install
---------------------------------

.. code-block:: bash

   pip install alakoro-fibersense

Exemplo Rápido / Quick Example
------------------------------

.. code-block:: python

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
   print(f"Success rate: {validation['success_rate']:.0f}%")

Processar DTS / Process DTS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from src.processing import DTSThermalProcessor

   temperature = jt['dts']
   proc = DTSThermalProcessor(
       depth_step_m=1.0,
       surface_temp=20.0,
       geothermal_gradient=0.03,
       spatial_median_window=5,
       anomaly_threshold_sigma=3.0,
   )
   result = proc.process(temperature)
   print(f"Gradient shape: {result['thermal_gradient'].shape}")
   print(f"Anomalies: {result['anomalies'].sum()}")

Índices e Tabelas / Indices and Tables
======================================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
