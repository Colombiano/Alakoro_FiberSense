"""
Alakoro FiberSense — Adapter DASDAE

Integra Alakoro com o ecossistema DASDAE (DASCore, Xdas).
Fornece conversores bidirecionais entre estruturas Alakoro e
Patch/Spool do DASCore, assim como para Xdas (quando instalado).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import numpy as np

import dascore as dc
from dascore import Patch
from dascore.core.attrs import PatchAttrs

from .alakoro_spool import AlakoroPatch, AlakoroSpool

if TYPE_CHECKING:
    import xdas  # type: ignore


class DASDAEAdapter:
    """
    Adapter entre estruturas Alakoro e o ecossistema DASDAE.

    Responsável por converter:
      - array Alakoro <-> DASCore Patch
      - AlakoroPatch <-> DASCore Patch
      - AlakoroSpool <-> DASCore Spool
      - (opcional) AlakoroSpool <-> Xdas DataArray
    """

    @staticmethod
    def array_to_patch(data: np.ndarray,
                       start_time: str = "2026-01-01T00:00:00",
                       dt_s: float = 2.0,
                       dx_m: float = 1.0,
                       modality: str = "DAS",
                       units: Optional[str] = None) -> Patch:
        """Converte array NumPy 2D (time, distance) em DASCore Patch."""
        n_t, n_z = data.shape
        time = (np.arange(n_t) * dt_s * 1_000_000_000).astype("timedelta64[ns]")
        distance = np.arange(n_z) * dx_m

        if units is None:
            units = "1/s" if modality.upper() == "DAS" else "degC"

        attrs = PatchAttrs(
            data_category=modality.lower(),
            data_units=units,
            time_step=np.timedelta64(int(dt_s * 1_000_000_000), "ns"),
            distance_step=dx_m,
        )

        return Patch(
            data=data,
            coords={"time": time, "distance": distance},
            dims=("time", "distance"),
            attrs=attrs,
        )

    @staticmethod
    def patch_to_array(patch: Patch) -> dict:
        """Converte DASCore Patch em dicionário Alakoro."""
        data = np.asarray(patch.data)
        coords = patch.coords
        time = np.asarray(coords.get_array("time"))
        distance = np.asarray(coords.get_array("distance"))

        dt_s = float(patch.attrs.time_step / np.timedelta64(1, "s")) \
            if patch.attrs.time_step is not None else 1.0
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

    @staticmethod
    def to_dascore(obj, well_id: Optional[str] = None) -> Patch:
        """Converte AlakoroPatch ou array para DASCore Patch."""
        if isinstance(obj, AlakoroPatch):
            return obj.patch
        if isinstance(obj, np.ndarray):
            return DASDAEAdapter.array_to_patch(obj)
        raise TypeError(f"Cannot convert {type(obj)} to DASCore Patch")

    @staticmethod
    def from_dascore(patch: Patch, well_id: Optional[str] = None,
                     modality: Optional[str] = None) -> AlakoroPatch:
        """Converte DASCore Patch para AlakoroPatch."""
        modality = modality or (patch.attrs.data_category or "das")
        return AlakoroPatch(patch, well_id=well_id, modality=modality)

    @staticmethod
    def spool_to_dascore(spool: AlakoroSpool):
        """Converte AlakoroSpool para Spool DASCore."""
        return spool.to_dascore()

    @staticmethod
    def spool_from_dascore(spool, well_id: Optional[str] = None,
                           modality: str = "das") -> AlakoroSpool:
        """Converte Spool DASCore para AlakoroSpool."""
        return AlakoroSpool.from_dascore(spool, well_id=well_id, modality=modality)

    # ─── Xdas (opcional) ───

    @staticmethod
    def to_xdas(patch: Patch):
        """Converte DASCore Patch para Xdas DataArray, se disponível."""
        try:
            import xdas
        except ImportError as exc:
            raise ImportError("xdas is not installed. Run: pip install xdas") from exc

        data = np.asarray(patch.data)
        time = np.asarray(patch.coords.get_array("time"))
        distance = np.asarray(patch.coords.get_array("distance"))

        return xdas.DataArray(
            data,
            coords={"time": time, "distance": distance},
            dims=("time", "distance"),
            attrs=dict(patch.attrs),
        )

    @staticmethod
    def from_xdas(da) -> Patch:
        """Converte Xdas DataArray para DASCore Patch."""
        try:
            import xdas
        except ImportError as exc:
            raise ImportError("xdas is not installed. Run: pip install xdas") from exc

        data = np.asarray(da.values)
        time = np.asarray(da.coords["time"].values)
        distance = np.asarray(da.coords["distance"].values)

        attrs = PatchAttrs(
            data_category=getattr(da, "attrs", {}).get("data_category", "das"),
            data_units=getattr(da, "attrs", {}).get("data_units", "unknown"),
        )

        return Patch(
            data=data,
            coords={"time": time, "distance": distance},
            dims=("time", "distance"),
            attrs=attrs,
        )


# ─── Funções de conveniência ───

def alakoro_to_dascore(obj, well_id: Optional[str] = None) -> Patch:
    """Alias para DASDAEAdapter.to_dascore."""
    return DASDAEAdapter.to_dascore(obj, well_id=well_id)


def dascore_to_alakoro(patch: Patch, well_id: Optional[str] = None,
                       modality: Optional[str] = None) -> AlakoroPatch:
    """Alias para DASDAEAdapter.from_dascore."""
    return DASDAEAdapter.from_dascore(patch, well_id=well_id, modality=modality)


def alakoro_to_xdas(patch: Patch):
    """Alias para DASDAEAdapter.to_xdas."""
    return DASDAEAdapter.to_xdas(patch)


def xdas_to_alakoro(da):
    """Alias para DASDAEAdapter.from_xdas."""
    return DASDAEAdapter.from_xdas(da)
