"""
Alakoro FiberSense — Avaliação de modelos ML

Métricas de classificação e regressão para modelos DAS.
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import (
    accuracy_score,
    auc,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from torch.utils.data import DataLoader


def evaluate_classifier(model: nn.Module,
                        loader: DataLoader,
                        device: Optional[torch.device] = None) -> Dict[str, float]:
    """
    Avalia um modelo classificador e retorna métricas.
    """
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    all_probs = []
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            outputs = model(x)
            probs = torch.softmax(outputs, dim=1)
            preds = outputs.argmax(dim=1)

            all_probs.append(probs.cpu().numpy())
            all_preds.append(preds.cpu().numpy())
            all_targets.append(y.numpy())

    probs = np.concatenate(all_probs)
    preds = np.concatenate(all_preds)
    targets = np.concatenate(all_targets)

    metrics = {
        "accuracy": accuracy_score(targets, preds),
        "precision": precision_score(targets, preds, average="macro", zero_division=0),
        "recall": recall_score(targets, preds, average="macro", zero_division=0),
        "f1": f1_score(targets, preds, average="macro", zero_division=0),
    }

    if probs.shape[1] == 2:
        metrics["roc_auc"] = roc_auc_score(targets, probs[:, 1])
        precision, recall, _ = precision_recall_curve(targets, probs[:, 1])
        metrics["pr_auc"] = auc(recall, precision)

    return metrics


def evaluate_regressor(model: nn.Module,
                       loader: DataLoader,
                       device: Optional[torch.device] = None) -> Dict[str, float]:
    """
    Avalia um modelo regressor e retorna métricas.
    """
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    all_preds = []
    all_targets = []

    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            outputs = model(x)
            all_preds.append(outputs.cpu().numpy())
            all_targets.append(y.cpu().numpy())

    preds = np.concatenate(all_preds)
    targets = np.concatenate(all_targets)

    mse = np.mean((preds - targets) ** 2)
    mae = np.mean(np.abs(preds - targets))
    return {
        "mse": mse,
        "mae": mae,
        "rmse": np.sqrt(mse),
    }


def get_roc_curve(targets: np.ndarray, scores: np.ndarray):
    """Retorna pontos da curva ROC."""
    return roc_curve(targets, scores)


def get_pr_curve(targets: np.ndarray, scores: np.ndarray):
    """Retorna pontos da curva precision-recall."""
    return precision_recall_curve(targets, scores)
