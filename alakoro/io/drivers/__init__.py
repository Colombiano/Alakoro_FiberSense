"""
Alakoro FiberSense — API pública de drivers de fabricantes (vendor drivers).

Plugins proprietários podem registrar-se via entry point ``alakoro.driver``.
O core permanece MIT; drivers comerciais são mantidos em pacotes separados.
"""

from __future__ import annotations

from .base import BaseVendorDriver
from .registry import (
    VendorDriverRegistry,
    detect_driver,
    list_available_drivers,
    read_vendor,
)

__all__ = [
    "BaseVendorDriver",
    "VendorDriverRegistry",
    "detect_driver",
    "list_available_drivers",
    "read_vendor",
]
