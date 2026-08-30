"""
Exemplo 4 — Pipeline híbrido DASCore + C++20.

Encadeia métodos nativos do DASCore (detrend, pass_filter, decimate)
com processadores avançados do alakoro_core (median_filter_1d,
wavelet_denoise, butterworth_lowpass).
"""

import numpy as np

from src.io.dasdae import DASDAEAdapter
from src.processing.hybrid_pipeline import HybridPipeline


if __name__ == "__main__":
    # Dados sintéticos: 2 canais com tendência linear + ruído
    n_t, n_z = 1000, 2
    rng = np.random.default_rng(123)
    data = rng.standard_normal((n_t, n_z))
    data[:, 0] += np.linspace(0, 50, n_t)  # tendência no canal 0

    patch = DASDAEAdapter.array_to_patch(data, dt_s=0.001, dx_m=1.0, modality="das")

    # Pipeline híbrido
    pipeline = (
        HybridPipeline(patch, well_id="BRA-002", modality="das")
        .dascore("detrend", dim="time", type="linear")
        .dascore("pass_filter", time=(0.5, 100.0))
        .cpp("median_filter_1d", window_size=5)
        .cpp("wavelet_denoise", scales=[1.0, 2.0, 4.0],
             sample_rate_hz=1000.0, threshold=0.3)
        .dascore("decimate", time=2)
    )
    result = pipeline.to_patch()

    print(f"Pipeline executado: {result}")
    print(f"Passos: {pipeline.history}")

    # Também é possível obter features de array no meio do fluxo
    psd = (
        HybridPipeline(patch, modality="das")
        .dascore("detrend", dim="time", type="linear")
        .apply_array("psd", sample_rate_hz=1000.0)
    )
    print(f"PSD shape: {psd.shape}")

    print("\nPipeline híbrido concluído com sucesso.")
