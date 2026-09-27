"""
Alakoro FiberSense — Integração direta com Xdas

Conversores bidirecionais entre AlakoroPatch/AlakoroSpool e
xdas.DataArray/xdas.DataCollection, sem depender do DASCore Patch.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import xdas

from .alakoro_spool import AlakoroPatch, AlakoroSpool


def _coord_step(coord) -> float:
    """Calcula o passo médio de uma coordenada Xdas (em segundos para tempo)."""
    values = np.asarray(coord)
    if len(values) < 2:
        return 1.0
    step = np.mean(np.diff(values))
    if np.issubdtype(values.dtype, np.timedelta64):
        return float(step / np.timedelta64(1, "s"))
    return float(step)


def _coord_first(coord):
    """Retorna o primeiro valor de uma coordenada Xdas."""
    values = np.asarray(coord)
    return values[0] if len(values) > 0 else 0


def array_to_dataarray(
    data: np.ndarray,
    dt_s: float = 1.0,
    dx_m: float = 1.0,
    modality: str = "das",
    well_id: Optional[str] = None,
    attrs: Optional[Dict[str, Any]] = None,
) -> xdas.DataArray:
    """
    Cria xdas.DataArray a partir de array NumPy 2D (time, distance).

    Args:
        data: array 2D com shape (n_times, n_channels).
        dt_s: passo temporal em segundos.
        dx_m: passo espacial em metros.
        modality: modalidade dos dados (das, dts, dss).
        well_id: identificador do poço.
        attrs: atributos extras.
    """
    n_t, n_z = data.shape
    time_step = np.timedelta64(int(dt_s * 1_000_000_000), "ns")
    time_start = np.timedelta64(0, "ns")
    time_coord = xdas.SampledCoordinate(
        {"tie_values": [time_start], "tie_lengths": [n_t], "sampling_interval": time_step}
    )
    distance_coord = xdas.SampledCoordinate(
        {"tie_values": [0.0], "tie_lengths": [n_z], "sampling_interval": dx_m}
    )

    final_attrs = dict(attrs) if attrs else {}
    final_attrs.setdefault("data_category", modality.lower())
    final_attrs.setdefault("data_units", "1/s" if modality.lower() == "das" else "degC")
    if well_id is not None:
        final_attrs.setdefault("well_id", well_id)

    return xdas.DataArray(
        data,
        coords={"time": time_coord, "distance": distance_coord},
        dims=("time", "distance"),
        attrs=final_attrs,
    )


def dataarray_to_array(da: xdas.DataArray) -> Dict[str, Any]:
    """Converte xdas.DataArray em dicionário Alakoro."""
    data = np.asarray(da.values)
    time = np.asarray(da.coords["time"])
    distance = np.asarray(da.coords["distance"])

    dt_s = _coord_step(da.coords["time"])
    dx_m = _coord_step(da.coords["distance"])

    modality = da.attrs.get("data_category", "unknown")
    units = da.attrs.get("data_units", "unknown")
    if hasattr(units, "magnitude"):
        units = str(units)

    return {
        "data": data,
        "time": time,
        "distance": distance,
        "dt_s": dt_s,
        "dx_m": dx_m,
        "modality": modality,
        "units": units,
        "well_id": da.attrs.get("well_id"),
    }


def alakoro_to_xdas(patch: AlakoroPatch) -> xdas.DataArray:
    """Converte AlakoroPatch em xdas.DataArray preservando metadados."""
    data = patch.data
    n_t, n_z = data.shape

    time_first = patch.coords.get_array("time")[0]
    time_step = _coord_step(patch.coords.get_array("time"))
    distance_first = float(patch.coords.get_array("distance")[0])
    distance_step = _coord_step(patch.coords.get_array("distance"))

    time_coord = xdas.SampledCoordinate({
        "tie_values": [time_first],
        "tie_lengths": [n_t],
        "sampling_interval": np.timedelta64(int(time_step * 1_000_000_000), "ns"),
    })
    distance_coord = xdas.SampledCoordinate({
        "tie_values": [distance_first],
        "tie_lengths": [n_z],
        "sampling_interval": distance_step,
    })

    attrs = dict(patch.attrs)
    attrs["well_id"] = patch.well_id
    attrs["data_category"] = patch.modality

    return xdas.DataArray(
        data,
        coords={"time": time_coord, "distance": distance_coord},
        dims=("time", "distance"),
        attrs=attrs,
    )


def xdas_to_alakoro(
    da: xdas.DataArray,
    well_id: Optional[str] = None,
    modality: Optional[str] = None,
) -> AlakoroPatch:
    """Converte xdas.DataArray em AlakoroPatch."""
    from dascore import Patch
    from dascore.core.attrs import PatchAttrs

    data = np.asarray(da.values)
    time = np.asarray(da.coords["time"])
    distance = np.asarray(da.coords["distance"])

    dt_s = _coord_step(da.coords["time"])
    dx_m = _coord_step(da.coords["distance"])

    modality = modality or da.attrs.get("data_category", "das")
    well_id = well_id or da.attrs.get("well_id")
    units = da.attrs.get("data_units", "1/s")
    if hasattr(units, "magnitude"):
        units = str(units)

    patch = Patch(
        data=data,
        coords={"time": time, "distance": distance},
        dims=("time", "distance"),
        attrs=PatchAttrs(
            data_category=modality.lower(),
            data_units=units,
            time_step=np.timedelta64(int(dt_s * 1_000_000_000), "ns"),
            distance_step=dx_m,
        ),
    )
    return AlakoroPatch(patch, well_id=well_id, modality=modality)


def spool_to_datacollection(spool: AlakoroSpool) -> xdas.DataCollection:
    """Converte AlakoroSpool em xdas.DataCollection."""
    items = {}
    for i, patch in enumerate(spool):
        key = f"{patch.well_id or 'patch'}_{i}_{patch.modality}"
        items[key] = alakoro_to_xdas(patch)
    return xdas.DataCollection(items)


def datacollection_to_spool(
    collection: xdas.DataCollection,
    well_id: Optional[str] = None,
    modality: Optional[str] = None,
) -> AlakoroSpool:
    """Converte xdas.DataCollection em AlakoroSpool."""
    patches = []
    for key, da in collection.items():
        wid = well_id or da.attrs.get("well_id") or key
        patches.append(xdas_to_alakoro(da, well_id=wid, modality=modality))
    return AlakoroSpool(patches)


__all__ = [
    "array_to_dataarray",
    "dataarray_to_array",
    "alakoro_to_xdas",
    "xdas_to_alakoro",
    "spool_to_datacollection",
    "datacollection_to_spool",
]
