"""
Alakoro FiberSense — Serializacao Protobuf para DAS/DTS/DSS

Wrapper Python em torno do serializador Protobuf C++20, permitindo salvar e
carregar patches de/para arquivos binarios.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import numpy as np

from .alakoro_spool import AlakoroPatch


def _has_protobuf_core() -> bool:
    """Verifica se a extensao C++ foi compilada com suporte a Protobuf."""
    try:
        import alakoro_core  # noqa: F401
        return hasattr(alakoro_core, "DASData_d")
    except Exception:  # pragma: no cover
        return False


def serialize_protobuf(
    data: Union[AlakoroPatch, np.ndarray],
    modality: str = "das",
) -> bytes:
    """
    Serializa AlakoroPatch ou array NumPy para bytes Protobuf.

    Args:
        data: AlakoroPatch ou array 2D NumPy (n_times, n_channels).
        modality: "das", "dts" ou "dss" (usado apenas se data for ndarray).

    Returns:
        Bytes Protobuf serializados.
    """
    if not _has_protobuf_core():
        raise ImportError(
            "Serializacao Protobuf requer extensao C++ compilada com "
            "-DALAKORO_WITH_PROTOBUF=ON."
        )

    if isinstance(data, AlakoroPatch):
        return data.to_protobuf_bytes()

    arr = np.asarray(data)
    if arr.ndim != 2:
        raise ValueError(f"Expected 2D array, got shape {arr.shape}")

    patch = AlakoroPatch.from_array(arr, modality=modality)
    return patch.to_protobuf_bytes()


def deserialize_protobuf(
    data: bytes,
    modality: str = "das",
    well_id: Optional[str] = None,
) -> AlakoroPatch:
    """
    Desserializa bytes Protobuf em AlakoroPatch.

    Args:
        data: bytes Protobuf.
        modality: "das", "dts" ou "dss".
        well_id: identificador opcional do poco.

    Returns:
        AlakoroPatch reconstruido.
    """
    if not _has_protobuf_core():
        raise ImportError(
            "Serializacao Protobuf requer extensao C++ compilada com "
            "-DALAKORO_WITH_PROTOBUF=ON."
        )

    return AlakoroPatch.from_protobuf_bytes(data, modality=modality, well_id=well_id)


def save_protobuf(path: Union[str, Path], data: Union[AlakoroPatch, np.ndarray]) -> None:
    """Salva AlakoroPatch ou array NumPy em arquivo Protobuf."""
    path = Path(path)
    payload = serialize_protobuf(data)
    path.write_bytes(payload)


def load_protobuf(
    path: Union[str, Path],
    modality: str = "das",
    well_id: Optional[str] = None,
) -> AlakoroPatch:
    """Carrega AlakoroPatch a partir de arquivo Protobuf."""
    path = Path(path)
    return deserialize_protobuf(path.read_bytes(), modality=modality, well_id=well_id)
