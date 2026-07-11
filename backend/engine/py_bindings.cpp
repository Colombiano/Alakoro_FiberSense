"""
Alakoro FiberSense - C++ Engine Python Bindings
pybind11 bindings para o engine de processamento de sinais.
"""
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include "signal_processor.h"

namespace py = pybind11;

PYBIND11_MODULE(alakoro_engine, m) {
    m.doc() = "Alakoro FiberSense C++ Engine - Signal Processing";

    // Enums
    py::enum_<SignalType>(m, "SignalType")
        .value("DAS", SignalType::DAS)
        .value("DTS", SignalType::DTS)
        .value("DSS", SignalType::DSS);

    // Structs
    py::class_<FiberParams>(m, "FiberParams")
        .def(py::init<>())
        .def_readwrite("fiber_length", &FiberParams::fiber_length)
        .def_readwrite("spatial_resolution", &FiberParams::spatial_resolution)
        .def_readwrite("sampling_rate", &FiberParams::sampling_rate)
        .def_readwrite("gauge_length", &FiberParams::gauge_length)
        .def_readwrite("refractive_index", &FiberParams::refractive_index)
        .def_readwrite("cable_type", &FiberParams::cable_type);

    py::class_<SignalData>(m, "SignalData")
        .def(py::init<SignalType, py::array_t<double>, FiberParams>())
        .def_readwrite("signal_type", &SignalData::signal_type)
        .def_readwrite("params", &SignalData::params);

    py::class_<ProcessedSignal>(m, "ProcessedSignal")
        .def(py::init<>())
        .def_readwrite("fft_magnitude", &ProcessedSignal::fft_magnitude)
        .def_readwrite("fft_frequencies", &ProcessedSignal::fft_frequencies)
        .def_readwrite("spectrogram", &ProcessedSignal::spectrogram)
        .def_readwrite("spectrogram_freqs", &ProcessedSignal::spectrogram_freqs)
        .def_readwrite("spectrogram_times", &ProcessedSignal::spectrogram_times)
        .def_readwrite("event_positions", &ProcessedSignal::event_positions)
        .def_readwrite("event_amplitudes", &ProcessedSignal::event_amplitudes)
        .def_readwrite("anomaly_scores", &ProcessedSignal::anomaly_scores);

    // SignalProcessor class
    py::class_<SignalProcessor>(m, "SignalProcessor")
        .def(py::init<FiberParams, SignalType>())
        
        // FFT
        .def("fft", [](SignalProcessor& self, py::array_t<double> signal) {
            auto buf = signal.request();
            std::vector<double> input(static_cast<double*>(buf.ptr), 
                                     static_cast<double*>(buf.ptr) + buf.size);
            auto result = self.fft(input);
            return py::dict(
                "magnitude"_a = result.fft_magnitude,
                "frequencies"_a = result.fft_frequencies
            );
        })
        
        // Bandpass filter
        .def("bandpass_filter", [](SignalProcessor& self, py::array_t<double> signal, 
                                    double lowcut, double highcut) {
            auto buf = signal.request();
            std::vector<double> input(static_cast<double*>(buf.ptr), 
                                     static_cast<double*>(buf.ptr) + buf.size);
            auto result = self.bandpass_filter(input, lowcut, highcut);
            return py::array_t<double>(result.size(), result.data());
        })
        
        // Spectrogram
        .def("spectrogram", [](SignalProcessor& self, py::array_t<double> signal, int nperseg) {
            auto buf = signal.request();
            std::vector<double> input(static_cast<double*>(buf.ptr), 
                                     static_cast<double*>(buf.ptr) + buf.size);
            auto result = self.spectrogram(input, nperseg);
            return py::dict(
                "S"_a = result.spectrogram,
                "frequencies"_a = result.spectrogram_freqs,
                "times"_a = result.spectrogram_times
            );
        })
        
        // Moving average
        .def("moving_average", [](SignalProcessor& self, py::array_t<double> signal, int window) {
            auto buf = signal.request();
            std::vector<double> input(static_cast<double*>(buf.ptr), 
                                     static_cast<double*>(buf.ptr) + buf.size);
            auto result = self.moving_average(input, window);
            return py::array_t<double>(result.size(), result.data());
        })
        
        // Anomaly detection
        .def("detect_anomalies", [](SignalProcessor& self, py::array_t<double> signal, double threshold) {
            auto buf = signal.request();
            std::vector<double> input(static_cast<double*>(buf.ptr), 
                                     static_cast<double*>(buf.ptr) + buf.size);
            auto result = self.detect_anomalies(input, threshold);
            return py::dict(
                "positions"_a = result.event_positions,
                "amplitudes"_a = result.event_amplitudes,
                "scores"_a = result.anomaly_scores
            );
        })
        
        // Full processing
        .def("process", [](SignalProcessor& self, py::array_t<double> signal) {
            auto buf = signal.request();
            std::vector<double> input(static_cast<double*>(buf.ptr), 
                                     static_cast<double*>(buf.ptr) + buf.size);
            auto result = self.process(input);
            return py::dict(
                "fft_magnitude"_a = result.fft_magnitude,
                "fft_frequencies"_a = result.fft_frequencies,
                "spectrogram"_a = result.spectrogram,
                "event_positions"_a = result.event_positions,
                "event_amplitudes"_a = result.event_amplitudes,
                "anomaly_scores"_a = result.anomaly_scores
            );
        });

    // Utility functions
    m.def("version", []() { return "2.0.0"; }, "Retorna a versao do engine");
}
