"""
Alakoro FiberSense — Extração de features para ML

Features estatísticas, espectrais e wavelet para dados DAS/DTS/DSS.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from scipy import signal, stats


class DASFeatureExtractor:
    """
    Extrator configurável de features para patches DAS.

    Pode operar em modo 'flat' (vetor 1D) ou 'image' (mapa 2D).
    """

    def __init__(self,
                 stats: bool = True,
                 spectral: bool = True,
                 wavelet: bool = False,
                 das_specific: bool = True):
        self.stats = stats
        self.spectral = spectral
        self.wavelet = wavelet
        self.das_specific = das_specific

    def __call__(self, patch: np.ndarray) -> np.ndarray:
        """Extrai features de um patch 2D (time, distance)."""
        features = []

        if self.stats:
            features.append(self._statistical_features(patch))

        if self.spectral:
            features.append(self._spectral_features(patch))

        if self.wavelet:
            features.append(self._wavelet_features(patch))

        if self.das_specific:
            features.append(self._das_features(patch))

        return np.concatenate(features)

    def _statistical_features(self, patch: np.ndarray) -> np.ndarray:
        return np.array([
            patch.mean(),
            patch.std(),
            np.median(patch),
            np.percentile(patch, 25),
            np.percentile(patch, 75),
            np.max(np.abs(patch)),
            float(stats.skew(patch.ravel())),
            float(stats.kurtosis(patch.ravel())),
        ], dtype=np.float32)

    def _spectral_features(self, patch: np.ndarray) -> np.ndarray:
        """Features espectrais via STFT ao longo do tempo (média por canal)."""
        n_t, n_c = patch.shape
        if n_t < 8:
            return np.zeros(4, dtype=np.float32)

        psd_per_channel = []
        for c in range(n_c):
            f, psd = signal.welch(patch[:, c], fs=1.0, nperseg=min(64, n_t))
            psd_per_channel.append(psd)

        psd_mean = np.mean(psd_per_channel, axis=0)
        return np.array([
            psd_mean.mean(),
            psd_mean.std(),
            psd_mean.max(),
            float(f[np.argmax(psd_mean)] if len(f) > 0 else 0.0),
        ], dtype=np.float32)

    def _wavelet_features(self, patch: np.ndarray) -> np.ndarray:
        """Features wavelet simplificadas usando CWT Morlet."""
        from scipy.signal import morlet2, cwt

        n_t, n_c = patch.shape
        if n_t < 16 or n_c < 2:
            return np.zeros(4, dtype=np.float32)

        # Usa apenas o primeiro canal para simplificar
        widths = np.arange(1, min(16, n_t // 2))
        w = morlet2(min(n_t, 64), 6)
        try:
            coef = cwt(patch[:, 0], lambda t, w: morlet2(t, w).imag, widths)
            energy = np.abs(coef) ** 2
            return np.array([
                energy.mean(),
                energy.std(),
                energy.max(),
                float(np.unravel_index(np.argmax(energy), energy.shape)[0]),
            ], dtype=np.float32)
        except Exception:
            return np.zeros(4, dtype=np.float32)

    def _das_features(self, patch: np.ndarray) -> np.ndarray:
        """Features específicas de DAS: strain rate e velocidade aparente."""
        n_t, n_c = patch.shape
        if n_t < 2 or n_c < 2:
            return np.zeros(4, dtype=np.float32)

        # Strain rate aproximado: derivada temporal média
        strain_rate = np.mean(np.abs(np.diff(patch, axis=0)))

        # Velocidade aparente simplificada: correlação entre canais adjacentes
        correlations = []
        for c in range(n_c - 1):
            if patch[:, c].std() > 0 and patch[:, c + 1].std() > 0:
                corr = np.corrcoef(patch[:, c], patch[:, c + 1])[0, 1]
                correlations.append(corr)
        mean_corr = np.mean(correlations) if correlations else 0.0

        return np.array([
            strain_rate,
            mean_corr,
            np.max(patch) - np.min(patch),  # amplitude pico-a-pico
            float(np.argmax(np.abs(patch)) / max(patch.size, 1)),
        ], dtype=np.float32)


def extract_features_batch(patches: list,
                           extractor: Optional[DASFeatureExtractor] = None) -> np.ndarray:
    """Extrai features de uma lista de patches NumPy."""
    if extractor is None:
        extractor = DASFeatureExtractor()
    return np.stack([extractor(p) for p in patches])
