#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/eigen.h>
#include <pybind11/functional.h>
#include "alakoro/event_detector.hpp"

namespace py = pybind11;
using namespace alakoro;

void init_event_detector(py::module& m) {
    py::enum_<EventType>(m, "EventType")
        .value("VIBRATION", EventType::VIBRATION)
        .value("FRACTURE", EventType::FRACTURE)
        .value("FLOW", EventType::FLOW)
        .value("LEAK", EventType::LEAK)
        .value("CUSTOM", EventType::CUSTOM);
    
    py::class_<Event>(m, "Event")
        .def(py::init<>())
        .def_readwrite("type", &Event::type)
        .def_readwrite("timestamp", &Event::timestamp)
        .def_readwrite("channel_start", &Event::channel_start)
        .def_readwrite("channel_end", &Event::channel_end)
        .def_readwrite("frequency_center", &Event::frequency_center)
        .def_readwrite("bandwidth", &Event::bandwidth)
        .def_readwrite("amplitude", &Event::amplitude)
        .def_readwrite("confidence", &Event::confidence)
        .def_readwrite("snr", &Event::snr)
        .def_readwrite("waveform", &Event::waveform)
        .def_readwrite("features", &Event::features)
        .def("__repr__", [](const Event& e) {
            return "<Event type=" + std::to_string(static_cast<int>(e.type)) + 
                   " timestamp=" + std::to_string(e.timestamp) + 
                   " channels=[" + std::to_string(e.channel_start) + 
                   "," + std::to_string(e.channel_end) + "]>";
        });
    
    py::class_<DetectorConfig>(m, "DetectorConfig")
        .def(py::init<>())
        .def_readwrite("threshold_snr", &DetectorConfig::threshold_snr)
        .def_readwrite("min_duration_ms", &DetectorConfig::min_duration_ms)
        .def_readwrite("max_duration_ms", &DetectorConfig::max_duration_ms)
        .def_readwrite("min_frequency", &DetectorConfig::min_frequency)
        .def_readwrite("max_frequency", &DetectorConfig::max_frequency)
        .def_readwrite("min_channels", &DetectorConfig::min_channels)
        .def_readwrite("merge_gap_ms", &DetectorConfig::merge_gap_ms)
        .def_readwrite("use_ml_classifier", &DetectorConfig::use_ml_classifier)
        .def_readwrite("model_path", &DetectorConfig::model_path);
    
    py::class_<EventDetector>(m, "EventDetector")
        .def(py::init<>())
        .def(py::init<const DetectorConfig&>())
        .def("set_config", &EventDetector::set_config)
        .def("get_config", &EventDetector::get_config)
        .def("detect_events", &EventDetector::detect_events, "Detect events in DAS data",
             py::arg("das_data"), py::arg("sample_rate"))
        .def("detect_on_single_channel", &EventDetector::detect_on_single_channel,
             "Detect events on single channel",
             py::arg("signal"), py::arg("sample_rate"), py::arg("channel_index"))
        .def("detect_in_region", &EventDetector::detect_in_region, "Detect events in region",
             py::arg("das_data"), py::arg("ch_start"), py::arg("ch_end"), py::arg("sample_rate"))
        .def("process_frame", &EventDetector::process_frame)
        .def("flush", &EventDetector::flush)
        .def("reset", &EventDetector::reset)
        .def("get_event_count", &EventDetector::get_event_count)
        .def("get_event_history", &EventDetector::get_event_history)
        .def("clear_history", &EventDetector::clear_history)
        .def("load_classifier_model", &EventDetector::load_classifier_model)
        .def("classify_event", &EventDetector::classify_event)
        .def("extract_features", &EventDetector::extract_features)
        .def("compute_features_matrix", &EventDetector::compute_features_matrix)
        .def_readwrite("on_event_detected", &EventDetector::on_event_detected)
        .def_readwrite("on_batch_processed", &EventDetector::on_batch_processed);
}
