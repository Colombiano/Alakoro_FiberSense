"""
Exemplo 3 — Monitoramento em tempo real de diretório.

Este exemplo demonstra a API; em produção, o watcher rodaria em uma
thread separada.
"""

import tempfile
import time
from pathlib import Path

import numpy as np

from src.io.dasdae import DASDAEAdapter
from src.io.streaming import StreamingSpool


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        # Simula arquivos chegando
        for i in range(3):
            data = np.random.randn(100, 8)
            patch = DASDAEAdapter.array_to_patch(data, modality="das")
            # Salvar como HDF5 DASDAE usando DASCore
            spool = dc.spool([patch])
            # spool.save(base / f"file_{i}.h5")  # requer dados reais
            time.sleep(0.1)

        # Carrega existentes e monitora
        streamer = StreamingSpool(base, modality="das")
        print(f"Diretório monitorado: {base}")
        print(f"Spool inicial: {streamer.spool}")
