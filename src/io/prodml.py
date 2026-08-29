"""
Alakoro FiberSense — ProdML I/O (Energistics)

Suporte básico de leitura/escrita de arquivos ProdML XML para dados
DAS/DTS/DSS. Implementação simplificada para prototipagem da Fase 2.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

from dascore import Patch
from dascore.core.attrs import PatchAttrs

from .alakoro_spool import AlakoroPatch


NS = {
    "prodml": "http://www.energistics.org/energyml/data/prodmlv2",
    "eml": "http://www.energistics.org/energyml/data/commonv2",
}


def read(path: str | Path) -> AlakoroPatch:
    """Lê um arquivo ProdML XML e retorna AlakoroPatch."""
    tree = ET.parse(str(path))
    root = tree.getroot()

    # Tenta encontrar elementos de dados (estrutura simplificada)
    data_elem = root.find(".//prodml:values", NS)
    if data_elem is None:
        raise ValueError("ProdML file does not contain <values> element")

    # Valores como texto separado por espaço/quebra de linha
    flat = [float(x) for x in data_elem.text.split() if x.strip()]

    time_elem = root.find(".//prodml:timeCount", NS)
    chan_elem = root.find(".//prodml:channelCount", NS)

    n_t = int(time_elem.text) if time_elem is not None else len(flat)
    n_c = int(chan_elem.text) if chan_elem is not None else 1

    data = np.array(flat, dtype=np.float64).reshape((n_t, n_c))

    dt_s = 1.0
    dx_m = 1.0
    modality = "das"
    units = ""

    cat = root.find(".//prodml:flowRate/[@uom]", NS)
    if cat is not None:
        units = cat.get("uom", units)

    patch = Patch(
        data=data,
        coords={
            "time": (np.arange(n_t) * dt_s * 1e9).astype("timedelta64[ns]"),
            "distance": np.arange(n_c) * dx_m,
        },
        dims=("time", "distance"),
        attrs=PatchAttrs(data_category=modality, data_units=units,
                         time_step=np.timedelta64(int(dt_s * 1e9), "ns"),
                         distance_step=dx_m),
    )
    return AlakoroPatch(patch, modality=modality)


def write(patch: AlakoroPatch, path: str | Path,
          well_id: Optional[str] = None,
          wellbore_id: Optional[str] = None):
    """Salva AlakoroPatch como ProdML XML simplificado."""
    path = Path(path)
    data = patch.data
    n_t, n_c = data.shape

    root = ET.Element("{http://www.energistics.org/energyml/data/prodmlv2}DASAcquisition")
    root.set("{http://www.w3.org/2001/XMLSchema-instance}schemaVersion", "2.0")

    metadata = ET.SubElement(root, "{http://www.energistics.org/energyml/data/prodmlv2}DASMetadata")
    ET.SubElement(metadata, "{http://www.energistics.org/energyml/data/prodmlv2}timeCount").text = str(n_t)
    ET.SubElement(metadata, "{http://www.energistics.org/energyml/data/prodmlv2}channelCount").text = str(n_c)
    units = str(patch.attrs.data_units)
    if hasattr(patch.attrs.data_units, "magnitude"):
        units = str(patch.attrs.data_units)
    ET.SubElement(metadata, "{http://www.energistics.org/energyml/data/prodmlv2}dataUnits").text = units

    values = ET.SubElement(root, "{http://www.energistics.org/energyml/data/prodmlv2}values")
    values.text = "\n".join(" ".join(str(v) for v in row) for row in data)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(path), encoding="utf-8", xml_declaration=True)
