"""
Testes do processador térmico DTS e integração com C++20.
"""

import numpy as np
import pytest

from alakoro_core import (
    DTSData,
    geothermal_baseline_correction,
    spatial_median_filter,
    thermal_anomaly_detection,
    thermal_gradient,
)

from src.io.alakoro_spool import AlakoroPatch
from src.io.dasdae import DASDAEAdapter
from src.ml.features import DTSFeatureExtractor
from src.processing.advanced_processors import (
    geothermal_baseline_correction as py_geothermal_baseline,
    spatial_median_filter as py_spatial_median,
    thermal_anomaly_detection as py_thermal_anomaly,
    thermal_gradient as py_thermal_gradient,
)
from src.processing.dts_processor import DTSThermalProcessor


def _make_dts(n_t=128, n_c=16):
    """Cria DTSData sintético com gradiente geotérmico e anomalia."""
    depth = np.arange(n_c, dtype=np.float64)
    time = np.arange(n_t, dtype=np.float64)
    # baseline geotérmico: 20 + 0.03 * depth
    baseline = 20.0 + 0.03 * depth[np.newaxis, :]
    # anomalia localizada aproximadamente no meio do perfil
    anomaly = np.zeros((n_t, n_c), dtype=np.float64)
    mid_c = n_c // 2
    mid_t = n_t // 2
    # pulso quente localizado no tempo e no canal do meio
    t0, t1 = max(0, mid_t - 5), min(n_t, mid_t + 5)
    anomaly[t0:t1, mid_c] = 20.0
    noise = 0.1 * np.random.randn(n_t, n_c)
    return baseline + anomaly + noise


def _make_clean_dts(n_t=128, n_c=16):
    """Cria DTSData sintético apenas com gradiente geotérmico e ruído."""
    depth = np.arange(n_c, dtype=np.float64)
    baseline = 20.0 + 0.03 * depth[np.newaxis, :]
    noise = 0.1 * np.random.randn(n_t, n_c)
    return baseline + noise


def _make_dts_patch(n_t=128, n_c=16):
    data = _make_dts(n_t, n_c)
    patch = DASDAEAdapter.array_to_patch(data, modality="dts", dx_m=1.0)
    return AlakoroPatch(patch, modality="dts")


def test_dts_data_buffer():
    data = _make_dts(64, 8)
    dts = DTSData(n_times=data.shape[0], n_channels=data.shape[1])
    arr = np.array(dts, copy=False)
    arr[:, :] = data
    assert dts.n_times == 64
    assert dts.n_channels == 8
    assert dts.modality == "DTS"
    assert np.allclose(np.array(dts, copy=True), data)


def test_thermal_gradient_cpp():
    patch = _make_dts_patch(128, 16)
    grad = py_thermal_gradient(patch, depth_step_m=1.0)
    assert grad.shape == (128, 16)
    # O gradiente geotérmico médio deve estar próximo de 0.03 °C/m
    assert 0.02 <= np.mean(grad) <= 0.05


def test_geothermal_baseline_correction_cpp():
    patch = _make_dts_patch(128, 16)
    corrected = py_geothermal_baseline(
        patch, depth_step_m=1.0, surface_temp=20.0, gradient=0.03
    )
    assert isinstance(corrected, AlakoroPatch)
    assert corrected.modality == "dts"
    # Resíduo médio por canal deve ser pequeno, exceto no canal com anomalia
    mean_residual = np.mean(np.abs(corrected.data), axis=0)
    # Ignora o canal do meio (anomalia)
    mask = np.ones(16, dtype=bool)
    mask[8] = False
    assert np.all(mean_residual[mask] < 1.0)


def test_thermal_anomaly_detection_cpp():
    patch = _make_dts_patch(128, 16)
    anomalies = py_thermal_anomaly(patch, threshold_sigma=1.5)
    assert anomalies.shape == (128, 16)
    # O canal do meio deve ter anomalias
    assert anomalies[:, 8].sum() > 0


def test_spatial_median_filter_cpp():
    patch = _make_dts_patch(128, 16)
    filtered = py_spatial_median(patch, window_size=5)
    assert isinstance(filtered, AlakoroPatch)
    assert filtered.shape == patch.shape
    assert filtered.modality == "dts"


def test_dts_thermal_processor_pipeline():
    data = _make_dts(128, 16)
    proc = DTSThermalProcessor(
        depth_step_m=1.0,
        surface_temp=20.0,
        geothermal_gradient=0.03,
        spatial_median_window=5,
        anomaly_threshold_sigma=2.0,
        use_cpp_backend=True,
    )
    result = proc.process(data)

    assert result["temperature_preprocessed"].shape == (128, 16)
    assert result["temperature_corrected"].shape == (128, 16)
    assert result["thermal_gradient"].shape == (128, 16)
    assert result["anomalies"].shape == (128, 16)
    assert result["mean_temperature"].shape == (16,)
    assert result["std_temperature"].shape == (16,)
    assert result["max_anomaly_score"].shape == (16,)
    assert result["metadata"]["use_cpp_backend"] is True


def test_dts_feature_extractor():
    data = _make_dts(128, 16)
    extractor = DTSFeatureExtractor()
    features = extractor(data, depth_step_m=1.0)
    assert features.ndim == 1
    assert features.size == 21  # 8 stats + 4 spectral + 5 thermal + 4 anomaly
    assert np.all(np.isfinite(features))


def test_dts_processor_rejects_non_dts_modality():
    data = np.random.randn(64, 8)
    patch = DASDAEAdapter.array_to_patch(data, modality="das")
    das_patch = AlakoroPatch(patch, modality="das")
    with pytest.raises(ValueError, match="exclusivo para modalidade DTS"):
        py_thermal_gradient(das_patch, depth_step_m=1.0)


def test_dts_thermal_front_velocity():
    data = _make_dts(64, 16)
    proc = DTSThermalProcessor()
    depth = np.arange(16, dtype=np.float64)
    time_s = np.arange(64, dtype=np.float64)
    front_depth, velocity = proc.compute_thermal_front_velocity(
        data, depth, time_s, threshold=0.5
    )
    assert front_depth.shape == (64,)
    assert velocity.shape == (63,)
