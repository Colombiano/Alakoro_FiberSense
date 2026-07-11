"""Streaming Service - Servico de streaming de dados DAS"""

from typing import Optional, Callable, List
import threading
import time
import numpy as np

from ..models import DASFrame, DASMetadata
from ..events import EventBus, EventType, Event


class StreamingService:
    """Servico de streaming de dados DAS em tempo real"""
    
    def __init__(self, buffer_size: int = 100):
        self.buffer_size = buffer_size
        self.event_bus = EventBus()
        
        self._buffer: List[DASFrame] = []
        self._buffer_lock = threading.Lock()
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._source: Optional[str] = None
        
        self.on_frame: Optional[Callable[[DASFrame], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
    
    def start(self, source: str) -> None:
        self._source = source
        self._running = True
        
        self.event_bus.publish(Event(
            EventType.STREAM_STARTED,
            {"source": source},
            source="streaming_service"
        ))
        
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=5.0)
        
        self.event_bus.publish(Event(
            EventType.STREAM_STOPPED,
            {"source": self._source},
            source="streaming_service"
        ))
    
    def _capture_loop(self) -> None:
        frame_number = 0
        
        try:
            while self._running:
                frame = self._generate_simulated_frame(frame_number)
                
                with self._buffer_lock:
                    self._buffer.append(frame)
                    if len(self._buffer) > self.buffer_size:
                        self._buffer.pop(0)
                
                self.event_bus.publish(Event(
                    EventType.FRAME_RECEIVED,
                    {"frame_number": frame_number},
                    source="streaming_service"
                ))
                
                if self.on_frame:
                    self.on_frame(frame)
                
                frame_number += 1
                time.sleep(0.001)
                
        except Exception as e:
            self.event_bus.publish(Event(
                EventType.STREAM_ERROR,
                {"error": str(e)},
                source="streaming_service"
            ))
            if self.on_error:
                self.on_error(e)
    
    def get_frame(self) -> Optional[DASFrame]:
        with self._buffer_lock:
            if self._buffer:
                return self._buffer[-1]
            return None
    
    def get_buffer(self) -> List[DASFrame]:
        with self._buffer_lock:
            return self._buffer.copy()
    
    def clear_buffer(self) -> None:
        with self._buffer_lock:
            self._buffer.clear()
    
    def _generate_simulated_frame(self, frame_number: int) -> DASFrame:
        num_samples = 1000
        num_channels = 100
        
        t = frame_number * 0.001
        data = np.random.randn(num_samples, num_channels) * 0.01
        
        signal_freq = 50.0
        for ch in range(40, 60):
            data[:, ch] += 0.5 * np.sin(2 * np.pi * signal_freq * np.arange(num_samples) / 1000 + t)
        
        metadata = DASMetadata(
            gauge_length=10.2,
            spatial_sampling=1.0,
            temporal_sampling=1000.0,
            num_channels=num_channels,
            num_samples=num_samples,
        )
        
        return DASFrame(
            data=data,
            timestamp=t,
            frame_number=frame_number,
            metadata=metadata
        )
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def buffer_count(self) -> int:
        with self._buffer_lock:
            return len(self._buffer)
