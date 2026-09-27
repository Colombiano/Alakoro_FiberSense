"""
Alakoro FiberSense — Escape Hatches

Conversores entre AlakoroPatch e estruturas populares do ecossistema
Python científico: NumPy, pandas, xarray e ObsPy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import numpy as np

from dascore import Patch

from .alakoro_spool import AlakoroPatch

if TYPE_CHECKING:
    import pandas as pd
    import xarray as xr
    from obspy.core import Stream


def to_numpy(patch: AlakoroPatch) -> np.ndarray:
    """Retorna array NumPy 2D (time, distance)."""
    return patch.data


def from_numpy(data: np.ndarray,
               time: Optional[np.ndarray] = None,
               distance: Optional[np.ndarray] = None,
               modality: str = "das") -> AlakoroPatch:
    """Cria AlakoroPatch a partir de arrays NumPy."""
    from .dasdae import DASDAEAdapter
    dc_patch = DASDAEAdapter.array_to_patch(data, modality=modality)

    if time is not None:
        dc_patch = dc_patch.update_coords(time=time)
    if distance is not None:
        dc_patch = dc_patch.update_coords(distance=distance)

    return AlakoroPatch(dc_patch, modality=modality)


def to_dataframe(patch: AlakoroPatch) -> "pd.DataFrame":
    """Converte AlakoroPatch para pandas DataFrame."""
    import pandas as pd
    time = np.asarray(patch.coords.get_array("time"))
    distance = np.asarray(patch.coords.get_array("distance"))
    return pd.DataFrame(
        patch.data,
        index=pd.Index(time, name="time"),
        columns=pd.Index(distance, name="distance"),
    )


def from_dataframe(df: "pd.DataFrame", modality: str = "das") -> AlakoroPatch:
    """Cria AlakoroPatch a partir de pandas DataFrame."""
    return from_numpy(
        df.values,
        time=df.index.values,
        distance=df.columns.values,
        modality=modality,
    )


def to_xarray(patch: AlakoroPatch) -> "xr.DataArray":
    """Converte AlakoroPatch para xarray DataArray."""
    import xarray as xr
    time = np.asarray(patch.coords.get_array("time"))
    distance = np.asarray(patch.coords.get_array("distance"))
    return xr.DataArray(
        patch.data,
        dims=("time", "distance"),
        coords={"time": time, "distance": distance},
        attrs=dict(patch.attrs),
    )


def from_xarray(da: "xr.DataArray", modality: str = "das") -> AlakoroPatch:
    """Cria AlakoroPatch a partir de xarray DataArray."""
    return from_numpy(
        da.values,
        time=da.coords["time"].values,
        distance=da.coords["distance"].values,
        modality=modality,
    )


def to_obspy(patch: AlakoroPatch) -> "Stream":
    """Converte AlakoroPatch para ObsPy Stream (uma trace por canal)."""
    return patch.to_obspy()


def from_obspy(stream: "Stream", distance_step: float = 1.0) -> AlakoroPatch:
    """Cria AlakoroPatch a partir de ObsPy Stream."""
    from obspy.core import Stream
    from dascore.core.attrs import PatchAttrs

    if len(stream) == 0:
        raise ValueError("Stream is empty")

    n_t = len(stream[0].data)
    n_c = len(stream)
    data = np.zeros((n_t, n_c), dtype=np.float64)

    for i, tr in enumerate(stream):
        data[:, i] = tr.data

    start_time = stream[0].stats.starttime.isoformat()
    dt_s = stream[0].stats.delta

    patch = Patch(
        data=data,
        coords={
            "time": (np.arange(n_t) * dt_s * 1e9).astype("timedelta64[ns]"),
            "distance": np.arange(n_c) * distance_step,
        },
        dims=("time", "distance"),
        attrs=PatchAttrs(data_category="das", data_units="strain_rate"),
    )
    return AlakoroPatch(patch, modality="das")
