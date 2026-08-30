"""Módulo de I/O / IO Module."""

from .alakoro_spool import AlakoroPatch, AlakoroSpool
from .dascore import alakoro_to_patch, patch_to_alakoro
from .dascore_formats import (
    read as read_dascore,
    write as write_dascore,
    supported_formats as supported_dascore_formats,
    patch_from_dascore,
    spool_from_dascore,
)
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
from .xdas_adapter import (
    alakoro_to_xdas,
    xdas_to_alakoro,
    spool_to_datacollection,
    datacollection_to_spool,
    array_to_dataarray,
    dataarray_to_array,
)
from .xdas_formats import read_xdas, write_xdas, supported_xdas_formats

__all__ = [
    "alakoro_to_patch",
    "patch_to_alakoro",
    "read_dascore",
    "write_dascore",
    "supported_dascore_formats",
    "patch_from_dascore",
    "spool_from_dascore",
    "AlakoroPatch",
    "AlakoroSpool",
    "DASDAEAdapter",
    "alakoro_to_dascore",
    "dascore_to_alakoro",
    "alakoro_to_xdas",
    "xdas_to_alakoro",
    "spool_to_datacollection",
    "datacollection_to_spool",
    "array_to_dataarray",
    "dataarray_to_array",
    "read_xdas",
    "write_xdas",
    "supported_xdas_formats",
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
