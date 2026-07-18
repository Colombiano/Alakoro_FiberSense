Referência da API / API Reference
=================================

Módulo de Simulação / Simulation Module
-----------------------------------------

.. automodule:: src.simulation.signature_generator
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

   .. autoclass:: SignatureGenerator
      :members:
      :undoc-members:

   .. autoclass:: WellGeometry
      :members:

   .. autoclass:: AcquisitionConfig
      :members:

   .. autoclass:: EventSignatureType
      :members:

   .. autoclass:: SurveyPhaseType
      :members:

Módulo de Processamento / Processing Module
--------------------------------------------

.. automodule:: src.processing.lfdas_processor
   :members:
   :undoc-members:
   :show-inheritance:

   .. autoclass:: LFDASProcessor
      :members:
      :undoc-members:

Módulo de Validação / Validation Module
----------------------------------------

.. automodule:: src.validation.signature_validator
   :members:
   :undoc-members:
   :show-inheritance:

   .. autoclass:: SignatureValidator
      :members:
      :undoc-members:

Módulo de Eventos / Events Module
----------------------------------

.. automodule:: src.events
   :members:
   :undoc-members:

Schema JSON / JSON Schema
^^^^^^^^^^^^^^^^^^^^^^^^^^

O schema de eventos semânticos está disponível em:
``src/events/fibersense_event_schema_v1.1.0.json``

The semantic event schema is available at:
``src/events/fibersense_event_schema_v1.1.0.json``

Eventos Suportados / Supported Events:

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Event Type
     - Assinatura / Signature
     - Descrição / Description
   * - JouleThomsonSignature
     - JOULE_THOMSON
     - Dipolo térmico Joule-Thomson
   * - WarmBackDetected
     - WARM_BACK
     - Recuperação térmica detectada
   * - LeakDetected
     - LEAK_PATH
     - Vazamento detectado
   * - ValveChatter
     - VALVE_CHATTER
     - Chatter de válvula
   * - SluggingCycle
     - SLUGGING_CYCLE
     - Ciclo de slugging
   * - CrossflowDetected
     - CROSSFLOW_ZONAL
     - Fluxo cruzado detectado
   * - VelocityEstimate
     - SLOPE_VELOCITY
     - Estimativa de velocidade
   * - CementBondEvaluated
     - CEMENT_BOND_EVALUATION
     - Cimentação avaliada
   * - ReCementingAssessed
     - RE_CEMENTING_ASSESSMENT
     - Recimentação avaliada
   * - CementChannelingDetected
     - CEMENT_CHANNELING
     - Canalização detectada
   * - FractureScreenoutDetected
     - FRAC_SCREENOUT
     - Screen-out detectado
   * - PerforationEffectivenessEvaluated
     - PERFORATION_EFFECTIVENESS
     - Efetividade de canhoneio avaliada
   * - ProppantDistributionMapped
     - FRAC_PROPPANT_DISTRIBUTION
     - Distribuição de propante mapeada
   * - FractureHeightGrowthDetected
     - FRAC_HEIGHT_GROWTH
     - Crescimento de altura detectado
   * - ValveMultipointing
     - GLV_BELLOW_RUPTURE
     - Multipointing de válvula
   * - RateEstimate
     - —
     - Estimativa de vazão
   * - FIPEstimate
     - —
     - Estimativa de FIP
   * - DiagnosisConcluded
     - —
     - Diagnóstico concluído
