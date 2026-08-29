"""
Testes da Fase 1 — C++20 core do Alakoro FiberSense.

Validam:
  - Importação do módulo nativo
  - Criação de DASData, DTSData, DSSData
  - Buffer protocol / zero-copy NumPy view
  - Acesso e modificação de elementos
  - Metadados
  - Processadores: detrend, demean, taper, decimate
  - Serialização JSON-LD
"""

import json
import math

import numpy as np
import pytest


def test_module_import():
    """O módulo nativo e o pacote Python devem importar."""
    import alakoro_core

    assert hasattr(alakoro_core, "DASData")
    assert hasattr(alakoro_core, "DTSData")
    assert hasattr(alakoro_core, "DSSData")


def test_data_shape_and_modality():
    """DASData deve reportar shape e modality corretamente."""
    from alakoro_core import DASData

    data = DASData(n_times=100, n_channels=64)
    assert data.n_times == 100
    assert data.n_channels == 64
    assert data.shape == (100, 64)
    assert data.modality == "DAS"


def test_numpy_zero_copy_view():
    """np.array(data) deve retornar uma view 2D sem cópia dos dados."""
    from alakoro_core import DASData

    data = DASData(n_times=10, n_channels=5)
    data[0, 0] = 3.14

    arr = np.array(data, copy=False)
    assert arr.shape == (10, 5)
    assert math.isclose(arr[0, 0], 3.14, rel_tol=1e-9)

    # Modificar o array deve refletir no objeto C++ (zero-copy)
    arr[1, 2] = 2.71
    assert math.isclose(data[1, 2], 2.71, rel_tol=1e-9)


def test_metadata_roundtrip():
    """Metadados devem ser acessíveis e modificáveis."""
    from alakoro_core import DASData, AcquisitionMetadata

    data = DASData(n_times=10, n_channels=5)
    data.metadata.sampling_rate_hz = 1000.0
    data.metadata.spatial_resolution_m = 1.25
    data.metadata.units = "strain_rate"

    assert data.metadata.sampling_rate_hz == 1000.0
    assert data.metadata.spatial_resolution_m == 1.25
    assert data.metadata.units == "strain_rate"


def test_detrend_removes_linear_trend():
    """detrend deve remover uma tendência linear por canal."""
    from alakoro_core import DASData, detrend

    n_t, n_c = 50, 4
    data = DASData(n_times=n_t, n_channels=n_c)
    arr = np.array(data, copy=False)

    for c in range(n_c):
        arr[:, c] = np.linspace(0, 10, n_t) + np.random.randn(n_t) * 0.1

    detrend(data)

    # Após detrend, a média e a inclinação devem ser próximas de zero
    for c in range(n_c):
        assert abs(arr[:, c].mean()) < 1e-6
        slope = np.polyfit(np.arange(n_t), arr[:, c], 1)[0]
        assert abs(slope) < 1e-6


def test_demean():
    """demean deve zerar a média de cada canal."""
    from alakoro_core import DASData, demean

    data = DASData(n_times=30, n_channels=3)
    arr = np.array(data, copy=False)
    arr[:, :] = np.random.randn(30, 3) + 5.0

    demean(data)

    for c in range(3):
        assert abs(arr[:, c].mean()) < 1e-12


def test_taper_reduces_edges():
    """taper deve atenuar as bordas temporais."""
    from alakoro_core import DASData, taper

    data = DASData(n_times=20, n_channels=2)
    arr = np.array(data, copy=False)
    arr[:, :] = 1.0

    taper(data, alpha=0.0)

    # Bordas devem ser menores que o centro
    assert arr[0, 0] < 1.0
    assert arr[-1, 0] < 1.0
    # O centro da janela deve ser o ponto de máxima amplitude
    center_value = arr[10, 0]
    assert center_value > arr[0, 0]
    assert center_value > arr[-1, 0]
    assert center_value > 0.99


def test_decimate_reduces_time_samples():
    """decimate deve reduzir o número de amostras temporais."""
    from alakoro_core import DASData, decimate

    data = DASData(n_times=100, n_channels=4)
    arr = np.array(data, copy=False)
    arr[:, :] = np.random.randn(100, 4)

    decimated = decimate(data, factor=4)
    assert decimated.n_channels == 4
    assert decimated.n_times == 25


def test_jsonld_serialization():
    """to_jsonld deve produzir JSON válido com campos esperados."""
    from alakoro_core import DASData

    data = DASData(n_times=5, n_channels=2)
    data.metadata.sampling_rate_hz = 1000.0
    data.metadata.units = "strain_rate"

    payload = data.to_jsonld()
    parsed = json.loads(payload)

    assert parsed["modality"] == "DAS"
    assert parsed["shape"] == [5, 2]
    assert parsed["metadata"]["sampling_rate_hz"] == 1000.0
    assert parsed["metadata"]["units"] == "strain_rate"
    assert len(parsed["data"]) == 5
    assert len(parsed["data"][0]) == 2


def test_dts_and_dss_modalities():
    """DTS e DSS devem ter modality e unidades padrão distintas."""
    from alakoro_core import DTSData, DSSData

    dts = DTSData(n_times=10, n_channels=5)
    dss = DSSData(n_times=10, n_channels=5)

    assert dts.modality == "DTS"
    assert dss.modality == "DSS"
