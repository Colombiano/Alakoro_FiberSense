"""
Alakoro FiberSense — WITSML I/O (Energistics)

Mapeamento básico entre objetos WITSML (well, wellbore, log) e
estruturas Alakoro. Implementação simplificada para prototipagem.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import numpy as np

from dascore import Patch
from dascore.core.attrs import PatchAttrs

from .alakoro_spool import AlakoroPatch


NS = {
    "witsml": "http://www.witsml.org/schemas/1series",
}


@dataclass
class Well:
    """Representação simplificada de um poço WITSML."""
    uid: str
    name: str
    field: Optional[str] = None
    country: Optional[str] = None
    operator: Optional[str] = None


@dataclass
class Wellbore:
    """Representação simplificada de um wellbore WITSML."""
    uid: str
    name: str
    well_uid: Optional[str] = None
    md_min: float = 0.0
    md_max: float = 0.0


@dataclass
class WITSMLLog:
    """Representação simplificada de um log WITSML."""
    uid: str
    name: str
    well_uid: Optional[str] = None
    wellbore_uid: Optional[str] = None
    mnemonic: str = "DATA"
    unit: str = "unknown"
    data: np.ndarray = field(default_factory=lambda: np.array([]))


def read_well(path: str | Path) -> Well:
    """Lê um arquivo WITSML Well e retorna Well."""
    tree = ET.parse(str(path))
    root = tree.getroot()
    elem = root.find(".//witsml:well", NS)
    if elem is None:
        raise ValueError("No <well> element found")
    return Well(
        uid=elem.get("uid", ""),
        name=_text(elem, "witsml:name"),
        field=_text(elem, "witsml:field"),
        country=_text(elem, "witsml:country"),
        operator=_text(elem, "witsml:operator"),
    )


def read_wellbore(path: str | Path) -> Wellbore:
    """Lê um arquivo WITSML Wellbore e retorna Wellbore."""
    tree = ET.parse(str(path))
    root = tree.getroot()
    elem = root.find(".//witsml:wellbore", NS)
    if elem is None:
        raise ValueError("No <wellbore> element found")
    return Wellbore(
        uid=elem.get("uid", ""),
        name=_text(elem, "witsml:name"),
        well_uid=_text(elem, "witsml:nameWell"),
    )


def read_log(path: str | Path) -> AlakoroPatch:
    """Lê um arquivo WITSML Log (curva 2D) e retorna AlakoroPatch."""
    tree = ET.parse(str(path))
    root = tree.getroot()
    log = root.find(".//witsml:log", NS)
    if log is None:
        raise ValueError("No <log> element found")

    data_elem = log.find(".//witsml:data", NS)
    if data_elem is None or not data_elem.text:
        raise ValueError("No <data> element found")

    rows = []
    for line in data_elem.text.strip().splitlines():
        rows.append([float(x) for x in line.split(",")])

    data = np.array(rows, dtype=np.float64)
    if data.ndim == 1:
        data = data.reshape(-1, 1)

    n_t, n_c = data.shape
    patch = Patch(
        data=data,
        coords={
            "time": (np.arange(n_t) * 1e9).astype("timedelta64[ns]"),
            "distance": np.arange(n_c),
        },
        dims=("time", "distance"),
        attrs=PatchAttrs(data_category="das", data_units=""),
    )
    return AlakoroPatch(patch, modality="das")


def write_log(patch: AlakoroPatch, path: str | Path,
              well_id: Optional[str] = None,
              wellbore_id: Optional[str] = None,
              log_name: str = "DASLog"):
    """Salva AlakoroPatch como WITSML Log simplificado."""
    path = Path(path)
    data = patch.data

    root = ET.Element("{http://www.witsml.org/schemas/1series}logs")
    root.set("version", "1.4.1.1")

    log = ET.SubElement(root, "{http://www.witsml.org/schemas/1series}log")
    log.set("uid", log_name)
    ET.SubElement(log, "{http://www.witsml.org/schemas/1series}name").text = log_name
    if well_id:
        ET.SubElement(log, "{http://www.witsml.org/schemas/1series}nameWell").text = well_id
    if wellbore_id:
        ET.SubElement(log, "{http://www.witsml.org/schemas/1series}nameWellbore").text = wellbore_id

    data_elem = ET.SubElement(log, "{http://www.witsml.org/schemas/1series}data")
    data_elem.text = "\n".join(",".join(str(v) for v in row) for row in data
    )

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(path), encoding="utf-8", xml_declaration=True)


def _text(elem, path: str) -> Optional[str]:
    child = elem.find(path, NS)
    return child.text if child is not None else None
