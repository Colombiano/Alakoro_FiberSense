"""Testes dos modelos"""

import pytest
import numpy as np
from datetime import datetime, timezone

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "python"))

from models import DASData, DASFrame, DASMetadata, DASEvent, EventClassification


class TestDASMetadata:
    def test_default_creation(self):
        meta = DASMetadata()
        assert meta.gauge_length == 10.2
        assert meta.spatial_sampling == 1.0
        assert meta.temporal_sampling == 1000.0
    
    def test_custom_values(self):
        meta = DASMetadata(
            gauge_length=5.0,
            num_channels=500,
            fiber_type="Custom"
        )
        assert meta.gauge_length == 5.0
        assert meta.num_channels == 500
        assert meta.fiber_type == "Custom"


class TestDASFrame:
    def test_creation(self):
        data = np.random.randn(100, 10)
        meta = DASMetadata()
        frame = DASFrame(data=data, timestamp=0.0, frame_number=0, metadata=meta)
        
        assert frame.num_samples == 100
        assert frame.num_channels == 10
        assert frame.shape == (100, 10)
    
    def test_1d_data(self):
        data = np.random.randn(100)
        meta = DASMetadata()
        frame = DASFrame(data=data, timestamp=0.0, frame_number=0, metadata=meta)
        
        assert frame.num_channels == 1


class TestDASData:
    def test_empty_creation(self):
        das = DASData()
        assert das.num_frames == 0
        assert das.total_samples == 0
    
    def test_add_frame(self):
        das = DASData()
        data = np.random.randn(100, 10)
        meta = DASMetadata()
        frame = DASFrame(data=data, timestamp=0.0, frame_number=0, metadata=meta)
        
        das.add_frame(frame)
        assert das.num_frames == 1
        assert das.total_samples == 100
    
    def test_statistics(self):
        das = DASData()
        data = np.ones((100, 10))
        meta = DASMetadata()
        frame = DASFrame(data=data, timestamp=0.0, frame_number=0, metadata=meta)
        das.add_frame(frame)
        
        stats = das.get_statistics()
        assert stats["mean"] == 1.0
        assert stats["std"] == 0.0


class TestDASEvent:
    def test_creation(self):
        event = DASEvent(
            timestamp=1.0,
            channel_start=10,
            channel_end=20,
            amplitude=0.5,
            snr=15.0,
            classification=EventClassification.VIBRATION
        )
        
        assert event.channel_start == 10
        assert event.channel_end == 20
        assert event.num_channels_affected == 11
        assert event.classification == EventClassification.VIBRATION
    
    def test_to_dict(self):
        event = DASEvent(
            timestamp=1.0,
            amplitude=0.5,
            classification=EventClassification.FRACTURE
        )
        
        d = event.to_dict()
        assert d["amplitude"] == 0.5
        assert d["classification"] == "fracture"
    
    def test_from_dict(self):
        data = {
            "event_id": "test123",
            "timestamp": 2.0,
            "channel_start": 5,
            "channel_end": 15,
            "amplitude": 0.3,
            "classification": "flow"
        }
        
        event = DASEvent.from_dict(data)
        assert event.event_id == "test123"
        assert event.classification == EventClassification.FLOW
