"""Configuracoes do sistema"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ProcessingConfig(BaseModel):
    """Configuracoes de processamento de sinais"""
    
    apply_calibration: bool = Field(default=True)
    compensate_attenuation: bool = Field(default=True)
    attenuation_coefficient: float = Field(default=0.2)
    
    filter_type: str = Field(default="bandpass")
    low_cutoff: float = Field(default=1.0)
    high_cutoff: float = Field(default=500.0)
    filter_order: int = Field(default=4)
    
    detection_threshold: float = Field(default=10.0)
    min_event_duration_ms: float = Field(default=10.0)
    max_event_duration_ms: float = Field(default=5000.0)
    min_channels: int = Field(default=1)
    merge_gap_ms: float = Field(default=50.0)
    
    stft_window_size: int = Field(default=256)
    stft_hop_size: int = Field(default=128)
    stft_window: str = Field(default="hann")
    
    classify_events: bool = Field(default=True)
    ml_model_path: Optional[str] = Field(default=None)
    
    quality_threshold: float = Field(default=0.5)
    detect_dead_channels: bool = Field(default=True)
    dead_channel_threshold: float = Field(default=1e-6)


class PipelineConfig(BaseModel):
    """Configuracao do pipeline de processamento"""
    
    name: str = Field(default="default_pipeline")
    description: str = Field(default="Pipeline padrao de processamento DAS")
    
    stages: List[str] = Field(default=[
        "decode",
        "calibrate",
        "filter",
        "detect",
        "classify",
        "export"
    ])
    
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    
    enable_streaming: bool = Field(default=False)
    stream_buffer_size: int = Field(default=100)
    
    output_format: str = Field(default="hdf5")
    output_path: Optional[str] = Field(default=None)
    save_intermediate: bool = Field(default=False)
    
    num_workers: int = Field(default=4)
    use_gpu: bool = Field(default=False)
    batch_size: int = Field(default=10)
    
    log_level: str = Field(default="INFO")
    log_file: Optional[str] = Field(default=None)
