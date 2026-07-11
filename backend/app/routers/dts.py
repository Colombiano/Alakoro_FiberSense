"""
Alakoro FiberSense - DTS Router
Endpoints para Distributed Temperature Sensing.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.controllers import SignalPipeline, SignalStore
from app.models import SignalType
from app.views import SignalDataView

router = APIRouter()


@router.post("/process/{signal_id}")
async def process_dts(signal_id: str, config: dict = None):
    """Processa dados DTS."""
    signal = SignalStore.get(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    if signal.signal_type != SignalType.DTS:
        raise HTTPException(status_code=400, detail="Signal is not DTS type")

    pipeline = SignalPipeline(SignalType.DTS)
    result = await pipeline.process(signal, config or {})
    return {
        "signal_id": signal_id,
        "result": result,
        "status": "completed",
    }


@router.get("/status/{signal_id}")
async def get_dts_status(signal_id: str):
    """Retorna status do processamento DTS."""
    signal = SignalStore.get(signal_id)
    if not signal or signal.signal_type != SignalType.DTS:
        raise HTTPException(status_code=404, detail="DTS signal not found")
    return SignalDataView.serialize(signal)


@router.get("/hotspots/{signal_id}")
async def get_dts_hotspots(signal_id: str):
    """Retorna hotspots detectados no sinal DTS."""
    signal = SignalStore.get(signal_id)
    if not signal or signal.signal_type != SignalType.DTS:
        raise HTTPException(status_code=404, detail="DTS signal not found")
    if signal.processed_data is None:
        raise HTTPException(status_code=400, detail="Signal not processed yet")

    pipeline = SignalPipeline(SignalType.DTS)
    hotspots = pipeline._detect_hotspots(signal.processed_data, signal)
    return {
        "signal_id": signal_id,
        "hotspots": [h.to_dict() for h in hotspots],
        "count": len(hotspots),
    }
