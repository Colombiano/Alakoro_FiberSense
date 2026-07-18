Instalação / Installation
=========================

Escolha seu modo / Choose your mode:

.. toctree::
   :maxdepth: 2

Modo Leigo / Easy Mode (Recomendado / Recommended)
--------------------------------------------------

> **Para quem não quer saber de código.**
> **For those who don't want to deal with code.**

Windows
^^^^^^^

1. Baixe o ZIP do projeto / Download the project ZIP
2. Extraia em qualquer pasta / Extract to any folder
3. **Clique duplo** em ``install/INSTALL_WINDOWS.bat`` / **Double-click** ``install/INSTALL_WINDOWS.bat``
4. Pronto! / Done!

macOS / Linux
^^^^^^^^^^^^^

.. code-block:: bash

   bash install/INSTALL_UNIX.sh

Interface Gráfica (todos os sistemas) / GUI (all systems)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   python install/INSTALL_GUI.py

Modo Geek / Geek Mode
---------------------

> **Para quem curte linha de comando.**
> **For terminal lovers.**

Via PyPI (recomendado) / Via PyPI (recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   pip install alakoro-fibersense

Via Git / Via Git
^^^^^^^^^^^^^^^^^

.. code-block:: bash

   git clone https://github.com/Colombiano/Alakoro_FiberSense.git
   cd Alakoro_FiberSense
   pip install -r requirements.txt
   pytest tests/ -v

Via Docker / Via Docker
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   docker pull colombiano/alakoro-fibersense:latest
   docker run -it --rm colombiano/alakoro-fibersense:latest

Verificando a Instalação / Verifying Installation
-------------------------------------------------

.. code-block:: python

   from src.simulation import SignatureGenerator, WellGeometry, AcquisitionConfig
   from src.validation import SignatureValidator
   from src.processing import LFDASProcessor

   well = WellGeometry(depth_top=0, depth_bottom=3000, n_channels=3000)
   acq = AcquisitionConfig(sampling_rate_hz=1000, trace_interval_s=2.0, duration_s=3600)

   gen = SignatureGenerator(well, acq)
   jt = gen.generate_joule_thomson(interface_depth=1500.0)

   print(f"✅ Alakoro FiberSense v2.2.1 pronto! / ready!")
   print(f"   Assinatura gerada: {jt['signature_type'].pt}")
   print(f"   DTS shape: {jt['dts'].shape}")
