"""Pipeline Controller - Orquestrador do processamento"""

from typing import Optional, List, Callable, Dict, Any
from pathlib import Path
import time
import numpy as np

from ..models import DASData, DASFrame, ProcessingConfig, PipelineConfig
from ..events import EventBus, EventType, Event, EventPriority
from ..services import ProcessingService, DetectionService, StreamingService


class PipelineController:
    """Controlador principal do pipeline de processamento"""
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.event_bus = EventBus()
        
        self.processing_service = ProcessingService(self.config.processing)
        self.detection_service = DetectionService(self.config.processing)
        self.streaming_service: Optional[StreamingService] = None
        
        self._initialized = False
        self._running = False
        self._current_data: Optional[DASData] = None
        self._pipeline_metrics: Dict[str, Any] = {}
        
        self.on_stage_complete: Optional[Callable[[str, Any], None]] = None
        self.on_pipeline_complete: Optional[Callable[[DASData], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
    
    def initialize(self) -> "PipelineController":
        try:
            self.event_bus.publish(Event(
                EventType.PIPELINE_INITIALIZED,
                {"config": self.config.dict()},
                EventPriority.HIGH,
                source="pipeline_controller"
            ))
            
            if self.config.enable_streaming:
                self.streaming_service = StreamingService(
                    buffer_size=self.config.stream_buffer_size
                )
                self.streaming_service.on_frame = self._on_stream_frame
            
            self._subscribe_events()
            self._initialized = True
            
            return self
            
        except Exception as e:
            self._handle_error(e)
            raise
    
    def configure(self, config: PipelineConfig) -> "PipelineController":
        self.config = config
        self.processing_service.update_config(config.processing)
        self.detection_service.update_config(config.processing)
        
        self.event_bus.publish(Event(
            EventType.PIPELINE_CONFIGURED,
            {"config": config.dict()},
            EventPriority.NORMAL,
            source="pipeline_controller"
        ))
        
        return self
    
    def run(self, input_path: str) -> DASData:
        if not self._initialized:
            self.initialize()
        
        self._running = True
        start_time = time.time()
        
        try:
            self.event_bus.publish(Event(
                EventType.PROCESSING_STARTED,
                {"input": input_path},
                EventPriority.HIGH,
                source="pipeline_controller"
            ))
            
            raw_data = self._load_data(input_path)
            self._current_data = raw_data
            
            result = self._execute_stages(raw_data)
            
            elapsed = time.time() - start_time
            self._pipeline_metrics = {
                "total_time": elapsed,
                "input_path": input_path,
                "num_frames": result.num_frames,
                "num_events": len(result.metadata.custom_fields.get("events", [])) if result.metadata else 0,
            }
            
            self.event_bus.publish(Event(
                EventType.PROCESSING_COMPLETED,
                self._pipeline_metrics,
                EventPriority.HIGH,
                source="pipeline_controller"
            ))
            
            if self.on_pipeline_complete:
                self.on_pipeline_complete(result)
            
            self._running = False
            return result
            
        except Exception as e:
            self._handle_error(e)
            raise
    
    def run_stream(self, source: str) -> None:
        if not self.streaming_service:
            raise RuntimeError("Streaming nao habilitado na configuracao")
        
        self.streaming_service.start(source)
        self._running = True
    
    def stop(self) -> None:
        self._running = False
        if self.streaming_service:
            self.streaming_service.stop()
        
        self.event_bus.publish(Event(
            EventType.STREAM_STOPPED,
            None,
            EventPriority.HIGH,
            source="pipeline_controller"
        ))
    
    def _execute_stages(self, data: DASData) -> DASData:
        current_data = data
        
        for stage in self.config.stages:
            if not self._running:
                break
            
            stage_start = time.time()
            
            if stage == "decode":
                pass
            elif stage == "calibrate":
                current_data = self._stage_calibrate(current_data)
            elif stage == "filter":
                current_data = self._stage_filter(current_data)
            elif stage == "detect":
                current_data = self._stage_detect(current_data)
            elif stage == "classify":
                current_data = self._stage_classify(current_data)
            elif stage == "export":
                current_data = self._stage_export(current_data)
            
            stage_time = time.time() - stage_start
            
            if self.on_stage_complete:
                self.on_stage_complete(stage, {
                    "time": stage_time,
                    "frames": current_data.num_frames
                })
            
            self.event_bus.publish(Event(
                EventType.PIPELINE_EXECUTED,
                {"stage": stage, "time": stage_time},
                EventPriority.NORMAL,
                source="pipeline_controller"
            ))
        
        return current_data
    
    def _stage_calibrate(self, data: DASData) -> DASData:
        if not self.config.processing.apply_calibration:
            return data
        
        for frame in data.frames:
            calibrated = self.processing_service.calibrate(frame)
            frame.data = calibrated.data
        
        return data
    
    def _stage_filter(self, data: DASData) -> DASData:
        for frame in data.frames:
            filtered = self.processing_service.filter_signal(frame)
            frame.data = filtered
        
        self.event_bus.publish(Event(
            EventType.DATA_FILTERED,
            {"frames": data.num_frames},
            EventPriority.NORMAL,
            source="pipeline_controller"
        ))
        
        return data
    
    def _stage_detect(self, data: DASData) -> DASData:
        all_events = []
        
        for i, frame in enumerate(data.frames):
            events = self.detection_service.detect_events(frame)
            all_events.extend(events)
        
        if data.metadata is None:
            from ..models import DASMetadata
            data.metadata = DASMetadata()
        
        data.metadata.custom_fields["events"] = [e.to_dict() for e in all_events]
        data.metadata.custom_fields["num_events"] = len(all_events)
        
        return data
    
    def _stage_classify(self, data: DASData) -> DASData:
        if not self.config.processing.classify_events:
            return data
        
        events_data = data.metadata.custom_fields.get("events", [])
        for event_dict in events_data:
            event_dict["classification"] = self.detection_service.classify_event_dict(event_dict)
        
        return data
    
    def _stage_export(self, data: DASData) -> DASData:
        if self.config.output_path:
            output_path = Path(self.config.output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if self.config.output_format == "hdf5":
                self._export_hdf5(data, output_path)
            elif self.config.output_format == "numpy":
                self._export_numpy(data, output_path)
        
        return data
    
    def _load_data(self, input_path: str) -> DASData:
        from ..services import DataLoaderService
        loader = DataLoaderService()
        return loader.load(input_path)
    
    def _export_hdf5(self, data: DASData, path: Path) -> None:
        try:
            import h5py
            with h5py.File(path.with_suffix(".h5"), "w") as f:
                f.create_dataset("data", data=data.get_concatenated_data())
                f.attrs["num_frames"] = data.num_frames
                if data.metadata:
                    f.attrs["temporal_sampling"] = data.metadata.temporal_sampling
        except ImportError:
            np.save(path.with_suffix(".npy"), data.get_concatenated_data())
    
    def _export_numpy(self, data: DASData, path: Path) -> None:
        np.save(path.with_suffix(".npy"), data.get_concatenated_data())
    
    def _on_stream_frame(self, frame: DASFrame) -> None:
        self.event_bus.publish(Event(
            EventType.FRAME_RECEIVED,
            {"frame_number": frame.frame_number},
            EventPriority.HIGH,
            source="streaming"
        ))
        
        if self._current_data is None:
            self._current_data = DASData()
        
        self._current_data.add_frame(frame)
    
    def _subscribe_events(self) -> None:
        self.event_bus.subscribe(EventType.ERROR, self._on_error_event)
    
    def _on_error_event(self, event: Event) -> None:
        if isinstance(event.data, dict) and "error" in event.data:
            print(f"[Pipeline Error] {event.data['error']}")
    
    def _handle_error(self, error: Exception) -> None:
        self._running = False
        
        self.event_bus.publish(Event(
            EventType.PROCESSING_ERROR,
            {"error": str(error), "type": type(error).__name__},
            EventPriority.CRITICAL,
            source="pipeline_controller"
        ))
        
        if self.on_error:
            self.on_error(error)
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def metrics(self) -> Dict[str, Any]:
        return self._pipeline_metrics.copy()
