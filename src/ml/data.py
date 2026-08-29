"""
Alakoro FiberSense — Dados para ML

DASDataset e DASDataLoader para consumir patches Alakoro/DASCore e
alimentar modelos PyTorch.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple, Union

import numpy as np
import torch
from torch.utils.data import Dataset

from src.io.alakoro_spool import AlakoroPatch, AlakoroSpool


class DASDataset(Dataset):
    """
    Dataset PyTorch para patches de DAS/DTS/DSS.

    Aceita:
      - AlakoroSpool
      - Lista de AlakoroPatch
      - Diretório de arquivos (via AlakoroSpool.from_directory)
      - Arrays NumPy com labels

    Cada patch é cortado em janelas (patches) de tamanho fixo.
    """

    def __init__(self,
                 source: Union[AlakoroSpool, Sequence[AlakoroPatch], np.ndarray, str, Path],
                 labels: Optional[Sequence[int]] = None,
                 window_size: Tuple[int, int] = (128, 32),
                 stride: Tuple[int, int] = (64, 16),
                 transform: Optional[Callable[[np.ndarray], np.ndarray]] = None,
                 normalize: str = "zscore"):
        """
        Args:
            source: origem dos dados
            labels: labels por patch (quando source é lista/spool)
            window_size: (n_time, n_distance) da janela extraída
            stride: passo entre janelas
            transform: função opcional de augmentação/pré-processamento
            normalize: 'zscore', 'minmax', 'robust' ou None
        """
        self.window_size = window_size
        self.stride = stride
        self.transform = transform
        self.normalize = normalize

        self.samples: List[Tuple[np.ndarray, int]] = []

        if isinstance(source, (str, Path)):
            spool = AlakoroSpool.from_directory(str(source))
            source = list(spool)

        if isinstance(source, AlakoroSpool):
            source = list(source)

        if isinstance(source, np.ndarray):
            # Array 3D: (n_samples, n_time, n_distance) com labels
            if labels is None:
                raise ValueError("labels required when source is ndarray")
            for arr, label in zip(source, labels):
                self.samples.append((arr.astype(np.float32), int(label)))
        else:
            # Sequence[AlakoroPatch]
            if labels is None:
                labels = [0] * len(source)
            if len(labels) != len(source):
                raise ValueError("labels and source must have same length")

            for patch, label in zip(source, labels):
                windows = self._extract_windows(patch.data)
                for w in windows:
                    self.samples.append((w, int(label)))

    def _extract_windows(self, data: np.ndarray) -> List[np.ndarray]:
        """Extrai janelas deslizantes 2D do patch."""
        n_t, n_d = data.shape
        w_t, w_d = self.window_size
        s_t, s_d = self.stride

        windows = []
        for t in range(0, max(1, n_t - w_t + 1), s_t):
            for d in range(0, max(1, n_d - w_d + 1), s_d):
                window = data[t:t + w_t, d:d + w_d]
                if window.shape != (w_t, w_d):
                    # Padding se necessário
                    pad_t = w_t - window.shape[0]
                    pad_d = w_d - window.shape[1]
                    window = np.pad(window, ((0, pad_t), (0, pad_d)), mode="edge")
                windows.append(window.astype(np.float32))
        return windows if windows else [np.zeros((w_t, w_d), dtype=np.float32)]

    def _normalize(self, arr: np.ndarray) -> np.ndarray:
        if self.normalize == "zscore":
            mean = arr.mean()
            std = arr.std() + 1e-8
            return (arr - mean) / std
        elif self.normalize == "minmax":
            min_val = arr.min()
            max_val = arr.max() + 1e-8
            return (arr - min_val) / (max_val - min_val)
        elif self.normalize == "robust":
            median = np.median(arr)
            iqr = np.percentile(arr, 75) - np.percentile(arr, 25) + 1e-8
            return (arr - median) / iqr
        return arr

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        arr, label = self.samples[idx]
        if self.transform:
            arr = self.transform(arr)
        arr = self._normalize(arr)
        # Adiciona canal: (1, time, distance)
        tensor = torch.from_numpy(arr).unsqueeze(0)
        return tensor, label


def split_dataset(dataset: DASDataset,
                  train_frac: float = 0.7,
                  val_frac: float = 0.15,
                  random_seed: int = 42) -> Tuple[DASDataset, DASDataset, DASDataset]:
    """Divide o dataset em treino/validação/teste."""
    n = len(dataset)
    indices = np.arange(n)
    np.random.seed(random_seed)
    np.random.shuffle(indices)

    n_train = int(n * train_frac)
    n_val = int(n * val_frac)

    train_idx = indices[:n_train]
    val_idx = indices[n_train:n_train + n_val]
    test_idx = indices[n_train + n_val:]

    return (
        torch.utils.data.Subset(dataset, train_idx),
        torch.utils.data.Subset(dataset, val_idx),
        torch.utils.data.Subset(dataset, test_idx),
    )
