"""
Alakoro FiberSense — WITSML I/O (Energistics)

Leitura e escrita robusta de objetos WITSML (well, wellbore, log) para
integracao com sistemas de poco de petroleo.

Suporta:
- WITSML v1.3.1.1 e v1.4.1.1 (namespaces 131 e 141)
- Leitura de Well, Wellbore e Log
- Escrita de Log com mnemonicos, unidades e logCurveInfo
- Conversao entre WITSML Log e AlakoroPatch

Referencias:
- WITSML v1.4.1.1: http://www.witsml.org/schemas/141
- WITSML v1.3.1.1: http://www.witsml.org/schemas/131
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from dascore import Patch
from dascore.core.attrs import PatchAttrs

from .alakoro_spool import AlakoroPatch


# Namespaces conhecidos do WITSML
_KNOWN_WITSML_NAMESPACES = [
    "http://www.witsml.org/schemas/141",
    "http://www.witsml.org/schemas/131",
    "http://www.witsml.org/schemas/1series",
]


def _detect_namespace(root: ET.Element) -> Dict[str, str]:
    """Detecta o namespace WITSML usado no documento."""
    tag_ns = ""
    if root.tag.startswith("{"):
        tag_ns = root.tag.split("}")[0][1:]

    nsmap: Dict[str, str] = {"witsml": tag_ns}

    if tag_ns and any(tag_ns.startswith(base) for base in _KNOWN_WITSML_NAMESPACES):
        return nsmap

    for attr, value in root.attrib.items():
        if attr in ("xmlns", "{http://www.w3.org/2000/xmlns/}witsml"):
            if any(value.startswith(base) for base in _KNOWN_WITSML_NAMESPACES):
                nsmap["witsml"] = value
                return nsmap

    for candidate in _KNOWN_WITSML_NAMESPACES:
        nsmap["witsml"] = candidate
        if root.find(".//witsml:log", nsmap) is not None or \
           root.find(".//witsml:well", nsmap) is not None:
            return nsmap

    nsmap["witsml"] = _KNOWN_WITSML_NAMESPACES[0]
    return nsmap


def _qname(ns: str, local: str) -> str:
    return f"{{{ns}}}{local}"


def _find_text(root: ET.Element, paths: list[str], ns: Dict[str, str],
               default: str = "") -> str:
    for path in paths:
        elem = root.find(path, ns)
        if elem is not None and elem.text:
            text = elem.text.strip()
            if text:
                return text
    return default


@dataclass
class Well:
    """Representacao simplificada de um poco WITSML."""
    uid: str
    name: str
    field: Optional[str] = None
    country: Optional[str] = None
    operator: Optional[str] = None


@dataclass
class Wellbore:
    """Representacao simplificada de um wellbore WITSML."""
    uid: str
    name: str
    well_uid: Optional[str] = None
    md_min: float = 0.0
    md_max: float = 0.0


@dataclass
class WITSMLLog:
    """Representacao simplificada de um log WITSML."""
    uid: str
    name: str
    well_uid: Optional[str] = None
    wellbore_uid: Optional[str] = None
    mnemonic: str = "DATA"
    unit: str = "unknown"
    data: np.ndarray = field(default_factory=lambda: np.array([]))


def read_well(path: str | Path) -> Well:
    """Le um arquivo WITSML Well e retorna Well."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"WITSML file not found: {path}")

    tree = ET.parse(str(path))
    root = tree.getroot()
    ns = _detect_namespace(root)

    elem = root.find(".//witsml:well", ns)
    if elem is None:
        elem = root.find(".//well")
    if elem is None:
        raise ValueError("No <well> element found")

    return Well(
        uid=elem.get("uid", ""),
        name=_find_text(elem, ["witsml:name", "name"], ns),
        field=_find_text(elem, ["witsml:field", "field"], ns) or None,
        country=_find_text(elem, ["witsml:country", "country"], ns) or None,
        operator=_find_text(elem, ["witsml:operator", "operator"], ns) or None,
    )


def read_wellbore(path: str | Path) -> Wellbore:
    """Le um arquivo WITSML Wellbore e retorna Wellbore."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"WITSML file not found: {path}")

    tree = ET.parse(str(path))
    root = tree.getroot()
    ns = _detect_namespace(root)

    elem = root.find(".//witsml:wellbore", ns)
    if elem is None:
        elem = root.find(".//wellbore")
    if elem is None:
        raise ValueError("No <wellbore> element found")

    md_min = 0.0
    md_max = 0.0
    md_elem = elem.find("witsml:md", ns) or elem.find("md")
    if md_elem is not None:
        md_min = float(md_elem.get("min", 0.0) or 0.0)
        md_max = float(md_elem.get("max", 0.0) or 0.0)

    return Wellbore(
        uid=elem.get("uid", ""),
        name=_find_text(elem, ["witsml:name", "name"], ns),
        well_uid=_find_text(elem, ["witsml:nameWell", "nameWell"], ns) or None,
        md_min=md_min,
        md_max=md_max,
    )


def _parse_log_data(log: ET.Element, ns: Dict[str, str]) -> Tuple[np.ndarray, List[str], List[str]]:
    """
    Faz parse dos dados de um log WITSML.

    Returns:
        (data_array, mnemonics, units)
    """
    # Tenta obter mnemonicos e unidades do logCurveInfo
    mnemonics: List[str] = []
    units: List[str] = []

    curve_infos = log.findall("witsml:logCurveInfo", ns)
    if not curve_infos:
        curve_infos = log.findall("logCurveInfo")

    for info in curve_infos:
        mnemonic = _find_text(info, ["witsml:mnemonic", "mnemonic"], ns)
        unit = _find_text(info, ["witsml:unit", "unit"], ns)
        if mnemonic:
            mnemonics.append(mnemonic)
            units.append(unit or "unknown")

    data_elem = log.find("witsml:data", ns)
    if data_elem is None:
        data_elem = log.find("data")
    if data_elem is None or not data_elem.text:
        raise ValueError("No <data> element found")

    rows: List[List[float]] = []
    for line in data_elem.text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        # WITSML usa virgula como separador de colunas
        values = [float(x) for x in line.split(",")]
        rows.append(values)

    data = np.array(rows, dtype=np.float64)
    if data.ndim == 1:
        data = data.reshape(-1, 1)

    # Se nao houver logCurveInfo, gera mnemonicos genericos
    n_cols = data.shape[1]
    if not mnemonics:
        mnemonics = [f"CH{i}" for i in range(n_cols)]
        units = ["unknown"] * n_cols

    return data, mnemonics, units


def read_log(path: str | Path) -> AlakoroPatch:
    """
    Le um arquivo WITSML Log (curva 2D) e retorna AlakoroPatch.

    Extrai mnemonicos e unidades do logCurveInfo quando disponivel.
    Assume que a primeira coluna e o indice (profundidade ou tempo) e
    as colunas subsequentes sao os dados.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"WITSML file not found: {path}")

    tree = ET.parse(str(path))
    root = tree.getroot()
    ns = _detect_namespace(root)

    log = root.find(".//witsml:log", ns)
    if log is None:
        log = root.find(".//log")
    if log is None:
        raise ValueError("No <log> element found")

    data, mnemonics, units = _parse_log_data(log, ns)

    # Se a primeira coluna for indice, remove-a dos dados
    if data.shape[1] >= 2:
        index_col = data[:, 0]
        values = data[:, 1:]
        n_t, n_c = values.shape
        distance = np.arange(n_c, dtype=np.float64)
        if len(index_col) >= 2:
            dx = float(index_col[1] - index_col[0])
        else:
            dx = 1.0
    else:
        values = data
        n_t, n_c = values.shape
        distance = np.arange(n_c, dtype=np.float64)
        dx = 1.0

    well_id = _find_text(log, ["witsml:nameWell", "nameWell"], ns) or None
    wellbore_id = _find_text(log, ["witsml:nameWellbore", "nameWellbore"], ns) or None
    unit = units[1] if len(units) >= 2 else units[0]

    patch = Patch(
        data=values,
        coords={
            "time": (np.arange(n_t) * 1e9).astype("timedelta64[ns]"),
            "distance": distance,
        },
        dims=("time", "distance"),
        attrs=PatchAttrs(
            data_category="das",
            data_units=unit,
            distance_step=dx,
        ),
    )
    out = AlakoroPatch(patch, well_id=well_id, modality="das")
    out.source_path = str(path)
    return out


def write_log(
    patch: AlakoroPatch,
    path: str | Path,
    well_id: Optional[str] = None,
    wellbore_id: Optional[str] = None,
    log_name: str = "DASLog",
    mnemonics: Optional[List[str]] = None,
    units: Optional[List[str]] = None,
    index_mnemonic: str = "TIME",
    index_unit: str = "s",
) -> Path:
    """
    Salva AlakoroPatch como WITSML Log robusto.

    Inclui logCurveInfo com mnemonicos e unidades, e formata os dados
    no padrao WITSML (colunas separadas por virgula).
    """
    path = Path(path)
    data = patch.data
    n_t, n_c = data.shape

    witsml_ns = _KNOWN_WITSML_NAMESPACES[0]

    root = ET.Element(_qname(witsml_ns, "logs"))
    root.set("version", "1.4.1.1")

    log = ET.SubElement(root, _qname(witsml_ns, "log"))
    log.set("uid", log_name)
    ET.SubElement(log, _qname(witsml_ns, "name")).text = log_name
    if well_id:
        ET.SubElement(log, _qname(witsml_ns, "nameWell")).text = well_id
    if wellbore_id:
        ET.SubElement(log, _qname(witsml_ns, "nameWellbore")).text = wellbore_id

    attrs = patch.attrs
    sampling_rate_hz = float(getattr(attrs, "sampling_rate_hz", 0.0) or 0.0)
    if sampling_rate_hz <= 0:
        time_step = getattr(attrs, "time_step", None)
        if time_step is not None:
            try:
                sampling_rate_hz = 1.0 / (float(time_step / np.timedelta64(1, "s")) or 1.0)
            except Exception:
                sampling_rate_hz = 1000.0
        else:
            sampling_rate_hz = 1000.0
    dt_s = 1.0 / sampling_rate_hz

    distance_step = float(getattr(attrs, "distance_step", 1.0) or 1.0)
    data_units = str(getattr(attrs, "data_units", "") or "")

    if mnemonics is None:
        mnemonics = [f"CH{i}" for i in range(n_c)]
    if units is None:
        units = [data_units or "unknown"] * n_c

    # Garante tamanhos consistentes
    mnemonics = list(mnemonics)[:n_c]
    units = list(units)[:n_c]
    while len(mnemonics) < n_c:
        mnemonics.append(f"CH{len(mnemonics)}")
    while len(units) < n_c:
        units.append(data_units or "unknown")

    # logCurveInfo para o indice (tempo)
    lci_index = ET.SubElement(log, _qname(witsml_ns, "logCurveInfo"))
    lci_index.set("uid", index_mnemonic)
    ET.SubElement(lci_index, _qname(witsml_ns, "mnemonic")).text = index_mnemonic
    ET.SubElement(lci_index, _qname(witsml_ns, "unit")).text = index_unit

    # logCurveInfo para cada canal
    for mnemonic, unit in zip(mnemonics, units):
        lci = ET.SubElement(log, _qname(witsml_ns, "logCurveInfo"))
        lci.set("uid", mnemonic)
        ET.SubElement(lci, _qname(witsml_ns, "mnemonic")).text = mnemonic
        ET.SubElement(lci, _qname(witsml_ns, "unit")).text = unit

    # Dados: primeira coluna = indice de tempo, demais = canais
    data_elem = ET.SubElement(log, _qname(witsml_ns, "data"))
    lines = []
    for i, row in enumerate(data):
        t = i * dt_s
        line = ",".join([f"{t:.6f}"] + [f"{v:.6f}" for v in row])
        lines.append(line)
    data_elem.text = "\n".join(lines)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(path), encoding="utf-8", xml_declaration=True)
    return path
