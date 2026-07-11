"""
Alakoro FiberSense - Upload Router
Endpoints para upload de arquivos de sinal.
"""
from __future__ import annotations

import tempfile
from typing import Optional

import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.controllers import SignalStore
from app.core.events import EventType, publish_event
from app.models import SignalData, SignalType

router = APIRouter()


@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    signal_type: str = Form("das"),
    fiber_length: float = Form(10000.0),
    spatial_resolution: float = Form(1.0),
    sampling_rate: float = Form(1000.0),
):
    """Upload de arquivo de sinal (HDF5, SEG-Y, TDMS, CSV, NPY)."""
    try:
        content = await file.read()
        filename = file.filename.lower()

        if filename.endswith(".npy"):
            data = _load_npy(content)
        elif filename.endswith(".csv"):
            data = _load_csv(content)
        elif filename.endswith(".h5") or filename.endswith(".hdf5"):
            data = _load_hdf5(content)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file format: {filename}")

        signal = SignalData(
            signal_type=SignalType(signal_type),
            raw_data=data,
            params=FiberParams(
                fiber_length=fiber_length,
                spatial_resolution=spatial_resolution,
                sampling_rate=sampling_rate,
            ),
            metadata={"filename": file.filename, "size": len(content)},
        )
        SignalStore.add(signal)

        await publish_event(EventType.DAS_RAW_RECEIVED if signal_type == "das" else
                          EventType.DTS_RAW_RECEIVED if signal_type == "dts" else
                          EventType.DSS_RAW_RECEIVED, {
            "signal_id": signal.id,
            "filename": file.filename,
            "signal_type": signal_type,
        })

        return {
            "signal_id": signal.id,
            "signal_type": signal_type,
            "shape": list(data.shape),
            "filename": file.filename,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _load_npy(content: bytes) -> np.ndarray:
    """Carrega arquivo NPY."""
    import io
    return np.load(io.BytesIO(content))


def _load_csv(content: bytes) -> np.ndarray:
    """Carrega arquivo CSV."""
    import io
    return np.loadtxt(io.StringIO(content.decode()), delimiter=",")


def _load_hdf5(content: bytes) -> np.ndarray:
    """Carrega arquivo HDF5."""
    import io
    import h5py
    with h5py.File(io.BytesIO(content), "r") as f:
        return f["signal"][:]
