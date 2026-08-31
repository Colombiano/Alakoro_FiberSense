"""
Alakoro FiberSense — ProdML I/O (Energistics)

Leitura e escrita robusta de arquivos ProdML XML para dados DAS/DTS/DSS.
Suporta namespaces comuns do ProdML v2.x e extrai/preserva metadados
relevantes para DFOS (sampling rate, resolucao espacial, gauge length,
well/wellbore, start time, unidades).

Aviso de propriedade intelectual:
- ProdML e um padrao aberto mantido pela Energistics.
- Esta implementacao e independente e nao e endossada pela Energistics.
- Nenhum schema XSD, documentacao ou codigo oficial da Energistics e
  redistribuido neste repositorio; apenas namespaces publicos e estruturas
  XML descritas nos schemas abertos sao utilizados.

Referencias:
- Energistics ProdML v2.2: http://www.energistics.org/energyml/data/prodmlv2
- DASAcquisition, FiberOpticalDASAcquisition
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
from dascore import Patch
from dascore.core.attrs import PatchAttrs

from .alakoro_spool import AlakoroPatch


# Namespaces conhecidos do ProdML v2.x (mais comuns primeiro)
_KNOWN_PRODML_NAMESPACES = [
    "http://www.energistics.org/energyml/data/prodmlv2",
    "http://www.energistics.org/energyml/data/prodmlv2.1",
    "http://www.energistics.org/energyml/data/prodmlv2.2",
    "http://www.energistics.org/energyml/data/prodmlv2.0",
]

_EML_NS = "http://www.energistics.org/energyml/data/commonv2"
_XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"


def _detect_namespace(root: ET.Element) -> tuple[str, Dict[str, str]]:
    """Detecta o namespace ProdML usado no documento."""
    # Tenta extrair do proprio elemento raiz
    tag_ns = ""
    if root.tag.startswith("{"):
        tag_ns = root.tag.split("}")[0][1:]

    nsmap: Dict[str, str] = {"prodml": tag_ns, "eml": _EML_NS, "xsi": _XSI_NS}

    if tag_ns and any(tag_ns.startswith(base) for base in _KNOWN_PRODML_NAMESPACES):
        return tag_ns, nsmap

    # Varre atributos xmlns do root
    for attr, value in root.attrib.items():
        if attr in ("xmlns", "{http://www.w3.org/2000/xmlns/}prodml"):
            if any(value.startswith(base) for base in _KNOWN_PRODML_NAMESPACES):
                nsmap["prodml"] = value
                return value, nsmap

    # Fallback: tenta cada namespace conhecido
    for candidate in _KNOWN_PRODML_NAMESPACES:
        nsmap["prodml"] = candidate
        if root.find(".//prodml:values", nsmap) is not None or \
           root.find(".//prodml:DASAcquisition", nsmap) is not None:
            return candidate, nsmap

    # Se nada der certo, assume o primeiro conhecido e permite leitura sem namespace
    nsmap["prodml"] = _KNOWN_PRODML_NAMESPACES[0]
    return _KNOWN_PRODML_NAMESPACES[0], nsmap


def _qname(ns: str, local: str) -> str:
    """Retorna tag qualificada {namespace}local."""
    return f"{{{ns}}}{local}"


def _find_text(root: ET.Element, paths: list[str], ns: Dict[str, str],
                 default: Any = None, convert=float) -> Any:
    """Procura texto em varios caminhos XPath e retorna convertido."""
    for path in paths:
        elem = root.find(path, ns)
        if elem is not None and elem.text:
            text = elem.text.strip()
            if text:
                try:
                    return convert(text)
                except Exception:
                    return default
    return default


def _find_attr(root: ET.Element, path: str, attr: str, ns: Dict[str, str],
               default: str = "") -> str:
    """Procura atributo em elemento."""
    elem = root.find(path, ns)
    if elem is not None:
        return elem.get(attr, default)
    return default


def read(path: str | Path) -> AlakoroPatch:
    """
    Le um arquivo ProdML XML e retorna AlakoroPatch.

    Aceita arquivos com ou sem namespace, e extrai metadados quando
    disponiveis: sampling_rate_hz, spatial_resolution_m, gauge_length_m,
    units, start_time, well_id, wellbore_id.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"ProdML file not found: {path}")

    tree = ET.parse(str(path))
    root = tree.getroot()

    prodml_ns, ns = _detect_namespace(root)

    # Raiz pode ser DASAcquisition diretamente ou estar dentro de outro elemento
    acquisition = root
    if not acquisition.tag.endswith("DASAcquisition"):
        acquisition = root.find(f".//prodml:DASAcquisition", ns)
        if acquisition is None:
            # Tenta sem namespace
            acquisition = root.find(".//DASAcquisition")
        if acquisition is None:
            raise ValueError("ProdML file does not contain a DASAcquisition element")

    # Leitura dos valores
    data_elem = acquisition.find(".//prodml:values", ns)
    if data_elem is None:
        data_elem = acquisition.find(".//values")
    if data_elem is None or not data_elem.text:
        raise ValueError("ProdML file does not contain <values> element")

    flat = [float(x) for x in data_elem.text.split() if x.strip()]
    if not flat:
        raise ValueError("ProdML <values> element is empty")

    n_t = int(_find_text(acquisition, [
        ".//prodml:timeCount",
        ".//prodml:DASMetadata/prodml:timeCount",
    ], ns, default=len(flat), convert=int))

    n_c = int(_find_text(acquisition, [
        ".//prodml:channelCount",
        ".//prodml:DASMetadata/prodml:channelCount",
    ], ns, default=1, convert=int))

    if n_t * n_c != len(flat):
        # Tenta ajustar se os metadados estiverem inconsistentes
        n_t = len(flat) // max(n_c, 1)
        if n_t * n_c != len(flat):
            n_c = len(flat) // max(n_t, 1)
        if n_t * n_c != len(flat):
            raise ValueError(
                f"ProdML shape mismatch: timeCount*channelCount={n_t * n_c}, "
                f"values={len(flat)}"
            )

    data = np.array(flat, dtype=np.float64).reshape((n_t, n_c))

    # Metadados
    dt_s = _find_text(acquisition, [
        ".//prodml:samplingInterval",
        ".//prodml:DASMetadata/prodml:samplingInterval",
        ".//prodml:temporalSamplingInterval",
    ], ns, default=1.0, convert=float)

    dx_m = _find_text(acquisition, [
        ".//prodml:spatialSamplingInterval",
        ".//prodml:DASMetadata/prodml:spatialSamplingInterval",
        ".//prodml:channelSpacing",
    ], ns, default=1.0, convert=float)

    gauge_length_m = _find_text(acquisition, [
        ".//prodml:gaugeLength",
        ".//prodml:DASMetadata/prodml:gaugeLength",
    ], ns, default=0.0, convert=float)

    units = _find_text(acquisition, [
        ".//prodml:dataUnits",
        ".//prodml:DASMetadata/prodml:dataUnits",
        ".//prodml:unitOfMeasure",
    ], ns, default="", convert=str)

    modality = _find_text(acquisition, [
        ".//prodml:modality",
        ".//prodml:DASMetadata/prodml:modality",
    ], ns, default="das", convert=str).lower()

    start_time_str = _find_text(acquisition, [
        ".//prodml:startTime",
        ".//prodml:DASMetadata/prodml:startTime",
        ".//prodml:acquisitionStartTime",
    ], ns, default="", convert=str)

    well_id = ""
    well_elem = acquisition.find(".//prodml:well", ns)
    if well_elem is None:
        well_elem = acquisition.find(".//well")
    if well_elem is not None:
        well_id = well_elem.get("uuid", "") or _find_text(
            well_elem, ["prodml:uuid", "uuid"], ns, default="", convert=str
        )
    if not well_id:
        well_id = _find_text(acquisition, [".//eml:Well/eml:uuid", ".//prodml:nameWell"], ns, default="", convert=str)

    wellbore_id = ""
    wb_elem = acquisition.find(".//prodml:wellbore", ns)
    if wb_elem is None:
        wb_elem = acquisition.find(".//wellbore")
    if wb_elem is not None:
        wellbore_id = wb_elem.get("uuid", "") or _find_text(
            wb_elem, ["prodml:uuid", "uuid"], ns, default="", convert=str
        )
    if not wellbore_id:
        wellbore_id = _find_text(
            acquisition, [".//eml:Wellbore/eml:uuid", ".//prodml:nameWellbore"], ns, default="", convert=str
        )

    patch = Patch(
        data=data,
        coords={
            "time": (np.arange(n_t) * dt_s * 1e9).astype("timedelta64[ns]"),
            "distance": np.arange(n_c) * dx_m,
        },
        dims=("time", "distance"),
        attrs=PatchAttrs(
            data_category=modality,
            data_units=units,
            time_step=np.timedelta64(int(dt_s * 1e9), "ns"),
            distance_step=dx_m,
        ),
    )

    patch_out = AlakoroPatch(patch, well_id=well_id or None, modality=modality)
    patch_out.source_path = str(path)
    # Preserva wellbore_id como atributo extra quando disponivel
    if wellbore_id:
        patch_out.wellbore_id = wellbore_id
    return patch_out


def write(
    patch: AlakoroPatch,
    path: str | Path,
    well_id: Optional[str] = None,
    wellbore_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
) -> Path:
    """
    Salva AlakoroPatch como ProdML XML simplificado mas robusto.

    Preserva metadados do patch: sampling_rate_hz, spatial_resolution_m,
    gauge_length_m, units, modality, well_id, wellbore_id e start_time.
    Se well_id/wellbore_id nao forem informados, usa os do patch quando
    disponiveis.
    """
    well_id = well_id if well_id is not None else patch.well_id
    wellbore_id = wellbore_id if wellbore_id is not None else getattr(patch, "wellbore_id", None)
    """
    Salva AlakoroPatch como ProdML XML simplificado mas robusto.

    Preserva metadados do patch: sampling_rate_hz, spatial_resolution_m,
    gauge_length_m, units, modality, well_id, wellbore_id e start_time.
    """
    path = Path(path)
    data = patch.data
    n_t, n_c = data.shape

    # Namespace padrao ProdML v2.2
    prodml_ns = _KNOWN_PRODML_NAMESPACES[0]
    eml_ns = _EML_NS
    xsi_ns = _XSI_NS

    root = ET.Element(_qname(prodml_ns, "DASAcquisition"))
    root.set(_qname(xsi_ns, "schemaVersion"), "2.2")

    # Referencias a Well/Wellbore
    if well_id:
        well = ET.SubElement(root, _qname(prodml_ns, "well"))
        well.set("uuid", well_id)
    if wellbore_id:
        wb = ET.SubElement(root, _qname(prodml_ns, "wellbore"))
        wb.set("uuid", wellbore_id)

    # Metadados
    metadata = ET.SubElement(root, _qname(prodml_ns, "DASMetadata"))
    ET.SubElement(metadata, _qname(prodml_ns, "timeCount")).text = str(n_t)
    ET.SubElement(metadata, _qname(prodml_ns, "channelCount")).text = str(n_c)

    attrs = patch.attrs
    sampling_rate_hz = float(getattr(attrs, "sampling_rate_hz", 0.0) or 0.0)
    if sampling_rate_hz <= 0:
        # Tenta inferir de time_step
        time_step = getattr(attrs, "time_step", None)
        if time_step is not None:
            try:
                sampling_rate_hz = 1.0 / (float(time_step / np.timedelta64(1, "s")) or 1.0)
            except Exception:
                sampling_rate_hz = 1000.0
        else:
            sampling_rate_hz = 1000.0

    dt_s = 1.0 / sampling_rate_hz
    ET.SubElement(metadata, _qname(prodml_ns, "samplingInterval")).text = f"{dt_s:.6f}"

    spatial_resolution_m = float(getattr(attrs, "spatial_resolution_m", 0.0) or 0.0)
    if spatial_resolution_m <= 0:
        spatial_resolution_m = float(getattr(attrs, "distance_step", 1.0) or 1.0)
    ET.SubElement(metadata, _qname(prodml_ns, "spatialSamplingInterval")).text = f"{spatial_resolution_m:.6f}"

    gauge_length_m = float(getattr(attrs, "gauge_length_m", 0.0) or 0.0)
    ET.SubElement(metadata, _qname(prodml_ns, "gaugeLength")).text = f"{gauge_length_m:.6f}"

    units = str(getattr(attrs, "data_units", "") or "")
    ET.SubElement(metadata, _qname(prodml_ns, "dataUnits")).text = units

    modality = patch.modality.lower()
    ET.SubElement(metadata, _qname(prodml_ns, "modality")).text = modality.upper()

    if start_time is None and hasattr(attrs, "start_time"):
        start_time = attrs.start_time
    if isinstance(start_time, datetime):
        start_time_str = start_time.astimezone(timezone.utc).isoformat()
    elif isinstance(start_time, str):
        start_time_str = start_time
    else:
        start_time_str = datetime.now(timezone.utc).isoformat()
    ET.SubElement(metadata, _qname(prodml_ns, "startTime")).text = start_time_str

    # Dados
    values = ET.SubElement(root, _qname(prodml_ns, "values"))
    values.text = "\n".join(" ".join(f"{v:.6f}" for v in row) for row in data)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(path), encoding="utf-8", xml_declaration=True)
    return path
