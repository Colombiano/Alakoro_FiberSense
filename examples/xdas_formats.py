"""
Exemplo 5 — Leitura/escrita de formatos Xdas via Alakoro.

Demonstra conversão direta AlakoroPatch ↔ xdas.DataArray,
AlakoroSpool ↔ xdas.DataCollection e roundtrip NetCDF.
"""

import tempfile
from pathlib import Path

import numpy as np

from src.io.alakoro_spool import AlakoroPatch, AlakoroSpool
from src.io.dasdae import DASDAEAdapter
from src.io.xdas_adapter import alakoro_to_xdas, spool_to_datacollection
from src.io.xdas_formats import read_xdas, write_xdas, supported_xdas_formats


if __name__ == "__main__":
    print("Formatos/engines Xdas suportados:")
    for fmt in supported_xdas_formats():
        print(f"  - {fmt}")

    # Dados sintéticos
    n_t, n_z = 256, 16
    data = np.random.default_rng(42).standard_normal((n_t, n_z))
    patch = DASDAEAdapter.array_to_patch(data, dt_s=1.0, dx_m=2.0, modality="das")
    alakoro = AlakoroPatch(patch, well_id="BRA-001", modality="das")

    # Conversão direta para xdas.DataArray
    da = alakoro_to_xdas(alakoro)
    print(f"\nDataArray shape: {da.shape}, attrs: {da.attrs}")

    # Conversão de spool para DataCollection
    spool = AlakoroSpool([alakoro, alakoro])
    collection = spool_to_datacollection(spool)
    print(f"DataCollection keys: {list(collection.keys())}")

    # Roundtrip NetCDF
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "example.nc"
        write_xdas(alakoro, path)
        back = read_xdas(path, well_id="BRA-001")
        print(f"\nNetCDF roundtrip: {back}, shape={back.shape}")
        assert np.allclose(back.data, data)

    print("\nIntegração Xdas concluída com sucesso.")
