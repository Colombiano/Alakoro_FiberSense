"""Modelo de dados DAS"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
import numpy as np
from pydantic import BaseModel, Field


class DASMetadata(BaseModel):
    """Metadados de aquisicao DAS"""
    gauge_length: float = Field(default=10.2, description="Comprimento da gauge em metros")
    spatial_sampling: float = Field(default=1.0, description="Amostragem espacial em m/canal")
    temporal_sampling: float = Field(default=1000.0, description="Taxa de amostragem temporal em Hz")
    pulse_width: float = Field(default=100.0, description="Largura do pulso em ns")
    num_channels: int = Field(default=1000, description="Numero de canais")
    num_samples: int = Field(default=10000, description="Numero de amostras temporais")
    start_distance: float = Field(default=0.0, description="Distancia inicial em metros")
    fiber_length: float = Field(default=1000.0, description="Comprimento da fibra em metros")
    unit: str = Field(default="strain_rate", description="Unidade dos dados")
    fiber_type: str = Field(default="SMF-28", description="Tipo da fibra")
    acquisition_time: Optional[datetime] = Field(default=None, description="Tempo de aquisicao")
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


@dataclass
class DASFrame:
    """Frame individual de dados DAS"""
    data: np.ndarray
    timestamp: float
    frame_number: int
    metadata: DASMetadata
    
    def __post_init__(self):
        if not isinstance(self.data, np.ndarray):
            self.data = np.array(self.data)
    
    @property
    def shape(self) -> tuple:
        return self.data.shape
    
    @property
    def num_channels(self) -> int:
        return self.data.shape[1] if len(self.data.shape) > 1 else 1
    
    @property
    def num_samples(self) -> int:
        return self.data.shape[0]


@dataclass
class DASData:
    """Container principal de dados DAS"""
    frames: List[DASFrame] = field(default_factory=list)
    metadata: Optional[DASMetadata] = None
    
    def add_frame(self, frame: DASFrame) -> None:
        """Adiciona um frame"""
        self.frames.append(frame)
        if self.metadata is None:
            self.metadata = frame.metadata
    
    def get_concatenated_data(self) -> np.ndarray:
        """Concatena todos os frames ao longo do tempo"""
        if not self.frames:
            return np.array([])
        return np.vstack([f.data for f in self.frames])
    
    def get_channel(self, channel_index: int) -> np.ndarray:
        """Extrai dados de um canal especifico"""
        if not self.frames:
            return np.array([])
        return np.concatenate([f.data[:, channel_index] for f in self.frames])
    
    @property
    def num_frames(self) -> int:
        return len(self.frames)
    
    @property
    def total_samples(self) -> int:
        return sum(f.num_samples for f in self.frames)
    
    @property
    def duration(self) -> float:
        """Duracao total em segundos"""
        if not self.frames or self.metadata is None:
            return 0.0
        return self.total_samples / self.metadata.temporal_sampling
    
    def get_statistics(self) -> Dict[str, Any]:
        """Calcula estatisticas dos dados"""
        if not self.frames:
            return {}
        
        all_data = self.get_concatenated_data()
        return {
            "mean": float(np.mean(all_data)),
            "std": float(np.std(all_data)),
            "min": float(np.min(all_data)),
            "max": float(np.max(all_data)),
            "rms": float(np.sqrt(np.mean(all_data ** 2))),
            "num_frames": self.num_frames,
            "duration_seconds": self.duration,
        }
