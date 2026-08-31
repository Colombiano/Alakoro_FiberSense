"""
Worker de processamento em background para não travar a GUI Qt.
"""

from __future__ import annotations

import hashlib
import json
import traceback
from typing import Any, Callable

import numpy as np
from PySide6.QtCore import QObject, Signal

from src.io.alakoro_spool import AlakoroPatch


class ProcessingWorker(QObject):
    """Executa processadores em thread separada com cache simples."""

    finished = Signal(object)   # resultado: AlakoroPatch ou np.ndarray
    error = Signal(str)
    progress = Signal(str)
    progress_percent = Signal(int)

    # Cache estático: {cache_key: result}
    _cache: dict[str, Any] = {}
    _max_cache_size = 20

    def __init__(self, patch: AlakoroPatch, action: str, kwargs: dict):
        super().__init__()
        self.patch = patch
        self.action = action
        self.kwargs = kwargs

    def _cache_key(self) -> str:
        """Gera chave de cache baseada nos dados, ação e parâmetros."""
        data = self.patch.data
        # Hash rápido baseado em shape, soma e amostras das bordas
        head = data.flat[:1024].tobytes()
        tail = data.flat[-1024:].tobytes()
        shape_bytes = str(data.shape).encode()
        sum_bytes = str(data.sum()).encode()
        data_hash = hashlib.md5(head + tail + shape_bytes + sum_bytes).hexdigest()
        params = json.dumps(self.kwargs, sort_keys=True, default=str)
        return f"{data_hash}:{self.action}:{params}"

    def run(self):
        try:
            self.progress_percent.emit(0)
            key = self._cache_key()
            if key in self._cache:
                self.progress.emit(f"Usando cache / Using cache: {self.action}")
                self.progress_percent.emit(100)
                self.finished.emit(self._cache[key])
                return

            self.progress.emit(f"Running {self.action}...")
            result = self._process()

            # Limita tamanho do cache
            if len(self._cache) >= self._max_cache_size:
                self._cache.pop(next(iter(self._cache)))
            self._cache[key] = result

            self.progress_percent.emit(100)
            self.finished.emit(result)
        except Exception as exc:
            tb = traceback.format_exc()
            self.error.emit(f"Error in {self.action}: {exc}\n{tb}")

    def _emit_progress(self, value: int, message: str = ""):
        self.progress_percent.emit(max(0, min(100, value)))
        if message:
            self.progress.emit(message)

    def _process(self) -> Any:
        from src.processing import advanced_processors as ap
        from src.processing.dts_processor import DTSThermalProcessor

        action = self.action
        patch = self.patch
        kwargs = self.kwargs

        dispatch: dict[str, Callable] = {
            "butterworth_lowpass": ap.butterworth_lowpass,
            "butterworth_highpass": ap.butterworth_highpass,
            "butterworth_bandpass": ap.butterworth_bandpass,
            "detrend": lambda p, **kw: AlakoroPatch(
                p.patch.detrend(dim="time", type="linear"), p.well_id, p.modality
            ),
            "demean": lambda p, **kw: AlakoroPatch(
                p.patch.detrend(dim="time", type="constant"), p.well_id, p.modality
            ),
            "taper": lambda p, **kw: p.taper(dimension="time", alpha=0.05),
            "median_filter_1d": ap.median_filter_1d,
            "svd_denoise": ap.svd_denoise,
            "sta_lta": ap.sta_lta,
            "hilbert_envelope": ap.hilbert_envelope,
            "psd": ap.psd,
            "thermal_gradient": ap.thermal_gradient,
            "geothermal_baseline_correction": ap.geothermal_baseline_correction,
            "thermal_anomaly_detection": ap.thermal_anomaly_detection,
            "spatial_median_filter": ap.spatial_median_filter,
        }

        if action == "dts_pipeline":
            self._emit_progress(10, "Initializing DTS pipeline...")
            proc = DTSThermalProcessor(
                depth_step_m=kwargs.get("depth_step_m", 1.0),
                surface_temp=kwargs.get("surface_temp", 20.0),
                geothermal_gradient=kwargs.get("gradient", 0.03),
                spatial_median_window=kwargs.get("window_size", 5),
                anomaly_threshold_sigma=kwargs.get("threshold_sigma", 3.0),
                use_cpp_backend=True,
            )
            self._emit_progress(40, "Processing thermal data...")
            result = proc.process(patch.data)
            self._emit_progress(90, "Finalizing...")
            return result

        if action in dispatch:
            self._emit_progress(30, f"Applying {action}...")
            result = dispatch[action](patch, **kwargs)
            self._emit_progress(90, "Finalizing...")
            return result

        raise ValueError(f"Unknown action: {action}")
