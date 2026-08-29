"""
Testes da Fase 4 — Machine Learning.
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest
import torch

from src.io.alakoro_spool import AlakoroPatch
from src.io.dasdae import DASDAEAdapter
from src.ml import (
    DASDataset,
    DASFeatureExtractor,
    EventCNN,
    FlowRegressor,
    Trainer,
    UNet2D,
    evaluate_classifier,
    predict_event,
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
