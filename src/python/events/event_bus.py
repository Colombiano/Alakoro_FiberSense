"""
Event Bus - Sistema de comunicacao assincrona baseado em eventos
Arquitetura Publish/Subscribe com prioridade
"""

import asyncio
import time
from enum import Enum, auto
from typing import Dict, List, Callable, Any, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
import threading
import queue


class EventType(Enum):
    """Tipos de eventos do sistema"""
    RAW_DATA_ARRIVED = auto()
    DATA_PROCESSED = auto()
    DATA_FILTERED = auto()
    EVENT_DETECTED = auto()
    EVENT_CLASSIFIED = auto()
    EVENT_MERGED = auto()
    STREAM_STARTED = auto()
    STREAM_STOPPED = auto()
    STREAM_ERROR = auto()
    FRAME_RECEIVED = auto()
    PROCESSING_STARTED = auto()
    PROCESSING_COMPLETED = auto()
    PROCESSING_ERROR = auto()
    PIPELINE_INITIALIZED = auto()
    PIPELINE_CONFIGURED = auto()
    PIPELINE_EXECUTED = auto()
    ERROR = auto()
    WARNING = auto()
    INFO = auto()
    SHUTDOWN = auto()


class EventPriority(Enum):
    """Prioridade de eventos"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class Event:
    """Representacao de um evento"""
    event_type: EventType
    data: Any = None
    priority: EventPriority = EventPriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        return f"<Event {self.event_type.name} priority={self.priority.name} source={self.source}>"


class EventBus:
    """Barramento de Eventos - Implementacao Singleton"""
    
    _instance: Optional["EventBus"] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> "EventBus":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        
        self._subscribers: Dict[EventType, List[Dict[str, Any]]] = defaultdict(list)
        self._global_subscribers: List[Dict[str, Any]] = []
        self._event_queue: queue.PriorityQueue = queue.PriorityQueue()
        self._history: List[Event] = []
        self._max_history = 10000
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._metrics: Dict[str, int] = defaultdict(int)
    
    def subscribe(self, event_type: EventType, handler: Callable[[Event], Any],
                  priority: EventPriority = EventPriority.NORMAL,
                  filter_fn: Optional[Callable[[Event], bool]] = None) -> str:
        import uuid
        sub_id = str(uuid.uuid4())
        
        subscriber = {
            "id": sub_id,
            "handler": handler,
            "priority": priority,
            "filter": filter_fn,
            "active": True
        }
        
        self._subscribers[event_type].append(subscriber)
        self._subscribers[event_type].sort(key=lambda x: x["priority"].value)
        
        return sub_id
    
    def subscribe_all(self, handler: Callable[[Event], Any],
                      priority: EventPriority = EventPriority.NORMAL) -> str:
        import uuid
        sub_id = str(uuid.uuid4())
        
        self._global_subscribers.append({
            "id": sub_id,
            "handler": handler,
            "priority": priority,
            "active": True
        })
        
        self._global_subscribers.sort(key=lambda x: x["priority"].value)
        return sub_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        for event_type, subscribers in self._subscribers.items():
            for sub in subscribers:
                if sub["id"] == subscription_id:
                    sub["active"] = False
                    subscribers.remove(sub)
                    return True
        
        for sub in self._global_subscribers:
            if sub["id"] == subscription_id:
                sub["active"] = False
                self._global_subscribers.remove(sub)
                return True
        
        return False
    
    def publish(self, event: Event) -> None:
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        
        self._metrics[event.event_type.name] += 1
        self._event_queue.put((event.priority.value, event.timestamp, event))
        self._process_event(event)
    
    def publish_sync(self, event: Event) -> List[Any]:
        results = []
        
        for sub in self._subscribers.get(event.event_type, []):
            if sub["active"] and (sub["filter"] is None or sub["filter"](event)):
                try:
                    result = sub["handler"](event)
                    results.append(result)
                except Exception as e:
                    self.publish(Event(EventType.ERROR, {"error": str(e), "event": event},
                                       EventPriority.HIGH, source="event_bus"))
        
        for sub in self._global_subscribers:
            if sub["active"]:
                try:
                    result = sub["handler"](event)
                    results.append(result)
                except Exception as e:
                    self.publish(Event(EventType.ERROR, {"error": str(e), "event": event},
                                       EventPriority.HIGH, source="event_bus"))
        
        return results
    
    def _process_event(self, event: Event) -> None:
        for sub in self._subscribers.get(event.event_type, []):
            if sub["active"] and (sub["filter"] is None or sub["filter"](event)):
                try:
                    if asyncio.iscoroutinefunction(sub["handler"]):
                        asyncio.create_task(sub["handler"](event))
                    else:
                        sub["handler"](event)
                except Exception as e:
                    print(f"Error in event handler: {e}")
        
        for sub in self._global_subscribers:
            if sub["active"]:
                try:
                    if asyncio.iscoroutinefunction(sub["handler"]):
                        asyncio.create_task(sub["handler"](event))
                    else:
                        sub["handler"](event)
                except Exception as e:
                    print(f"Error in global handler: {e}")
    
    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._process_queue, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
    
    def _process_queue(self) -> None:
        while self._running:
            try:
                _, _, event = self._event_queue.get(timeout=0.1)
                self._process_event(event)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Queue processing error: {e}")
    
    def get_history(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
        filtered = self._history
        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]
        return filtered[-limit:]
    
    def get_metrics(self) -> Dict[str, int]:
        return dict(self._metrics)
    
    def clear_history(self) -> None:
        self._history.clear()
    
    def reset_metrics(self) -> None:
        self._metrics.clear()
    
    def wait_for_event(self, event_type: EventType, timeout: float = 10.0) -> Optional[Event]:
        start_time = time.time()
        while time.time() - start_time < timeout:
            for event in reversed(self._history):
                if event.event_type == event_type:
                    return event
            time.sleep(0.01)
        return None
