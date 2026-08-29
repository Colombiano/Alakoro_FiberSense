"""
Alakoro FiberSense — Treinamento de modelos ML

Trainer com early stopping, LR scheduling, checkpointing e logging.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset


class Trainer:
    """
    Treinador genérico para modelos PyTorch do Alakoro.
    """

    def __init__(self,
                 model: nn.Module,
                 optimizer: Optional[torch.optim.Optimizer] = None,
                 loss_fn: Optional[nn.Module] = None,
                 device: Optional[torch.device] = None,
                 log_interval: int = 10):
        self.model = model
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

        self.optimizer = optimizer or optim.Adam(model.parameters(), lr=1e-3)
        self.loss_fn = loss_fn or nn.CrossEntropyLoss()
        self.log_interval = log_interval

        self.history: Dict[str, list] = {"train_loss": [], "val_loss": [], "val_metric": []}

    def fit(self,
            train_loader: DataLoader,
            val_loader: Optional[DataLoader] = None,
            epochs: int = 10,
            early_stopping_patience: int = 5,
            checkpoint_dir: Optional[str] = None,
            metric_fn: Optional[Callable] = None) -> Dict[str, list]:
        """
        Treina o modelo.

        Args:
            train_loader: DataLoader de treino
            val_loader: DataLoader de validação (opcional)
            epochs: número de épocas
            early_stopping_patience: épocas sem melhora antes de parar
            checkpoint_dir: diretório para salvar checkpoints
            metric_fn: função de métrica (recebe y_true, y_pred)
        """
        best_val_loss = float("inf")
        patience_counter = 0

        for epoch in range(epochs):
            train_loss = self._train_epoch(train_loader)
            self.history["train_loss"].append(train_loss)

            log_msg = f"Epoch {epoch + 1}/{epochs} — train_loss: {train_loss:.4f}"

            if val_loader is not None:
                val_loss, val_metric = self._validate(val_loader, metric_fn)
                self.history["val_loss"].append(val_loss)
                self.history["val_metric"].append(val_metric)
                log_msg += f" — val_loss: {val_loss:.4f} — val_metric: {val_metric:.4f}"

                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    if checkpoint_dir:
                        self.save_checkpoint(Path(checkpoint_dir) / "best_model.pt")
                else:
                    patience_counter += 1

                if patience_counter >= early_stopping_patience:
                    print(f"Early stopping at epoch {epoch + 1}")
                    break

            if (epoch + 1) % self.log_interval == 0 or epoch == 0:
                print(log_msg)

        return self.history

    def _train_epoch(self, loader: DataLoader) -> float:
        self.model.train()
        total_loss = 0.0
        for x, y in loader:
            x, y = x.to(self.device), y.to(self.device)
            self.optimizer.zero_grad()
            outputs = self.model(x)
            loss = self.loss_fn(outputs, y)
            loss.backward()
            self.optimizer.step()
            total_loss += loss.item() * x.size(0)
        return total_loss / len(loader.dataset)

    def _validate(self, loader: DataLoader, metric_fn: Optional[Callable]) -> Tuple[float, float]:
        self.model.eval()
        total_loss = 0.0
        all_preds = []
        all_targets = []

        with torch.no_grad():
            for x, y in loader:
                x, y = x.to(self.device), y.to(self.device)
                outputs = self.model(x)
                loss = self.loss_fn(outputs, y)
                total_loss += loss.item() * x.size(0)

                if outputs.dim() > 1 and outputs.size(1) > 1:
                    preds = outputs.argmax(dim=1)
                else:
                    preds = (outputs > 0.5).float()

                all_preds.extend(preds.cpu().numpy())
                all_targets.extend(y.cpu().numpy())

        avg_loss = total_loss / len(loader.dataset)
        metric = 0.0
        if metric_fn is not None:
            metric = float(metric_fn(np.array(all_targets), np.array(all_preds)))
        return avg_loss, metric

    def save_checkpoint(self, path: Path):
        """Salva modelo, optimizer e histórico."""
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "history": self.history,
        }, str(path))

    def load_checkpoint(self, path: Path):
        """Carrega modelo, optimizer e histórico."""
        checkpoint = torch.load(str(path), map_location=self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.history = checkpoint.get("history", {"train_loss": [], "val_loss": [], "val_metric": []})
