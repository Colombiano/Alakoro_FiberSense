"""
Alakoro FiberSense — Integração DASCore
DASCore Integration

Converte dados Alakoro ↔ Patch/Spool do DASCore.
"""

import numpy as np
import dascore as dc
from dascore import Patch
from dascore.core.attrs import PatchAttrs
from typing import Dict, Optional


def alakoro_to_patch(data: np.ndarray,
                     start_time: str = "2026-01-01T00:00:00",
                     dt_s: float = 2.0,
                     dx_m: float = 1.0,
                     modality: str = "DAS",
                     units: Optional[str] = None) -> Patch:
    """Converte array Alakoro (time, distance) em Patch DASCore."""
    n_t, n_z = data.shape
    time = (np.arange(n_t) * dt_s * 1_000_000_000).astype("timedelta64[ns]")
    distance = np.arange(n_z) * dx_m

    if units is None:
        units = "1/s" if modality == "DAS" else "degC"

    attrs = PatchAttrs(
        data_category=modality.lower(),
        data_units=units,
        time_step=np.timedelta64(int(dt_s * 1_000_000_000), "ns"),
        distance_step=dx_m,
    )

    patch = Patch(data=data, coords={"time": time, "distance": distance}, dims=("time", "distance"), attrs=attrs)
    return patch


def patch_to_alakoro(patch: Patch) -> Dict:
    """Converte Patch DASCore em dicionário Alakoro."""
    data = np.asarray(patch.data)
    coords = patch.coords

    time = np.asarray(coords.get_array("time"))
    distance = np.asarray(coords.get_array("distance"))

    dt_s = float(patch.attrs.time_step / np.timedelta64(1, "s")) if patch.attrs.time_step is not None else 1.0
    dx_m = float(patch.attrs.distance_step) if patch.attrs.distance_step is not None else 1.0

    units = patch.attrs.data_units
    if hasattr(units, "magnitude"):
        units = str(units)

    return {
        "data": data,
        "time": time,
        "distance": distance,
        "dt_s": dt_s,
        "dx_m": dx_m,
        "modality": patch.attrs.data_category or "unknown",
        "units": units or "unknown",
    }
