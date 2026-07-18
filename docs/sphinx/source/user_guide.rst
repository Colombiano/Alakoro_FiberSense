Guia do Usuário / User Guide
============================

Primeiros Passos / Quick Start
------------------------------

Gerar uma Assinatura / Generate a Signature
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from src.simulation import SignatureGenerator, WellGeometry, AcquisitionConfig

   well = WellGeometry(depth_top=0, depth_bottom=3000, n_channels=3000)
   acq = AcquisitionConfig(sampling_rate_hz=1000, trace_interval_s=2.0, duration_s=3600)

   gen = SignatureGenerator(well, acq)
   jt = gen.generate_joule_thomson(interface_depth=1500.0)

   print(f"📝 Assinatura: {jt['signature_type'].pt}")
   print(f"   Dados DTS: {jt['dts'].shape}")
   print(f"   Dados DAS: {jt['das'].shape}")

Processar com LF-DAS / Process with LF-DAS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from src.processing import LFDASProcessor

   lfdas = LFDASProcessor(cutoff_hz=1.0, refresh_rate_target_s=2.0)
   result = lfdas.process(jt['das'], trace_interval_s=2.0)

   print(f"🌡️ Temperatura extraída: {result['temperature'].shape}")
   print(f"   Refresh rate: {result['refresh_rate_s']:.1f}s")

Validar a Assinatura / Validate the Signature
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from src.validation import SignatureValidator

   validator = SignatureValidator(well, acq)
   validation = validator.validate_signature(jt, result)

   print(f"✅ Validação: {validation['passed']}/{validation['total']} passaram")
   print(f"   Taxa de sucesso: {validation['success_rate']:.0f}%")

As 15 Assinaturas Canônicas / The 15 Canonical Signatures
--------------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 5 25 25 45

   * - #
     - Nome (PT)
     - Name (EN)
     - Uso / Use
   * - 1
     - Dipolo Térmico Joule-Thomson
     - Joule-Thomson Thermal Dipole
     - Interface gás/óleo / Gas/oil interface
   * - 2
     - Rastreamento de Inclinação
     - Slope Tracking
     - Velocidade de fluxo / Flow velocity
   * - 3
     - Recuperação Térmica
     - Warm-Back
     - Avaliação de injeção / Injection assessment
   * - 4
     - Chatter de Válvula
     - Valve Chatter
     - Diagnóstico de GLV / GLV diagnosis
   * - 5
     - Ciclo de Slugging
     - Slugging Cycle
     - Instabilidade de produção / Production instability
   * - 6
     - Vazamento Tubing↔Ânulo
     - Leak Path
     - Detecção de vazamento / Leak detection
   * - 7
     - Fole Furado GLV
     - GLV Bellow Rupture
     - Falha de válvula / Valve failure
   * - 8
     - Efetividade de Canhoneio
     - Perforation Effectiveness
     - Avaliação de perfurações / Perforation assessment
   * - 9
     - Embuchamento de Fratura
     - Fracture Screen-out
     - Fraturamento hidráulico / Hydraulic fracturing
   * - 10
     - Distribuição de Propante
     - Proppant Distribution
     - Mapeamento de propante / Proppant mapping
   * - 11
     - Crescimento de Altura
     - Fracture Height Growth
     - Controle de fratura / Fracture control
   * - 12
     - Avaliação de Cimentação
     - Cement Bond Evaluation
     - Qualidade de cimentação / Cement quality
   * - 13
     - Avaliação de Recimentação
     - Re-Cementing Assessment
     - Reparo de cimentação / Cement repair
   * - 14
     - Fluxo Cruzado Zonal
     - Zonal Crossflow
     - Comunicação entre zonas / Zonal communication
   * - 15
     - Canalização de Cimento
     - Cement Channeling
     - Canais no cimento / Cement channels

Executar Testes / Run Tests
---------------------------

.. code-block:: bash

   # Todos os testes / All tests
   pytest tests/ -v

   # Apenas assinaturas / Only signatures
   pytest tests/test_alakoro_fibersense.py::TestSignatures -v

   # Apenas LF-DAS / Only LF-DAS
   pytest tests/test_alakoro_fibersense.py::TestLFDASProcessor -v

   # Com cobertura / With coverage
   pytest tests/ --cov=src --cov-report=html
