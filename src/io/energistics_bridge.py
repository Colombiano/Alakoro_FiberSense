"""
Alakoro FiberSense — Ponte Semantica Energistics (ProdML ↔ WITSML)

Este modulo implementa um mapeamento semantico profundo entre os padroes
Energistics ProdML e WITSML, permitindo:

- Representacao comum de aquisicoes DFOS via `SensingAcquisition`.
- Enriquecimento cruzado: ler ProdML e enriquecer com Well/Wellbore WITSML.
- Conversao bidirecional mantendo semantica de poco, wellbore, coordenadas,
  unidades e metadados de aquisicao.
- Cross-reference entre arquivos ProdML e WITSML por UUID/nome.

Conceitos alinhados:

    WITSML          ProdML                  SensingAcquisition
    ────────        ───────                 ──────────────────
    <well>          DASAcquisition.well     well.uid, well.name
    <wellbore>      DASAcquisition.wellbore wellbore.uid, wellbore.name
    <log>           DASAcquisition          data + modality + units
    logCurveInfo    DASMetadata             channels[] {mnemonic, unit}

Referencias:
- ProdML v2.2: http://www.energistics.org/energyml/data/prodmlv2
- WITSML v1.4.1.1: http://www.witsml.org/schemas/141
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import numpy as np
from dascore import Patch
from dascore.core.attrs import PatchAttrs

from .alakoro_spool import AlakoroPatch
from . import prodml, witsml


@dataclass
class WellReference:
    """Referencia semantica a um poco (Well) — comum a WITSML e ProdML."""
    uid: str
    name: str
    field: Optional[str] = None
    country: Optional[str] = None
    operator: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "name": self.name,
            "field": self.field,
            "country": self.country,
            "operator": self.operator,
        }

    @classmethod
    def from_witsml(cls, well: witsml.Well) -> "WellReference":
        return cls(
            uid=well.uid,
            name=well.name,
            field=well.field,
            country=well.country,
            operator=well.operator,
        )


@dataclass
class WellboreReference:
    """Referencia semantica a um wellbore — comum a WITSML e ProdML."""
    uid: str
    name: str
    well_uid: Optional[str] = None
    md_min: float = 0.0
    md_max: float = 0.0

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "name": self.name,
            "well_uid": self.well_uid,
            "md_min": self.md_min,
            "md_max": self.md_max,
        }

    @classmethod
    def from_witsml(cls, wellbore: witsml.Wellbore) -> "WellboreReference":
        return cls(
            uid=wellbore.uid,
            name=wellbore.name,
            well_uid=wellbore.well_uid,
            md_min=wellbore.md_min,
            md_max=wellbore.md_max,
        )


@dataclass
class ChannelInfo:
    """Descricao semantica de um canal de aquisicao."""
    mnemonic: str
    unit: str
    index: int = 0


@dataclass
class SensingAcquisition:
    """
    Representacao semantica comum de uma aquisicao DFOS (DAS/DTS/DSS).

    Desacopla os dados do formato XML, permitindo conversao entre ProdML,
    WITSML e outras representacoes futuras.
    """

    data: np.ndarray
    modality: str = "das"
    units: str = ""
    sampling_rate_hz: float = 1000.0
    spatial_resolution_m: float = 1.0
    gauge_length_m: float = 0.0
    start_time: Optional[datetime] = None
    well: Optional[WellReference] = None
    wellbore: Optional[WellboreReference] = None
    channels: List[ChannelInfo] = field(default_factory=list)
    source_format: Optional[str] = None
    source_path: Optional[str] = None

    def __post_init__(self):
        self.data = np.asarray(self.data)
        self.modality = self.modality.lower()
        if not self.channels and self.data.ndim == 2:
            n_c = self.data.shape[1]
            self.channels = [
                ChannelInfo(mnemonic=f"CH{i}", unit=self.units, index=i)
                for i in range(n_c)
            ]

    @property
    def shape(self) -> tuple:
        return tuple(self.data.shape)

    @property
    def n_times(self) -> int:
        return int(self.data.shape[0])

    @property
    def n_channels(self) -> int:
        return int(self.data.shape[1]) if self.data.ndim >= 2 else 1

    def to_alakoro_patch(self) -> AlakoroPatch:
        """Converte a aquisicao semantica em AlakoroPatch."""
        n_t = self.n_times
        n_c = self.n_channels
        dt_s = 1.0 / self.sampling_rate_hz if self.sampling_rate_hz > 0 else 1.0
        dx_m = self.spatial_resolution_m if self.spatial_resolution_m > 0 else 1.0

        patch = Patch(
            data=self.data,
            coords={
                "time": (np.arange(n_t) * dt_s * 1e9).astype("timedelta64[ns]"),
                "distance": np.arange(n_c) * dx_m,
            },
            dims=("time", "distance"),
            attrs=PatchAttrs(
                data_category=self.modality,
                data_units=self.units,
                time_step=np.timedelta64(int(dt_s * 1e9), "ns"),
                distance_step=dx_m,
            ),
        )
        out = AlakoroPatch(
            patch,
            well_id=self.well.uid if self.well else None,
            modality=self.modality,
        )
        out.source_path = self.source_path
        # Preserva gauge_length e spatial_resolution como extras se possivel
        try:
            out.attrs.gauge_length_m = self.gauge_length_m
            out.attrs.spatial_resolution_m = self.spatial_resolution_m
        except Exception:
            pass
        return out

    def to_dict(self) -> dict:
        return {
            "shape": self.shape,
            "modality": self.modality,
            "units": self.units,
            "sampling_rate_hz": self.sampling_rate_hz,
            "spatial_resolution_m": self.spatial_resolution_m,
            "gauge_length_m": self.gauge_length_m,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "well": self.well.to_dict() if self.well else None,
            "wellbore": self.wellbore.to_dict() if self.wellbore else None,
            "channels": [
                {"mnemonic": c.mnemonic, "unit": c.unit, "index": c.index}
                for c in self.channels
            ],
            "source_format": self.source_format,
            "source_path": self.source_path,
        }


def from_alakoro_patch(patch: AlakoroPatch) -> SensingAcquisition:
    """Cria SensingAcquisition a partir de AlakoroPatch."""
    attrs = patch.attrs
    dt_s = float(attrs.time_step / np.timedelta64(1, "s")) if attrs.time_step is not None else 1.0
    sampling_rate_hz = 1.0 / dt_s if dt_s > 0 else 1000.0
    spatial_resolution_m = float(getattr(attrs, "spatial_resolution_m", attrs.distance_step or 1.0))
    gauge_length_m = float(getattr(attrs, "gauge_length_m", 0.0))
    units = str(attrs.data_units) if attrs.data_units else ""

    n_c = patch.shape[1] if len(patch.shape) >= 2 else 1
    channels = [
        ChannelInfo(mnemonic=f"CH{i}", unit=units, index=i)
        for i in range(n_c)
    ]

    return SensingAcquisition(
        data=patch.data.copy(),
        modality=patch.modality,
        units=units,
        sampling_rate_hz=sampling_rate_hz,
        spatial_resolution_m=spatial_resolution_m,
        gauge_length_m=gauge_length_m,
        start_time=None,
        well=WellReference(uid=patch.well_id, name=patch.well_id) if patch.well_id else None,
        wellbore=WellboreReference(
            uid=patch.wellbore_id,
            name=patch.wellbore_id,
            well_uid=patch.well_id,
        ) if getattr(patch, "wellbore_id", None) else None,
        channels=channels,
        source_format="alakoro",
    )


def cross_reference(
    prodml_path: str | Path,
    witsml_well_path: Optional[str | Path] = None,
    witsml_wellbore_path: Optional[str | Path] = None,
) -> SensingAcquisition:
    """
    Le um arquivo ProdML e enriquece com metadados WITSML de well/wellbore.

    Se os arquivos WITSML forem fornecidos, valida o cruzamento de UUIDs/nomes
    e retorna uma `SensingAcquisition` unificada.
    """
    prodml_path = Path(prodml_path)
    patch = prodml.read(prodml_path)
    acquisition = from_alakoro_patch(patch)
    acquisition.source_format = "prodml"
    acquisition.source_path = str(prodml_path)

    # Tenta enriquecer well
    if witsml_well_path is not None:
        well = witsml.read_well(witsml_well_path)
        acquisition.well = WellReference.from_witsml(well)
        # Se o patch ja tinha well_id, valida consistencia
        if patch.well_id and patch.well_id != well.uid:
            # Aceita tambem por nome
            if patch.well_id != well.name:
                raise ValueError(
                    f"Cross-reference mismatch: ProdML well_id={patch.well_id!r} "
                    f"does not match WITSML well uid={well.uid!r} / name={well.name!r}"
                )

    # Tenta enriquecer wellbore
    if witsml_wellbore_path is not None:
        wellbore = witsml.read_wellbore(witsml_wellbore_path)
        acquisition.wellbore = WellboreReference.from_witsml(wellbore)
        # Valida ligacao wellbore -> well
        if acquisition.well and wellbore.well_uid:
            if wellbore.well_uid != acquisition.well.uid and \
               wellbore.well_uid != acquisition.well.name:
                raise ValueError(
                    f"Cross-reference mismatch: WITSML wellbore references "
                    f"well_uid={wellbore.well_uid!r}, but WITSML well is "
                    f"uid={acquisition.well.uid!r} / name={acquisition.well.name!r}"
                )

    return acquisition


def from_witsml_log(
    witsml_log_path: str | Path,
    prodml_path: Optional[str | Path] = None,
) -> SensingAcquisition:
    """
    Le um arquivo WITSML Log e opcionalmente enriquece com metadados ProdML.

    Retorna uma `SensingAcquisition` unificada.
    """
    witsml_log_path = Path(witsml_log_path)
    patch = witsml.read_log(witsml_log_path)
    acquisition = from_alakoro_patch(patch)
    acquisition.source_format = "witsml"
    acquisition.source_path = str(witsml_log_path)

    if prodml_path is not None:
        prod_patch = prodml.read(prodml_path)
        # Enriquece metadados tecnicos do ProdML
        attrs = prod_patch.attrs
        dt_s = float(attrs.time_step / np.timedelta64(1, "s")) if attrs.time_step is not None else 1.0
        acquisition.sampling_rate_hz = 1.0 / dt_s if dt_s > 0 else acquisition.sampling_rate_hz
        acquisition.spatial_resolution_m = float(
            getattr(attrs, "spatial_resolution_m", attrs.distance_step or acquisition.spatial_resolution_m)
        )
        acquisition.gauge_length_m = float(getattr(attrs, "gauge_length_m", acquisition.gauge_length_m))
        acquisition.units = str(attrs.data_units) if attrs.data_units else acquisition.units

    return acquisition


def to_prodml(acquisition: SensingAcquisition, path: str | Path) -> Path:
    """Escreve arquivo ProdML a partir de uma SensingAcquisition."""
    patch = acquisition.to_alakoro_patch()
    well_id = acquisition.well.uid if acquisition.well else None
    wellbore_id = acquisition.wellbore.uid if acquisition.wellbore else None
    return prodml.write(
        patch,
        path,
        well_id=well_id,
        wellbore_id=wellbore_id,
        start_time=acquisition.start_time,
    )


def to_witsml_log(
    acquisition: SensingAcquisition,
    path: str | Path,
    log_name: str = "DASLog",
) -> Path:
    """Escreve arquivo WITSML Log a partir de uma SensingAcquisition."""
    patch = acquisition.to_alakoro_patch()
    well_id = acquisition.well.uid if acquisition.well else None
    wellbore_id = acquisition.wellbore.uid if acquisition.wellbore else None
    mnemonics = [c.mnemonic for c in acquisition.channels]
    units = [c.unit for c in acquisition.channels]
    return witsml.write_log(
        patch,
        path,
        well_id=well_id,
        wellbore_id=wellbore_id,
        log_name=log_name,
        mnemonics=mnemonics,
        units=units,
    )
