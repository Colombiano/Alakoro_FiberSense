"""Event definitions and utilities for event-driven architecture."""
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
import json
import uuid


class EventType(str, Enum):
    """Event types for the event bus."""
    # DAS Events
    DAS_FILE_UPLOADED = "das.file_uploaded"
    DAS_DATA_VALIDATED = "das.data_validated"
    DAS_PROCESSING_STARTED = "das.processing_started"
    DAS_PROCESSING_COMPLETED = "das.processing_completed"
    DAS_PROCESSING_FAILED = "das.processing_failed"

    # DTS Events
    DTS_FILE_UPLOADED = "dts.file_uploaded"
    DTS_DATA_VALIDATED = "dts.data_validated"
    DTS_PROCESSING_STARTED = "dts.processing_started"
    DTS_PROCESSING_COMPLETED = "dts.processing_completed"
    DTS_PROCESSING_FAILED = "dts.processing_failed"

    # DSS Events
    DSS_FILE_UPLOADED = "dss.file_uploaded"
    DSS_DATA_VALIDATED = "dss.data_validated"
    DSS_PROCESSING_STARTED = "dss.processing_started"
    DSS_PROCESSING_COMPLETED = "dss.processing_completed"
    DSS_PROCESSING_FAILED = "dss.processing_failed"

    # Simulation Events
    SIMULATION_REQUESTED = "sim.requested"
    SIMULATION_STARTED = "sim.started"
    SIMULATION_COMPLETED = "sim.completed"
    SIMULATION_FAILED = "sim.failed"

    # Visualization Events
    VIZ_REQUESTED = "viz.requested"
    VIZ_RENDERING_STARTED = "viz.rendering_started"
    VIZ_RENDERING_COMPLETED = "viz.rendering_completed"
    VIZ_RENDERING_FAILED = "viz.rendering_failed"

    # Wavelet Events
    WAVELET_CWT_REQUESTED = "wavelet.cwt_requested"
    WAVELET_CWT_COMPLETED = "wavelet.cwt_completed"
    WAVELET_TRANSIENT_DETECTED = "wavelet.transient_detected"
    WAVELET_DENOISE_REQUESTED = "wavelet.denoise_requested"
    WAVELET_DENOISE_COMPLETED = "wavelet.denoise_completed"

    # Alert Events
    ALERT_THRESHOLD_EXCEEDED = "alert.threshold_exceeded"
    ALERT_CRITICAL_DETECTED = "alert.critical_detected"

    # System Events
    STATUS_UPDATE = "status.update"
    EXPORT_READY = "export.ready"
    WS_PUSH = "ws.push"


class Event:
    """Event message for the event bus."""

    def __init__(
        self,
        event_type: EventType,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.event_type = event_type
        self.payload = payload
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            event_type=EventType(data["event_type"]),
            payload=data["payload"],
            correlation_id=data.get("correlation_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else None,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Event":
        return cls.from_dict(json.loads(json_str))


class EventChannels:
    """Redis channel names for Alakoro FiberSense."""

    @staticmethod
    def raw_data(signal_type: str) -> str:
        return f"alakoro:{signal_type}:raw_data"

    @staticmethod
    def processing(signal_type: str) -> str:
        return f"alakoro:{signal_type}:processing"

    @staticmethod
    def visualization(signal_type: str) -> str:
        return f"alakoro:{signal_type}:visualization"

    @staticmethod
    def alerts() -> str:
        return "alakoro:alerts"

    @staticmethod
    def status() -> str:
        return "alakoro:status"

    @staticmethod
    def ws_broadcast() -> str:
        return "alakoro:ws:broadcast"
