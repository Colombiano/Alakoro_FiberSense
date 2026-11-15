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

    A velocidade aparente (ML:D-04) é estimada com SINAL por correlação de
    pico entre canais adjacentes — v = Δz/Δt — e é reportada em m/s quando
    fs_hz e channel_spacing_m são informados, ou em canais/amostra caso
    contrário. / The apparent velocity feature is estimated WITH SIGN via
    peak cross-correlation between adjacent channels (v = Δz/Δt), reported
    in m/s when fs_hz and channel_spacing_m are given.
    """

    def __init__(self,
                 stats: bool = True,
                 spectral: bool = True,
                 wavelet: bool = False,
                 das_specific: bool = True,
                 fs_hz: Optional[float] = None,
                 channel_spacing_m: Optional[float] = None):
        self.stats = stats
        self.spectral = spectral
        self.wavelet = wavelet
        self.das_specific = das_specific
        self.fs_hz = fs_hz
        self.channel_spacing_m = channel_spacing_m

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
        """Features espectrais via Welch ao longo do tempo (média por canal).

        Usa a taxa de amostragem real fs_hz (ML:I-03) quando informada no
        construtor; caso contrário assume fs=1.0 (comportamento legado).
        """
        n_t, n_c = patch.shape
        if n_t < 8:
            return np.zeros(4, dtype=np.float32)

        fs = float(self.fs_hz) if self.fs_hz else 1.0
        psd_per_channel = []
        for c in range(n_c):
            f, psd = signal.welch(patch[:, c], fs=fs, nperseg=min(64, n_t))
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

    def _apparent_velocity(self, patch: np.ndarray) -> float:
        """
        Velocidade aparente COM SINAL (ML:D-04) via correlação de pico entre
        canais adjacentes: v = Δz/Δt, com Δt atraso do pico de correlação
        cruzada. Eventos descendentes (atraso crescente com a profundidade)
        têm v > 0; ascendentes têm v < 0. / Signed apparent velocity via
        peak cross-correlation between adjacent channels; downward events
        (increasing delay with depth) are positive, upward negative.

        Unidades: m/s quando fs_hz e channel_spacing_m são informados no
        construtor; canais/amostra (1/atraso, com sinal) caso contrário.
        """
        n_t, n_c = patch.shape
        if n_t < 2 or n_c < 2:
            return 0.0

        velocities = []
        for c in range(n_c - 1):
            x0 = patch[:, c]
            x1 = patch[:, c + 1]
            if x0.std() < 1e-12 or x1.std() < 1e-12:
                continue
            x0 = x0 - x0.mean()
            x1 = x1 - x1.mean()
            corr = np.correlate(x1, x0, mode="full")
            lag = int(np.argmax(corr)) - (n_t - 1)
            if lag == 0:
                velocities.append(0.0)
            elif self.fs_hz and self.channel_spacing_m:
                velocities.append(
                    float(np.sign(lag) * self.channel_spacing_m * self.fs_hz / abs(lag))
                )
            else:
                velocities.append(float(np.sign(lag) / abs(lag)))
        return float(np.median(velocities)) if velocities else 0.0

    def _das_features(self, patch: np.ndarray) -> np.ndarray:
        """Features específicas de DAS: strain rate e velocidade aparente."""
        n_t, n_c = patch.shape
        if n_t < 2 or n_c < 2:
            return np.zeros(4, dtype=np.float32)

        # Strain rate aproximado: derivada temporal média
        strain_rate = np.mean(np.abs(np.diff(patch, axis=0)))

        # Velocidade aparente com sinal (substitui a correlação adjacente
        # sempre-positiva removida na Onda 2, ML:D-04)
        apparent_velocity = self._apparent_velocity(patch)

        return np.array([
            strain_rate,
            apparent_velocity,
            np.max(patch) - np.min(patch),  # amplitude pico-a-pico
            float(np.argmax(np.abs(patch)) / max(patch.size, 1)),
        ], dtype=np.float32)


class DTSFeatureExtractor:
    """
    Extrator configurável de features para patches DTS.

    Além de estatísticas e espectrais básicas, inclui features térmicas
    como gradiente geotérmico, anomalias, dT/dz e delta_T_over_xf
    (ΔT do cluster térmico / comprimento de fratura estimado, ML:E-05).

    A taxa de amostragem real fs_hz (ML:I-03) pode ser informada no
    construtor para as features espectrais; o default 1.0 preserva o
    comportamento legado. / The real sampling rate fs_hz can be given for
    spectral features; default 1.0 keeps legacy behavior.
    """

    def __init__(self,
                 stats: bool = True,
                 spectral: bool = True,
                 thermal: bool = True,
                 anomaly: bool = True,
                 fs_hz: Optional[float] = None):
        self.stats = stats
        self.spectral = spectral
        self.thermal = thermal
        self.anomaly = anomaly
        self.fs_hz = fs_hz

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
        """Features espectrais via Welch ao longo do tempo (média por canal).

        Usa a taxa de amostragem real fs_hz (ML:I-03) quando informada no
        construtor; caso contrário assume fs=1.0 (comportamento legado).
        """
        n_t, n_c = patch.shape
        if n_t < 8:
            return np.zeros(4, dtype=np.float32)

        fs = float(self.fs_hz) if self.fs_hz else 1.0
        psd_per_channel = []
        for c in range(n_c):
            f, psd = signal.welch(patch[:, c], fs=fs, nperseg=min(64, n_t))
            psd_per_channel.append(psd)

        psd_mean = np.mean(psd_per_channel, axis=0)
        return np.array([
            psd_mean.mean(),
            psd_mean.std(),
            psd_mean.max(),
            float(f[np.argmax(psd_mean)] if len(f) > 0 else 0.0),
        ], dtype=np.float32)

    def delta_T_over_xf(self, patch: np.ndarray, depth_step_m: float) -> float:
        """
        ΔT do cluster térmico / comprimento de fratura estimado [°C/m]
        (ML:E-05). / Thermal-cluster ΔT over estimated fracture length.

        O desvio é medido contra o perfil espacial mediano em cada instante
        (robusto ao próprio cluster); o cluster é a faixa contígua de canais
        ao redor do pico cuja amplitude excede 50% da amplitude de pico.
        ΔT é a amplitude de pico do cluster e X_f a sua extensão em metros.
        Sem desvio significativo (campo plano), retorna 0.0. / Deviation is
        measured against the per-time spatial median (robust to the cluster
        itself); the cluster is the contiguous channel run around the peak
        whose amplitude exceeds 50% of the peak amplitude. ΔT is the peak
        in-cluster amplitude and X_f its span in meters.
        """
        n_t, n_c = patch.shape
        if n_t < 2 or n_c < 3:
            return 0.0

        deviation = patch - np.median(patch, axis=1, keepdims=True)
        channel_amp = np.max(np.abs(deviation), axis=0)
        peak_channel = int(np.argmax(channel_amp))
        peak_amp = float(channel_amp[peak_channel])
        if peak_amp < 1e-9:
            return 0.0

        half = 0.5 * peak_amp
        hot = channel_amp >= half
        lo = peak_channel
        while lo - 1 >= 0 and hot[lo - 1]:
            lo -= 1
        hi = peak_channel
        while hi + 1 < n_c and hot[hi + 1]:
            hi += 1

        xf = float((hi - lo + 1) * depth_step_m)
        return peak_amp / xf if xf > 0.0 else 0.0

    def _thermal_features(self, patch: np.ndarray, depth_step_m: float) -> np.ndarray:
        """Features térmicas: gradiente médio, variabilidade espacial e ΔT/X_f."""
        n_t, n_c = patch.shape
        if n_c < 2:
            return np.zeros(6, dtype=np.float32)

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
            self.delta_T_over_xf(patch, depth_step_m),
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
