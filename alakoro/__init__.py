"""
Alakoro FiberSense v2.11.0
Plataforma Open-Source Multi-Modal para DFOS em Poços de Petróleo
Open-Source Multi-Modal Platform for DFOS in Oil & Gas Wells

Autor/Author: Luiz Paulo Colombiano
Licença/License: MIT
"""

__version__ = "2.11.0"
__author__ = "Luiz Paulo Colombiano"
__license__ = "MIT"


def main():
    """Entry point mínimo da CLI / Minimal CLI entry point."""
    print(f"🎸 Alakoro FiberSense v{__version__}")
    print("Módulos disponíveis / Available modules:")
    print("  - alakoro_core      (C++20 core: DASData, DTSData, DSSData, processors)")
    print("  - alakoro.simulation    (SignatureGenerator, WellGeometry, AcquisitionConfig)")
    print("  - alakoro.processing    (LFDASProcessor, DTSThermalProcessor)")
    print("  - alakoro.validation    (SignatureValidator)")
    print("  - alakoro.events        (EVENT_SCHEMA)")
    print("  - alakoro.gui           (AlakoroMainWindow — PySide6 GUI)")
    print(f"Licença / License: {__license__}")


def main_gui():
    """Entry point da interface gráfica desktop / Desktop GUI entry point."""
    try:
        from alakoro.gui.main_window import main as _gui_main
    except ImportError as exc:
        raise ImportError(
            "GUI dependencies not installed. Run: "
            "pip install alakoro-fibersense[gui]"
        ) from exc
    _gui_main()


if __name__ == "__main__":
    main()
