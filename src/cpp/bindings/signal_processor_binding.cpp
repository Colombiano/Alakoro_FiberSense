#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/eigen.h>
#include <pybind11/functional.h>
#include "alakoro/signal_processor.hpp"

namespace py = pybind11;
using namespace alakoro;

void init_signal_processor(py::module& m) {
    py::enum_<FilterType>(m, "FilterType")
        .value("LOWPASS", FilterType::LOWPASS)
        .value("HIGHPASS", FilterType::HIGHPASS)
        .value("BANDPASS", FilterType::BANDPASS)
        .value("NOTCH", FilterType::NOTCH);
    
    py::enum_<WindowType>(m, "WindowType")
        .value("HANN", WindowType::HANN)
        .value("HAMMING", WindowType::HAMMING)
        .value("BLACKMAN", WindowType::BLACKMAN)
        .value("KAISER", WindowType::KAISER);
    
    py::class_<SignalProcessor>(m, "SignalProcessor")
        .def(py::init<>())
        
        .def_static("fft", &SignalProcessor::fft, "Compute FFT of signal", py::arg("signal"))
        .def_static("ifft", &SignalProcessor::ifft, "Compute inverse FFT", py::arg("spectrum"))
        .def_static("stft", &SignalProcessor::stft, "Compute Short-Time Fourier Transform",
                    py::arg("signal"), py::arg("window_size"), py::arg("hop_size"),
                    py::arg("window") = WindowType::HANN)
        .def_static("istft", &SignalProcessor::istft, "Compute inverse STFT",
                    py::arg("spectrogram"), py::arg("hop_size"),
                    py::arg("window") = WindowType::HANN)
        
        .def_static("fir_filter", &SignalProcessor::fir_filter, "Apply FIR filter",
                    py::arg("signal"), py::arg("coefficients"))
        .def_static("iir_filter", &SignalProcessor::iir_filter, "Apply IIR filter",
                    py::arg("signal"), py::arg("b"), py::arg("a"))
        .def_static("butterworth_filter", &SignalProcessor::butterworth_filter, "Apply Butterworth filter",
                    py::arg("signal"), py::arg("cutoff"), py::arg("order"),
                    py::arg("type"), py::arg("sample_rate"))
        
        .def_static("create_window", &SignalProcessor::create_window, "Create window function",
                    py::arg("size"), py::arg("type"), py::arg("parameter") = 0.0)
        
        .def_static("power_spectrum", &SignalProcessor::power_spectrum, "Compute power spectrum",
                    py::arg("signal"))
        .def_static("power_spectral_density", &SignalProcessor::power_spectral_density, "Compute PSD",
                    py::arg("signal"), py::arg("sample_rate"))
        .def_static("detect_peaks", &SignalProcessor::detect_peaks, "Detect spectral peaks",
                    py::arg("spectrum"), py::arg("threshold"), py::arg("min_distance"))
        
        .def_static("envelope", &SignalProcessor::envelope, "Compute signal envelope",
                    py::arg("signal"))
        .def_static("rms", &SignalProcessor::rms, "Compute RMS value", py::arg("signal"))
        .def_static("crest_factor", &SignalProcessor::crest_factor, "Compute crest factor",
                    py::arg("signal"))
        .def_static("moving_average", &SignalProcessor::moving_average, "Compute moving average",
                    py::arg("signal"), py::arg("window_size"))
        
        .def_static("instantaneous_frequency", &SignalProcessor::instantaneous_frequency,
                    "Compute instantaneous frequency", py::arg("signal"), py::arg("sample_rate"))
        .def_static("phase_unwrap", &SignalProcessor::phase_unwrap, "Unwrap phase signal",
                    py::arg("phase"))
        
        .def_static("decimate", &SignalProcessor::decimate, "Decimate signal by factor",
                    py::arg("signal"), py::arg("factor"))
        .def_static("interpolate", &SignalProcessor::interpolate, "Interpolate signal by factor",
                    py::arg("signal"), py::arg("factor"));
}
