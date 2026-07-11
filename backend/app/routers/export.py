"""
Alakoro FiberSense - Export Router
Endpoints para exportacao de dados em multiplos formatos.
"""
from __future__ import annotations

import io
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.controllers import SignalStore

router = APIRouter()


@router.get("/{signal_id}")
async def export_signal(
    signal_id: str,
    format: str = Query("hdf5", enum=["hdf5", "csv", "netcdf"]),
):
    """Exporta um sinal para o formato especificado."""
    signal = SignalStore.get(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    data = signal.processed_data if signal.processed_data is not None else signal.raw_data
    if data.size == 0:
        raise HTTPException(status_code=400, detail="No data to export")

    if format == "hdf5":
        return _export_hdf5(signal, data)
    elif format == "csv":
        return _export_csv(signal, data)
    elif format == "netcdf":
        return _export_netcdf(signal, data)

    raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


def _export_hdf5(signal, data):
    """Exporta para HDF5."""
    import h5py

    buffer = io.BytesIO()
    with h5py.File(buffer, "w") as f:
        f.create_dataset("signal", data=data)
        f.attrs["signal_type"] = signal.signal_type.value
        f.attrs["fiber_length"] = signal.params.fiber_length
        f.attrs["spatial_resolution"] = signal.params.spatial_resolution
        if signal.distance is not None:
            f.create_dataset("distance", data=signal.distance)

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/x-hdf5",
        headers={"Content-Disposition": f"attachment; filename={signal.id}.h5"},
    )


def _export_csv(signal, data):
    """Exporta para CSV."""
    buffer = io.StringIO()
    if data.ndim == 1:
        if signal.distance is not None:
            np.savetxt(buffer, np.column_stack([signal.distance, data]), delimiter=",", header="distance,amplitude")
        else:
            np.savetxt(buffer, data, delimiter=",")
    elif data.ndim == 2:
        np.savetxt(buffer, data, delimiter=",")

    buffer.seek(0)
    return StreamingResponse(
        io.BytesIO(buffer.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={signal.id}.csv"},
    )


def _export_netcdf(signal, data):
    """Exporta para NetCDF."""
    from netCDF4 import Dataset

    buffer = io.BytesIO()
    nc = Dataset("memory", mode="w", format="NETCDF4", memory=buffer)

    nc.signal_type = signal.signal_type.value
    nc.fiber_length = signal.params.fiber_length
    nc.spatial_resolution = signal.params.spatial_resolution

    if data.ndim == 1:
        dist_dim = nc.createDimension("distance", len(data))
        var = nc.createVariable("signal", "f8", ("distance",))
        var[:] = data
        if signal.distance is not None:
            dist_var = nc.createVariable("distance", "f8", ("distance",))
            dist_var[:] = signal.distance
    elif data.ndim == 2:
        time_dim = nc.createDimension("time", data.shape[0])
        dist_dim = nc.createDimension("distance", data.shape[1])
        var = nc.createVariable("signal", "f8", ("time", "distance"))
        var[:] = data

    nc.close()
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/x-netcdf",
        headers={"Content-Disposition": f"attachment; filename={signal.id}.nc"},
    )
