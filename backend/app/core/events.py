"""
Alakoro FiberSense - Event System
Event-driven architecture with Redis Pub/Sub.
"""
from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any, Callable, Dict, List

from app.core.redis_client import event_bus

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    DAS_RAW_RECEIVED = "das.raw_received"
    DAS_PROCESSING_COMPLETED = "das.processing.completed"
    DAS_PROCESSING_ERROR = "das.processing.error"

    DTS_RAW_RECEIVED = "dts.raw_received"
    DTS_PROCESSING_COMPLETED = "dts.processing.completed"
    DTS_PROCESSING_ERROR = "dts.processing.error"
    DTS_HOTSPOT_DETECTED = "dts.hotspot.detected"

    DSS_RAW_RECEIVED = "dss.raw_received"
    DSS_PROCESSING_COMPLETED = "dss.processing.completed"
    DSS_PROCESSING_ERROR = "dss.processing.error"
    DSS_EVENT_DETECTED = "dss.event.detected"

    SIMULATION_STARTED = "simulation.started"
    SIMULATION_COMPLETED = "simulation.completed"
    SIMULATION_ERROR = "simulation.error"

    ALERT_TRIGGERED = "alert.triggered"
    ALERT_ACKNOWLEDGED = "alert.acknowledged"

    PROCESSING_COMPLETED = "processing.completed"
    PROCESSING_ERROR = "processing.error"

    WS_UPDATE = "ws.update"


async def publish_event(event_type: EventType, data: Dict[str, Any]):
    """Publica um evento no Redis."""
    try:
        message = json.dumps({"type": event_type.value, "data": data})
        await event_bus.publish(event_type.value, message)
    except Exception as e:
        logger.error(f"Error publishing event {event_type}: {e}")


async def subscribe_event(event_type: EventType, handler: Callable):
    """Subscreve um handler para um tipo de evento."""
    async def wrapper(message: str):
        try:
            data = json.loads(message)
            await handler(data.get("data", {}))
        except Exception as e:
            logger.error(f"Error handling event {event_type}: {e}")

    await event_bus.subscribe(event_type.value, wrapper)
