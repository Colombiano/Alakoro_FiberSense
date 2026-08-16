"""
Alakoro FiberSense v2.2.1
Plataforma Open-Source Multi-Modal para DFOS em Poços de Petróleo
Open-Source Multi-Modal Platform for DFOS in Oil & Gas Wells

Autor/Author: Luiz Paulo Colombiano
Licença/License: MIT
"""

__version__ = "2.3.0"
__author__ = "Luiz Paulo Colombiano"
__license__ = "MIT"


def main():
    """Entry point mínimo da CLI / Minimal CLI entry point."""
    print(f"🎸 Alakoro FiberSense v{__version__}")
    print("Módulos disponíveis / Available modules:")
    print("  - src.simulation    (SignatureGenerator, WellGeometry, AcquisitionConfig)")
    print("  - src.processing    (LFDASProcessor)")
    print("  - src.validation    (SignatureValidator)")
    print("  - src.events        (EVENT_SCHEMA)")
    print(f"Licença / License: {__license__}")


if __name__ == "__main__":
    main()
