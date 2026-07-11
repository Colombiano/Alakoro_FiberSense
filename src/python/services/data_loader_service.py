"""Data Loader Service - Carregamento de dados DAS"""

from typing import Optional, Union
from pathlib import Path
import numpy as np

from ..models import DASData, DASFrame, DASMetadata


class DataLoaderService:
    """Servico de carregamento de dados DAS"""
    
    SUPPORTED_FORMATS = {
        ".h5": "hdf5",
        ".hdf5": "hdf5",
        ".tdms": "tdms",
        ".npy": "numpy",
        ".npz": "numpy",
        ".bin": "raw_binary",
        ".raw": "raw_binary",
        ".csv": "csv",
    }
    
    def load(self, filepath: str) -> DASData:
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"Arquivo nao encontrado: {filepath}")
        
        suffix = path.suffix.lower()
        format_type = self.SUPPORTED_FORMATS.get(suffix, "unknown")
        
        if format_type == "hdf5":
            return self._load_hdf5(filepath)
        elif format_type == "numpy":
            return self._load_numpy(filepath)
        elif format_type == "raw_binary":
            return self._load_raw_binary(filepath)
        elif format_type == "csv":
            return self._load_csv(filepath)
        else:
            return self._load_generic(filepath)
    
    def _load_hdf5(self, filepath: str) -> DASData:
        try:
            import h5py
            
            with h5py.File(filepath, "r") as f:
                data = DASData()
                
                if "data" in f:
                    raw_data = f["data"][:]
                elif "raw" in f:
                    raw_data = f["raw"][:]
                else:
                    first_key = list(f.keys())[0]
                    raw_data = f[first_key][:]
                
                metadata = DASMetadata()
                for attr_name in ["gauge_length", "spatial_sampling", "temporal_sampling",
                                 "pulse_width", "num_channels", "num_samples"]:
                    if attr_name in f.attrs:
                        setattr(metadata, attr_name, f.attrs[attr_name])
                
                frame_size = metadata.num_samples if metadata.num_samples else raw_data.shape[0]
                for i in range(0, raw_data.shape[0], frame_size):
                    end = min(i + frame_size, raw_data.shape[0])
                    frame_data = raw_data[i:end]
                    
                    frame = DASFrame(
                        data=frame_data,
                        timestamp=i / metadata.temporal_sampling,
                        frame_number=i // frame_size,
                        metadata=metadata
                    )
                    data.add_frame(frame)
                
                return data
                
        except ImportError:
            print("h5py nao instalado - tentando fallback")
            return self._load_generic(filepath)
    
    def _load_numpy(self, filepath: str) -> DASData:
        path = Path(filepath)
        
        if path.suffix == ".npz":
            loaded = np.load(filepath)
            raw_data = loaded[list(loaded.keys())[0]]
        else:
            raw_data = np.load(filepath)
        
        return self._create_das_data(raw_data)
    
    def _load_raw_binary(self, filepath: str) -> DASData:
        try:
            import alakoro
            decoder = alakoro.DASDecoder(alakoro.DASFormat.ALAKORO_RAW)
            frames = decoder.decode_file(filepath)
            
            data = DASData()
            for frame in frames:
                das_frame = DASFrame(
                    data=frame.data,
                    timestamp=frame.timestamp,
                    frame_number=frame.frame_number,
                    metadata=DASMetadata(
                        gauge_length=frame.metadata.gauge_length,
                        spatial_sampling=frame.metadata.spatial_sampling,
                        temporal_sampling=frame.metadata.temporal_sampling,
                        num_channels=frame.metadata.num_channels,
                        num_samples=frame.metadata.num_samples,
                    )
                )
                data.add_frame(das_frame)
            
            return data
            
        except ImportError:
            raw_data = np.fromfile(filepath, dtype=np.float64)
            if len(raw_data) >= 2:
                num_samples = int(raw_data[0])
                num_channels = int(raw_data[1])
                data_values = raw_data[2:]
                reshaped = data_values[:num_samples * num_channels].reshape(num_samples, num_channels)
                return self._create_das_data(reshaped)
            return self._create_das_data(raw_data)
    
    def _load_csv(self, filepath: str) -> DASData:
        raw_data = np.loadtxt(filepath, delimiter=",")
        return self._create_das_data(raw_data)
    
    def _load_generic(self, filepath: str) -> DASData:
        try:
            raw_data = np.load(filepath, allow_pickle=True)
            if isinstance(raw_data, np.ndarray):
                return self._create_das_data(raw_data)
        except:
            pass
        
        raise ValueError(f"Formato de arquivo nao suportado: {filepath}")
    
    def _create_das_data(self, raw_data: np.ndarray) -> DASData:
        data = DASData()
        
        if len(raw_data.shape) == 1:
            raw_data = raw_data.reshape(-1, 1)
        
        metadata = DASMetadata(
            num_channels=raw_data.shape[1],
            num_samples=raw_data.shape[0],
        )
        
        frame = DASFrame(
            data=raw_data,
            timestamp=0.0,
            frame_number=0,
            metadata=metadata
        )
        data.add_frame(frame)
        
        return data
    
    def get_supported_formats(self) -> list:
        return list(self.SUPPORTED_FORMATS.keys())
