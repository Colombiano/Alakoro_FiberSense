"""
Exemplo 1 — Lendo dados DAS com Alakoro + DASCore.
"""

import numpy as np

from src.io.alakoro_spool import AlakoroPatch, AlakoroSpool
from src.io.dasdae import DASDAEAdapter


if __name__ == "__main__":
    # Dados sintéticos
    data = np.random.randn(1000, 64)

    # Array -> DASCore Patch -> AlakoroPatch
    patch = DASDAEAdapter.array_to_patch(data, dt_s=0.5, dx_m=1.0, modality="das")
    alakoro_patch = AlakoroPatch(patch, well_id="BRA-001", modality="das")

    print(f"Criado: {alakoro_patch}")

    # Operações compatíveis com DASCore
    detrended = alakoro_patch.detrend()
    decimated = detrended.decimate(factor=2)
    print(f"Após decimate: {decimated.shape}")

    # Spool
    spool = AlakoroSpool([alakoro_patch, decimated])
    print(f"Spool: {spool}")
    print(f"Conteúdo: {spool.get_contents()}")
