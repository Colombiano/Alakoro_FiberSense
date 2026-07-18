Assinaturas Canônicas / Canonical Signatures
===========================================

Visão Geral / Overview
----------------------

O Alakoro FiberSense implementa **15 assinaturas canônicas** que cobrem as principais operações de monitoramento de poço de petróleo e gás usando fibra óptica distribuída (DFOS).

**Alakoro FiberSense implements 15 canonical signatures covering the main oil and gas well monitoring operations using distributed fiber optic sensing (DFOS).**

Categorias / Categories
-----------------------

Fluxo e Pressão / Flow and Pressure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. **Joule-Thomson** — Interface gás/óleo / Gas/oil interface
2. **Slope Velocity** — Rastreamento de fluxo / Flow tracking
3. **Warm-Back** — Recuperação térmica / Thermal recovery
4. **Slugging Cycle** — Ciclo de slugging / Slugging cycle

Válvulas e Vazamentos / Valves and Leaks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

5. **Valve Chatter** — Chatter de válvula / Valve chatter
6. **Leak Path** — Vazamento tubing↔ânulo / Tubing↔annulus leak
7. **GLV Bellow Rupture** — Fole furado de GLV / GLV bellow rupture

Fraturamento / Fracturing
^^^^^^^^^^^^^^^^^^^^^^^^^

8. **Perforation Effectiveness** — Efetividade de canhoneio / Perforation effectiveness
9. **Frac Screen-out** — Embuchamento de fratura / Fracture screen-out
10. **Proppant Distribution** — Distribuição de propante / Proppant distribution
11. **Frac Height Growth** — Crescimento de altura / Fracture height growth

Cimentação / Cementing
^^^^^^^^^^^^^^^^^^^^^^

12. **Cement Bond Evaluation** — Avaliação de cimentação / Cement bond evaluation
13. **Re-Cementing Assessment** — Avaliação de recimentação / Re-cementing assessment
14. **Zonal Crossflow** — Fluxo cruzado zonal / Zonal crossflow
15. **Cement Channeling** — Canalização de cimento / Cement channeling

Parâmetros Físicos / Physical Parameters
----------------------------------------

Gradiente Geotérmico / Geothermal Gradient
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   T_GRADIENT = 0.03  # °C/m (padrão / default)
   T_SURFACE = 20.0   # °C (temperatura superficial / surface temperature)

Ruído / Noise
^^^^^^^^^^^^^^

.. code-block:: python

   SNR_DTS = 25.0  # dB (temperatura / temperature)
   SNR_DAS = 20.0  # dB (acústica / acoustic)

Exemplo de Geração / Generation Example
---------------------------------------

.. code-block:: python

   from src.simulation import SignatureGenerator, WellGeometry, AcquisitionConfig

   well = WellGeometry(depth_top=0, depth_bottom=3000, n_channels=3000)
   acq = AcquisitionConfig(sampling_rate_hz=1000, trace_interval_s=2.0, duration_s=3600)
   gen = SignatureGenerator(well, acq)

   # Gerar todas as 15 assinaturas / Generate all 15 signatures
   signatures = {
       'jt': gen.generate_joule_thomson(interface_depth=1500.0),
       'sv': gen.generate_slope_velocity(),
       'wb': gen.generate_warm_back(),
       'vc': gen.generate_valve_chatter(),
       'sc': gen.generate_slugging_cycle(),
       'lp': gen.generate_leak_path(),
       'glv': gen.generate_glv_bellow_rupture(),
       'pe': gen.generate_perforation_effectiveness(),
       'fs': gen.generate_frac_screenout(),
       'fp': gen.generate_frac_proppant_distribution(),
       'fh': gen.generate_frac_height_growth(),
       'cb': gen.generate_cement_bond_evaluation(),
       'rc': gen.generate_re_cementing_assessment(),
       'cf': gen.generate_crossflow_zonal(),
       'cc': gen.generate_cement_channeling(),
   }
