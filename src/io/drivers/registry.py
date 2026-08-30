"""
Alakoro FiberSense — Registry de drivers de fabricantes

Descobre plugins via entry points e fornece fallback para leitores
open-source (DASCore, Xdas) quando nenhum plugin proprietário corresponder.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from src.io.alakoro_spool import AlakoroPatch, AlakoroSpool
from src.io.dascore_formats import read as read_dascore
from src.io.xdas_formats import read_xdas

from .base import BaseVendorDriver

try:
    from importlib.metadata import entry_points
except ImportError:  # pragma: no cover
    # Python < 3.10 fallback
    from importlib_metadata import entry_points  # type: ignore


ENTRY_POINT_GROUP = "alakoro.driver"


def _discover_drivers() -> List[Type[BaseVendorDriver]]:
    """Descobre classes de driver via entry points do setuptools."""
    drivers: List[Type[BaseVendorDriver]] = []

    try:
        eps = entry_points(group=ENTRY_POINT_GROUP)
    except TypeError:  # pragma: no cover
        # Compatibilidade com APIs antigas
        eps = entry_points().get(ENTRY_POINT_GROUP, [])

    for ep in eps:
        try:
            cls = ep.load()
            if (
                isinstance(cls, type)
                and issubclass(cls, BaseVendorDriver)
                and cls is not BaseVendorDriver
            ):
                drivers.append(cls)
        except Exception as exc:
            warnings.warn(f"Failed to load driver entry point {ep.name}: {exc}")

    # Também carrega drivers opcionais embarcados no pacote, se disponíveis
    try:
        from .optional import example_vendor

        if (
            example_vendor.ExampleVendorDriver.is_available()
            and example_vendor.ExampleVendorDriver not in drivers
        ):
            drivers.append(example_vendor.ExampleVendorDriver)
    except Exception:
        pass

    return drivers


class VendorDriverRegistry:
    """Registry singleton de drivers de fabricantes."""

    def __init__(self):
        self._drivers: Optional[List[Type[BaseVendorDriver]]] = None

    def _load(self) -> List[Type[BaseVendorDriver]]:
        if self._drivers is None:
            self._drivers = _discover_drivers()
        return self._drivers

    def list_drivers(self) -> List[Type[BaseVendorDriver]]:
        """Lista todas as classes de driver descobertas."""
        return list(self._load())

    def list_available(self) -> List[Type[BaseVendorDriver]]:
        """Lista drivers que estão disponíveis para uso (SDK/licença OK)."""
        return [d for d in self._load() if d.is_available()]

    def detect_driver(self, path: Union[str, Path]) -> Optional[Type[BaseVendorDriver]]:
        """Detecta o driver mais adequado para um arquivo/diretório."""
        path = Path(path)
        for driver_cls in self.list_available():
            try:
                if driver_cls.detect(path):
                    return driver_cls
            except Exception as exc:
                warnings.warn(f"Driver {driver_cls.name} detection failed: {exc}")
        return None

    def get_driver(self, name: str) -> Optional[Type[BaseVendorDriver]]:
        """Retorna driver pelo nome."""
        for driver_cls in self._load():
            if driver_cls.name.lower() == name.lower():
                return driver_cls
        return None


def _fallback_read(path: Union[str, Path], **kwargs: Any) -> Union[AlakoroPatch, AlakoroSpool]:
    """
    Fallback para leitores open-source quando nenhum driver proprietário
    corresponder. Tenta Xdas primeiro, depois DASCore.
    """
    errors: Dict[str, Exception] = {}

    try:
        return read_xdas(path, **kwargs)
    except Exception as exc:
        errors["xdas"] = exc

    try:
        return read_dascore(path, **kwargs)
    except Exception as exc:
        errors["dascore"] = exc

    raise RuntimeError(
        f"No vendor driver or open-source reader could load {path}. "
        f"Errors: {errors}"
    )


def read_vendor(
    path: Union[str, Path],
    vendor_hint: Optional[str] = None,
    fallback: bool = True,
    **kwargs: Any,
) -> Union[AlakoroPatch, AlakoroSpool]:
    """
    Lê um arquivo ou diretório usando driver de fabricante, com fallback
    para DASCore/Xdas.

    Args:
        path: caminho para arquivo ou diretório.
        vendor_hint: nome do fabricante para forçar uso de um driver específico.
        fallback: se True, tenta DASCore/Xdas quando nenhum driver proprietário
                  corresponder.
        **kwargs: extras repassados para o driver ou leitor fallback.

    Returns:
        AlakoroPatch ou AlakoroSpool.
    """
    registry = VendorDriverRegistry()

    if vendor_hint:
        driver_cls = registry.get_driver(vendor_hint)
        if driver_cls is None:
            raise ValueError(f"Vendor driver '{vendor_hint}' not found")
        if not driver_cls.is_available():
            raise RuntimeError(f"Vendor driver '{vendor_hint}' is not available")
        return driver_cls().read(path, **kwargs)

    driver_cls = registry.detect_driver(path)
    if driver_cls is not None:
        return driver_cls().read(path, **kwargs)

    if fallback:
        return _fallback_read(path, **kwargs)

    raise ValueError(f"No vendor driver detected for {path}")


def list_available_drivers() -> List[str]:
    """Retorna lista de nomes dos drivers disponíveis."""
    registry = VendorDriverRegistry()
    return [d.name for d in registry.list_available()]


def detect_driver(path: Union[str, Path]) -> Optional[str]:
    """Detecta e retorna o nome do driver mais adequado, ou None."""
    registry = VendorDriverRegistry()
    driver_cls = registry.detect_driver(path)
    return driver_cls.name if driver_cls else None
