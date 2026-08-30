/**
 * @file bindings.cpp
 * @brief Bindings pybind11 da camada C++20 do Alakoro.
 *
 * Expomos DASData, DTSData, DSSData e processadores para Python.
 * Usamos buffer_protocol para que np.array(obj) retorne uma view
 * zero-copy (quando possível) dos dados internos.
 */

#include "alakoro/core.hpp"
#include "alakoro/denoising.hpp"
#include "alakoro/event_detection.hpp"
#include "alakoro/filters.hpp"
#include "alakoro/fft.hpp"
#include "alakoro/processors.hpp"
#include "alakoro/serialization.hpp"
#include "alakoro/wavelet.hpp"

#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <cstddef>
#include <sstream>
#include <string>

namespace py = pybind11;
using namespace alakoro;

/**
 * @brief Converte std::vector<T> para numpy array 1D sem cópia.
 *
 * pybind11 pode fazer isso automaticamente com py::array_t, mas criamos
 * um helper para garantir controle do dtype e do ownership.
 */
template <typename T>
py::array_t<T> vector_to_numpy(const std::vector<T>& vec) {
    return py::array_t<T>(
        {vec.size()},
        {sizeof(T)},
        vec.data(),
        py::cast(vec)  // pybind11 gerencia o lifetime do vetor
    );
}

/**
 * @brief Converte std::vector<std::vector<T>> para numpy array 2D.
 */
template <typename T>
py::array_t<T> matrix_to_numpy(const std::vector<std::vector<T>>& mat) {
    if (mat.empty()) {
        return py::array_t<T>({0, 0}, static_cast<T*>(nullptr));
    }
    const std::size_t rows = mat.size();
    const std::size_t cols = mat[0].size();
    std::vector<T> flat;
    flat.reserve(rows * cols);
    for (const auto& row : mat) {
        flat.insert(flat.end(), row.begin(), row.end());
    }
    return py::array_t<T>({rows, cols}, flat.data());
}

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

    // ─── Filtros avançados ───
    m.def("butterworth_lowpass_f",
          [](SensingData<float, SensingModality::DAS>& d, double fs, double fc) {
              alakoro::filters::butterworth_lowpass<float, 2>(
                  d.data(), d.n_times(), d.n_channels(), fs, fc);
          },
          py::arg("data"), py::arg("sample_rate_hz"), py::arg("cutoff_hz"),
          "Apply 2nd-order Butterworth lowpass filter (float)");

    m.def("butterworth_lowpass_d",
          [](SensingData<double, SensingModality::DAS>& d, double fs, double fc) {
              alakoro::filters::butterworth_lowpass<double, 2>(
                  d.data(), d.n_times(), d.n_channels(), fs, fc);
          },
          py::arg("data"), py::arg("sample_rate_hz"), py::arg("cutoff_hz"),
          "Apply 2nd-order Butterworth lowpass filter (double)");

    m.def("butterworth_highpass_f",
          [](SensingData<float, SensingModality::DAS>& d, double fs, double fc) {
              alakoro::filters::butterworth_highpass<float, 2>(
                  d.data(), d.n_times(), d.n_channels(), fs, fc);
          },
          py::arg("data"), py::arg("sample_rate_hz"), py::arg("cutoff_hz"),
          "Apply 2nd-order Butterworth highpass filter (float)");

    m.def("butterworth_highpass_d",
          [](SensingData<double, SensingModality::DAS>& d, double fs, double fc) {
              alakoro::filters::butterworth_highpass<double, 2>(
                  d.data(), d.n_times(), d.n_channels(), fs, fc);
          },
          py::arg("data"), py::arg("sample_rate_hz"), py::arg("cutoff_hz"),
          "Apply 2nd-order Butterworth highpass filter (double)");

    m.def("butterworth_bandpass_f",
          [](SensingData<float, SensingModality::DAS>& d, double fs, double f1, double f2) {
              alakoro::filters::butterworth_bandpass<float, 2>(
                  d.data(), d.n_times(), d.n_channels(), fs, f1, f2);
          },
          py::arg("data"), py::arg("sample_rate_hz"), py::arg("low_hz"), py::arg("high_hz"),
          "Apply 2nd-order Butterworth bandpass filter (float)");

    m.def("butterworth_bandpass_d",
          [](SensingData<double, SensingModality::DAS>& d, double fs, double f1, double f2) {
              alakoro::filters::butterworth_bandpass<double, 2>(
                  d.data(), d.n_times(), d.n_channels(), fs, f1, f2);
          },
          py::arg("data"), py::arg("sample_rate_hz"), py::arg("low_hz"), py::arg("high_hz"),
          "Apply 2nd-order Butterworth bandpass filter (double)");

    // ─── FFT e PSD ───
    m.def("magnitude_spectrum_d",
          [](const SensingData<double, SensingModality::DAS>& d) {
              auto spec = alakoro::fft::magnitude_spectrum<double>(
                  d.data(), d.n_times(), d.n_channels());
              return vector_to_numpy(spec);
          },
          "Compute magnitude spectrum per channel (double)");

    m.def("psd_d",
          [](const SensingData<double, SensingModality::DAS>& d, double fs) {
              auto spec = alakoro::fft::psd<double>(
                  d.data(), d.n_times(), d.n_channels(), fs);
              return vector_to_numpy(spec);
          },
          py::arg("data"), py::arg("sample_rate_hz"),
          "Compute power spectral density per channel (double)");

    // ─── Wavelet CWT ───
    m.def("cwt_d",
          [](const SensingData<double, SensingModality::DAS>& d,
             const std::vector<double>& scales,
             double sample_rate_hz,
             const std::string& wavelet_name) {
              auto type = alakoro::wavelet::WaveletType::Morlet;
              if (wavelet_name == "ricker") {
                  type = alakoro::wavelet::WaveletType::Ricker;
              }
              auto coefs = alakoro::wavelet::cwt_2d<double>(
                  d.data(), d.n_times(), d.n_channels(), scales, sample_rate_hz, type);
              // Retorna lista de arrays 2D (um por canal)
              py::list result;
              for (const auto& channel_coefs : coefs) {
                  result.append(matrix_to_numpy(channel_coefs));
              }
              return result;
          },
          py::arg("data"), py::arg("scales"), py::arg("sample_rate_hz"),
          py::arg("wavelet") = "morlet",
          "Compute CWT per channel (double). Returns list of (n_scales, n_times) arrays.");

    // ─── Detecção de eventos ───
    m.def("sta_lta_d",
          [](const SensingData<double, SensingModality::DAS>& d,
             std::size_t n_sta,
             std::size_t n_lta) {
              auto ratio = alakoro::event_detection::sta_lta_2d<double>(
                  d.data(), d.n_times(), d.n_channels(), n_sta, n_lta);
              return vector_to_numpy(ratio);
          },
          py::arg("data"), py::arg("n_sta"), py::arg("n_lta"),
          "Compute STA/LTA ratio per channel (double).");

    m.def("hilbert_envelope_d",
          [](const SensingData<double, SensingModality::DAS>& d) {
              auto envelope = alakoro::event_detection::hilbert_envelope_2d<double>(
                  d.data(), d.n_times(), d.n_channels());
              return vector_to_numpy(envelope);
          },
          py::arg("data"),
          "Compute Hilbert envelope per channel (double).");

    m.def("teager_kaiser_d",
          [](const SensingData<double, SensingModality::DAS>& d) {
              auto energy = alakoro::event_detection::teager_kaiser_2d<double>(
                  d.data(), d.n_times(), d.n_channels());
              return vector_to_numpy(energy);
          },
          py::arg("data"),
          "Compute Teager-Kaiser energy operator per channel (double).");

    // ─── Denoising ───
    m.def("median_filter_1d_d",
          [](const SensingData<double, SensingModality::DAS>& d, std::size_t window_size) {
              auto filtered = alakoro::denoising::median_filter_1d_2d<double>(
                  d.data(), d.n_times(), d.n_channels(), window_size);
              return vector_to_numpy(filtered);
          },
          py::arg("data"), py::arg("window_size"),
          "Apply 1D median filter per channel (double).");

    m.def("median_filter_2d_d",
          [](const SensingData<double, SensingModality::DAS>& d,
             std::size_t window_t, std::size_t window_c) {
              auto filtered = alakoro::denoising::median_filter_2d<double>(
                  d.data(), d.n_times(), d.n_channels(), window_t, window_c);
              return vector_to_numpy(filtered);
          },
          py::arg("data"), py::arg("window_t"), py::arg("window_c"),
          "Apply 2D median filter (double).");

    m.def("svd_denoise_d",
          [](const SensingData<double, SensingModality::DAS>& d, std::size_t n_components) {
              auto denoised = alakoro::denoising::svd_denoise<double>(
                  d.data(), d.n_times(), d.n_channels(), n_components);
              return vector_to_numpy(denoised);
          },
          py::arg("data"), py::arg("n_components"),
          "Denoise using SVD/PCA keeping n_components principal components (double).");

    m.def("wavelet_denoise_d",
          [](const SensingData<double, SensingModality::DAS>& d,
             const std::vector<double>& scales,
             double sample_rate_hz,
             double threshold,
             const std::string& rule) {
              auto denoised = alakoro::denoising::wavelet_denoise_2d<double>(
                  d.data(), d.n_times(), d.n_channels(), scales, sample_rate_hz, threshold, rule);
              return vector_to_numpy(denoised);
          },
          py::arg("data"), py::arg("scales"), py::arg("sample_rate_hz"),
          py::arg("threshold"), py::arg("rule") = "soft",
          "Wavelet thresholding denoising per channel using Morlet CWT (double).");

    // ─── Serialização stubs ───
    m.def("serialize_avro", []() {
        throw std::runtime_error("Avro serialization not implemented in Phase 1");
    }, "Avro serialization (stub)");
    m.def("serialize_protobuf", []() {
        throw std::runtime_error("Protobuf serialization not implemented in Phase 1");
    }, "Protobuf serialization (stub)");
}
