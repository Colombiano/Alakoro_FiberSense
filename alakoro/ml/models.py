"""
Alakoro FiberSense — Modelos de ML

Arquiteturas PyTorch para tarefas DAS/DTS/DSS:
  - CNN 2D para classificação de eventos
  - U-Net para segmentação espacial-temporal
  - MLP regressor para perfilagem de fluxo
"""

from __future__ import annotations

from typing import Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


class EventCNN(nn.Module):
    """
    CNN 2D leve para classificação de eventos em patches DAS.

    Entrada: (batch, 1, n_time, n_distance)
    Saída: (batch, n_classes)
    """

    def __init__(self,
                 input_shape: Tuple[int, int] = (128, 32),
                 n_classes: int = 2,
                 dropout: float = 0.3):
        super().__init__()
        self.input_shape = input_shape

        self.conv1 = nn.Conv2d(1, 16, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(16)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(32)
        self.conv3 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm2d(64)

        self.pool = nn.MaxPool2d(2, 2)
        self.dropout = nn.Dropout(dropout)

        # Calcula tamanho do flatten
        with torch.no_grad():
            dummy = torch.zeros(1, 1, *input_shape)
            flattened = self._forward_conv(dummy).view(1, -1).shape[1]

        self.fc1 = nn.Linear(flattened, 128)
        self.fc2 = nn.Linear(128, n_classes)

    def _forward_conv(self, x: torch.Tensor) -> torch.Tensor:
        x = self.pool(F.relu(self.bn1(self.conv1(x))))
        x = self.pool(F.relu(self.bn2(self.conv2(x))))
        x = self.pool(F.relu(self.bn3(self.conv3(x))))
        return x

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self._forward_conv(x)
        x = x.view(x.size(0), -1)
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        return self.fc2(x)


class UNet2D(nn.Module):
    """
    U-Net 2D para segmentação de eventos em patches DAS.

    Entrada: (batch, 1, n_time, n_distance)
    Saída: (batch, n_classes, n_time, n_distance)
    """

    def __init__(self,
                 input_shape: Tuple[int, int] = (128, 32),
                 n_classes: int = 1):
        super().__init__()
        self.input_shape = input_shape

        # Encoder
        self.enc1 = self._block(1, 32)
        self.enc2 = self._block(32, 64)
        self.enc3 = self._block(64, 128)

        self.pool = nn.MaxPool2d(2, 2)

        # Bottleneck
        self.bottleneck = self._block(128, 256)

        # Decoder
        self.upconv3 = nn.ConvTranspose2d(256, 128, kernel_size=2, stride=2)
        self.dec3 = self._block(256, 128)
        self.upconv2 = nn.ConvTranspose2d(128, 64, kernel_size=2, stride=2)
        self.dec2 = self._block(128, 64)
        self.upconv1 = nn.ConvTranspose2d(64, 32, kernel_size=2, stride=2)
        self.dec1 = self._block(64, 32)

        self.out = nn.Conv2d(32, n_classes, kernel_size=1)

    def _block(self, in_ch: int, out_ch: int) -> nn.Module:
        return nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))

        b = self.bottleneck(self.pool(e3))

        d3 = self.upconv3(b)
        d3 = self._crop_concat(d3, e3)
        d3 = self.dec3(d3)

        d2 = self.upconv2(d3)
        d2 = self._crop_concat(d2, e2)
        d2 = self.dec2(d2)

        d1 = self.upconv1(d2)
        d1 = self._crop_concat(d1, e1)
        d1 = self.dec1(d1)

        return self.out(d1)

    def _crop_concat(self, upsampled: torch.Tensor, bypass: torch.Tensor) -> torch.Tensor:
        """Corta o bypass para combinar com upsampled e concatena."""
        diff_h = bypass.size(2) - upsampled.size(2)
        diff_w = bypass.size(3) - upsampled.size(3)
        bypass = bypass[:, :, diff_h // 2:bypass.size(2) - (diff_h - diff_h // 2),
                              diff_w // 2:bypass.size(3) - (diff_w - diff_w // 2)]
        return torch.cat([upsampled, bypass], dim=1)


class FlowRegressor(nn.Module):
    """
    MLP/CNN híbrido para perfilagem de fluxo a partir de perfis DTS + DAS.

    Entrada: (batch, 2, n_time, n_distance) — canal 0: DAS, canal 1: DTS
    Saída: (batch, n_zones) — taxa de fluxo por zona
    """

    def __init__(self,
                 input_shape: Tuple[int, int] = (128, 32),
                 n_zones: int = 4):
        super().__init__()
        self.input_shape = input_shape

        self.conv = nn.Sequential(
            nn.Conv2d(2, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )

        with torch.no_grad():
            dummy = torch.zeros(1, 2, *input_shape)
            flattened = self.conv(dummy).view(1, -1).shape[1]

        self.fc = nn.Sequential(
            nn.Linear(flattened, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, n_zones),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv(x)
        x = x.view(x.size(0), -1)
        return self.fc(x)
