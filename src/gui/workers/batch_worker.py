"""
Worker de processamento em lote (batch) de arquivos DFOS.
"""

from __future__ import annotations

import traceback
from pathlib import Path
from typing import Any, Callable

import numpy as np
from PySide6.QtCore import QObject, Signal

from src.gui.data_loader import load_patch
from src.gui.workers.processing_worker import ProcessingWorker
from src.io.alakoro_spool import AlakoroPatch


class BatchWorker(QObject):
    """Processa múltiplos arquivos com o mesmo pipeline."""

    file_started = Signal(str)          # path do arquivo atual
    file_finished = Signal(str, object)  # path, resultado
    file_error = Signal(str, str)       # path, mensagem
    progress_percent = Signal(int)
    finished = Signal()

    def __init__(
        self,
        files: list[str],
        pipeline: list[dict],
        output_dir: str,
        export_format: str = "nc",
    ):
        super().__init__()
        self.files = files
        self.pipeline = pipeline
        self.output_dir = Path(output_dir)
        self.export_format = export_format.lower().lstrip(".")
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        total = len(self.files)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        for i, path in enumerate(self.files):
            if self._cancelled:
                break

            self.progress_percent.emit(int(100 * i / total))
            self.file_started.emit(path)

            try:
                patch = load_patch(path)
                if patch is None:
                    raise ValueError("Não foi possível carregar o arquivo")

                result = self._apply_pipeline(patch)
                out_path = self._export(result, path)
                self.file_finished.emit(path, str(out_path))
            except Exception as exc:
                tb = traceback.format_exc()
                self.file_error.emit(path, f"{exc}\n{tb}")

        self.progress_percent.emit(100)
        self.finished.emit()

    def _apply_pipeline(self, patch: AlakoroPatch) -> Any:
        current = patch
        for step in self.pipeline:
            action = step.get("action", "")
            kwargs = step.get("kwargs", {})
            worker = ProcessingWorker(current, action, kwargs)
            result = worker._process()
            if isinstance(result, AlakoroPatch):
                current = result
            elif isinstance(result, np.ndarray):
                # Converte array de volta para patch preservando metadados
                current = AlakoroPatch(
                    current.patch.new(data=result),
                    current.well_id,
                    current.modality,
                    current.source_path,
                )
            elif isinstance(result, dict) and "temperature_corrected" in result:
                current = AlakoroPatch(
                    current.patch.new(data=result["temperature_corrected"]),
                    current.well_id,
                    current.modality,
                    current.source_path,
                )
            else:
                raise ValueError(f"Resultado não suportado para batch: {type(result)}")
        return current

    def _export(self, patch: AlakoroPatch, source_path: str) -> Path:
        stem = Path(source_path).stem
        out_path = self.output_dir / f"{stem}_processed.{self.export_format}"

        if self.export_format == "nc":
            import xarray as xr
            xr.DataArray(patch.data, dims=("time", "channel")).to_netcdf(out_path)
        elif self.export_format == "npy":
            np.save(out_path, patch.data)
        elif self.export_format == "csv":
            np.savetxt(out_path, patch.data, delimiter=",")
        elif self.export_format in ("png", "jpg"):
            import matplotlib.pyplot as plt
            plt.imsave(out_path, patch.data.T, cmap="RdBu_r")
        else:
            np.save(out_path, patch.data)

        return out_path
