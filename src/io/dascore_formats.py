"""
Alakoro FiberSense — Integração com formatos de arquivo DASCore

Abstrai leitura e escrita de formatos suportados pelo DASCore,
retornando sempre estruturas Alakoro (AlakoroPatch / AlakoroSpool).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import dascore as dc
import numpy as np
from dascore import Patch
from dascore.core.spool import BaseSpool

from .alakoro_spool import AlakoroPatch, AlakoroSpool


def supported_formats() -> List[str]:
    """
    Retorna lista de formatos detectados no subpacote `dascore.io`.

    Inclui leitores nativos como tdms, segy, dashdf5, h5simple, wav, pickle,
    dasdae, febus, terra15, optodas, entre outros.
    """
    import pkgutil

    formats: List[str] = []
    for _, modname, _ in pkgutil.iter_modules(dc.io.__path__):
        # Módulos internos como 'core' e 'indexer' não são formatos
        if modname in {"core", "indexer"}:
            continue
        formats.append(modname)
    return sorted(formats)


def _patch_from_dascore(
    patch: Patch, well_id: Optional[str] = None, modality: Optional[str] = None
) -> AlakoroPatch:
    """Converte um Patch DASCore em AlakoroPatch preservando metadados."""
    modality = modality or (patch.attrs.data_category or "das")
    return AlakoroPatch(patch, well_id=well_id, modality=modality)


def _spool_from_dascore(
    spool: BaseSpool, well_id: Optional[str] = None, modality: Optional[str] = None
) -> AlakoroSpool:
    """Converte um Spool DASCore em AlakoroSpool preservando metadados."""
    patches = []
    for patch in spool:
        mod = modality or (patch.attrs.data_category or "das")
        patches.append(AlakoroPatch(patch, well_id=well_id, modality=mod))
    return AlakoroSpool(patches)


def read(
    path: Union[str, Path],
    modality: Optional[str] = None,
    well_id: Optional[str] = None,
    **kwargs: Any,
) -> Union[AlakoroPatch, AlakoroSpool]:
    """
    Lê um arquivo ou diretório suportado pelo DASCore.

    Args:
        path: caminho para arquivo ou diretório.
        modality: força a modalidade (das/dts/dss). Se None, usa `data_category`.
        well_id: identificador do poço.
        **kwargs: extras repassados para `dascore.spool`.

    Returns:
        AlakoroPatch se o arquivo contiver um único Patch,
        AlakoroSpool se contiver múltiplos Patches.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")

    spool = dc.spool(path, **kwargs)
    patches = list(spool)

    if len(patches) == 0:
        raise ValueError(f"No DAS data found in {path}")

    if len(patches) == 1:
        return _patch_from_dascore(patches[0], well_id=well_id, modality=modality)

    return _spool_from_dascore(spool, well_id=well_id, modality=modality)


def _to_dascore_spool(obj: Any) -> BaseSpool:
    """Converte AlakoroPatch, AlakoroSpool, Patch ou BaseSpool em Spool DASCore."""
    if isinstance(obj, AlakoroPatch):
        return dc.spool([obj.patch])
    if isinstance(obj, AlakoroSpool):
        return obj.to_dascore()
    if isinstance(obj, Patch):
        return dc.spool([obj])
    if isinstance(obj, BaseSpool):
        return obj
    raise TypeError(
        f"Cannot write object of type {type(obj)}. "
        "Expected AlakoroPatch, AlakoroSpool, dascore.Patch or dascore.BaseSpool."
    )


def write(
    obj: Union[AlakoroPatch, AlakoroSpool, Patch, Spool],
    path: Union[str, Path],
    file_format: Optional[str] = None,
    **kwargs: Any,
) -> Path:
    """
    Salva AlakoroPatch/AlakoroSpool em um formato suportado pelo DASCore.

    Args:
        obj: AlakoroPatch, AlakoroSpool, Patch ou Spool.
        path: caminho de destino.
        file_format: formato de saída (ex: 'dasdae', 'pickle').
                     Se None, tenta inferir da extensão.
        **kwargs: extras repassados para `dascore.write`.

    Returns:
        Path do arquivo escrito.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    spool = _to_dascore_spool(obj)

    if file_format is None:
        file_format = _infer_format_from_extension(path.suffix)
        if file_format is None:
            raise ValueError(
                f"Could not infer DASCore format from extension '{path.suffix}'. "
                f"Supported extensions: {list(_EXTENSION_MAP.keys())}"
            )

    # dc.write aceita Patch ou Spool; usamos o primeiro patch se só houver um
    patches = list(spool)
    to_write = spool if len(patches) > 1 else patches[0]

    dc.write(to_write, str(path), file_format=file_format, **kwargs)
    return path


# Mapeamento simples de extensões para formatos DASCore.
_EXTENSION_MAP: Dict[str, str] = {
    ".h5": "dasdae",
    ".hdf5": "dasdae",
    ".dasdae": "dasdae",
    ".pkl": "pickle",
    ".pickle": "pickle",
    ".wav": "wav",
    ".tdms": "tdms",
    ".segy": "segy",
    ".rsf": "rsf",
}


def _infer_format_from_extension(suffix: str) -> Optional[str]:
    """Infere formato DASCore a partir da extensão do arquivo."""
    return _EXTENSION_MAP.get(suffix.lower())


def patch_from_dascore(
    patch: Patch, well_id: Optional[str] = None, modality: Optional[str] = None
) -> AlakoroPatch:
    """Função pública de conveniência para converter Patch → AlakoroPatch."""
    return _patch_from_dascore(patch, well_id=well_id, modality=modality)


def spool_from_dascore(
    spool: BaseSpool, well_id: Optional[str] = None, modality: Optional[str] = None
) -> AlakoroSpool:
    """Função pública de conveniência para converter Spool → AlakoroSpool."""
    return _spool_from_dascore(spool, well_id=well_id, modality=modality)


__all__ = [
    "supported_formats",
    "read",
    "write",
    "patch_from_dascore",
    "spool_from_dascore",
]
