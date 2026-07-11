#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/eigen.h>
#include <pybind11/functional.h>
#include "alakoro/das_decoder.hpp"

namespace py = pybind11;
using namespace alakoro;

void init_das_decoder(py::module& m) {
    py::enum_<DASFormat>(m, "DASFormat")
        .value("SILIXA_HDF5", DASFormat::SILIXA_HDF5)
        .value("OPTASENSE_TDMS", DASFormat::OPTASENSE_TDMS)
        .value("FEBUS_H5", DASFormat::FEBUS_H5)
        .value("ALAKORO_RAW", DASFormat::ALAKORO_RAW)
        .value("CUSTOM", DASFormat::CUSTOM);
    
    py::class_<DASMetadata>(m, "DASMetadata")
        .def(py::init<>())
        .def_readwrite("gauge_length", &DASMetadata::gauge_length)
        .def_readwrite("spatial_sampling", &DASMetadata::spatial_sampling)
        .def_readwrite("temporal_sampling", &DASMetadata::temporal_sampling)
        .def_readwrite("pulse_width", &DASMetadata::pulse_width)
        .def_readwrite("num_channels", &DASMetadata::num_channels)
        .def_readwrite("num_samples", &DASMetadata::num_samples)
        .def_readwrite("start_distance", &DASMetadata::start_distance)
        .def_readwrite("fiber_length", &DASMetadata::fiber_length)
        .def_readwrite("unit", &DASMetadata::unit)
        .def_readwrite("fiber_type", &DASMetadata::fiber_type)
        .def_readwrite("custom_fields", &DASMetadata::custom_fields)
        .def("__repr__", [](const DASMetadata& m) {
            return "<DASMetadata gauge_length=" + std::to_string(m.gauge_length) + 
                   " spatial_sampling=" + std::to_string(m.spatial_sampling) + ">";
        });
    
    py::class_<DASFrame>(m, "DASFrame")
        .def(py::init<>())
        .def_readwrite("data", &DASFrame::data)
        .def_readwrite("timestamp", &DASFrame::timestamp)
        .def_readwrite("frame_number", &DASFrame::frame_number)
        .def_readwrite("metadata", &DASFrame::metadata);
    
    py::class_<DASDecoder>(m, "DASDecoder")
        .def(py::init<>())
        .def(py::init<DASFormat>())
        .def("set_format", &DASDecoder::set_format)
        .def("set_metadata", &DASDecoder::set_metadata)
        .def("set_custom_parser", &DASDecoder::set_custom_parser)
        .def("decode_file", &DASDecoder::decode_file, "Decode DAS data from file", py::arg("filepath"))
        .def("decode_buffer", &DASDecoder::decode_buffer, "Decode DAS data from buffer", py::arg("buffer"))
        .def("read_metadata", &DASDecoder::read_metadata)
        .def("write_metadata", &DASDecoder::write_metadata)
        .def("start_stream", &DASDecoder::start_stream)
        .def("stop_stream", &DASDecoder::stop_stream)
        .def("is_streaming", &DASDecoder::is_streaming)
        .def("apply_calibration", &DASDecoder::apply_calibration)
        .def("compensate_attenuation", &DASDecoder::compensate_attenuation)
        .def("compute_snr", &DASDecoder::compute_snr)
        .def("compute_quality_map", &DASDecoder::compute_quality_map)
        .def("detect_dead_channels", &DASDecoder::detect_dead_channels)
        .def_readwrite("on_frame_received", &DASDecoder::on_frame_received);
}
