"""
Exemplo 2 — Processamento híbrido C++/Python.

Usa alakoro_core (C++20) para detrend e taper, e DASCore para filtering.
"""

import numpy as np

from alakoro_core import DASData, detrend, taper
from src.io.dasdae import DASDAEAdapter


if __name__ == "__main__":
    # Criar dados no C++ core
    das = DASData(n_times=2000, n_channels=32)
    arr = np.array(das, copy=False)
    arr[:, :] = np.random.randn(2000, 32)
    arr[:, 0] += np.linspace(0, 100, 2000)  # tendência linear

    # Processadores C++20
    detrend(das)
    taper(das, alpha=0.0)

    # Converter para DASCore Patch para filtering
    patch = DASDAEAdapter.array_to_patch(arr, modality="das")
    filtered = patch.pass_filter(time=(0.1, 50.0))

    print(f"Shape original: {arr.shape}")
    print(f"Shape filtrado: {filtered.data.shape}")
