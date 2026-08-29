/**
 * @file bindings.cpp
 * @brief Bindings pybind11 da camada C++20 do Alakoro.
 *
 * Expomos DASData, DTSData, DSSData e processadores para Python.
 * Usamos buffer_protocol para que np.array(obj) retorne uma view
 * zero-copy (quando possível) dos dados internos.
 */

#include "alakoro/core.hpp"
#include "alakoro/processors.hpp"
#include "alakoro/serialization.hpp"

#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <cstddef>
#include <sstream>
#include <string>

namespace py = pybind11;
using namespace alakoro;

/**
 * @brief Registra uma classe SensingData<T, M> no módulo Python.
 *
 * Usamos uma função template para evitar repetir código para cada
 * combinação de tipo e modalidade. O nome da classe Python inclui
 * o tipo (f/d) para permitir overloads claros.
 */
template <NumericScalar T, SensingModality M>
void bind_sensing_data(py::module& m, const char* class_name) {
    using DataT = SensingData<T, M>;

    py::class_<DataT>(m, class_name, py::buffer_protocol())
        .def(py::init<std::size_t, std::size_t>(),
             py::arg("n_times"), py::arg("n_channels"),
             ("Construct " + std::string(class_name) + " with shape (n_times, n_channels)").c_str())
        .def_buffer([](DataT& d) -> py::buffer_info {
            // Buffer protocol: expõe o std::vector interno como um array NumPy 2D
            // row-major [time, channel]. Como os dados são contíguos, não há cópia.
            return py::buffer_info(
                d.data().data(),                          // ponteiro para dados
                sizeof(T),                                // tamanho do elemento
                py::format_descriptor<T>::format(),       // formato numpy
                2,                                        // ndim
                {d.n_times(), d.n_channels()},            // shape
                {sizeof(T) * d.n_channels(), sizeof(T)}   // strides (row-major)
            );
        })
        .def("__getitem__",
             [](DataT& d, std::pair<std::size_t, std::size_t> idx) -> T {
                 return d(idx.first, idx.second);
             },
             py::arg("idx"), "Access data[t, c]")
        .def("__setitem__",
             [](DataT& d, std::pair<std::size_t, std::size_t> idx, T value) {
                 d(idx.first, idx.second) = value;
             },
             py::arg("idx"), py::arg("value"), "Set data[t, c]")
        .def_property_readonly("n_times", &DataT::n_times, "Number of time samples")
        .def_property_readonly("n_channels", &DataT::n_channels, "Number of channels")
        .def_property_readonly("shape",
             [](const DataT& d) { return std::make_pair(d.n_times(), d.n_channels()); },
             "Shape as (n_times, n_channels)")
        .def_property_readonly("modality",
             [](const DataT& d) { return std::string(d.modality_str()); },
             "Modality string")
        .def_property("metadata",
             [](DataT& d) -> AcquisitionMetadata& { return d.metadata(); },
             [](DataT& d, const AcquisitionMetadata& m) { d.metadata() = m; },
             py::return_value_policy::reference_internal,
             "Acquisition metadata")
        .def("to_jsonld", &serialization::to_jsonld<T, M>, "Serialize to JSON-LD string");
}

/**
 * @brief Bind da struct AcquisitionMetadata.
 */
void bind_metadata(py::module& m) {
    py::class_<AcquisitionMetadata>(m, "AcquisitionMetadata")
        .def(py::init<>())
        .def_readwrite("sampling_rate_hz", &AcquisitionMetadata::sampling_rate_hz)
        .def_readwrite("spatial_resolution_m", &AcquisitionMetadata::spatial_resolution_m)
        .def_readwrite("gauge_length_m", &AcquisitionMetadata::gauge_length_m)
        .def_readwrite("units", &AcquisitionMetadata::units)
        .def_readwrite("start_time", &AcquisitionMetadata::start_time)
        .def("__repr__", [](const AcquisitionMetadata& m) {
            std::ostringstream oss;
            oss << "AcquisitionMetadata(sampling_rate_hz=" << m.sampling_rate_hz
                << ", spatial_resolution_m=" << m.spatial_resolution_m
                << ", gauge_length_m=" << m.gauge_length_m
                << ", units=" << m.units
                << ", start_time=" << m.start_time << ")";
            return oss.str();
        });
}

/**
 * @brief Helpers para processadores funcionarem com SensingData via Python.
 */
template <NumericScalar T, SensingModality M>
void bind_processor_overloads(py::module& m) {
    using DataT = SensingData<T, M>;

    // Nota: não sobrecarregamos o nome global aqui para evitar ambiguidade.
    // Em Python usamos alakoro_core.detrend_das(data), etc.
}

PYBIND11_MODULE(_alakoro_core, m) {
    m.doc() = "Alakoro FiberSense — C++20 core extension";

    bind_metadata(m);

    // ─── Modalidades ───
    bind_sensing_data<float,  SensingModality::DAS>(m, "DASData_f");
    bind_sensing_data<double, SensingModality::DAS>(m, "DASData_d");
    bind_sensing_data<float,  SensingModality::DTS>(m, "DTSData_f");
    bind_sensing_data<double, SensingModality::DTS>(m, "DTSData_d");
    bind_sensing_data<float,  SensingModality::DSS>(m, "DSSData_f");
    bind_sensing_data<double, SensingModality::DSS>(m, "DSSData_d");

    // ─── Processadores (especializados por tipo para evitar ambiguidade) ───
    m.def("detrend_f",
          [](SensingData<float, SensingModality::DAS>& d) { detrend(d); },
          "Detrend DAS float data");
    m.def("detrend_d",
          [](SensingData<double, SensingModality::DAS>& d) { detrend(d); },
          "Detrend DAS double data");
    m.def("detrend_f",
          [](SensingData<float, SensingModality::DTS>& d) { detrend(d); },
          "Detrend DTS float data");
    m.def("detrend_d",
          [](SensingData<double, SensingModality::DTS>& d) { detrend(d); },
          "Detrend DTS double data");

    m.def("demean_f",
          [](SensingData<float, SensingModality::DAS>& d) { demean(d); },
          "Remove mean from DAS float data");
    m.def("demean_d",
          [](SensingData<double, SensingModality::DAS>& d) { demean(d); },
          "Remove mean from DAS double data");

    m.def("taper_f",
          [](SensingData<float, SensingModality::DAS>& d, double alpha) { taper(d, alpha); },
          py::arg("data"), py::arg("alpha") = 0.0,
          "Apply cosine taper to DAS float data");
    m.def("taper_d",
          [](SensingData<double, SensingModality::DAS>& d, double alpha) { taper(d, alpha); },
          py::arg("data"), py::arg("alpha") = 0.0,
          "Apply cosine taper to DAS double data");

    m.def("decimate_f",
          [](const SensingData<float, SensingModality::DAS>& d, std::size_t factor) {
              auto out = decimate(d.data(), d.n_times(), d.n_channels(), factor);
              const std::size_t n_out = out.size() / d.n_channels();
              return SensingData<float, SensingModality::DAS>(n_out, d.n_channels(),
                                                              std::span<const float>(out));
          },
          py::arg("data"), py::arg("factor"),
          "Decimate DAS float data by factor");

    m.def("decimate_d",
          [](const SensingData<double, SensingModality::DAS>& d, std::size_t factor) {
              auto out = decimate(d.data(), d.n_times(), d.n_channels(), factor);
              const std::size_t n_out = out.size() / d.n_channels();
              return SensingData<double, SensingModality::DAS>(n_out, d.n_channels(),
                                                               std::span<const double>(out));
          },
          py::arg("data"), py::arg("factor"),
          "Decimate DAS double data by factor");

    // ─── Serialização stubs ───
    m.def("serialize_avro", []() {
        throw std::runtime_error("Avro serialization not implemented in Phase 1");
    }, "Avro serialization (stub)");
    m.def("serialize_protobuf", []() {
        throw std::runtime_error("Protobuf serialization not implemented in Phase 1");
    }, "Protobuf serialization (stub)");
}
