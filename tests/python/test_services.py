"""Testes dos servicos"""

import pytest
import numpy as np

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "python"))

from models import DASFrame, DASMetadata, DASEvent, EventClassification, ProcessingConfig
from services import ProcessingService, DetectionService, DataLoaderService


class TestProcessingService:
    def test_creation(self):
        service = ProcessingService()
        assert service.config is not None
    
    def test_filter_signal(self):
        config = ProcessingConfig(filter_type="bandpass", low_cutoff=10, high_cutoff=100)
        service = ProcessingService(config)
        
        data = np.random.randn(1000, 10)
        frame = DASFrame(data=data, timestamp=0.0, frame_number=0, 
                        metadata=DASMetadata(temporal_sampling=1000.0))
        
        result = service.filter_signal(frame)
        assert result.shape == data.shape
    
    def test_quality_metrics(self):
        service = ProcessingService()
        data = np.random.randn(1000, 100)
        
        metrics = service.compute_quality_metrics(data)
        assert "mean" in metrics
        assert "std" in metrics
        assert "snr" in metrics


class TestDetectionService:
    def test_creation(self):
        service = DetectionService()
        assert service.config is not None
    
    def test_detect_events(self):
        service = DetectionService()
        
        data = np.random.randn(1000, 100) * 0.01
        for ch in range(45, 55):
            data[:, ch] += 0.5 * np.sin(2 * np.pi * 50 * np.arange(1000) / 1000)
        
        frame = DASFrame(data=data, timestamp=0.0, frame_number=0,
                        metadata=DASMetadata(temporal_sampling=1000.0))
        
        events = service.detect_events(frame)
        assert len(events) > 0
    
    def test_classify_event(self):
        service = DetectionService()
        
        event = DASEvent(frequency_center=5.0)
        classification = service.classify_event(event)
        assert classification == EventClassification.FLOW
        
        event = DASEvent(frequency_center=30.0)
        classification = service.classify_event(event)
        assert classification == EventClassification.VIBRATION


class TestDataLoaderService:
    def test_creation(self):
        service = DataLoaderService()
        assert service is not None
    
    def test_get_supported_formats(self):
        service = DataLoaderService()
        formats = service.get_supported_formats()
        assert ".h5" in formats
        assert ".npy" in formats
    
    def test_load_numpy(self, tmp_path):
        test_data = np.random.randn(100, 10)
        test_file = tmp_path / "test.npy"
        np.save(test_file, test_data)
        
        service = DataLoaderService()
        result = service.load(str(test_file))
        
        assert result.num_frames == 1
        assert result.total_samples == 100
