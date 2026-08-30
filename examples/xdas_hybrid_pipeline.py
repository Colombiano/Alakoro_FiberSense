"""
Exemplo 6 — Pipeline híbrido Xdas + C++20.

Encadeia processadores nativos do Xdas (detrend, filter) com
processadores avançados C++20 do alakoro_core (median_filter_1d).
"""

import numpy as np

from src.io.dasdae import DASDAEAdapter
from src.processing.hybrid_pipeline import HybridPipeline


if __name__ == "__main__":
    # Dados sintéticos com tendência linear
    n_t, n_z = 1000, 4
    rng = np.random.default_rng(123)
    data = rng.standard_normal((n_t, n_z))
    data[:, 0] += np.linspace(0, 50, n_t)

    patch = DASDAEAdapter.array_to_patch(data, dt_s=0.1, dx_m=1.0, modality="das")

    pipeline = (
        HybridPipeline(patch, well_id="BRA-003", modality="das")
        .xdas("detrend", dim="time", type="linear")
        .xdas("filter", freq=2.0, dim="time", btype="lowpass")
        .cpp("median_filter_1d", window_size=5)
    )
    result = pipeline.to_patch()

    print(f"Pipeline executado: {result}")
    print(f"Passos: {pipeline.history}")

    # Espectro via Xdas
    spec = HybridPipeline(patch, modality="das").apply_array_xdas("rfft")
    print(f"RFFT shape: {spec.shape}")

    print("\nPipeline híbrido Xdas concluído com sucesso.")
