"""Data Controller - Gerenciamento de dados DAS"""

from typing import Optional, List, Dict, Any
from pathlib import Path
import numpy as np

from ..models import DASData, DASFrame, DASMetadata
from ..events import EventBus, EventType, Event


class DataController:
    """Controlador de dados - gerencia carregamento e acesso"""
    
    def __init__(self):
        self.event_bus = EventBus()
        self._datasets: Dict[str, DASData] = {}
        self._active_dataset: Optional[str] = None
    
    def load_file(self, filepath: str, dataset_id: Optional[str] = None) -> str:
        from ..services import DataLoaderService
        
        loader = DataLoaderService()
        data = loader.load(filepath)
        
        if dataset_id is None:
            import uuid
            dataset_id = f"dataset_{uuid.uuid4().hex[:8]}"
        
        self._datasets[dataset_id] = data
        self._active_dataset = dataset_id
        
        self.event_bus.publish(Event(
            EventType.RAW_DATA_ARRIVED,
            {"dataset_id": dataset_id, "filepath": filepath, "frames": data.num_frames},
            source="data_controller"
        ))
        
        return dataset_id
    
    def get_dataset(self, dataset_id: Optional[str] = None) -> DASData:
        id_ = dataset_id or self._active_dataset
        if id_ is None or id_ not in self._datasets:
            raise KeyError(f"Dataset nao encontrado: {id_}")
        return self._datasets[id_]
    
    def list_datasets(self) -> List[str]:
        return list(self._datasets.keys())
    
    def get_channel_data(self, channel: int, dataset_id: Optional[str] = None) -> np.ndarray:
        data = self.get_dataset(dataset_id)
        return data.get_channel(channel)
    
    def get_statistics(self, dataset_id: Optional[str] = None) -> Dict[str, Any]:
        data = self.get_dataset(dataset_id)
        return data.get_statistics()
    
    def remove_dataset(self, dataset_id: str) -> None:
        if dataset_id in self._datasets:
            del self._datasets[dataset_id]
            if self._active_dataset == dataset_id:
                self._active_dataset = None
    
    def clear(self) -> None:
        self._datasets.clear()
        self._active_dataset = None
