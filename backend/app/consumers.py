"""
Alakoro FiberSense - Event Consumers
"""
from __future__ import annotations

import asyncio
import json
import logging

from app.connection_manager import manager
from app.controllers import AlertController, SignalPipeline, SignalStore
from app.core.events import EventType
from app.core.redis_client import event_bus
from app.models import ProcessingStatus, SignalAlert, SignalAlertView, SignalData, SignalType

logger = logging.getLogger(__name__)


async def handle_das_raw(event: dict):
    """Processa dados DAS brutos."""
    try:
        signal_id = event.get("signal_id")
        signal = SignalStore.get(signal_id)
        if signal and signal.signal_type == SignalType.DAS:
            signal.status = ProcessingStatus.PROCESSING
            pipeline = SignalPipeline(SignalType.DAS)
            result = await pipeline.process(signal, event.get("config", {}))
            await manager.broadcast({
                "type": "das.processing.completed",
                "signal_id": signal_id,
                "result": result,
            })
    except Exception as e:
        logger.error(f"DAS processing error: {e}")


async def handle_dts_raw(event: dict):
    """Processa dados DTS brutos."""
    try:
        signal_id = event.get("signal_id")
        signal = SignalStore.get(signal_id)
        if signal and signal.signal_type == SignalType.DTS:
            signal.status = ProcessingStatus.PROCESSING
            pipeline = SignalPipeline(SignalType.DTS)
            result = await pipeline.process(signal, event.get("config", {}))
            await manager.broadcast({
                "type": "dts.processing.completed",
                "signal_id": signal_id,
                "result": result,
            })
    except Exception as e:
        logger.error(f"DTS processing error: {e}")


async def handle_dss_raw(event: dict):
    """Processa dados DSS brutos."""
    try:
        signal_id = event.get("signal_id")
        signal = SignalStore.get(signal_id)
        if signal and signal.signal_type == SignalType.DSS:
            signal.status = ProcessingStatus.PROCESSING
            pipeline = SignalPipeline(SignalType.DSS)
            result = await pipeline.process(signal, event.get("config", {}))
            await manager.broadcast({
                "type": "dss.processing.completed",
                "signal_id": signal_id,
                "result": result,
            })
    except Exception as e:
        logger.error(f"DSS processing error: {e}")


async def handle_alert(event: dict):
    """Processa alertas."""
    try:
        alert_data = event.get("alert", {})
        alert = SignalAlert(
            signal_type=SignalType(alert_data.get("signal_type", "das")),
            level=alert_data.get("level", "info"),
            message=alert_data.get("message", ""),
            event_id=alert_data.get("event_id"),
        )
        AlertController.add_alert(alert)
        await manager.broadcast({
            "type": "alert.triggered",
            "alert": alert.to_dict(),
        })
    except Exception as e:
        logger.error(f"Alert handling error: {e}")


async def handle_simulation_completed(event: dict):
    """Processa simulacao concluida."""
    try:
        await manager.broadcast({
            "type": "simulation.completed",
            "simulation_id": event.get("simulation_id"),
            "signal_type": event.get("signal_type"),
            "result": event.get("result"),
        })
    except Exception as e:
        logger.error(f"Simulation completed error: {e}")


async def handle_ws_update(event: dict):
    """Processa updates WebSocket."""
    try:
        await manager.broadcast({
            "type": "ws.update",
            "data": event.get("data", {}),
        })
    except Exception as e:
        logger.error(f"WS update error: {e}")


# Event handlers mapping
EVENT_HANDLERS = {
    EventType.DAS_RAW_RECEIVED: handle_das_raw,
    EventType.DTS_RAW_RECEIVED: handle_dts_raw,
    EventType.DSS_RAW_RECEIVED: handle_dss_raw,
    EventType.ALERT_TRIGGERED: handle_alert,
    EventType.SIMULATION_COMPLETED: handle_simulation_completed,
    EventType.WS_UPDATE: handle_ws_update,
}


async def start_event_consumers():
    """Inicia todos os consumidores de eventos."""
    logger.info("Starting event consumers...")
    for event_type, handler in EVENT_HANDLERS.items():
        await event_bus.subscribe(event_type.value, handler)
        logger.info(f"  Subscribed: {event_type.value}")
    logger.info(f"All {len(EVENT_HANDLERS)} consumers started")
