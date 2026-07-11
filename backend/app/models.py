"""
Alakoro FiberSense - Models
MVC Models para DAS, DTS e DSS.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np


class SignalType(str, Enum):
    DAS = "das"
    DTS = "dts"
    DSS = "dss"


class AlertLevel(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class FiberParams:
    fiber_length: float = 10000.0
    spatial_resolution: float = 1.0
    sampling_rate: float = 1000.0
    gauge_length: float = 10.0
    refractive_index: float = 1.468
    cable_type: str = "single_mode"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fiber_length": self.fiber_length,
            "spatial_resolution": self.spatial_resolution,
            "sampling_rate": self.sampling_rate,
            "gauge_length": self.gauge_length,
            "refractive_index": self.refractive_index,
            "cable_type": self.cable_type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FiberParams:
        return cls(**data)


@dataclass
class SignalData:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    signal_type: SignalType = SignalType.DAS
    raw_data: np.ndarray = field(default_factory=lambda: np.array([]))
    processed_data: Optional[np.ndarray] = None
    distance: Optional[np.ndarray] = None
    time: Optional[np.ndarray] = None
    params: FiberParams = field(default_factory=FiberParams)
    status: ProcessingStatus = ProcessingStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.distance is None and self.params.fiber_length > 0:
            n_samples = int(self.params.fiber_length / self.params.spatial_resolution)
            self.distance = np.linspace(0, self.params.fiber_length, n_samples)
        if self.time is None and self.params.sampling_rate > 0:
            n_time = int(self.raw_data.shape[0]) if self.raw_data.ndim > 1 else 1
            duration = n_time / self.params.sampling_rate
            self.time = np.linspace(0, duration, n_time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "signal_type": self.signal_type.value,
            "shape": list(self.raw_data.shape) if self.raw_data.size > 0 else [],
            "distance_range": [float(self.distance.min()), float(self.distance.max())] if self.distance is not None else None,
            "time_range": [float(self.time.min()), float(self.time.max())] if self.time is not None else None,
            "params": self.params.to_dict(),
            "status": self.status.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class SignalEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    signal_type: SignalType = SignalType.DAS
    event_type: str = "anomaly"
    position: Optional[float] = None
    amplitude: Optional[float] = None
    frequency: Optional[float] = None
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "signal_type": self.signal_type.value,
            "event_type": self.event_type,
            "position": self.position,
            "amplitude": self.amplitude,
            "frequency": self.frequency,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class SignalAlert:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    signal_type: SignalType = SignalType.DAS
    level: AlertLevel = AlertLevel.INFO
    message: str = ""
    event_id: Optional[str] = None
    acknowledged: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "signal_type": self.signal_type.value,
            "level": self.level.value,
            "message": self.message,
            "event_id": self.event_id,
            "acknowledged": self.acknowledged,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ProcessingJob:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    signal_id: str = ""
    signal_type: SignalType = SignalType.DAS
    status: ProcessingStatus = ProcessingStatus.PENDING
    pipeline_config: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "signal_type": self.signal_type.value,
            "status": self.status.value,
            "pipeline_config": self.pipeline_config,
            "result": self.result,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class SimulationConfig:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    signal_type: SignalType = SignalType.DAS
    fiber_length: float = 10000.0
    spatial_resolution: float = 1.0
    sampling_rate: float = 1000.0
    duration: float = 10.0
    events: List[Dict[str, Any]] = field(default_factory=list)
    noise_level: float = 0.01
    seed: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "signal_type": self.signal_type.value,
            "fiber_length": self.fiber_length,
            "spatial_resolution": self.spatial_resolution,
            "sampling_rate": self.sampling_rate,
            "duration": self.duration,
            "events": self.events,
            "noise_level": self.noise_level,
            "seed": self.seed,
            "created_at": self.created_at.isoformat(),
        }
