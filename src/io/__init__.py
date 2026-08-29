"""Módulo de I/O / IO Module."""

from .alakoro_spool import AlakoroPatch, AlakoroSpool
from .dascore import alakoro_to_patch, patch_to_alakoro
from .dasdae import (
    DASDAEAdapter,
    alakoro_to_dascore,
    dascore_to_alakoro,
    alakoro_to_xdas,
    xdas_to_alakoro,
)
from .escape_hatches import (
    to_numpy,
    from_numpy,
    to_dataframe,
    from_dataframe,
    to_xarray,
    from_xarray,
    to_obspy,
    from_obspy,
)
from .prodml import read as read_prodml, write as write_prodml
from .witsml import read_log as read_witsml_log, write_log as write_witsml_log
from .streaming import StreamingSpool, DirectoryWatcher

__all__ = [
    "alakoro_to_patch",
    "patch_to_alakoro",
    "AlakoroPatch",
    "AlakoroSpool",
    "DASDAEAdapter",
    "alakoro_to_dascore",
    "dascore_to_alakoro",
    "alakoro_to_xdas",
    "xdas_to_alakoro",
    "to_numpy",
    "from_numpy",
    "to_dataframe",
    "from_dataframe",
    "to_xarray",
    "from_xarray",
    "to_obspy",
    "from_obspy",
    "read_prodml",
    "write_prodml",
    "read_witsml_log",
    "write_witsml_log",
    "StreamingSpool",
    "DirectoryWatcher",
]
