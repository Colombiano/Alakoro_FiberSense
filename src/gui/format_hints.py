"""
Mapeamento de extensões de arquivos DFOS conhecidos.
"""

from __future__ import annotations

from pathlib import Path


_EXTENSION_HINTS = {
    ".tdms": "TDMS (National Instruments)",
    ".segy": "SEG-Y",
    ".sgy": "SEG-Y",
    ".h5": "HDF5",
    ".hdf5": "HDF5",
    ".nc": "NetCDF",
    ".netcdf": "NetCDF",
    ".dasdae": "DASDAE",
    ".pkl": "Pickle",
    ".pickle": "Pickle",
    ".miniseed": "MiniSEED",
    ".mseed": "MiniSEED",
    ".exd": "Example Vendor (HDF5)",
}


def detect_format(path: Path) -> str:
    """Detecta o formato do arquivo a partir da extensão."""
    suffix = path.suffix.lower()
    return _EXTENSION_HINTS.get(suffix, suffix or "desconhecido")
