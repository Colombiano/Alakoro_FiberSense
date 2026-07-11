"""
Alakoro FiberSense - DSS Router
Endpoints para Distributed Strain Sensing.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.controllers import SignalPipeline, SignalStore
from app.models import SignalType
from app.views import SignalDataView

router = APIRouter()


@router.post("/process/{signal_id}")
async def process_dss(signal_id: str, config: dict = None):
    """Processa dados DSS."""
    signal = SignalStore.get(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    if signal.signal_type != SignalType.DSS:
        raise HTTPException(status_code=400, detail="Signal is not DSS type")

    pipeline = SignalPipeline(SignalType.DSS)
    result = await pipeline.process(signal, config or {})
    return {
        "signal_id": signal_id,
        "result": result,
        "status": "completed",
    }


@router.get("/status/{signal_id}")
async def get_dss_status(signal_id: str):
    """Retorna status do processamento DSS."""
    signal = SignalStore.get(signal_id)
    if not signal or signal.signal_type != SignalType.DSS:
        raise HTTPException(status_code=404, detail="DSS signal not found")
    return SignalDataView.serialize(signal)
