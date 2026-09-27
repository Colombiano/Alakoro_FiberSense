"""
Alakoro FiberSense — Driver de exemplo open-source.

Este driver demonstra a API ``BaseVendorDriver`` usando um formato
hipotético ``.exd`` baseado em HDF5. Não depende de SDKs comerciais
e serve de template para plugins proprietários.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Union

import numpy as np

from ...alakoro_spool import AlakoroPatch, AlakoroSpool
from ..base import BaseVendorDriver

# Tenta importar h5py sem torná-lo obrigatório para o subpacote
try:
    import h5py

    HAS_H5PY = True
except Exception:  # pragma: no cover
    HAS_H5PY = False


class ExampleVendorDriver(BaseVendorDriver):
    """
    Driver de exemplo para arquivos ``.exd`` (Example Vendor Data).

    Formato hipotético: HDF5 com grupos/datasets padronizados:
      - /data          : array 2D (distance, time)
      - /distance      : coordenada de distância (m)
      - /time          : coordenada de tempo (s)
      - /attrs         : metadados chave/valor
    """

    name = "example_vendor"
    supported_extensions = {".exd", ".example"}
    version = "1.0.0"

    @classmethod
    def is_available(cls) -> bool:
        """Disponível sempre que h5py estiver instalado."""
        return HAS_H5PY

    @classmethod
    def detect(cls, path: Union[str, Path]) -> bool:
        """Detecta pelo sufixo e pela assinatura HDF5."""
        path = Path(path)
        if not path.is_file():
            return False
        if path.suffix.lower() not in cls.supported_extensions:
            return False
        if not HAS_H5PY:
            return False
        try:
            with h5py.File(path, "r") as f:
                # Confirma que é um arquivo nosso verificando atributo de formato
                return f.attrs.get("alakoro_format", "").startswith("example_vendor")
        except Exception:
            return False

    def read(
        self, path: Union[str, Path], **kwargs: Any
    ) -> Union[AlakoroPatch, AlakoroSpool]:
        """Lê um arquivo ``.exd`` e retorna AlakoroPatch."""
        path = Path(path)
        if not HAS_H5PY:
            raise RuntimeError("h5py is required to read example_vendor files")

        with h5py.File(path, "r") as f:
            data = np.asarray(f["data"])
            distance = np.asarray(f["distance"])
            time = np.asarray(f["time"])
            attrs = dict(f.attrs)

        # Constrói Patch DASCore a partir dos arrays lidos
        import dascore as dc

        patch = dc.Patch(
            data=data,
            coords={"distance": distance, "time": time},
            dims=("distance", "time"),
            attrs={
                "data_category": attrs.get("modality", "das"),
                "data_units": attrs.get("data_units", "1/s"),
                "distance_step": float(distance[1] - distance[0]) if len(distance) > 1 else 1.0,
                "time_step": float(time[1] - time[0]) if len(time) > 1 else 1.0,
            },
        )
        return AlakoroPatch(
            patch,
            well_id=attrs.get("well_id"),
            modality=attrs.get("modality", "das"),
        )

    def metadata(self, path: Union[str, Path], **kwargs: Any) -> Dict[str, Any]:
        """Retorna metadados sem carregar os dados."""
        path = Path(path)
        if not HAS_H5PY:
            raise RuntimeError("h5py is required to read example_vendor files")

        with h5py.File(path, "r") as f:
            meta = dict(f.attrs)
            meta["shape"] = f["data"].shape
            meta["distance_count"] = f["distance"].shape[0]
            meta["time_count"] = f["time"].shape[0]
        return meta


def write_example_file(
    path: Union[str, Path],
    shape: tuple = (100, 500),
    modality: str = "das",
    well_id: str = "example-well-01",
) -> Path:
    """
    Cria um arquivo ``.exd`` de exemplo para testes/demonstração.

    Args:
        path: caminho de saída (recomenda-se extensão ``.exd``).
        shape: tupla (n_distances, n_times).
        modality: modalidade do dado.
        well_id: identificador do poço.

    Returns:
        Caminho do arquivo criado.
    """
    if not HAS_H5PY:
        raise RuntimeError("h5py is required to write example_vendor files")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n_dist, n_time = shape

    rng = np.random.default_rng(42)
    data = rng.standard_normal(shape).astype(np.float32)
    distance = np.linspace(0.0, float(n_dist - 1), n_dist)
    time = np.linspace(0.0, float(n_time - 1), n_time)

    with h5py.File(path, "w") as f:
        f.create_dataset("data", data=data)
        f.create_dataset("distance", data=distance)
        f.create_dataset("time", data=time)
        f.attrs["alakoro_format"] = "example_vendor/1.0"
        f.attrs["modality"] = modality
        f.attrs["well_id"] = well_id
        f.attrs["data_units"] = "1/s"

    return path
