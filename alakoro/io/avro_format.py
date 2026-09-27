"""
Alakoro FiberSense — Serializacao Avro para DAS/DTS/DSS

Implementacao Python usando fastavro. Avro e o formato preferido para
streaming enterprise (Kafka) porque e compacto, evoluciona via schemas e tem
suporte nativo em ecossistemas de dados (Spark, Flink, Kafka Connect).
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np

from .alakoro_spool import AlakoroPatch


def _schema_path() -> str:
    return os.path.join(os.path.dirname(__file__), "schemas", "alakoro_sensing.avsc")


def _load_schema() -> Dict[str, Any]:
    with open(_schema_path(), "r", encoding="utf-8") as f:
        return json.load(f)


try:
    import fastavro
    import fastavro.schema

    _SCHEMA = fastavro.schema.parse_schema(_load_schema())
    _HAS_FASTAVRO = True
except Exception:  # pragma: no cover
    _SCHEMA = None
    _HAS_FASTAVRO = False


def _check_fastavro() -> None:
    if not _HAS_FASTAVRO:
        raise ImportError(
            "fastavro is required for Avro serialization. "
            "Install it with: pip install fastavro"
        )


def serialize_avro(
    data: Union[AlakoroPatch, np.ndarray],
    modality: str = "das",
    metadata: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Serializa AlakoroPatch ou array NumPy para bytes Avro.

    Args:
        data: AlakoroPatch ou array 2D NumPy (n_times, n_channels).
        modality: "das", "dts" ou "dss".
        metadata: dicionario com campos opcionais:
            sampling_rate_hz, spatial_resolution_m, gauge_length_m,
            units, start_time.

    Returns:
        Bytes Avro serializados.
    """
    _check_fastavro()

    if isinstance(data, AlakoroPatch):
        arr = np.asarray(data.data)
        modality = data.modality
        attrs = getattr(data, "attrs", None)
        meta_src: Dict[str, Any] = {}
        if attrs is not None:
            meta_src = {
                "sampling_rate_hz": float(getattr(attrs, "sampling_rate_hz", 0.0) or 0.0),
                "spatial_resolution_m": float(getattr(attrs, "spatial_resolution_m", 0.0) or 0.0),
                "gauge_length_m": float(getattr(attrs, "gauge_length_m", 0.0) or 0.0),
                "units": str(getattr(attrs, "data_units", "") or ""),
                "start_time": str(getattr(attrs, "start_time", "") or ""),
            }
        if metadata:
            meta_src.update(metadata)
        metadata = meta_src
    else:
        arr = np.asarray(data)

    modality = modality.upper()
    if modality not in {"DAS", "DTS", "DSS"}:
        raise ValueError(f"Unknown modality: {modality}")

    if arr.ndim != 2:
        raise ValueError(f"Expected 2D array, got shape {arr.shape}")

    n_times, n_channels = arr.shape
    dtype = str(arr.dtype)
    if dtype not in {"float32", "float64"}:
        raise ValueError(f"Unsupported dtype for Avro: {dtype}")

    metadata = metadata or {}
    record = {
        "modality": modality,
        "n_times": int(n_times),
        "n_channels": int(n_channels),
        "sampling_rate_hz": float(metadata.get("sampling_rate_hz", 0.0)),
        "spatial_resolution_m": float(metadata.get("spatial_resolution_m", 0.0)),
        "gauge_length_m": float(metadata.get("gauge_length_m", 0.0)),
        "units": str(metadata.get("units", "")),
        "start_time": str(metadata.get("start_time", "")),
        "dtype": dtype,
        "data": arr.tobytes(),
    }

    buf = io.BytesIO()
    fastavro.schemaless_writer(buf, _SCHEMA, record)
    return buf.getvalue()


def deserialize_avro(data: bytes) -> Dict[str, Any]:
    """
    Desserializa bytes Avro em dicionario com array NumPy.

    Returns:
        {
            "modality": str,
            "n_times": int,
            "n_channels": int,
            "metadata": dict,
            "dtype": str,
            "array": np.ndarray,
        }
    """
    _check_fastavro()

    buf = io.BytesIO(data)
    record = fastavro.schemaless_reader(buf, _SCHEMA)

    modality = record["modality"]
    n_times = int(record["n_times"])
    n_channels = int(record["n_channels"])
    dtype = record["dtype"]

    arr = np.frombuffer(record["data"], dtype=dtype).reshape((n_times, n_channels))

    return {
        "modality": modality,
        "n_times": n_times,
        "n_channels": n_channels,
        "metadata": {
            "sampling_rate_hz": record["sampling_rate_hz"],
            "spatial_resolution_m": record["spatial_resolution_m"],
            "gauge_length_m": record["gauge_length_m"],
            "units": record["units"],
            "start_time": record["start_time"],
        },
        "dtype": dtype,
        "array": arr.copy(),
    }


def write_avro(path: Union[str, Path], records: list) -> None:
    """
    Escreve multiplos registros Avro em arquivo usando schema embutido.

    Args:
        path: caminho do arquivo de saida.
        records: lista de dicts retornados por serialize_avro (bytes) ou
            dicts com chave "data" contendo bytes Avro.
    """
    _check_fastavro()

    path = Path(path)
    with open(path, "wb") as f:
        for rec in records:
            if isinstance(rec, dict) and "data" in rec:
                f.write(rec["data"])
            elif isinstance(rec, bytes):
                f.write(rec)
            else:
                raise TypeError("Each record must be bytes or dict with 'data' key")


def read_avro(path: Union[str, Path]) -> list:
    """
    Le um arquivo com registros Avro concatenados (formato schemaless).

    Returns:
        Lista de dicts retornados por deserialize_avro.
    """
    _check_fastavro()

    path = Path(path)
    results = []
    with open(path, "rb") as f:
        payload = f.read()

    offset = 0
    while offset < len(payload):
        buf = io.BytesIO(payload[offset:])
        record = fastavro.schemaless_reader(buf, _SCHEMA)
        n_times = int(record["n_times"])
        n_channels = int(record["n_channels"])
        dtype = record["dtype"]
        arr = np.frombuffer(record["data"], dtype=dtype).reshape((n_times, n_channels))
        results.append(
            {
                "modality": record["modality"],
                "n_times": n_times,
                "n_channels": n_channels,
                "metadata": {
                    "sampling_rate_hz": record["sampling_rate_hz"],
                    "spatial_resolution_m": record["spatial_resolution_m"],
                    "gauge_length_m": record["gauge_length_m"],
                    "units": record["units"],
                    "start_time": record["start_time"],
                },
                "dtype": dtype,
                "array": arr.copy(),
            }
        )
        offset += buf.tell()

    return results
