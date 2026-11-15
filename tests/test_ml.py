"""
Testes da Fase 4 — Machine Learning.
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest
import torch

from alakoro.io.alakoro_spool import AlakoroPatch
from alakoro.io.dasdae import DASDAEAdapter
from alakoro.ml import (
    DASDataset,
    DASFeatureExtractor,
    EventCNN,
    FlowRegressor,
    Trainer,
    UNet2D,
    evaluate_classifier,
    predict_event,
    predict_flow,
    predict_segmentation,
    split_dataset,
)


def _make_patch(n_t=64, n_d=16, label=0):
    data = np.random.randn(n_t, n_d).astype(np.float32)
    if label == 1:
        # Simula um evento localizado
        data[20:40, 5:10] += 5.0
    patch = DASDAEAdapter.array_to_patch(data, modality="das")
    return AlakoroPatch(patch, modality="das")


def test_das_dataset_shape():
    patches = [_make_patch() for _ in range(4)]
    labels = [0, 1, 0, 1]
    dataset = DASDataset(patches, labels=labels, window_size=(32, 8), stride=(32, 8))

    x, y = dataset[0]
    assert x.shape == (1, 32, 8)
    assert y in {0, 1}


def test_split_dataset():
    patches = [_make_patch() for _ in range(20)]
    labels = [i % 2 for i in range(20)]
    dataset = DASDataset(patches, labels=labels, window_size=(32, 8), stride=(32, 8))

    train, val, test = split_dataset(dataset, train_frac=0.6, val_frac=0.2)
    assert len(train) > 0
    assert len(val) > 0
    assert len(test) > 0


def test_feature_extractor():
    patch = np.random.randn(64, 16).astype(np.float32)
    extractor = DASFeatureExtractor(stats=True, spectral=True, wavelet=False, das_specific=True)
    features = extractor(patch)
    assert features.ndim == 1
    assert features.size > 0
    assert np.all(np.isfinite(features))


def test_event_cnn_forward():
    model = EventCNN(input_shape=(64, 16), n_classes=2)
    x = torch.randn(2, 1, 64, 16)
    out = model(x)
    assert out.shape == (2, 2)


def test_unet_forward():
    model = UNet2D(input_shape=(64, 16), n_classes=1)
    x = torch.randn(2, 1, 64, 16)
    out = model(x)
    assert out.shape == (2, 1, 64, 16)


def test_flow_regressor_forward():
    model = FlowRegressor(input_shape=(64, 16), n_zones=4)
    x = torch.randn(2, 2, 64, 16)
    out = model(x)
    assert out.shape == (2, 4)


def test_trainer_classifier():
    patches = [_make_patch(label=i % 2) for i in range(8)]
    labels = [i % 2 for i in range(8)]
    dataset = DASDataset(patches, labels=labels, window_size=(32, 8), stride=(32, 8))

    train, val, test = split_dataset(dataset, train_frac=0.6, val_frac=0.2, random_seed=42)
    train_loader = torch.utils.data.DataLoader(train, batch_size=2)
    val_loader = torch.utils.data.DataLoader(val, batch_size=2)

    model = EventCNN(input_shape=(32, 8), n_classes=2)
    trainer = Trainer(model, loss_fn=torch.nn.CrossEntropyLoss())

    history = trainer.fit(train_loader, val_loader, epochs=2, early_stopping_patience=5)
    assert "train_loss" in history
    assert len(history["train_loss"]) == 2


def test_predict_event():
    model = EventCNN(input_shape=(64, 16), n_classes=2)
    patch = _make_patch(label=1)
    result = predict_event(model, patch)
    assert "event" in result
    assert "confidence" in result


def test_predict_segmentation():
    model = UNet2D(input_shape=(64, 16), n_classes=1)
    patch = _make_patch(label=1)
    mask = predict_segmentation(model, patch)
    assert mask.shape == (64, 16)


def test_evaluate_classifier():
    patches = [_make_patch(label=i % 2) for i in range(8)]
    labels = [i % 2 for i in range(8)]
    dataset = DASDataset(patches, labels=labels, window_size=(32, 8), stride=(32, 8))
    loader = torch.utils.data.DataLoader(dataset, batch_size=2)

    model = EventCNN(input_shape=(32, 8), n_classes=2)
    metrics = evaluate_classifier(model, loader)
    assert "accuracy" in metrics
    assert "f1" in metrics


# =============================================================================
# CL-02 — Alinhamento multimodal antes do stack (ML:D-02)
# =============================================================================

def _make_modality_patch(n_t=64, n_d=16, dt_s=2.0, dx_m=1.0, modality="das",
                         units=None):
    data = np.random.default_rng(1).normal(size=(n_t, n_d)).astype(np.float64)
    patch = DASDAEAdapter.array_to_patch(
        data, modality=modality, dt_s=dt_s, dx_m=dx_m, units=units
    )
    return AlakoroPatch(patch, modality=modality)


def test_predict_flow_same_shape_arrays():
    """Arrays com mesmo shape e sem coordenadas: caminho legado preservado."""
    model = FlowRegressor(input_shape=(64, 16), n_zones=4)
    das = np.random.default_rng(0).normal(size=(64, 16)).astype(np.float32)
    dts = np.random.default_rng(0).normal(size=(64, 16)).astype(np.float32)
    result = predict_flow(model, das, dts)
    assert len(result["zones"]) == 4
    assert all("rate" in z for z in result["zones"])


def test_predict_flow_mismatched_arrays_raise():
    """Shapes diferentes sem coordenadas: ValueError claro."""
    model = FlowRegressor(input_shape=(64, 16), n_zones=4)
    das = np.random.default_rng(0).normal(size=(64, 16)).astype(np.float32)
    dts = np.random.default_rng(0).normal(size=(32, 16)).astype(np.float32)
    with pytest.raises(ValueError, match="align"):
        predict_flow(model, das, dts)


def test_predict_flow_regrids_divergent_patches():
    """Patches com grades temporais diferentes são realinhados antes do stack.

    DAS: 64 amostras @ dt=2s (0..126s); DTS: 32 amostras @ dt=4s (0..124s).
    A grade comum é a mais grosseira (DTS): 32 tempos. O FlowRegressor é
    construído com input_shape (32, 16) para provar que o tensor empilhado
    chega com as dimensões realinhadas.
    """
    model = FlowRegressor(input_shape=(32, 16), n_zones=4)
    das_patch = _make_modality_patch(n_t=64, n_d=16, dt_s=2.0, modality="das",
                                     units="1/s")
    dts_patch = _make_modality_patch(n_t=32, n_d=16, dt_s=4.0, modality="dts",
                                     units="degC")
    result = predict_flow(model, das_patch, dts_patch)
    assert len(result["zones"]) == 4


def test_predict_flow_rejects_patch_plus_array():
    """Um patch com coordenadas + array puro de shape diferente: ValueError."""
    model = FlowRegressor(input_shape=(64, 16), n_zones=4)
    das_patch = _make_modality_patch(n_t=64, n_d=16, dt_s=2.0, modality="das")
    dts = np.random.default_rng(0).normal(size=(32, 16)).astype(np.float32)
    with pytest.raises(ValueError, match="coordinate grids"):
        predict_flow(model, das_patch, dts)


def test_flow_regressor_channel_guard():
    """FlowRegressor exige exatamente 2 canais (DAS+DTS alinhados)."""
    model = FlowRegressor(input_shape=(16, 8), n_zones=4)
    with pytest.raises(ValueError, match="batch, 2"):
        model(torch.randn(1, 3, 16, 8))
