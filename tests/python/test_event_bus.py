"""Testes do Event Bus"""

import pytest
import time
import threading

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "python"))

from events import EventBus, EventType, EventPriority, Event


class TestEventBus:
    def setup_method(self):
        EventBus._instance = None
    
    def test_singleton(self):
        bus1 = EventBus()
        bus2 = EventBus()
        assert bus1 is bus2
    
    def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []
        
        def handler(event):
            received.append(event)
        
        sub_id = bus.subscribe(EventType.RAW_DATA_ARRIVED, handler)
        
        event = Event(EventType.RAW_DATA_ARRIVED, {"test": 123})
        bus.publish(event)
        
        time.sleep(0.1)
        assert len(received) == 1
        assert received[0].data["test"] == 123
    
    def test_unsubscribe(self):
        bus = EventBus()
        received = []
        
        def handler(event):
            received.append(event)
        
        sub_id = bus.subscribe(EventType.RAW_DATA_ARRIVED, handler)
        bus.unsubscribe(sub_id)
        
        event = Event(EventType.RAW_DATA_ARRIVED, {"test": 123})
        bus.publish(event)
        
        time.sleep(0.1)
        assert len(received) == 0
    
    def test_priority(self):
        bus = EventBus()
        order = []
        
        def low_handler(event):
            order.append("low")
        
        def high_handler(event):
            order.append("high")
        
        bus.subscribe(EventType.INFO, low_handler, EventPriority.LOW)
        bus.subscribe(EventType.INFO, high_handler, EventPriority.HIGH)
        
        bus.publish(Event(EventType.INFO, None))
        time.sleep(0.1)
        
        assert order[0] == "high"
        assert order[1] == "low"
    
    def test_global_subscriber(self):
        bus = EventBus()
        received = []
        
        def handler(event):
            received.append(event.event_type)
        
        bus.subscribe_all(handler)
        
        bus.publish(Event(EventType.RAW_DATA_ARRIVED, None))
        bus.publish(Event(EventType.EVENT_DETECTED, None))
        
        time.sleep(0.1)
        assert len(received) == 2
    
    def test_history(self):
        bus = EventBus()
        
        for i in range(5):
            bus.publish(Event(EventType.INFO, {"i": i}))
        
        history = bus.get_history(EventType.INFO, limit=3)
        assert len(history) == 3
    
    def test_metrics(self):
        bus = EventBus()
        
        bus.publish(Event(EventType.INFO, None))
        bus.publish(Event(EventType.INFO, None))
        bus.publish(Event(EventType.ERROR, None))
        
        metrics = bus.get_metrics()
        assert metrics["INFO"] == 2
        assert metrics["ERROR"] == 1
