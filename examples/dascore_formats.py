"""
Exemplo 3 — Leitura/escrita de formatos DASCore via Alakoro.

Demonstra como salvar e carregar AlakoroPatch em formatos suportados
pelo DASCore (dasdae, pickle, etc.) usando a API unificada de
src.io.dascore_formats.
"""

import tempfile
from pathlib import Path

import numpy as np

from src.io.dascore_formats import read, write, supported_formats
from src.io.dasdae import DASDAEAdapter
from src.io.alakoro_spool import AlakoroPatch, AlakoroSpool


if __name__ == "__main__":
    print("Formatos suportados pelo DASCore:")
    for fmt in supported_formats():
        print(f"  - {fmt}")

    # Criar dados sintéticos
    n_t, n_z = 256, 16
    data = np.random.default_rng(42).standard_normal((n_t, n_z))
    patch = DASDAEAdapter.array_to_patch(data, dt_s=1.0, dx_m=2.0, modality="das")
    alakoro = AlakoroPatch(patch, well_id="BRA-001", modality="das")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Escrever e ler de volta em diferentes formatos
        for fmt in ["dasdae", "pickle"]:
            path = tmp_path / f"example.{fmt}"
            write(alakoro, path)
            back = read(path, well_id="BRA-001")
            print(f"\n{fmt}: escrito {path.stat().st_size} bytes")
            print(f"  lido -> {back}, shape={back.shape}")
            assert np.allclose(back.data, data)

        # Spool com múltiplos patches (pickle preserva a coleção)
        spool = AlakoroSpool([alakoro, alakoro])
        spool_path = tmp_path / "spool.pickle"
        write(spool, spool_path)
        back_spool = read(spool_path, well_id="BRA-001")
        print(f"\nspool.pickle: lido -> {back_spool}, len={len(back_spool)}")

    print("\nRoundtrip concluído com sucesso.")
