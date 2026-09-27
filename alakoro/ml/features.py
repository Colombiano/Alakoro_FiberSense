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


class DTSFeatureExtractor:
    """
    Extrator configurável de features para patches DTS.

    Além de estatísticas e espectrais básicas, inclui features térmicas
    como gradiente geotérmico, anomalias e dT/dz.
    """

    def __init__(self,
                 stats: bool = True,
                 spectral: bool = True,
                 thermal: bool = True,
                 anomaly: bool = True):
        self.stats = stats
        self.spectral = spectral
        self.thermal = thermal
        self.anomaly = anomaly

    def __call__(self, patch: np.ndarray, depth_step_m: float = 1.0) -> np.ndarray:
        """Extrai features de um patch 2D DTS (time, depth)."""
        features = []

        if self.stats:
            features.append(self._statistical_features(patch))

        if self.spectral:
            features.append(self._spectral_features(patch))

        if self.thermal:
            features.append(self._thermal_features(patch, depth_step_m))

        if self.anomaly:
            features.append(self._anomaly_features(patch))

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
        """Features espectrais via Welch ao longo do tempo (média por canal)."""
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

    def _thermal_features(self, patch: np.ndarray, depth_step_m: float) -> np.ndarray:
        """Features térmicas: gradiente médio e variabilidade espacial."""
        n_t, n_c = patch.shape
        if n_c < 2:
            return np.zeros(5, dtype=np.float32)

        # Gradiente geotérmico médio no tempo (dT/dz)
        gradients = np.zeros((n_t, n_c - 1), dtype=np.float32)
        for t in range(n_t):
            gradients[t, :] = np.gradient(patch[t, :], depth_step_m)[:n_c - 1]

        mean_profile = np.mean(patch, axis=0)
        depth = np.arange(n_c) * depth_step_m
        geo_gradient = float(np.polyfit(depth, mean_profile, 1)[0])

        return np.array([
            geo_gradient,
            gradients.mean(),
            gradients.std(),
            gradients.max(),
            gradients.min(),
        ], dtype=np.float32)

    def _anomaly_features(self, patch: np.ndarray) -> np.ndarray:
        """Features de anomalia: outliers temporais por canal."""
        mean_per_channel = patch.mean(axis=0)
        std_per_channel = patch.std(axis=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            zscore = (patch - mean_per_channel) / (std_per_channel + 1e-12)

        anomaly_mask = np.abs(zscore) > 3.0
        anomaly_ratio = anomaly_mask.mean()
        max_zscore = np.max(np.abs(zscore))

        return np.array([
            anomaly_ratio,
            max_zscore,
            np.sum(anomaly_mask),
            np.std(std_per_channel),
        ], dtype=np.float32)


def extract_features_batch(patches: list,
                           extractor: Optional[DASFeatureExtractor] = None) -> np.ndarray:
    """Extrai features de uma lista de patches NumPy."""
    if extractor is None:
        extractor = DASFeatureExtractor()
    return np.stack([extractor(p) for p in patches])
