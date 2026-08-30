"""
Alakoro FiberSense — Integração com formatos de arquivo Xdas

Abstrai leitura e escrita de formatos suportados pelo Xdas,
retornando sempre estruturas Alakoro (AlakoroPatch / AlakoroSpool).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import xdas

from .alakoro_spool import AlakoroPatch, AlakoroSpool
from .xdas_adapter import (
    alakoro_to_xdas,
    datacollection_to_spool,
    spool_to_datacollection,
    xdas_to_alakoro,
)


def supported_xdas_formats() -> List[str]:
    """
    Retorna lista de engines/formatos detectados no subpacote `xdas.io`.
    """
    import pkgutil

    formats: List[str] = []
    for _, modname, _ in pkgutil.iter_modules(xdas.io.__path__):
        if modname in {"core", "autoengine"}:
            continue
        formats.append(modname)
    return sorted(formats)


def _infer_engine_from_extension(suffix: str) -> Optional[str]:
    """Infere engine Xdas a partir da extensão do arquivo."""
    return _EXTENSION_MAP.get(suffix.lower())


_EXTENSION_MAP: Dict[str, str] = {
    ".nc": "netcdf",
    ".netcdf": "netcdf",
    ".xdas": "xdas",
    ".tdms": "tdms",
    ".miniseed": "miniseed",
    ".mseed": "miniseed",
}


def _to_xdas_collection(obj: Any) -> Union[xdas.DataArray, xdas.DataCollection]:
    """Converte AlakoroPatch/AlakoroSpool em DataArray ou DataCollection Xdas."""
    if isinstance(obj, AlakoroPatch):
        return alakoro_to_xdas(obj)
    if isinstance(obj, AlakoroSpool):
        return spool_to_datacollection(obj)
    if isinstance(obj, xdas.DataArray):
        return obj
    if isinstance(obj, xdas.DataCollection):
        return obj
    raise TypeError(
        f"Cannot write object of type {type(obj)}. "
        "Expected AlakoroPatch, AlakoroSpool, xdas.DataArray or xdas.DataCollection."
    )


def write_xdas(
    obj: Union[AlakoroPatch, AlakoroSpool, xdas.DataArray, xdas.DataCollection],
    path: Union[str, Path],
    engine: Optional[str] = None,
    **kwargs: Any,
) -> Path:
    """
    Salva AlakoroPatch/AlakoroSpool em um formato suportado pelo Xdas.

    Args:
        obj: AlakoroPatch, AlakoroSpool, xdas.DataArray ou xdas.DataCollection.
        path: caminho de destino.
        engine: engine de escrita (ex: 'netcdf'). Se None, tenta inferir da extensão.
        **kwargs: extras repassados para `xdas.DataArray.to_netcdf`.

    Returns:
        Path do arquivo escrito.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if engine is None:
        engine = _infer_engine_from_extension(path.suffix)
        if engine is None:
            raise ValueError(
                f"Could not infer Xdas engine from extension '{path.suffix}'. "
                f"Supported extensions: {list(_EXTENSION_MAP.keys())}"
            )

    xdas_obj = _to_xdas_collection(obj)

    if engine in {"netcdf", "nc"}:
        # Limpar attrs para garantir compatibilidade com NetCDF/h5py
        clean_attrs = {}
        for key, value in xdas_obj.attrs.items():
            if isinstance(value, str):
                clean_attrs[key] = value
            elif isinstance(value, (int, float, np.integer, np.floating)):
                clean_attrs[key] = value
            elif isinstance(value, np.ndarray):
                clean_attrs[key] = value
            elif value is None:
                continue
            else:
                clean_attrs[key] = str(value)
        xdas_obj.attrs = clean_attrs

        if isinstance(xdas_obj, xdas.DataCollection):
            # DataCollection não tem to_netcdf direto; salvamos o primeiro item
            # ou concatenamos. Aqui optamos por salvar o primeiro item e avisar.
            raise NotImplementedError(
                "Writing AlakoroSpool/DataCollection to NetCDF is not directly "
                "supported. Convert to a single DataArray or save each patch separately."
            )
        xdas_obj.to_netcdf(str(path), **kwargs)
    else:
        raise NotImplementedError(
            f"Xdas engine '{engine}' write is not yet supported by Alakoro. "
            "Currently only 'netcdf' is supported."
        )

    return path


def read_xdas(
    path: Union[str, Path, List[Union[str, Path]]],
    modality: Optional[str] = None,
    well_id: Optional[str] = None,
    lazy: bool = False,
    **kwargs: Any,
) -> Union[AlakoroPatch, AlakoroSpool]:
    """
    Lê arquivo(s) Xdas e converte para AlakoroPatch ou AlakoroSpool.

    Args:
        path: caminho único ou lista de caminhos.
        modality: força a modalidade. Se None, usa attr do arquivo.
        well_id: identificador do poço.
        lazy: se True, tenta carregar dados de forma lazy via Dask (quando suportado).
        **kwargs: extras repassados para `xdas.open_dataarray` / `open_mfdataarray`.

    Returns:
        AlakoroPatch para arquivo único, AlakoroSpool para múltiplos arquivos.
    """
    if isinstance(path, (str, Path)):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        da = xdas.open(str(path), **kwargs)
        if lazy and hasattr(da, "load"):
            # lazy=True mantém carregamento lazy; processadores C++20 precisam de .load()
            pass
        return xdas_to_alakoro(da, well_id=well_id, modality=modality)

    # Múltiplos arquivos
    paths = [str(p) for p in path]
    for p in paths:
        if not Path(p).exists():
            raise FileNotFoundError(f"Path not found: {p}")

    da = xdas.open_mfdataarray(paths, **kwargs)
    if lazy and hasattr(da, "load"):
        pass
    return xdas_to_alakoro(da, well_id=well_id, modality=modality)


__all__ = [
    "supported_xdas_formats",
    "read_xdas",
    "write_xdas",
]
