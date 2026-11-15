"""
Alakoro FiberSense — Alinhamento Multimodal LF-DAS/DTS
Multimodal LF-DAS/DTS Alignment

Alinha grades temporais e espaciais distintas antes de fusões DAS+DTS
(ex.: ``np.stack`` em ``alakoro.ml.api.predict_flow``). A regra geral é
interpolar ambas as modalidades para a grade mais grosseira de cada eixo,
restrita à janela de sobreposição — evita inventar amostras (upsampling) e
preserva unidades e metadados originais.

Aligns distinct temporal/spatial grids before DAS+DTS fusion (e.g. the
``np.stack`` in ``alakoro.ml.api.predict_flow``). Both modalities are
resampled onto the coarser grid of each axis, restricted to the overlap
window — this avoids inventing samples (upsampling) and preserves the
original units and metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional, Tuple, Union

import numpy as np

try:  # xarray é opcional / xarray is an optional dependency
    import xarray as xr
except ImportError:  # pragma: no cover
    xr = None

__all__ = [
    "AlignedData",
    "align_lfdas_dts",
    "regrid_to_common",
]

# Chaves aceitas para arrays em dicionários / Accepted dict array keys
_DATA_KEYS = ("data", "temperature", "values")
_TIME_KEYS = ("time", "time_s", "t")
_DEPTH_KEYS = ("depth", "depth_m", "distance", "z")


@dataclass
class AlignedData:
    """Resultado do alinhamento multimodal / Multimodal alignment result.

    Attributes
    ----------
    data : dict[str, np.ndarray]
        Arrays 2D ``(time, depth)`` de cada modalidade, já na grade comum.
        / 2D arrays on the common grid.
    time : np.ndarray
        Grade temporal comum (segundos ou unidade original) / common time axis.
    depth : np.ndarray
        Grade espacial comum / common depth axis.
    units : dict[str, str]
        Unidades de cada modalidade, preservadas da entrada / preserved units.
    attrs : dict[str, dict]
        Metadados originais de cada entrada / original metadata per input.
    """

    data: Dict[str, np.ndarray]
    time: np.ndarray
    depth: np.ndarray
    units: Dict[str, str] = field(default_factory=dict)
    attrs: Dict[str, dict] = field(default_factory=dict)

    @property
    def shape(self) -> Tuple[int, int]:
        """Shape comum (n_time, n_depth) / common (n_time, n_depth) shape."""
        first = next(iter(self.data.values()))
        return first.shape


def _first_key(mapping: Mapping, keys) -> Optional[str]:
    for key in keys:
        if key in mapping:
            return key
    return None


def _extract_grid(obj, name: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, str, dict]:
    """Extrai (data, time, depth, units, attrs) de um objeto suportado.

    Formatos aceitos / accepted formats:
      - dict com 'data'|'temperature', 'time'|'time_s', 'depth'|'distance'
        (unidades via 'units'; metadados via 'metadata'|'attrs');
      - xarray.Dataset/DataArray com dims (time, depth|distance);
      - np.ndarray 2D (grade inteira implícita / implicit integer grid).
    """
    if isinstance(obj, Mapping):
        data_key = _first_key(obj, _DATA_KEYS)
        time_key = _first_key(obj, _TIME_KEYS)
        depth_key = _first_key(obj, _DEPTH_KEYS)
        if data_key is None or time_key is None or depth_key is None:
            raise ValueError(
                f"{name}: dict must contain data ({_DATA_KEYS}), "
                f"time ({_TIME_KEYS}) and depth ({_DEPTH_KEYS})"
            )
        data = np.asarray(obj[data_key], dtype=np.float64)
        time = np.asarray(obj[time_key], dtype=np.float64)
        depth = np.asarray(obj[depth_key], dtype=np.float64)
        units = str(obj.get("units", ""))
        attrs = dict(obj.get("metadata") or obj.get("attrs") or {})
        return data, time, depth, units, attrs

    if xr is not None and isinstance(obj, (xr.Dataset, xr.DataArray)):
        da = obj["data"] if isinstance(obj, xr.Dataset) else obj
        dims = set(da.dims)
        if len(dims) != 2:
            raise ValueError(
                f"{name}: xarray object must be 2D with (time, depth|distance) "
                f"dims, got {tuple(da.dims)}"
            )
        t_dim = "time" if "time" in dims else next(iter(dims))
        d_dim = "depth" if "depth" in dims else ("distance" if "distance" in dims else None)
        if d_dim is None:
            raise ValueError(
                f"{name}: xarray object needs a 'depth' or 'distance' dim, "
                f"got {tuple(da.dims)}"
            )
        time = np.asarray(da[t_dim].values, dtype=np.float64)
        depth = np.asarray(da[d_dim].values, dtype=np.float64)
        units = str(da.attrs.get("units", ""))
        attrs = dict(da.attrs)
        return np.asarray(da.values, dtype=np.float64), time, depth, units, attrs

    arr = np.asarray(obj, dtype=np.float64)
    if arr.ndim == 2:
        # Sem coordenadas: grade inteira implícita / implicit integer grid.
        return arr, np.arange(arr.shape[0], dtype=np.float64), \
            np.arange(arr.shape[1], dtype=np.float64), "", {}

    raise ValueError(
        f"{name}: unsupported type {type(obj).__name__}; expected dict, "
        "xarray.Dataset/DataArray or 2D np.ndarray"
    )


def _validate_grid(data: np.ndarray, time: np.ndarray, depth: np.ndarray, name: str):
    """Valida dimensionalidade e compatibilidade de shapes / validates shapes."""
    if data.ndim != 2:
        raise ValueError(f"{name}: data must be 2D (time, depth), got {data.ndim}D")
    if time.ndim != 1 or depth.ndim != 1:
        raise ValueError(f"{name}: time and depth must be 1D arrays")
    if data.shape != (time.size, depth.size):
        raise ValueError(
            f"{name}: data shape {data.shape} does not match "
            f"(len(time)={time.size}, len(depth)={depth.size})"
        )


def _interp_axis(data: np.ndarray, src: np.ndarray, dst: np.ndarray, axis: int) -> np.ndarray:
    """Interpolação linear de um eixo / linear interpolation along one axis.

    Usa np.interp: pontos fora do alcance recebem o valor da borda
    (sem extrapolação). / Uses np.interp: out-of-range points are clamped
    to the edge value (no extrapolation).
    """
    if np.array_equal(src, dst):
        return data
    moved = np.moveaxis(data, axis, 0)
    out = np.empty((dst.size,) + moved.shape[1:], dtype=np.float64)
    flat_src = moved.reshape(moved.shape[0], -1)
    flat_out = out.reshape(out.shape[0], -1)
    for i in range(flat_src.shape[1]):
        flat_out[:, i] = np.interp(dst, src, flat_src[:, i])
    return np.moveaxis(out, 0, axis)


def _common_axis(a: np.ndarray, b: np.ndarray, axis_name: str) -> np.ndarray:
    """Grade comum = grelha mais grosseira contida na sobreposição.

    Common grid = coarser source grid restricted to the overlap window.
    Levanta ValueError quando a sobreposição é vazia ou tem < 2 pontos
    (incompatível de forma irrecuperável) / raises ValueError when the
    overlap is empty or has fewer than 2 points (irrecoverable).
    """
    lo = max(float(a.min()), float(b.min()))
    hi = min(float(a.max()), float(b.max()))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi < lo:
        raise ValueError(
            f"no overlap on {axis_name} axis "
            f"([{a.min()}, {a.max()}] vs [{b.min()}, {b.max()}])"
        )
    spacing_a = float(np.median(np.diff(a))) if a.size > 1 else np.inf
    spacing_b = float(np.median(np.diff(b))) if b.size > 1 else np.inf
    src = a if spacing_a >= spacing_b else b
    grid = src[(src >= lo) & (src <= hi)]
    if grid.size < 2:
        raise ValueError(
            f"{axis_name} axes are irrecoverably incompatible: fewer than 2 "
            f"grid points in the overlap [{lo}, {hi}]"
        )
    return grid


def align_lfdas_dts(
    lfdas: Union[dict, "xr.Dataset", "xr.DataArray", np.ndarray],
    dts: Union[dict, "xr.Dataset", "xr.DataArray", np.ndarray],
    *,
    method: str = "interpolate",
) -> AlignedData:
    """Alinha LF-DAS e DTS em grade temporal/espacial comum.

    Align LF-DAS and DTS onto common temporal/spatial grids.

    Ambas as modalidades são interpoladas (linear) para a grade mais grosseira
    de cada eixo, restrita à sobreposição. Se as grades já coincidem, a
    operação é um no-op e os dados originais são preservados. Unidades e
    metadados de cada entrada são propagados para o resultado.

    Both modalities are linearly interpolated onto the coarser grid of each
    axis, restricted to the overlap window. If the grids already match this
    is a no-op and the original data is preserved. Units and metadata are
    propagated to the result.

    Parameters
    ----------
    lfdas : dict | xarray.Dataset | xarray.DataArray | np.ndarray
        Dados LF-DAS (ex.: saída de LFDASProcessor). Dicts usam as chaves
        'data'/'temperature', 'time'/'time_s' e 'depth'/'distance'.
        / LF-DAS data (e.g. LFDASProcessor output). Dicts use the keys
        'data'/'temperature', 'time'/'time_s' and 'depth'/'distance'.
    dts : dict | xarray.Dataset | xarray.DataArray | np.ndarray
        Dados DTS na mesma convenção / DTS data in the same convention.
    method : str
        "interpolate" (único suportado / only supported): interpolação linear.

    Returns
    -------
    AlignedData
        data={"lfdas", "dts"} na grade comum, com time/depth comuns e
        unidades/metadados preservados / both modalities on the common grid
        with shared time/depth axes and preserved units/metadata.

    Raises
    ------
    ValueError
        Se as dimensionalidades divergem de (time, depth), se shapes e eixos
        não correspondem, ou se as grades não se sobrepõem de forma
        recuperável / if dimensions are not (time, depth), shapes and axes
        mismatch, or grids do not overlap recoverably.

    Exemplo / Example
    -----------------
    >>> import numpy as np
    >>> lfdas = {"data": np.ones((50, 40)), "time": np.arange(50) * 2.0,
    ...          "depth": np.arange(40) * 1.0, "units": "degC"}
    >>> dts = {"data": np.ones((25, 20)) * 2, "time": np.arange(25) * 4.0,
    ...        "depth": np.arange(20) * 2.0, "units": "degC"}
    >>> aligned = align_lfdas_dts(lfdas, dts)
    >>> aligned.shape          # grade mais grosseira: 25 tempos, 20 profundidades
    (25, 20)
    >>> aligned.units["lfdas"]
    'degC'
    """
    if method != "interpolate":
        raise ValueError(f"unsupported alignment method {method!r}; use 'interpolate'")

    lf_data, lf_time, lf_depth, lf_units, lf_attrs = _extract_grid(lfdas, "lfdas")
    dts_data, dts_time, dts_depth, dts_units, dts_attrs = _extract_grid(dts, "dts")
    _validate_grid(lf_data, lf_time, lf_depth, "lfdas")
    _validate_grid(dts_data, dts_time, dts_depth, "dts")

    common_time = _common_axis(lf_time, dts_time, "time")
    common_depth = _common_axis(lf_depth, dts_depth, "depth")

    aligned: Dict[str, np.ndarray] = {}
    for name, data, t_src, d_src in (
        ("lfdas", lf_data, lf_time, lf_depth),
        ("dts", dts_data, dts_time, dts_depth),
    ):
        out = _interp_axis(data, t_src, common_time, axis=0)
        out = _interp_axis(out, d_src, common_depth, axis=1)
        aligned[name] = out

    return AlignedData(
        data=aligned,
        time=common_time,
        depth=common_depth,
        units={"lfdas": lf_units, "dts": dts_units},
        attrs={"lfdas": lf_attrs, "dts": dts_attrs},
    )


def regrid_to_common(
    arrays: Dict[str, Tuple[np.ndarray, np.ndarray]],
    eixo_comum: np.ndarray,
    *,
    method: str = "interpolate",
) -> Dict[str, np.ndarray]:
    """Regride arrays 1D para um eixo comum / regrid 1D arrays to a common axis.

    Parameters
    ----------
    arrays : dict[str, tuple[np.ndarray, np.ndarray]]
        Mapeia nome → (valores, coordenadas) 1D / maps name → (values, coords).
    eixo_comum : np.ndarray
        Coordenadas alvo 1D / target 1D coordinates.
    method : str
        "interpolate" (único suportado / only supported): interpolação linear.

    Returns
    -------
    dict[str, np.ndarray]
        Mapeia nome → valores regridados em ``eixo_comum`` / name → values
        on ``eixo_comum``.

    Raises
    ------
    ValueError
        Se algum par não for 1D ou tiver tamanhos incompatíveis / if any pair
        is not 1D or sizes mismatch.

    Exemplo / Example
    -----------------
    >>> import numpy as np
    >>> a = (np.array([0.0, 1.0, 2.0]), np.array([0.0, 1.0, 2.0]))
    >>> b = (np.array([10.0, 20.0]), np.array([0.0, 2.0]))
    >>> out = regrid_to_common({"a": a, "b": b}, np.array([0.0, 1.0, 2.0]))
    >>> out["b"]
    array([10., 15., 20.])
    """
    if method != "interpolate":
        raise ValueError(f"unsupported alignment method {method!r}; use 'interpolate'")
    target = np.asarray(eixo_comum, dtype=np.float64)
    if target.ndim != 1:
        raise ValueError("eixo_comum must be a 1D array")

    out: Dict[str, np.ndarray] = {}
    for name, pair in arrays.items():
        values, coords = pair
        values = np.asarray(values, dtype=np.float64)
        coords = np.asarray(coords, dtype=np.float64)
        if values.ndim != 1 or coords.ndim != 1:
            raise ValueError(f"{name}: values and coords must be 1D arrays")
        if values.shape != coords.shape:
            raise ValueError(
                f"{name}: values and coords shapes differ "
                f"({values.shape} vs {coords.shape})"
            )
        out[name] = np.interp(target, coords, values)
    return out
