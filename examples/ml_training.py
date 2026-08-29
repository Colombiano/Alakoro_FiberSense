"""
Exemplo 4 — Treinamento de CNN para detecção de eventos DAS.

Usa dados sintéticos gerados a partir de patches com/sem evento.
"""

import numpy as np
import torch

from src.io.alakoro_spool import AlakoroPatch
from src.io.dasdae import DASDAEAdapter
from src.ml import DASDataset, EventCNN, Trainer, split_dataset


def generate_synthetic_data(n_samples=100, n_t=64, n_d=16):
    """Gera patches sintéticos com e sem evento."""
    patches = []
    labels = []
    for i in range(n_samples):
        data = np.random.randn(n_t, n_d).astype(np.float32)
        label = i % 2
        if label == 1:
            # Evento localizado
            data[20:45, 5:11] += 4.0
        patch = DASDAEAdapter.array_to_patch(data, modality="das")
        patches.append(AlakoroPatch(patch, modality="das"))
        labels.append(label)
    return patches, labels


if __name__ == "__main__":
    patches, labels = generate_synthetic_data(n_samples=120)

    dataset = DASDataset(
        patches,
        labels=labels,
        window_size=(32, 8),
        stride=(32, 8),
        normalize="zscore",
    )

    train, val, test = split_dataset(dataset, train_frac=0.7, val_frac=0.15)
    train_loader = torch.utils.data.DataLoader(train, batch_size=8, shuffle=True)
    val_loader = torch.utils.data.DataLoader(val, batch_size=8)

    model = EventCNN(input_shape=(32, 8), n_classes=2)
    trainer = Trainer(model, loss_fn=torch.nn.CrossEntropyLoss())

    print("Iniciando treinamento...")
    history = trainer.fit(
        train_loader,
        val_loader,
        epochs=5,
        early_stopping_patience=3,
    )

    print(f"Histórico: {history}")
