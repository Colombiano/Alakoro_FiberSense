/** Python Bindings for Alakoro FiberSense C++ Engine
 *
 * Exposes signal processing and wavelet transform capabilities
 * to Python via pybind11.
 */
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <pybind11/complex.h>
#include "src/signal_processor.h"
#include "src/wavelet_transforms.h"

namespace py = pybind11;
using namespace alakoro;

// Helper: std::vector<double> to numpy array
py::array_t<double> vec_to_numpy(const std::vector<double>& vec) {
    return py::array_t<double>(vec.size(), vec.data());
}

// Helper: 2D vector to numpy array
py::array_t<double> vec2d_to_numpy(const std::vector<std::vector<double>>& mat) {
    if (mat.empty()) return py::array_t<double>({0, 0});
    size_t rows = mat.size();
    size_t cols = mat[0].size();
    py::array_t<double> result({rows, cols});
    auto buf = result.mutable_unchecked<2>();
    for (size_t i = 0; i < rows; ++i) {
        for (size_t j = 0; j < cols; ++j) {
            buf(i, j) = mat[i][j];
        }
    }
    return result;
}

PYBIND11_MODULE(alakoro_engine, m) {
    m.doc() = R"doc(
        Alakoro FiberSense C++ Engine v2.1.0
        =====================================

        High-performance signal processing engine for Distributed Fiber Optic
        Sensing (DAS, DTS, DSS). Includes FFT, filtering, spectrograms, and
        wavelet transforms for acoustic transient detection.

        Modules:
            SignalProcessor  -- FFT, filtering, spectrogram, anomaly detection
            WaveletProcessor -- CWT, DWT, wavelet denoising, transient detection
    )doc";

    // ========================================================================
    // Enums
    // ========================================================================
    py::enum_<SignalType>(m, "SignalType")
        .value("DAS", SignalType::DAS, "Distributed Acoustic Sensing")
        .value("DTS", SignalType::DTS, "Distributed Temperature Sensing")
        .value("DSS", SignalType::DSS, "Distributed Strain Sensing");

    // ========================================================================
    // Structs - Signal Processing
    // ========================================================================
    py::class_<FiberParams>(m, "FiberParams")
        .def(py::init<>())
        .def_readwrite("length", &FiberParams::length)
        .def_readwrite("spatial_resolution", &FiberParams::spatial_resolution)
        .def_readwrite("sampling_rate", &FiberParams::sampling_rate)
        .def_readwrite("duration", &FiberParams::duration)
        .def_readwrite("attenuation", &FiberParams::attenuation);

    py::class_<SignalData>(m, "SignalData")
        .def(py::init<>())
        .def_readwrite("type", &SignalData::type)
        .def_readwrite("params", &SignalData::params)
        .def_readwrite("data", &SignalData::data);

    py::class_<ProcessedSignal>(m, "ProcessedSignal")
        .def(py::init<>())
        .def_readwrite("waterfall", &ProcessedSignal::waterfall)
        .def_readwrite("spectrogram", &ProcessedSignal::spectrogram)
        .def_readwrite("profile", &ProcessedSignal::profile)
        .def_readwrite("fft", &ProcessedSignal::fft)
        .def_readwrite("frequencies", &ProcessedSignal::frequencies)
        .def_readwrite("distance", &ProcessedSignal::distance)
        .def_readwrite("time", &ProcessedSignal::time);

    py::class_<SignalAlert>(m, "SignalAlert")
        .def(py::init<>())
        .def_readwrite("id", &SignalAlert::id)
        .def_readwrite("type", &SignalAlert::type)
        .def_readwrite("message", &SignalAlert::message)
        .def_readwrite("timestamp", &SignalAlert::timestamp)
        .def_readwrite("channel", &SignalAlert::channel)
        .def_readwrite("position", &SignalAlert::position)
        .def_readwrite("value", &SignalAlert::value);

    // ========================================================================
    // Structs - Wavelet
    // ========================================================================
    py::class_<WaveletConfig>(m, "WaveletConfig")
        .def(py::init<>())
        .def_readwrite("central_freq", &WaveletConfig::central_freq,
            "Morlet central frequency omega0 (default 6.0)")
        .def_readwrite("num_scales", &WaveletConfig::num_scales,
            "Number of scales for CWT (default 128)")
        .def_readwrite("scale_min", &WaveletConfig::scale_min,
            "Minimum scale (default 1.0)")
        .def_readwrite("scale_max", &WaveletConfig::scale_max,
            "Maximum scale (default 512.0)")
        .def_readwrite("wavelet_type", &WaveletConfig::wavelet_type,
            "Wavelet family: 'morlet', 'paul', 'dog' (default 'morlet')")
        .def_readwrite("dwt_levels", &WaveletConfig::dwt_levels,
            "DWT decomposition levels (default 4)")
        .def_readwrite("denoise_threshold", &WaveletConfig::denoise_threshold,
            "Threshold multiplier for denoising (default 3.0)")
        .def_readwrite("threshold_mode", &WaveletConfig::threshold_mode,
            "'soft' or 'hard' thresholding (default 'soft')");

    py::class_<CWTResult>(m, "CWTResult")
        .def(py::init<>())
        .def_readwrite("scalogram", &CWTResult::scalogram,
            "Scalogram |W(a,b)|^2 [scales x time]")
        .def_readwrite("coeffs", &CWTResult::coeffs,
            "Complex wavelet coefficients")
        .def_readwrite("scales", &CWTResult::scales,
            "Analysis scales")
        .def_readwrite("frequencies", &CWTResult::frequencies,
            "Equivalent Fourier frequencies (Hz)")
        .def_readwrite("time", &CWTResult::time,
            "Time axis (seconds)")
        .def("scalogram_numpy", [](const CWTResult& r) { return vec2d_to_numpy(r.scalogram); },
            "Get scalogram as numpy array")
        .def("frequencies_numpy", [](const CWTResult& r) { return vec_to_numpy(r.frequencies); },
            "Get frequencies as numpy array")
        .def("time_numpy", [](const CWTResult& r) { return vec_to_numpy(r.time); },
            "Get time axis as numpy array");

    py::class_<DWTResult>(m, "DWTResult")
        .def(py::init<>())
        .def_readwrite("approximation", &DWTResult::approximation,
            "Coarsest approximation coefficients")
        .def_readwrite("details", &DWTResult::details,
            "Detail coefficients per decomposition level")
        .def_readwrite("levels", &DWTResult::levels,
            "Number of decomposition levels")
        .def_readwrite("wavelet_name", &DWTResult::wavelet_name,
            "Wavelet used for decomposition")
        .def("approximation_numpy", [](const DWTResult& r) { return vec_to_numpy(r.approximation); })
        .def("detail_numpy", [](const DWTResult& r, int level) {
            if (level < 0 || level >= static_cast<int>(r.details.size()))
                return vec_to_numpy({});
            return vec_to_numpy(r.details[level]);
        }, py::arg("level"), "Get detail coefficients at given level as numpy array");

    // ========================================================================
    // SignalProcessor
    // ========================================================================
    py::class_<SignalProcessor>(m, "SignalProcessor")
        .def(py::init<>())
        .def("process", &SignalProcessor::process,
            py::arg("input"),
            "Process a signal and return visualization data")
        .def("process_das", &SignalProcessor::process_das,
            py::arg("input"),
            "Process DAS acoustic signal")
        .def("process_dts", &SignalProcessor::process_dts,
            py::arg("input"),
            "Process DTS temperature signal")
        .def("process_dss", &SignalProcessor::process_dss,
            py::arg("input"),
            "Process DSS strain signal")
        .def("fft", &SignalProcessor::fft,
            py::arg("signal"),
            "Compute FFT of a 1D signal")
        .def("ifft", &SignalProcessor::ifft,
            py::arg("spectrum"),
            "Compute inverse FFT")
        .def("bandpass_filter", &SignalProcessor::bandpass_filter,
            py::arg("signal"), py::arg("low_freq"), py::arg("high_freq"), py::arg("sample_rate"),
            "Apply Butterworth bandpass filter")
        .def("spectrogram", &SignalProcessor::spectrogram,
            py::arg("signal"), py::arg("sample_rate"), py::arg("window_size") = 256, py::arg("overlap") = 128,
            "Compute spectrogram [freq x time]")
        .def("moving_average", &SignalProcessor::moving_average,
            py::arg("signal"), py::arg("window_size"),
            "Apply moving average filter")
        .def("detect_anomalies", &SignalProcessor::detect_anomalies,
            py::arg("input"), py::arg("threshold") = 3.0,
            "Detect anomalies in signal (Z-score based)")
        .def("get_last_error", &SignalProcessor::get_last_error,
            "Get last error message");

    // ========================================================================
    // WaveletProcessor
    // ========================================================================
    py::class_<WaveletProcessor>(m, "WaveletProcessor",
        R"doc(
        Wavelet Transform Processor for DAS Acoustic Analysis

        Implements Continuous Wavelet Transform (CWT) with Morlet wavelet
        for transient acoustic detection, and Discrete Wavelet Transform (DWT)
        with Daubechies-4 for multi-resolution denoising.

        The Morlet wavelet is optimal for DAS because it provides the best
        time-frequency localization for oscillatory, non-stationary signals
        like hydraulic fracture microseismic events and flow noise.

        Example::

            import alakoro_engine as ae
            import numpy as np

            # Create processor
            wp = ae.WaveletProcessor()

            # Configure for DAS transient detection
            config = ae.WaveletConfig()
            config.central_freq = 6.0      # Morlet omega0
            config.num_scales = 128        # Scale resolution
            config.scale_min = 1.0         # Finest scale
            config.scale_max = 512.0       # Coarsest scale
            wp.set_config(config)

            # Simulate DAS signal with transient
            fs = 1000.0  # Hz
            t = np.linspace(0, 1.0, int(fs))
            signal = np.sin(2*np.pi*50*t) + 0.5*np.random.randn(len(t))

            # Compute CWT scalogram
            cwt_result = wp.cwt(signal.tolist(), fs)
            scalogram = np.array(cwt_result.scalogram)  # [scales x time]

            # Detect transients (ridges in scalogram)
            transients = wp.detect_transients(signal.tolist(), fs, threshold=4.0)
            # Returns list of (time, frequency, amplitude) tuples

            # Wavelet denoising
            denoised = wp.denoise(signal.tolist())
        )doc")

        .def(py::init<>(), "Create WaveletProcessor with default config")
        .def(py::init<const WaveletConfig&>(), py::arg("config"),
            "Create WaveletProcessor with custom config")

        // CWT
        .def("cwt", &WaveletProcessor::cwt,
            py::arg("signal"), py::arg("fs"),
            R"doc(
            Compute Continuous Wavelet Transform (CWT) with Morlet wavelet.

            Args:
                signal: 1D signal vector
                fs: Sampling frequency in Hz

            Returns:
                CWTResult with scalogram, complex coefficients, scales,
                equivalent frequencies, and time axis.
            )doc")

        .def("scalogram", &WaveletProcessor::scalogram,
            py::arg("signal"), py::arg("fs"),
            "Compute CWT scalogram only (faster than full CWT)")

        // Transient detection
        .def("detect_transients", &WaveletProcessor::detect_transients,
            py::arg("signal"), py::arg("fs"), py::arg("threshold") = 4.0,
            R"doc(
            Detect transient acoustic events using CWT ridge detection.

            Finds ridges in the scalogram that correspond to transient events.
            More sensitive than STFT spectrogram for short-duration events.

            Args:
                signal: Input signal
                fs: Sampling frequency in Hz
                threshold: Ridge detection threshold (multiples of std dev)

            Returns:
                List of (time_seconds, frequency_hz, amplitude) tuples
            )doc")

        // DWT
        .def("dwt", &WaveletProcessor::dwt,
            py::arg("signal"), py::arg("levels") = -1,
            R"doc(
            Discrete Wavelet Transform using Daubechies-4.

            Multi-level decomposition useful for denoising and
            multi-resolution feature extraction.

            Args:
                signal: Input signal
                levels: Decomposition levels (-1 uses config default)

            Returns:
                DWTResult with approximation and detail coefficients
            )doc")

        .def("idwt", &WaveletProcessor::idwt,
            py::arg("dwt_result"),
            "Inverse DWT reconstruction")

        // Denoising
        .def("denoise", &WaveletProcessor::denoise,
            py::arg("signal"), py::arg("levels") = -1,
            R"doc(
            Wavelet denoising with universal threshold (VisuShrink).

            Applies DWT, thresholds detail coefficients using MAD noise
            estimate, and reconstructs. Effective for DAS where noise is
            spread across scales but transients concentrate at specific scales.

            Args:
                signal: Noisy input signal
                levels: Decomposition levels (-1 uses config default)

            Returns:
                Denoised signal vector
            )doc")

        .def("denoise_sure", &WaveletProcessor::denoise_sure,
            py::arg("signal"), py::arg("levels") = -1,
            R"doc(
            Wavelet denoising with SURE threshold (SureShrink).

            Uses Stein's Unbiased Risk Estimate for adaptive threshold
            per decomposition level. Better preserves transient features
            than VisuShrink.

            Args:
                signal: Noisy input signal
                levels: Decomposition levels (-1 uses config default)

            Returns:
                Denoised signal vector
            )doc")

        // Multi-scale analysis
        .def("wavelet_power_spectrum", &WaveletProcessor::wavelet_power_spectrum,
            py::arg("signal"), py::arg("fs"),
            "Compute global wavelet power spectrum averaged over time")

        .def("scale_average_power", &WaveletProcessor::scale_average_power,
            py::arg("cwt"), py::arg("fmin"), py::arg("fmax"),
            R"doc(
            Compute scale-averaged wavelet power over a frequency band.

            Useful for identifying energy concentration in specific
            frequency bands (e.g., fracture events at 50-200 Hz).
            )doc")

        .def("cone_of_influence", &WaveletProcessor::cone_of_influence,
            py::arg("signal_length"), py::arg("scales"), py::arg("fs"),
            R"doc(
            Compute Cone of Influence (COI) mask.

            Marks regions of the scalogram affected by edge effects.
            Points inside COI (true) are reliable; outside (false) are
            contaminated by boundary effects.
            )doc")

        // Config
        .def("set_config", &WaveletProcessor::set_config, py::arg("config"))
        .def("get_config", &WaveletProcessor::get_config)
        .def("get_last_error", &WaveletProcessor::get_last_error);

    // ========================================================================
    // Module-level functions
    // ========================================================================
    m.def("version", []() { return "2.1.0"; }, "Engine version string (v2.1.0 with wavelet support)");

    m.def("have_wavelets", []() { return true; },
        "Check if wavelet module is available");
}
