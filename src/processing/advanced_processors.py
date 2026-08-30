"""
Alakoro FiberSense — Processadores Avançados

Wrappers Python de conveniência para processadores C++20:
  - Filtros Butterworth (lowpass, highpass, bandpass)
  - FFT / magnitude spectrum / PSD
  - CWT wavelet (Morlet, Ricker)
  - Detecção de eventos (STA/LTA, Hilbert, Teager-Kaiser)
  - Denoising (median 1D/2D, SVD, wavelet thresholding)
  - Tempo-frequência (espectrograma, correlação cruzada, coerência)
  - Filtros adaptativos (LMS, RLS, gauge-length compensation)
  - Decomposições (EMD, EEMD, NMF)
  - Processadores térmicos para DTS (gradiente, baseline geotérmico,
    anomalias, mediana espacial)

Todas as funções que recebem AlakoroPatch respeitam a modalidade
(DAS/DTS/DSS) e roteiam para a implementação C++ correspondente.
"""

from __future__ import annotations

from typing import List, Tuple, Union

import numpy as np

from alakoro_core import (
    DASData,
    DTSData,
    DSSData,
    butterworth_bandpass_d_das as _bw_bandpass_das,
    butterworth_bandpass_d_dts as _bw_bandpass_dts,
    butterworth_highpass_d_das as _bw_highpass_das,
    butterworth_highpass_d_dts as _bw_highpass_dts,
    butterworth_lowpass_d_das as _bw_lowpass_das,
    butterworth_lowpass_d_dts as _bw_lowpass_dts,
    coherence_d_das as _coherence_das,
    coherence_d_dts as _coherence_dts,
    cross_correlation_d_das as _xcorr_das,
    cross_correlation_d_dts as _xcorr_dts,
    cwt_d_das as _cwt_das,
    cwt_d_dts as _cwt_dts,
    eemd_d_das as _eemd_das,
    eemd_d_dts as _eemd_dts,
    emd_d_das as _emd_das,
    emd_d_dts as _emd_dts,
    gauge_length_compensation_d_das as _glc_das,
    gauge_length_compensation_d_dts as _glc_dts,
    geothermal_baseline_correction_d as _geothermal_baseline_d,
    hilbert_envelope_d_das as _hilbert_das,
    hilbert_envelope_d_dts as _hilbert_dts,
    lms_filter_d_das as _lms_das,
    lms_filter_d_dts as _lms_dts,
    magnitude_spectrum_d_das as _mag_spec_das,
    magnitude_spectrum_d_dts as _mag_spec_dts,
    median_filter_1d_d_das as _median1d_das,
    median_filter_1d_d_dts as _median1d_dts,
    median_filter_2d_d_das as _median2d_das,
    median_filter_2d_d_dts as _median2d_dts,
    nmf_d_das as _nmf_das,
    nmf_d_dts as _nmf_dts,
    psd_d_das as _psd_das,
    psd_d_dts as _psd_dts,
    rls_filter_d_das as _rls_das,
    rls_filter_d_dts as _rls_dts,
    spatial_median_filter_d as _spatial_median_d,
    spectrogram_d_das as _spectrogram_das,
    spectrogram_d_dts as _spectrogram_dts,
    sta_lta_d_das as _sta_lta_das,
    sta_lta_d_dts as _sta_lta_dts,
    svd_denoise_d_das as _svd_das,
    svd_denoise_d_dts as _svd_dts,
    teager_kaiser_d_das as _teager_das,
    teager_kaiser_d_dts as _teager_dts,
    thermal_anomaly_detection_d as _thermal_anomaly_d,
    thermal_gradient_d as _thermal_gradient_d,
    wavelet_denoise_d_das as _wdn_das,
    wavelet_denoise_d_dts as _wdn_dts,
)

from src.io.alakoro_spool import AlakoroPatch

# Tipos de dados C++ expostos para cada modalidade.
SensingData = Union[DASData, DTSData, DSSData]

# DSS ainda não tem processadores avançados dedicados; usamos DAS como fallback.
_PROCESSOR_MAP = {
    "das": {
        "butterworth_lowpass": _bw_lowpass_das,
        "butterworth_highpass": _bw_highpass_das,
        "butterworth_bandpass": _bw_bandpass_das,
        "magnitude_spectrum": _mag_spec_das,
        "psd": _psd_das,
        "cwt": _cwt_das,
        "sta_lta": _sta_lta_das,
        "hilbert_envelope": _hilbert_das,
        "teager_kaiser": _teager_das,
        "median_filter_1d": _median1d_das,
        "median_filter_2d": _median2d_das,
        "svd_denoise": _svd_das,
        "wavelet_denoise": _wdn_das,
        "spectrogram": _spectrogram_das,
        "cross_correlation": _xcorr_das,
        "coherence": _coherence_das,
        "gauge_length_compensation": _glc_das,
        "lms_filter": _lms_das,
        "rls_filter": _rls_das,
        "emd": _emd_das,
        "eemd": _eemd_das,
        "nmf": _nmf_das,
    },
    "dts": {
        "butterworth_lowpass": _bw_lowpass_dts,
        "butterworth_highpass": _bw_highpass_dts,
        "butterworth_bandpass": _bw_bandpass_dts,
        "magnitude_spectrum": _mag_spec_dts,
        "psd": _psd_dts,
        "cwt": _cwt_dts,
        "sta_lta": _sta_lta_dts,
        "hilbert_envelope": _hilbert_dts,
        "teager_kaiser": _teager_dts,
        "median_filter_1d": _median1d_dts,
        "median_filter_2d": _median2d_dts,
        "svd_denoise": _svd_dts,
        "wavelet_denoise": _wdn_dts,
        "spectrogram": _spectrogram_dts,
        "cross_correlation": _xcorr_dts,
        "coherence": _coherence_dts,
        "gauge_length_compensation": _glc_dts,
        "lms_filter": _lms_dts,
        "rls_filter": _rls_dts,
        "emd": _emd_dts,
        "eemd": _eemd_dts,
        "nmf": _nmf_dts,
    },
    "dss": {
        # fallback para DAS — processadores avançados de DSS serão adicionados
        # em iteração futura, quando houver funções C++ específicas.
        "butterworth_lowpass": _bw_lowpass_das,
        "butterworth_highpass": _bw_highpass_das,
        "butterworth_bandpass": _bw_bandpass_das,
        "magnitude_spectrum": _mag_spec_das,
        "psd": _psd_das,
        "cwt": _cwt_das,
        "sta_lta": _sta_lta_das,
        "hilbert_envelope": _hilbert_das,
        "teager_kaiser": _teager_das,
        "median_filter_1d": _median1d_das,
        "median_filter_2d": _median2d_das,
        "svd_denoise": _svd_das,
        "wavelet_denoise": _wdn_das,
        "spectrogram": _spectrogram_das,
        "cross_correlation": _xcorr_das,
        "coherence": _coherence_das,
        "gauge_length_compensation": _glc_das,
        "lms_filter": _lms_das,
        "rls_filter": _rls_das,
        "emd": _emd_das,
        "eemd": _eemd_das,
        "nmf": _nmf_das,
    },
}


def _data_cls(modality: str):
    """Retorna a classe C++ correspondente à modalidade."""
    modality = modality.lower()
    if modality == "das":
        return DASData
    if modality == "dts":
        return DTSData
    if modality == "dss":
        return DSSData
    raise ValueError(f"Modalidade desconhecida: {modality}")


def _patch_to_sensingdata(patch: AlakoroPatch) -> SensingData:
    """Converte AlakoroPatch para o tipo C++ adequado (DASData/DTSData/DSSData)."""
    data = patch.data.astype(np.float64)
    cls = _data_cls(patch.modality)
    obj = cls(n_times=data.shape[0], n_channels=data.shape[1])
    arr = np.array(obj, copy=False)
    arr[:, :] = data
    return obj


def _sensingdata_to_array(obj: SensingData) -> np.ndarray:
    """Retorna cópia dos dados do objeto C++ como array NumPy 2D."""
    return np.array(obj, copy=True)


def _proc(name: str, modality: str):
    """Roteia para o processador C++ correto conforme modalidade."""
    modality = modality.lower()
    if modality not in _PROCESSOR_MAP:
        raise ValueError(f"Modalidade desconhecida: {modality}")
    proc = _PROCESSOR_MAP[modality].get(name)
    if proc is None:
        raise NotImplementedError(
            f"Processador '{name}' não disponível para modalidade '{modality}'"
        )
    return proc


def _patch_from_array(obj: SensingData, patch: AlakoroPatch) -> AlakoroPatch:
    """Reconstrói AlakoroPatch a partir de um objeto C++ com mesma modalidade."""
    from src.io.dasdae import DASDAEAdapter

    arr = _sensingdata_to_array(obj)
    new_patch = DASDAEAdapter.array_to_patch(
        arr, modality=patch.modality.upper()
    )
    return AlakoroPatch(new_patch, well_id=patch.well_id, modality=patch.modality)


# ──────────────────────────────────────────────────────────────────────────────
# Filtros Butterworth
# ──────────────────────────────────────────────────────────────────────────────

def butterworth_lowpass(patch: AlakoroPatch,
                        sample_rate_hz: float,
                        cutoff_hz: float) -> AlakoroPatch:
    """Aplica filtro passa-baixa Butterworth de 2ª ordem."""
    data = _patch_to_sensingdata(patch)
    _proc("butterworth_lowpass", patch.modality)(data, sample_rate_hz, cutoff_hz)
    return _patch_from_array(data, patch)


def butterworth_highpass(patch: AlakoroPatch,
                         sample_rate_hz: float,
                         cutoff_hz: float) -> AlakoroPatch:
    """Aplica filtro passa-alta Butterworth de 2ª ordem."""
    data = _patch_to_sensingdata(patch)
    _proc("butterworth_highpass", patch.modality)(data, sample_rate_hz, cutoff_hz)
    return _patch_from_array(data, patch)


def butterworth_bandpass(patch: AlakoroPatch,
                         sample_rate_hz: float,
                         low_hz: float,
                         high_hz: float) -> AlakoroPatch:
    """Aplica filtro passa-faixa Butterworth de 2ª ordem."""
    data = _patch_to_sensingdata(patch)
    _proc("butterworth_bandpass", patch.modality)(data, sample_rate_hz, low_hz, high_hz)
    return _patch_from_array(data, patch)


# ──────────────────────────────────────────────────────────────────────────────
# FFT / Espectro
# ──────────────────────────────────────────────────────────────────────────────

def magnitude_spectrum(patch: AlakoroPatch) -> np.ndarray:
    """
    Calcula magnitude do espectro por canal.

    Retorna array de shape (n_freq, n_channels), onde n_freq = n_times/2 + 1.
    """
    data = _patch_to_sensingdata(patch)
    return _proc("magnitude_spectrum", patch.modality)(data)


def psd(patch: AlakoroPatch, sample_rate_hz: float) -> np.ndarray:
    """
    Calcula densidade espectral de potência por canal.

    Retorna array de shape (n_freq, n_channels).
    """
    data = _patch_to_sensingdata(patch)
    return _proc("psd", patch.modality)(data, sample_rate_hz)


# ──────────────────────────────────────────────────────────────────────────────
# Wavelet
# ──────────────────────────────────────────────────────────────────────────────

def cwt(patch: AlakoroPatch,
        scales: List[float],
        sample_rate_hz: float,
        wavelet: str = "morlet") -> List[np.ndarray]:
    """
    Calcula CWT para cada canal.

    Retorna lista de arrays com shape (n_scales, n_times).
    """
    data = _patch_to_sensingdata(patch)
    return _proc("cwt", patch.modality)(data, scales, sample_rate_hz, wavelet)


# ──────────────────────────────────────────────────────────────────────────────
# Detecção de eventos
# ──────────────────────────────────────────────────────────────────────────────

def sta_lta(patch: AlakoroPatch, n_sta: int, n_lta: int) -> np.ndarray:
    """
    Calcula razão STA/LTA para cada canal.

    Retorna array 1D flat com shape (n_valid * n_channels,).
    """
    data = _patch_to_sensingdata(patch)
    return _proc("sta_lta", patch.modality)(data, n_sta, n_lta)


def hilbert_envelope(patch: AlakoroPatch) -> np.ndarray:
    """
    Calcula a envoltória de Hilbert para cada canal.

    Retorna array 1D flat com shape (n_times * n_channels,).
    """
    data = _patch_to_sensingdata(patch)
    return _proc("hilbert_envelope", patch.modality)(data)


def teager_kaiser(patch: AlakoroPatch) -> np.ndarray:
    """
    Calcula o operador de energia de Teager-Kaiser para cada canal.

    Retorna array 1D flat com shape (n_times * n_channels,).
    """
    data = _patch_to_sensingdata(patch)
    return _proc("teager_kaiser", patch.modality)(data)


# ──────────────────────────────────────────────────────────────────────────────
# Denoising
# ──────────────────────────────────────────────────────────────────────────────

def median_filter_1d(patch: AlakoroPatch, window_size: int) -> AlakoroPatch:
    """Aplica filtro de mediana 1D por canal."""
    data = _patch_to_sensingdata(patch)
    filtered = _proc("median_filter_1d", patch.modality)(data, window_size)
    from src.io.dasdae import DASDAEAdapter
    new_patch = DASDAEAdapter.array_to_patch(
        filtered.reshape(data.n_times, data.n_channels), modality=patch.modality.upper()
    )
    return AlakoroPatch(new_patch, well_id=patch.well_id, modality=patch.modality)


def median_filter_2d(patch: AlakoroPatch,
                     window_t: int,
                     window_c: int) -> AlakoroPatch:
    """Aplica filtro de mediana 2D (tempo x canais)."""
    data = _patch_to_sensingdata(patch)
    filtered = _proc("median_filter_2d", patch.modality)(data, window_t, window_c)
    from src.io.dasdae import DASDAEAdapter
    new_patch = DASDAEAdapter.array_to_patch(
        filtered.reshape(data.n_times, data.n_channels), modality=patch.modality.upper()
    )
    return AlakoroPatch(new_patch, well_id=patch.well_id, modality=patch.modality)


def svd_denoise(patch: AlakoroPatch, n_components: int) -> AlakoroPatch:
    """Denoising por SVD/PCA mantendo n_components componentes principais."""
    data = _patch_to_sensingdata(patch)
    denoised = _proc("svd_denoise", patch.modality)(data, n_components)
    from src.io.dasdae import DASDAEAdapter
    new_patch = DASDAEAdapter.array_to_patch(
        denoised.reshape(data.n_times, data.n_channels), modality=patch.modality.upper()
    )
    return AlakoroPatch(new_patch, well_id=patch.well_id, modality=patch.modality)


def wavelet_denoise(patch: AlakoroPatch,
                    scales: List[float],
                    sample_rate_hz: float,
                    threshold: float,
                    rule: str = "soft") -> AlakoroPatch:
    """Denoising por thresholding de coeficientes wavelet (Morlet)."""
    data = _patch_to_sensingdata(patch)
    denoised = _proc("wavelet_denoise", patch.modality)(
        data, scales, sample_rate_hz, threshold, rule
    )
    from src.io.dasdae import DASDAEAdapter
    new_patch = DASDAEAdapter.array_to_patch(
        denoised.reshape(data.n_times, data.n_channels), modality=patch.modality.upper()
    )
    return AlakoroPatch(new_patch, well_id=patch.well_id, modality=patch.modality)


# ──────────────────────────────────────────────────────────────────────────────
# Tempo-frequência
# ──────────────────────────────────────────────────────────────────────────────

def spectrogram(patch: AlakoroPatch,
                window_size: int,
                hop_size: int,
                n_fft: int) -> List[np.ndarray]:
    """
    Calcula o espectrograma para cada canal.

    Retorna lista de arrays com shape (n_frames, n_freq).
    """
    data = _patch_to_sensingdata(patch)
    return _proc("spectrogram", patch.modality)(data, window_size, hop_size, n_fft)


def cross_correlation_channels(patch: AlakoroPatch, max_lag: int) -> np.ndarray:
    """
    Calcula correlação cruzada entre canais adjacentes.

    Retorna array de shape (n_channels, 2*max_lag+1).
    """
    data = _patch_to_sensingdata(patch)
    return _proc("cross_correlation", patch.modality)(data, max_lag)


def coherence_channels(patch: AlakoroPatch,
                       window_size: int,
                       hop_size: int,
                       n_fft: int) -> np.ndarray:
    """
    Calcula magnitude squared coherence entre canais adjacentes.

    Retorna array de shape (n_channels, n_fft/2+1).
    """
    data = _patch_to_sensingdata(patch)
    return _proc("coherence", patch.modality)(data, window_size, hop_size, n_fft)


# ──────────────────────────────────────────────────────────────────────────────
# Adaptativos
# ──────────────────────────────────────────────────────────────────────────────

def gauge_length_compensation(patch: AlakoroPatch,
                              gauge_length_m: float,
                              channel_spacing_m: float,
                              regularization: float = 0.1) -> AlakoroPatch:
    """Compensação aproximada de gauge length no domínio espacial."""
    data = _patch_to_sensingdata(patch)
    compensated = _proc("gauge_length_compensation", patch.modality)(
        data, gauge_length_m, channel_spacing_m, regularization
    )
    from src.io.dasdae import DASDAEAdapter
    new_patch = DASDAEAdapter.array_to_patch(
        compensated.reshape(data.n_times, data.n_channels), modality=patch.modality.upper()
    )
    return AlakoroPatch(new_patch, well_id=patch.well_id, modality=patch.modality)


def lms_filter(patch: AlakoroPatch,
               mu: float,
               filter_order: int) -> AlakoroPatch:
    """
    Aplica filtro adaptativo LMS por canal.

    Usa o canal vizinho como referência e retorna o sinal de erro.
    """
    data = _patch_to_sensingdata(patch)
    filtered = _proc("lms_filter", patch.modality)(data, mu, filter_order)
    from src.io.dasdae import DASDAEAdapter
    new_patch = DASDAEAdapter.array_to_patch(
        filtered.reshape(data.n_times, data.n_channels), modality=patch.modality.upper()
    )
    return AlakoroPatch(new_patch, well_id=patch.well_id, modality=patch.modality)


def rls_filter(patch: AlakoroPatch,
               lambda_: float,
               delta: float,
               filter_order: int) -> AlakoroPatch:
    """
    Aplica filtro adaptativo RLS por canal.

    Usa o canal vizinho como referência e retorna o sinal de erro.
    """
    data = _patch_to_sensingdata(patch)
    filtered = _proc("rls_filter", patch.modality)(data, lambda_, delta, filter_order)
    from src.io.dasdae import DASDAEAdapter
    new_patch = DASDAEAdapter.array_to_patch(
        filtered.reshape(data.n_times, data.n_channels), modality=patch.modality.upper()
    )
    return AlakoroPatch(new_patch, well_id=patch.well_id, modality=patch.modality)


# ──────────────────────────────────────────────────────────────────────────────
# Decomposições
# ──────────────────────────────────────────────────────────────────────────────

def emd(patch: AlakoroPatch, max_imfs: int = 5) -> List[List[np.ndarray]]:
    """
    EMD por canal.

    Retorna lista de listas: [channel][imf] -> array 1D.
    """
    data = _patch_to_sensingdata(patch)
    return _proc("emd", patch.modality)(data, max_imfs)


def eemd(patch: AlakoroPatch,
         n_ensembles: int,
         noise_std: float,
         max_imfs: int = 5) -> List[List[np.ndarray]]:
    """
    EEMD por canal.

    Retorna lista de listas: [channel][imf] -> array 1D.
    """
    data = _patch_to_sensingdata(patch)
    return _proc("eemd", patch.modality)(data, n_ensembles, noise_std, max_imfs)


def nmf(patch: AlakoroPatch,
        n_components: int,
        max_iter: int = 100) -> Tuple[np.ndarray, np.ndarray]:
    """
    NMF da matriz (time, channels).

    Retorna (W, H) onde data ≈ W @ H.
    """
    data = _patch_to_sensingdata(patch)
    return _proc("nmf", patch.modality)(data, n_components, max_iter)


# ──────────────────────────────────────────────────────────────────────────────
# Processadores térmicos (DTS)
# ──────────────────────────────────────────────────────────────────────────────

def thermal_gradient(patch: AlakoroPatch, depth_step_m: float) -> np.ndarray:
    """
    Calcula gradiente térmico dT/dz para cada canal de profundidade.

    Retorna array de shape (n_times, n_channels).
    """
    if patch.modality != "dts":
        raise ValueError("thermal_gradient é exclusivo para modalidade DTS")
    data = _patch_to_sensingdata(patch)
    return _thermal_gradient_d(data, depth_step_m)


def geothermal_baseline_correction(patch: AlakoroPatch,
                                   depth_step_m: float,
                                   surface_temp: float,
                                   gradient: float) -> AlakoroPatch:
    """
    Remove baseline geotérmico linear estimado de cada perfil de temperatura.
    """
    if patch.modality != "dts":
        raise ValueError("geothermal_baseline_correction é exclusivo para modalidade DTS")
    data = _patch_to_sensingdata(patch)
    corrected = _geothermal_baseline_d(data, depth_step_m, surface_temp, gradient)
    from src.io.dasdae import DASDAEAdapter
    new_patch = DASDAEAdapter.array_to_patch(
        corrected.reshape(data.n_times, data.n_channels), modality="DTS"
    )
    return AlakoroPatch(new_patch, well_id=patch.well_id, modality="dts")


def thermal_anomaly_detection(patch: AlakoroPatch,
                              threshold_sigma: float) -> np.ndarray:
    """
    Detecta anomalias térmicas por canal usando desvio padrão temporal.

    Retorna array binário de shape (n_times, n_channels).
    """
    if patch.modality != "dts":
        raise ValueError("thermal_anomaly_detection é exclusivo para modalidade DTS")
    data = _patch_to_sensingdata(patch)
    return _thermal_anomaly_d(data, threshold_sigma)


def spatial_median_filter(patch: AlakoroPatch, window_size: int) -> AlakoroPatch:
    """
    Aplica filtro de mediana espacial ao longo da profundidade (DTS).
    """
    if patch.modality != "dts":
        raise ValueError("spatial_median_filter é exclusivo para modalidade DTS")
    data = _patch_to_sensingdata(patch)
    filtered = _spatial_median_d(data, window_size)
    from src.io.dasdae import DASDAEAdapter
    new_patch = DASDAEAdapter.array_to_patch(
        filtered.reshape(data.n_times, data.n_channels), modality="DTS"
    )
    return AlakoroPatch(new_patch, well_id=patch.well_id, modality="dts")


__all__ = [
    "butterworth_lowpass",
    "butterworth_highpass",
    "butterworth_bandpass",
    "magnitude_spectrum",
    "psd",
    "cwt",
    "sta_lta",
    "hilbert_envelope",
    "teager_kaiser",
    "median_filter_1d",
    "median_filter_2d",
    "svd_denoise",
    "wavelet_denoise",
    "spectrogram",
    "cross_correlation_channels",
    "coherence_channels",
    "gauge_length_compensation",
    "lms_filter",
    "rls_filter",
    "emd",
    "eemd",
    "nmf",
    "thermal_gradient",
    "geothermal_baseline_correction",
    "thermal_anomaly_detection",
    "spatial_median_filter",
]
