"""Event Controller - Gerenciamento de eventos detectados"""

from typing import List, Optional, Dict, Any, Callable
import numpy as np

from ..models import DASEvent, EventClassification
from ..events import EventBus, EventType, Event


class EventController:
    """Controlador de eventos - gerencia deteccao e analise"""
    
    def __init__(self):
        self.event_bus = EventBus()
        self._events: List[DASEvent] = []
        self._filters: List[Callable[[DASEvent], bool]] = []
        
        self.event_bus.subscribe(EventType.EVENT_DETECTED, self._on_event_detected)
    
    def add_event(self, event: DASEvent) -> None:
        self._events.append(event)
        
        self.event_bus.publish(Event(
            EventType.EVENT_DETECTED,
            event.to_dict(),
            source="event_controller"
        ))
    
    def get_events(self, classification: Optional[EventClassification] = None,
                   min_confidence: float = 0.0, min_snr: float = 0.0,
                   channel_range: Optional[tuple] = None) -> List[DASEvent]:
        filtered = self._events
        
        if classification:
            filtered = [e for e in filtered if e.classification == classification]
        
        if min_confidence > 0:
            filtered = [e for e in filtered if e.confidence >= min_confidence]
        
        if min_snr > 0:
            filtered = [e for e in filtered if e.snr >= min_snr]
        
        if channel_range:
            start, end = channel_range
            filtered = [e for e in filtered 
                       if e.channel_start >= start and e.channel_end <= end]
        
        for filter_fn in self._filters:
            filtered = [e for e in filtered if filter_fn(e)]
        
        return filtered
    
    def get_event_by_id(self, event_id: str) -> Optional[DASEvent]:
        for event in self._events:
            if event.event_id == event_id:
                return event
        return None
    
    def add_filter(self, filter_fn: Callable[[DASEvent], bool]) -> None:
        self._filters.append(filter_fn)
    
    def clear_filters(self) -> None:
        self._filters.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        if not self._events:
            return {}
        
        classifications = {}
        for e in self._events:
            cls = e.classification.value
            classifications[cls] = classifications.get(cls, 0) + 1
        
        return {
            "total_events": len(self._events),
            "classifications": classifications,
            "avg_confidence": np.mean([e.confidence for e in self._events]),
            "avg_snr": np.mean([e.snr for e in self._events]),
            "max_amplitude": max([e.amplitude for e in self._events]) if self._events else 0,
        }
    
    def export_events(self, filepath: str) -> None:
        import json
        events_data = [e.to_dict() for e in self._events]
        with open(filepath, "w") as f:
            json.dump(events_data, f, indent=2)
    
    def clear(self) -> None:
        self._events.clear()
    
    def _on_event_detected(self, event: Event) -> None:
        if isinstance(event.data, dict):
            das_event = DASEvent.from_dict(event.data)
            if das_event not in self._events:
                self._events.append(das_event)
    
    @property
    def num_events(self) -> int:
        return len(self._events)
