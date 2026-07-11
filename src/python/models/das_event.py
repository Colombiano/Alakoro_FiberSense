"""Modelo de eventos detectados"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime
import numpy as np


class EventClassification(Enum):
    """Classificacao de eventos"""
    VIBRATION = "vibration"
    FRACTURE = "fracture"
    FLOW = "flow"
    LEAK = "leak"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


@dataclass
class DASEvent:
    """Evento detectado em dados DAS"""
    
    event_id: str = ""
    timestamp: float = 0.0
    datetime_utc: Optional[datetime] = None
    
    channel_start: int = 0
    channel_end: int = 0
    distance_start: float = 0.0
    distance_end: float = 0.0
    
    frequency_center: float = 0.0
    bandwidth: float = 0.0
    dominant_frequency: Optional[float] = None
    
    amplitude: float = 0.0
    snr: float = 0.0
    confidence: float = 0.0
    
    classification: EventClassification = EventClassification.UNKNOWN
    classification_confidence: float = 0.0
    
    waveform: Optional[np.ndarray] = None
    
    features: Dict[str, float] = field(default_factory=dict)
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.event_id:
            import uuid
            self.event_id = str(uuid.uuid4())[:8]
        if self.datetime_utc is None:
            from datetime import datetime, timezone
            self.datetime_utc = datetime.now(timezone.utc)
    
    @property
    def duration_ms(self) -> float:
        if self.waveform is not None and len(self.waveform) > 0:
            return self.features.get("duration", len(self.waveform))
        return self.features.get("duration", 0.0)
    
    @property
    def num_channels_affected(self) -> int:
        return self.channel_end - self.channel_start + 1
    
    @property
    def spatial_extent(self) -> float:
        return self.distance_end - self.distance_start
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "datetime_utc": self.datetime_utc.isoformat() if self.datetime_utc else None,
            "channel_start": self.channel_start,
            "channel_end": self.channel_end,
            "distance_start": self.distance_start,
            "distance_end": self.distance_end,
            "frequency_center": self.frequency_center,
            "bandwidth": self.bandwidth,
            "amplitude": self.amplitude,
            "snr": self.snr,
            "confidence": self.confidence,
            "classification": self.classification.value,
            "classification_confidence": self.classification_confidence,
            "duration_ms": self.duration_ms,
            "num_channels": self.num_channels_affected,
            "spatial_extent": self.spatial_extent,
            "features": self.features,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DASEvent":
        event = cls(
            event_id=data.get("event_id", ""),
            timestamp=data.get("timestamp", 0.0),
            channel_start=data.get("channel_start", 0),
            channel_end=data.get("channel_end", 0),
            distance_start=data.get("distance_start", 0.0),
            distance_end=data.get("distance_end", 0.0),
            frequency_center=data.get("frequency_center", 0.0),
            bandwidth=data.get("bandwidth", 0.0),
            amplitude=data.get("amplitude", 0.0),
            snr=data.get("snr", 0.0),
            confidence=data.get("confidence", 0.0),
            classification=EventClassification(data.get("classification", "unknown")),
            classification_confidence=data.get("classification_confidence", 0.0),
            features=data.get("features", {}),
        )
        if "waveform" in data and data["waveform"] is not None:
            event.waveform = np.array(data["waveform"])
        return event
