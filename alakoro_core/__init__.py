"""
Alakoro FiberSense — Pacote C++20 core.

Este pacote expõe as estruturas de dados e processadores implementados
em C++20 com pybind11. O módulo nativo é `_alakoro_core`.

Para facilitar o uso, fornecemos aliases sem sufixo de tipo:
  - DASData  -> DASData_d (double)
  - DTSData  -> DTSData_d (double)
  - DSSData  -> DSSData_d (double)
"""

from ._alakoro_core import (
    AcquisitionMetadata,
    DASData_f,
    DASData_d,
    DTSData_f,
    DTSData_d,
    DSSData_f,
    DSSData_d,
    detrend_f,
    detrend_d,
    demean_f,
    demean_d,
    taper_f,
    taper_d,
    decimate_f,
    decimate_d,
    butterworth_lowpass_f,
    butterworth_lowpass_d,
    butterworth_highpass_f,
    butterworth_highpass_d,
    butterworth_bandpass_f,
    butterworth_bandpass_d,
    magnitude_spectrum_d,
    psd_d,
    cwt_d,
    sta_lta_d,
    hilbert_envelope_d,
    teager_kaiser_d,
    median_filter_1d_d,
    median_filter_2d_d,
    svd_denoise_d,
    wavelet_denoise_d,
    spectrogram_d,
    cross_correlation_d,
    coherence_d,
    gauge_length_compensation_d,
    lms_filter_d,
    rls_filter_d,
    emd_d,
    eemd_d,
    nmf_d,
    serialize_avro,
    serialize_protobuf,
)

# Aliases padrão: precisão double
DASData = DASData_d
DTSData = DTSData_d
DSSData = DSSData_d

# Aliases de processadores padrão: precisão double
detrend = detrend_d
demean = demean_d
taper = taper_d
decimate = decimate_d
butterworth_lowpass = butterworth_lowpass_d
butterworth_highpass = butterworth_highpass_d
butterworth_bandpass = butterworth_bandpass_d
magnitude_spectrum = magnitude_spectrum_d
psd = psd_d
cwt = cwt_d
sta_lta = sta_lta_d
hilbert_envelope = hilbert_envelope_d
teager_kaiser = teager_kaiser_d
median_filter_1d = median_filter_1d_d
median_filter_2d = median_filter_2d_d
svd_denoise = svd_denoise_d
wavelet_denoise = wavelet_denoise_d
spectrogram = spectrogram_d
cross_correlation = cross_correlation_d
coherence = coherence_d
gauge_length_compensation = gauge_length_compensation_d
lms_filter = lms_filter_d
rls_filter = rls_filter_d
emd = emd_d
eemd = eemd_d
nmf = nmf_d

__all__ = [
    "AcquisitionMetadata",
    "DASData",
    "DTSData",
    "DSSData",
    "DASData_f",
    "DASData_d",
    "DTSData_f",
    "DTSData_d",
    "DSSData_f",
    "DSSData_d",
    "detrend",
    "demean",
    "taper",
    "decimate",
    "butterworth_lowpass",
    "butterworth_highpass",
    "butterworth_bandpass",
    "magnitude_spectrum",
    "psd",
    "cwt",
    "sta_lta",
    "hilbert_envelope",
    "teager_kaiser",
    "magnitude_spectrum_d",
    "psd_d",
    "cwt_d",
    "sta_lta_d",
    "hilbert_envelope_d",
    "teager_kaiser_d",
    "median_filter_1d",
    "median_filter_2d",
    "svd_denoise",
    "wavelet_denoise",
    "spectrogram",
    "cross_correlation",
    "coherence",
    "gauge_length_compensation",
    "lms_filter",
    "rls_filter",
    "emd",
    "eemd",
    "nmf",
    "spectrogram_d",
    "cross_correlation_d",
    "coherence_d",
    "gauge_length_compensation_d",
    "lms_filter_d",
    "rls_filter_d",
    "emd_d",
    "eemd_d",
    "nmf_d",
    "median_filter_1d_d",
    "median_filter_2d_d",
    "svd_denoise_d",
    "wavelet_denoise_d",
    "spectrogram_d",
    "cross_correlation_d",
    "coherence_d",
    "detrend_f",
    "detrend_d",
    "demean_f",
    "demean_d",
    "taper_f",
    "taper_d",
    "decimate_f",
    "decimate_d",
    "butterworth_lowpass_f",
    "butterworth_lowpass_d",
    "butterworth_highpass_f",
    "butterworth_highpass_d",
    "butterworth_bandpass_f",
    "butterworth_bandpass_d",
    "serialize_avro",
    "serialize_protobuf",
]
