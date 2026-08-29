"""
Alakoro FiberSense — API de inferência ML

Funções de alto nível para predição com modelos treinados.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn as nn

from src.io.alakoro_spool import AlakoroPatch
from src.ml.models import EventCNN, FlowRegressor, UNet2D


def predict_event(model: nn.Module,
                  patch: Union[AlakoroPatch, np.ndarray],
                  device: Optional[torch.device] = None,
                  threshold: float = 0.5) -> Dict[str, Union[bool, float, Tuple]]:
    """
    Prediz se um patch contém um evento.

    Retorna:
        {
            "event": bool,
            "confidence": float,
            "location": (t_index, d_index) se houver evento
        }
    """
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    if isinstance(patch, AlakoroPatch):
        data = patch.data
    else:
        data = patch

    tensor = torch.from_numpy(data.astype(np.float32)).unsqueeze(0).unsqueeze(0)
    tensor = tensor.to(device)

    with torch.no_grad():
        output = model(tensor)
        probs = torch.softmax(output, dim=1)
        confidence = float(probs[0, 1].cpu().numpy())
        event = confidence >= threshold

    result: Dict[str, Union[bool, float, Tuple]] = {
        "event": event,
        "confidence": confidence,
    }

    if event:
        # Localização aproximada: ponto de máxima amplitude
        t_idx, d_idx = np.unravel_index(np.argmax(np.abs(data)), data.shape)
        result["location"] = (int(t_idx), int(d_idx))

    return result


def predict_segmentation(model: nn.Module,
                         patch: Union[AlakoroPatch, np.ndarray],
                         device: Optional[torch.device] = None,
                         threshold: float = 0.5) -> np.ndarray:
    """
    Prediz máscara de segmentação para um patch.

    Retorna array binário (n_time, n_distance).
    """
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    if isinstance(patch, AlakoroPatch):
        data = patch.data
    else:
        data = patch

    tensor = torch.from_numpy(data.astype(np.float32)).unsqueeze(0).unsqueeze(0)
    tensor = tensor.to(device)

    with torch.no_grad():
        output = model(tensor)
        probs = torch.sigmoid(output)
        mask = (probs > threshold).float()

    return mask.squeeze().cpu().numpy()


def predict_flow(model: nn.Module,
                 das_patch: Union[AlakoroPatch, np.ndarray],
                 dts_patch: Union[AlakoroPatch, np.ndarray],
                 device: Optional[torch.device] = None) -> Dict[str, list]:
    """
    Prediz taxa de fluxo por zona a partir de DAS + DTS.

    Retorna:
        {"zones": [{"zone": int, "rate": float}]}
    """
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    def _to_array(p):
        return p.data if isinstance(p, AlakoroPatch) else p

    das = _to_array(das_patch)
    dts = _to_array(dts_patch)

    # Empilha canais: (1, 2, time, distance)
    stacked = np.stack([das, dts], axis=0).astype(np.float32)
    tensor = torch.from_numpy(stacked).unsqueeze(0).to(device)

    with torch.no_grad():
        output = model(tensor)
        rates = output.squeeze().cpu().numpy()

    return {
        "zones": [
            {"zone": i, "rate": float(rate)}
            for i, rate in enumerate(rates)
        ]
    }


def load_model_for_inference(model_class: str,
                             checkpoint_path: str,
                             input_shape: Tuple[int, int] = (128, 32),
                             n_classes: int = 2,
                             n_zones: int = 4) -> nn.Module:
    """
    Carrega um modelo salvo para inferência.

    Args:
        model_class: 'EventCNN', 'UNet2D' ou 'FlowRegressor'
        checkpoint_path: caminho para o checkpoint do Trainer
    """
    if model_class == "EventCNN":
        model = EventCNN(input_shape=input_shape, n_classes=n_classes)
    elif model_class == "UNet2D":
        model = UNet2D(input_shape=input_shape, n_classes=n_classes)
    elif model_class == "FlowRegressor":
        model = FlowRegressor(input_shape=input_shape, n_zones=n_zones)
    else:
        raise ValueError(f"Unknown model class: {model_class}")

    checkpoint = torch.load(str(checkpoint_path), map_location="cpu")
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model
