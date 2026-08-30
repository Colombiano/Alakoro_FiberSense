"""
Alakoro FiberSense — Pipeline Híbrido DASCore + C++20

Permite encadear métodos nativos do DASCore com processadores avançados
C++20 do alakoro_core de forma fluente, sempre retornando AlakoroPatch.
"""

from __future__ import annotations

from typing import Any, List, Optional, Union

import numpy as np
from dascore import Patch

from src.io.alakoro_spool import AlakoroPatch, AlakoroSpool
from src.io.dasdae import DASDAEAdapter


class HybridPipeline:
    """
    Pipeline fluente que combina operações DASCore e processadores C++20.

    Exemplo:
        result = (
            HybridPipeline(patch)
            .dascore("detrend", dim="time", type="linear")
            .dascore("pass_filter", time=(0.5, 25.0))
            .cpp("median_filter_1d", window_size=5)
            .cpp("wavelet_denoise", scales=[1.0, 2.0, 4.0],
                 sample_rate_hz=1000.0, threshold=0.5)
            .to_patch()
        )
    """

    def __init__(
        self,
        data: Union[AlakoroPatch, Patch, np.ndarray],
        well_id: Optional[str] = None,
        modality: str = "das",
    ):
        """
        Args:
            data: AlakoroPatch, Patch DASCore ou array NumPy 2D (time, distance).
            well_id: identificador do poço.
            modality: modalidade dos dados (das, dts, dss).
        """
        self._well_id = well_id
        self._modality = modality.lower()
        self._patch = self._ensure_patch(data)
        self._history: List[str] = []

    def _ensure_patch(self, data: Union[AlakoroPatch, Patch, np.ndarray]) -> AlakoroPatch:
        """Garante que o dado interno seja AlakoroPatch."""
        if isinstance(data, AlakoroPatch):
            if self._well_id is None:
                self._well_id = data.well_id
            if data.modality:
                self._modality = data.modality
            return data

        if isinstance(data, Patch):
            modality = self._modality or (data.attrs.data_category or "das")
            return AlakoroPatch(data, well_id=self._well_id, modality=modality)

        if isinstance(data, np.ndarray):
            if data.ndim != 2:
                raise ValueError("HybridPipeline expects 2D NumPy array (time, distance)")
            patch = DASDAEAdapter.array_to_patch(data, modality=self._modality)
            return AlakoroPatch(patch, well_id=self._well_id, modality=self._modality)

        raise TypeError(
            f"HybridPipeline expects AlakoroPatch, dascore.Patch or np.ndarray, "
            f"got {type(data)}"
        )

    def dascore(self, method: str, *args: Any, **kwargs: Any) -> "HybridPipeline":
        """
        Aplica um método nativo do Patch DASCore.

        Args:
            method: nome do método do Patch (ex: 'detrend', 'pass_filter',
                    'decimate', 'taper', 'select', 'convert_units').
            *args, **kwargs: argumentos do método.
        """
        if not hasattr(self._patch.patch, method):
            raise AttributeError(
                f"dascore.Patch has no method '{method}'. "
                f"Available: detrend, pass_filter, decimate, taper, select, convert_units, ..."
            )

        try:
            new_patch = getattr(self._patch.patch, method)(*args, **kwargs)
        except Exception as exc:
            raise RuntimeError(f"DASCore method '{method}' failed: {exc}") from exc

        self._patch = AlakoroPatch(
            new_patch, well_id=self._patch.well_id, modality=self._patch.modality
        )
        self._history.append(f"dascore.{method}")
        return self

    def cpp(self, processor: str, *args: Any, **kwargs: Any) -> "HybridPipeline":
        """
        Aplica um processador avançado C++20 do alakoro_core.

        Args:
            processor: nome da função em src.processing.advanced_processors
                       (ex: 'median_filter_1d', 'butterworth_lowpass', 'psd', 'cwt').
            *args, **kwargs: argumentos do processador.
        """
        from src.processing import advanced_processors as adv

        if not hasattr(adv, processor):
            raise AttributeError(
                f"advanced_processors has no function '{processor}'. "
                f"See src.processing.advanced_processors.__all__ for available names."
            )

        func = getattr(adv, processor)
        try:
            result = func(self._patch, *args, **kwargs)
        except Exception as exc:
            raise RuntimeError(f"C++ processor '{processor}' failed: {exc}") from exc

        if isinstance(result, AlakoroPatch):
            self._patch = result
        elif isinstance(result, Patch):
            self._patch = AlakoroPatch(
                result, well_id=self._patch.well_id, modality=self._patch.modality
            )
        elif isinstance(result, np.ndarray):
            # Processadores que retornam arrays (psd, cwt, etc.) não podem ser
            # encadeados como patch. Guardamos o array e encerramos o pipeline.
            raise TypeError(
                f"Processor '{processor}' returns np.ndarray and cannot be chained "
                f"as a patch. Use .apply_array('{processor}', ...) to capture the output."
            )
        else:
            raise TypeError(
                f"Processor '{processor}' returned unexpected type {type(result)}"
            )

        self._history.append(f"cpp.{processor}")
        return self

    def apply_array(
        self, processor: str, *args: Any, **kwargs: Any
    ) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Executa um processador C++20 que retorna array(s) e retorna o resultado
        bruto, encerrando o pipeline.

        Útil para: psd, cwt, magnitude_spectrum, spectrogram, sta_lta,
        hilbert_envelope, teager_kaiser, cross_correlation_channels,
        coherence_channels, emd, eemd, nmf.
        """
        from src.processing import advanced_processors as adv

        if not hasattr(adv, processor):
            raise AttributeError(f"advanced_processors has no function '{processor}'")

        func = getattr(adv, processor)
        try:
            return func(self._patch, *args, **kwargs)
        except Exception as exc:
            raise RuntimeError(f"C++ processor '{processor}' failed: {exc}") from exc

    def to_patch(self) -> AlakoroPatch:
        """Retorna o AlakoroPatch resultante."""
        return self._patch

    def to_numpy(self) -> np.ndarray:
        """Retorna array NumPy 2D (time, distance)."""
        return self._patch.data

    def to_spool(self) -> AlakoroSpool:
        """Retorna AlakoroSpool contendo o patch atual."""
        return AlakoroSpool([self._patch])

    def clone(self) -> "HybridPipeline":
        """Cria uma cópia do pipeline no estado atual."""
        new = HybridPipeline(self._patch)
        new._history = list(self._history)
        return new

    @property
    def history(self) -> List[str]:
        """Lista de passos executados no pipeline."""
        return list(self._history)

    def __repr__(self) -> str:
        steps = " -> ".join(self._history) if self._history else "empty"
        return f"HybridPipeline(shape={self._patch.shape}, steps=[{steps}])"


__all__ = ["HybridPipeline"]
