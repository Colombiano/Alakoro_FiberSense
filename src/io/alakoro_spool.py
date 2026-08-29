"""
Alakoro FiberSense — AlakoroSpool e AlakoroPatch

Interfaces compatíveis com DASCore para integração nativa ao ecossistema
DASDAE. Usamos DASCore Patch/Spool como backend, mas adicionamos
metadados Alakoro e métodos específicos do domínio de petróleo.
"""

from __future__ import annotations

import warnings
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Any, Callable, Iterator, List, Optional, Sequence, Union

import numpy as np

import dascore as dc
from dascore import Patch
from dascore.core.attrs import PatchAttrs


class AlakoroPatch:
    """
    Wrapper compatível com DASCore Patch.

    Mantém um Patch DASCore interno e expõe métodos comuns
    (decimate, detrend, pass_filter, taper, select, convert_units)
    mais metadados do domínio Alakoro.
    """

    def __init__(self, patch: Patch, well_id: Optional[str] = None,
                 modality: str = "das"):
        self._patch = patch
        self.well_id = well_id
        self.modality = modality.lower()

    # ─── Propriedades de acesso ───

    @property
    def patch(self) -> Patch:
        """Acesso ao Patch DASCore subjacente."""
        return self._patch

    @property
    def data(self) -> np.ndarray:
        return np.asarray(self._patch.data)

    @property
    def coords(self):
        return self._patch.coords

    @property
    def attrs(self) -> PatchAttrs:
        return self._patch.attrs

    @property
    def shape(self) -> tuple:
        return self.data.shape

    @property
    def dims(self) -> tuple:
        return self._patch.dims

    # ─── Métodos compatíveis com DASCore Patch ───

    def decimate(self, factor: int, dimension: str = "time") -> "AlakoroPatch":
        """Reduz a amostragem ao longo de uma dimensão."""
        # DASCore espera kwargs nomeados, e.g. time=factor
        new_patch = self._patch.decimate(**{dimension: factor})
        return AlakoroPatch(new_patch, self.well_id, self.modality)

    def detrend(self, dimension: str = "time", type_: str = "linear") -> "AlakoroPatch":
        """Remove tendência linear ou constante."""
        new_patch = self._patch.detrend(dim=dimension, type=type_)
        return AlakoroPatch(new_patch, self.well_id, self.modality)

    def pass_filter(self, corner_hz: tuple, dimension: str = "time") -> "AlakoroPatch":
        """Filtro passa-banda (tupla com freq baixa e alta)."""
        new_patch = self._patch.pass_filter(**{dimension: (corner_hz[0], corner_hz[1])})
        return AlakoroPatch(new_patch, self.well_id, self.modality)

    def taper(self, dimension: str = "time", type_: str = "cosine",
              alpha: float = 0.0) -> "AlakoroPatch":
        """Aplica janela de taper."""
        new_patch = self._patch.taper(**{dimension: alpha})
        return AlakoroPatch(new_patch, self.well_id, self.modality)

    def select(self, **kwargs) -> "AlakoroPatch":
        """Seleciona sub-região do patch."""
        new_patch = self._patch.select(**kwargs)
        return AlakoroPatch(new_patch, self.well_id, self.modality)

    def convert_units(self, units: str, dimension: Optional[str] = None) -> "AlakoroPatch":
        """Converte unidades dos dados ou de uma coordenada."""
        new_patch = self._patch.convert_units_to(units, dimension=dimension)
        return AlakoroPatch(new_patch, self.well_id, self.modality)

    # ─── Escape hatches ───

    def to_numpy(self) -> np.ndarray:
        return self.data

    def to_dataframe(self):
        """Converte para pandas DataFrame (time x distance)."""
        import pandas as pd
        time = np.asarray(self.coords.get_array("time"))
        distance = np.asarray(self.coords.get_array("distance"))
        return pd.DataFrame(
            self.data,
            index=pd.Index(time, name="time"),
            columns=pd.Index(distance, name="distance"),
        )

    def to_xarray(self):
        """Converte para xarray DataArray."""
        import xarray as xr
        time = np.asarray(self.coords.get_array("time"))
        distance = np.asarray(self.coords.get_array("distance"))
        return xr.DataArray(
            self.data,
            dims=("time", "distance"),
            coords={"time": time, "distance": distance},
            attrs=dict(self.attrs),
        )

    def to_obspy(self):
        """Converte para Stream Obspy (uma trace por canal)."""
        from obspy.core import Stream, Trace
        from obspy.core import UTCDateTime

        time = np.asarray(self.coords.get_array("time"))
        distance = np.asarray(self.coords.get_array("distance"))
        dt_s = float(self.attrs.time_step / np.timedelta64(1, "s"))
        start_time = UTCDateTime(str(time[0]))

        stream = Stream()
        for i, dist in enumerate(distance):
            trace = Trace(data=self.data[:, i].astype(np.float32))
            trace.stats.starttime = start_time
            trace.stats.delta = dt_s
            trace.stats.station = f"D{dist:.1f}"
            stream.append(trace)
        return stream

    def __repr__(self) -> str:
        return f"AlakoroPatch(shape={self.shape}, modality={self.modality}, well_id={self.well_id})"


class AlakoroSpool:
    """
    Wrapper compatível com DASCore Spool.

    Permite iterar, indexar, selecionar e aplicar operações map/chunk
    sobre uma sequência de AlakoroPatch.
    """

    def __init__(self, patches: Sequence[AlakoroPatch]):
        self._patches = list(patches)

    @classmethod
    def from_dascore(cls, spool: Spool, well_id: Optional[str] = None,
                     modality: str = "das") -> "AlakoroSpool":
        """Cria AlakoroSpool a partir de um Spool DASCore."""
        patches = [AlakoroPatch(p, well_id, modality) for p in spool]
        return cls(patches)

    @classmethod
    def from_directory(cls, path: str, modality: str = "das") -> "AlakoroSpool":
        """Carrega arquivos de um diretório via DASCore."""
        spool = dc.spool(path)
        return cls.from_dascore(spool, modality=modality)

    @classmethod
    def from_patch(cls, patch: AlakoroPatch) -> "AlakoroSpool":
        return cls([patch])

    # ─── Métodos compatíveis com DASCore Spool ───

    def __len__(self) -> int:
        return len(self._patches)

    def __iter__(self) -> Iterator[AlakoroPatch]:
        return iter(self._patches)

    def __getitem__(self, index: int) -> AlakoroPatch:
        return self._patches[index]

    def __repr__(self) -> str:
        return f"AlakoroSpool(n_patches={len(self._patches)})"

    def select(self, **kwargs) -> "AlakoroSpool":
        """Seleciona sub-região em cada patch."""
        return AlakoroSpool([p.select(**kwargs) for p in self._patches])

    def chunk(self, time: Optional[float] = None,
              overlap: float = 0.0,
              **kwargs) -> "AlakoroSpool":
        """
        Divide cada patch em janelas temporais.

        Args:
            time: duração da janela em segundos
            overlap: sobreposição entre janelas em segundos
        """
        if time is None:
            return self

        new_patches: List[AlakoroPatch] = []
        for patch in self._patches:
            pts = _chunk_patch(patch.patch, time, overlap)
            new_patches.extend([AlakoroPatch(p, patch.well_id, patch.modality) for p in pts])
        return AlakoroSpool(new_patches)

    def map(self, func: Callable[[AlakoroPatch], AlakoroPatch],
            parallel: bool = False,
            max_workers: Optional[int] = None,
            use_processes: bool = False) -> "AlakoroSpool":
        """
        Aplica uma função a cada patch.

        Args:
            func: função que recebe e retorna AlakoroPatch
            parallel: se True, usa ProcessPoolExecutor/ThreadPoolExecutor
            max_workers: número de workers
            use_processes: se True, usa processos; senão threads
        """
        if not parallel:
            return AlakoroSpool([func(p) for p in self._patches])

        Executor = ProcessPoolExecutor if use_processes else ThreadPoolExecutor
        with Executor(max_workers=max_workers) as executor:
            results = list(executor.map(func, self._patches))
        return AlakoroSpool(results)

    def update(self, new_patches: Sequence[AlakoroPatch]) -> "AlakoroSpool":
        """Retorna um novo spool concatenando novos patches."""
        return AlakoroSpool(list(self._patches) + list(new_patches))

    def to_dascore(self) -> Spool:
        """Retorna um Spool DASCore puro."""
        return dc.spool([p.patch for p in self._patches])

    def get_contents(self) -> dict:
        """Resumo do conteúdo do spool."""
        return {
            "n_patches": len(self._patches),
            "modalities": list(set(p.modality for p in self._patches)),
            "well_ids": list(set(p.well_id for p in self._patches if p.well_id)),
            "total_samples": sum(p.shape[0] for p in self._patches),
            "n_channels": self._patches[0].shape[1] if self._patches else 0,
        }


def _chunk_patch(patch: Patch, window_s: float, overlap_s: float) -> List[Patch]:
    """Divide um Patch DASCore em janelas temporais (por amostras)."""
    n_t = patch.data.shape[0]
    if n_t < 2:
        return [patch]

    # Aqui window_s é interpretado como número de amostras por chunk
    window = max(int(window_s), 1)
    overlap = max(int(overlap_s), 0)
    step = max(window - overlap, 1)

    chunks = []
    start = 0
    while start < n_t:
        end = min(start + window, n_t)
        try:
            sub = patch.select(time=(start, end), samples=True)
            chunks.append(sub)
        except Exception as exc:
            warnings.warn(f"chunk select failed: {exc}")
            break
        start += step

    return chunks if chunks else [patch]
