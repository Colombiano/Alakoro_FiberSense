"""
Worker de processamento em background para não travar a GUI Qt.
"""

from __future__ import annotations

import traceback
from typing import Any, Callable

import numpy as np
from PySide6.QtCore import QObject, Signal

from src.io.alakoro_spool import AlakoroPatch


class ProcessingWorker(QObject):
    """Executa processadores em thread separada."""

    finished = Signal(object)   # resultado: AlakoroPatch ou np.ndarray
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, patch: AlakoroPatch, action: str, kwargs: dict):
        super().__init__()
        self.patch = patch
        self.action = action
        self.kwargs = kwargs

    def run(self):
        try:
            self.progress.emit(f"Running {self.action}...")
            result = self._process()
            self.finished.emit(result)
        except Exception as exc:
            tb = traceback.format_exc()
            self.error.emit(f"Error in {self.action}: {exc}\n{tb}")

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
            proc = DTSThermalProcessor(
                depth_step_m=kwargs.get("depth_step_m", 1.0),
                surface_temp=kwargs.get("surface_temp", 20.0),
                geothermal_gradient=kwargs.get("gradient", 0.03),
                spatial_median_window=kwargs.get("window_size", 5),
                anomaly_threshold_sigma=kwargs.get("threshold_sigma", 3.0),
                use_cpp_backend=True,
            )
            return proc.process(patch.data)

        if action in dispatch:
            return dispatch[action](patch, **kwargs)

        raise ValueError(f"Unknown action: {action}")
