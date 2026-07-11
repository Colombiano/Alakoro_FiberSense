#!/usr/bin/env python3
"""
Benchmark de performance do Alakoro FiberSense
"""

import time
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "python"))


def benchmark_fft():
    """Benchmark FFT"""
    print("\n[FFT]")
    sizes = [1000, 10000, 100000, 1000000]
    
    for size in sizes:
        signal = np.random.randn(size)
        
        # Python (numpy)
        start = time.time()
        _ = np.fft.fft(signal)
        py_time = (time.time() - start) * 1000
        
        print(f"  Size {size:>10}: NumPy={py_time:>8.2f}ms")


def benchmark_filtering():
    """Benchmark filtragem"""
    print("\n[Filtering]")
    
    from scipy import signal
    
    sizes = [1000, 10000, 100000]
    
    for size in sizes:
        data = np.random.randn(size)
        b, a = signal.butter(4, [0.1, 0.4], btype="band")
        
        start = time.time()
        _ = signal.filtfilt(b, a, data)
        elapsed = (time.time() - start) * 1000
        
        print(f"  Size {size:>10}: {elapsed:>8.2f}ms")


def benchmark_detection():
    """Benchmark deteccao"""
    print("\n[Event Detection]")
    
    sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "python"))
    from services import DetectionService
    from models import DASFrame, DASMetadata
    
    sizes = [(1000, 100), (5000, 500), (10000, 1000)]
    detector = DetectionService()
    
    for samples, channels in sizes:
        data = np.random.randn(samples, channels) * 0.01
        # Adiciona sinal
        for ch in range(40, 60):
            data[:, ch] += 0.5 * np.sin(2 * np.pi * 50 * np.arange(samples) / 1000)
        
        frame = DASFrame(
            data=data,
            timestamp=0.0,
            frame_number=0,
            metadata=DASMetadata(temporal_sampling=1000.0)
        )
        
        start = time.time()
        events = detector.detect_events(frame)
        elapsed = (time.time() - start) * 1000
        
        print(f"  {samples}x{channels}: {elapsed:>8.2f}ms ({len(events)} events)")


def benchmark_memory():
    """Benchmark uso de memoria"""
    print("\n[Memory Usage]")
    
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    
    sizes = [(1000, 100), (10000, 1000), (50000, 5000)]
    
    for samples, channels in sizes:
        mem_before = process.memory_info().rss / 1024 / 1024
        
        data = np.random.randn(samples, channels)
        
        mem_after = process.memory_info().rss / 1024 / 1024
        
        print(f"  {samples}x{channels}: "
              f"data={data.nbytes/1024/1024:.1f}MB, "
              f"process={mem_after-mem_before:.1f}MB")


def main():
    print("=" * 60)
    print("  ALAKORO FIBERSENSE - Benchmark")
    print("=" * 60)
    
    print(f"\nPython: {sys.version}")
    print(f"NumPy: {np.__version__}")
    
    try:
        import alakoro
        print(f"Alakoro C++: {alakoro.__version__}")
    except ImportError:
        print("Alakoro C++: Nao disponivel")
    
    benchmark_fft()
    benchmark_filtering()
    benchmark_detection()
    benchmark_memory()
    
    print("\n" + "=" * 60)
    print("  Benchmark completo!")
    print("=" * 60)


if __name__ == "__main__":
    main()
