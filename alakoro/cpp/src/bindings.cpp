/**
 * @file bindings.cpp
 * @brief Bindings pybind11 da camada C++20 do Alakoro.
 *
 * Expomos DASData, DTSData, DSSData e processadores para Python.
 * Usamos buffer_protocol para que np.array(obj) retorne uma view
 * zero-copy (quando possível) dos dados internos.
 */

#include "alakoro/adaptive.hpp"
#include "alakoro/core.hpp"
#include "alakoro/decomposition.hpp"
#include "alakoro/decoupling.hpp"
#include "alakoro/denoising.hpp"
#include "alakoro/event_detection.hpp"
#include "alakoro/filters.hpp"
#include "alakoro/fft.hpp"
#include "alakoro/inference_engine.hpp"
#include "alakoro/mse.hpp"
#include "alakoro/processors.hpp"
#include "alakoro/serialization.hpp"
#include "alakoro/thermal.hpp"
#include "alakoro/time_frequency.hpp"
#include "alakoro/wavelet.hpp"

#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <optional>
#include <span>
#include <sstream>
#include <string>
#include <utility>

namespace py = pybind11;
using namespace alakoro;

/**
 * @brief Converte std::vector<T> para numpy array 1D sem cópia.
 *
 * O vetor é movido para um py::capsule com deleter customizado,
 * garantindo que o array NumPy mantenha os dados vivos.
 */
template <typename T>
py::array_t<T> vector_to_numpy(std::vector<T> vec) {
    const std::size_t size = vec.size();
    T* data = vec.data();
    auto* owned = new std::vector<T>(std::move(vec));
    py::capsule capsule(owned, [](void* p) { delete static_cast<std::vector<T>*>(p); });
    return py::array_t<T>({size}, {sizeof(T)}, data, capsule);
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
    return vector_to_numpy(std::move(flat)).reshape({static_cast<py::ssize_t>(rows), static_cast<py::ssize_t>(cols)});
}

/**
 * @brief Registra uma classe SensingData<T, M> no módulo Python.
 */
template <NumericScalar T, SensingModality M>
void bind_sensing_data(py::module& m, const char* class_name) {
    using DataT = SensingData<T, M>;

    py::class_<DataT>(m, class_name, py::buffer_protocol())
        .def(py::init<std::size_t, std::size_t>(),
             py::arg("n_times"), py::arg("n_channels"),
             ("Construct " + std::string(class_name) + " with shape (n_times, n_channels)").c_str())
        .def_buffer([](DataT& d) -> py::buffer_info {
            return py::buffer_info(
                d.data().data(),
                sizeof(T),
                py::format_descriptor<T>::format(),
                2,
                {d.n_times(), d.n_channels()},
                {sizeof(T) * d.n_channels(), sizeof(T)}
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
             [](DataT& d, const AcquisitionMetadata& meta) { d.metadata() = meta; },
             py::return_value_policy::reference_internal,
             "Acquisition metadata")
        .def("to_jsonld", &serialization::to_jsonld<T, M>, "Serialize to JSON-LD string")
        .def("to_protobuf_bytes",
             [](const DataT& d) -> py::bytes {
                 return py::bytes(serialization::to_protobuf<T, M>(d));
             },
             "Serialize to Protobuf bytes")
        .def_static("from_protobuf_bytes",
             [](const py::bytes& b) {
                 std::string s = b;
#ifdef ALAKORO_WITH_PROTOBUF
                 return protobuf::from_protobuf<T, M>(s);
#else
                 (void)s;
                 throw std::runtime_error("Protobuf not available");
#endif
             },
             py::arg("data"), "Deserialize from Protobuf bytes");
}

void bind_metadata(py::module& m) {
    py::class_<AcquisitionMetadata>(m, "AcquisitionMetadata")
        .def(py::init<>())
        .def_readwrite("sampling_rate_hz", &AcquisitionMetadata::sampling_rate_hz)
        .def_readwrite("spatial_resolution_m", &AcquisitionMetadata::spatial_resolution_m)
        .def_readwrite("gauge_length_m", &AcquisitionMetadata::gauge_length_m)
        .def_readwrite("units", &AcquisitionMetadata::units)
        .def_readwrite("start_time", &AcquisitionMetadata::start_time)
        .def_readwrite("brillouin_c11_mhz_per_ustrain",
                       &AcquisitionMetadata::brillouin_c11_mhz_per_ustrain,
                       "Brillouin strain sensitivity at 1550 nm (MHz per microstrain)")
        .def_readwrite("brillouin_c12_mhz_per_c",
                       &AcquisitionMetadata::brillouin_c12_mhz_per_c,
                       "Brillouin temperature sensitivity at 1550 nm (MHz per degC)")
        .def_readwrite("thermal_reference_modality",
                       &AcquisitionMetadata::thermal_reference_modality,
                       "Thermal reference modality for cross-compensation ('dts'|'das'|'none')")
        .def_readwrite("dual_fiber_config", &AcquisitionMetadata::dual_fiber_config,
                       "Dual-fiber (double-ended loop) configuration flag")
        .def("__repr__", [](const AcquisitionMetadata& meta) {
            std::ostringstream oss;
            oss << "AcquisitionMetadata(sampling_rate_hz=" << meta.sampling_rate_hz
                << ", spatial_resolution_m=" << meta.spatial_resolution_m
                << ", gauge_length_m=" << meta.gauge_length_m
                << ", units=" << meta.units
                << ", start_time=" << meta.start_time
                << ", brillouin_c11_mhz_per_ustrain=" << meta.brillouin_c11_mhz_per_ustrain
                << ", brillouin_c12_mhz_per_c=" << meta.brillouin_c12_mhz_per_c
                << ", thermal_reference_modality=" << meta.thermal_reference_modality
                << ", dual_fiber_config=" << meta.dual_fiber_config << ")";
            return oss.str();
        });
}

// Funções auxiliares para converter lista de vetores em lista de arrays 2D
py::list vector_of_matrix_to_list(const std::vector<std::vector<std::vector<double>>>& data) {
    py::list result;
    for (const auto& mat : data) {
        result.append(matrix_to_numpy(mat));
    }
    return result;
}

py::list vector_of_vector_to_list(const std::vector<std::vector<double>>& data) {
    py::list result;
    for (const auto& row : data) {
        result.append(vector_to_numpy(row));
    }
    return result;
}

/**
 * @brief Converte std::vector<T> flat 2D de volta para numpy array 2D.
 */
template <typename T>
py::array_t<T> vector_to_numpy_2d(std::vector<T> vec, std::size_t n_times, std::size_t n_channels) {
    auto* owned = new std::vector<T>(std::move(vec));
    T* data = owned->data();
    py::capsule capsule(owned, [](void* p) { delete static_cast<std::vector<T>*>(p); });
    return py::array_t<T>(
        {static_cast<py::ssize_t>(n_times), static_cast<py::ssize_t>(n_channels)},
        {sizeof(T) * n_channels, sizeof(T)},
        data,
        capsule
    );
}

/**
 * @brief Dispacha o nome de um material (string) para uma função template.
 *
 * Cada branch passa um std::integral_constant<MaterialAlvenaria, M>, assim o
 * corpo da lambda pode usar `constexpr auto M = decltype(c)::value` com
 * if constexpr — dispatch em tempo de compilação a partir de runtime.
 *
 * @throws std::invalid_argument Se o material não for um dos quatro conhecidos.
 */
template <typename F>
decltype(auto) dispatch_mse_material(const std::string& material, F&& fn) {
    namespace mse = alakoro::mse;
    if (material == "tijolo") {
        return fn(std::integral_constant<mse::MaterialAlvenaria, mse::MaterialAlvenaria::Tijolo>{});
    }
    if (material == "pedra") {
        return fn(std::integral_constant<mse::MaterialAlvenaria, mse::MaterialAlvenaria::Pedra>{});
    }
    if (material == "argamassa") {
        return fn(std::integral_constant<mse::MaterialAlvenaria, mse::MaterialAlvenaria::Argamassa>{});
    }
    if (material == "concreto") {
        return fn(std::integral_constant<mse::MaterialAlvenaria, mse::MaterialAlvenaria::Concreto>{});
    }
    throw std::invalid_argument(
        "dispatch_mse_material: unknown material '" + material +
        "' (expected: tijolo, pedra, argamassa, concreto)");
}

PYBIND11_MODULE(_alakoro_core, m) {
    m.doc() = "Alakoro FiberSense — C++20 core extension";

    bind_metadata(m);

    // Modalidades
    bind_sensing_data<float,  SensingModality::DAS>(m, "DASData_f");
    bind_sensing_data<double, SensingModality::DAS>(m, "DASData_d");
    bind_sensing_data<float,  SensingModality::DTS>(m, "DTSData_f");
    bind_sensing_data<double, SensingModality::DTS>(m, "DTSData_d");
    bind_sensing_data<float,  SensingModality::DSS>(m, "DSSData_f");
    bind_sensing_data<double, SensingModality::DSS>(m, "DSSData_d");

    // Processadores básicos — DAS/DTS/DSS
    m.def("detrend_f_das", [](SensingData<float, SensingModality::DAS>& d) { detrend(d); }, "Detrend DAS float");
    m.def("detrend_d_das", [](SensingData<double, SensingModality::DAS>& d) { detrend(d); }, "Detrend DAS double");
    m.def("detrend_f_dts", [](SensingData<float, SensingModality::DTS>& d) { detrend(d); }, "Detrend DTS float");
    m.def("detrend_d_dts", [](SensingData<double, SensingModality::DTS>& d) { detrend(d); }, "Detrend DTS double");
    m.def("detrend_f_dss", [](SensingData<float, SensingModality::DSS>& d) { detrend(d); }, "Detrend DSS float");
    m.def("detrend_d_dss", [](SensingData<double, SensingModality::DSS>& d) { detrend(d); }, "Detrend DSS double");
    m.attr("detrend_f") = m.attr("detrend_f_das");
    m.attr("detrend_d") = m.attr("detrend_d_das");

    m.def("demean_f_das", [](SensingData<float, SensingModality::DAS>& d) { demean(d); }, "Demean DAS float");
    m.def("demean_d_das", [](SensingData<double, SensingModality::DAS>& d) { demean(d); }, "Demean DAS double");
    m.def("demean_f_dts", [](SensingData<float, SensingModality::DTS>& d) { demean(d); }, "Demean DTS float");
    m.def("demean_d_dts", [](SensingData<double, SensingModality::DTS>& d) { demean(d); }, "Demean DTS double");
    m.def("demean_f_dss", [](SensingData<float, SensingModality::DSS>& d) { demean(d); }, "Demean DSS float");
    m.def("demean_d_dss", [](SensingData<double, SensingModality::DSS>& d) { demean(d); }, "Demean DSS double");
    m.attr("demean_f") = m.attr("demean_f_das");
    m.attr("demean_d") = m.attr("demean_d_das");

    m.def("taper_f_das", [](SensingData<float, SensingModality::DAS>& d, double alpha) { taper(d, alpha); },
          py::arg("data"), py::arg("alpha") = 0.0, "Taper DAS float");
    m.def("taper_d_das", [](SensingData<double, SensingModality::DAS>& d, double alpha) { taper(d, alpha); },
          py::arg("data"), py::arg("alpha") = 0.0, "Taper DAS double");
    m.def("taper_f_dts", [](SensingData<float, SensingModality::DTS>& d, double alpha) { taper(d, alpha); },
          py::arg("data"), py::arg("alpha") = 0.0, "Taper DTS float");
    m.def("taper_d_dts", [](SensingData<double, SensingModality::DTS>& d, double alpha) { taper(d, alpha); },
          py::arg("data"), py::arg("alpha") = 0.0, "Taper DTS double");
    m.attr("taper_f") = m.attr("taper_f_das");
    m.attr("taper_d") = m.attr("taper_d_das");

    m.def("decimate_f_das", [](const SensingData<float, SensingModality::DAS>& d, std::size_t factor) {
              auto out = decimate(d.data(), d.n_times(), d.n_channels(), factor);
              return SensingData<float, SensingModality::DAS>(out.size() / d.n_channels(), d.n_channels(), std::span<const float>(out));
          }, py::arg("data"), py::arg("factor"), "Decimate DAS float");
    m.def("decimate_d_das", [](const SensingData<double, SensingModality::DAS>& d, std::size_t factor) {
              auto out = decimate(d.data(), d.n_times(), d.n_channels(), factor);
              return SensingData<double, SensingModality::DAS>(out.size() / d.n_channels(), d.n_channels(), std::span<const double>(out));
          }, py::arg("data"), py::arg("factor"), "Decimate DAS double");
    m.def("decimate_f_dts", [](const SensingData<float, SensingModality::DTS>& d, std::size_t factor) {
              auto out = decimate(d.data(), d.n_times(), d.n_channels(), factor);
              return SensingData<float, SensingModality::DTS>(out.size() / d.n_channels(), d.n_channels(), std::span<const float>(out));
          }, py::arg("data"), py::arg("factor"), "Decimate DTS float");
    m.def("decimate_d_dts", [](const SensingData<double, SensingModality::DTS>& d, std::size_t factor) {
              auto out = decimate(d.data(), d.n_times(), d.n_channels(), factor);
              return SensingData<double, SensingModality::DTS>(out.size() / d.n_channels(), d.n_channels(), std::span<const double>(out));
          }, py::arg("data"), py::arg("factor"), "Decimate DTS double");
    m.attr("decimate_f") = m.attr("decimate_f_das");
    m.attr("decimate_d") = m.attr("decimate_d_das");

    // Filtros Butterworth — DAS e DTS
    auto bw_lowpass_d_das = [](SensingData<double, SensingModality::DAS>& d, double fs, double fc) {
        alakoro::filters::butterworth_lowpass<double, 2>(d.data(), d.n_times(), d.n_channels(), fs, fc);
    };
    auto bw_lowpass_d_dts = [](SensingData<double, SensingModality::DTS>& d, double fs, double fc) {
        alakoro::filters::butterworth_lowpass<double, 2>(d.data(), d.n_times(), d.n_channels(), fs, fc);
    };
    m.def("butterworth_lowpass_d", bw_lowpass_d_das,
          py::arg("data"), py::arg("sample_rate_hz"), py::arg("cutoff_hz"),
          "Apply 2nd-order Butterworth lowpass filter (double, DAS/DTS)");
    m.def("butterworth_lowpass_d_das", bw_lowpass_d_das,
          py::arg("data"), py::arg("sample_rate_hz"), py::arg("cutoff_hz"),
          "Apply 2nd-order Butterworth lowpass filter (double, DAS)");
    m.def("butterworth_lowpass_d_dts", bw_lowpass_d_dts,
          py::arg("data"), py::arg("sample_rate_hz"), py::arg("cutoff_hz"),
          "Apply 2nd-order Butterworth lowpass filter (double, DTS)");

    auto bw_highpass_d_das = [](SensingData<double, SensingModality::DAS>& d, double fs, double fc) {
        alakoro::filters::butterworth_highpass<double, 2>(d.data(), d.n_times(), d.n_channels(), fs, fc);
    };
    auto bw_highpass_d_dts = [](SensingData<double, SensingModality::DTS>& d, double fs, double fc) {
        alakoro::filters::butterworth_highpass<double, 2>(d.data(), d.n_times(), d.n_channels(), fs, fc);
    };
    m.def("butterworth_highpass_d", bw_highpass_d_das,
          py::arg("data"), py::arg("sample_rate_hz"), py::arg("cutoff_hz"),
          "Apply 2nd-order Butterworth highpass filter (double, DAS/DTS)");
    m.def("butterworth_highpass_d_das", bw_highpass_d_das,
          py::arg("data"), py::arg("sample_rate_hz"), py::arg("cutoff_hz"),
          "Apply 2nd-order Butterworth highpass filter (double, DAS)");
    m.def("butterworth_highpass_d_dts", bw_highpass_d_dts,
          py::arg("data"), py::arg("sample_rate_hz"), py::arg("cutoff_hz"),
          "Apply 2nd-order Butterworth highpass filter (double, DTS)");

    auto bw_bandpass_d_das = [](SensingData<double, SensingModality::DAS>& d, double fs, double f1, double f2) {
        alakoro::filters::butterworth_bandpass<double, 2>(d.data(), d.n_times(), d.n_channels(), fs, f1, f2);
    };
    auto bw_bandpass_d_dts = [](SensingData<double, SensingModality::DTS>& d, double fs, double f1, double f2) {
        alakoro::filters::butterworth_bandpass<double, 2>(d.data(), d.n_times(), d.n_channels(), fs, f1, f2);
    };
    m.def("butterworth_bandpass_d", bw_bandpass_d_das,
          py::arg("data"), py::arg("sample_rate_hz"), py::arg("low_hz"), py::arg("high_hz"),
          "Apply 2nd-order Butterworth bandpass filter (double, DAS/DTS)");
    m.def("butterworth_bandpass_d_das", bw_bandpass_d_das,
          py::arg("data"), py::arg("sample_rate_hz"), py::arg("low_hz"), py::arg("high_hz"),
          "Apply 2nd-order Butterworth bandpass filter (double, DAS)");
    m.def("butterworth_bandpass_d_dts", bw_bandpass_d_dts,
          py::arg("data"), py::arg("sample_rate_hz"), py::arg("low_hz"), py::arg("high_hz"),
          "Apply 2nd-order Butterworth bandpass filter (double, DTS)");

    // Manter aliases float antigos (DAS) para compatibilidade
    m.def("butterworth_lowpass_f",
          [](SensingData<float, SensingModality::DAS>& d, double fs, double fc) {
              alakoro::filters::butterworth_lowpass<float, 2>(d.data(), d.n_times(), d.n_channels(), fs, fc);
          }, py::arg("data"), py::arg("sample_rate_hz"), py::arg("cutoff_hz"),
          "Apply 2nd-order Butterworth lowpass filter (float, DAS)");
    m.def("butterworth_highpass_f",
          [](SensingData<float, SensingModality::DAS>& d, double fs, double fc) {
              alakoro::filters::butterworth_highpass<float, 2>(d.data(), d.n_times(), d.n_channels(), fs, fc);
          }, py::arg("data"), py::arg("sample_rate_hz"), py::arg("cutoff_hz"),
          "Apply 2nd-order Butterworth highpass filter (float, DAS)");
    m.def("butterworth_bandpass_f",
          [](SensingData<float, SensingModality::DAS>& d, double fs, double f1, double f2) {
              alakoro::filters::butterworth_bandpass<float, 2>(d.data(), d.n_times(), d.n_channels(), fs, f1, f2);
          }, py::arg("data"), py::arg("sample_rate_hz"), py::arg("low_hz"), py::arg("high_hz"),
          "Apply 2nd-order Butterworth bandpass filter (float, DAS)");

    // FFT / PSD
    auto mag_spec_d_das = [](const SensingData<double, SensingModality::DAS>& d) {
        return vector_to_numpy(alakoro::fft::magnitude_spectrum<double>(d.data(), d.n_times(), d.n_channels()));
    };
    auto mag_spec_d_dts = [](const SensingData<double, SensingModality::DTS>& d) {
        return vector_to_numpy(alakoro::fft::magnitude_spectrum<double>(d.data(), d.n_times(), d.n_channels()));
    };
    m.def("magnitude_spectrum_d", mag_spec_d_das, py::arg("data"), "Compute magnitude spectrum per channel (double, DAS)");
    m.def("magnitude_spectrum_d_das", mag_spec_d_das, py::arg("data"), "Compute magnitude spectrum per channel (double, DAS)");
    m.def("magnitude_spectrum_d_dts", mag_spec_d_dts, py::arg("data"), "Compute magnitude spectrum per channel (double, DTS)");

    auto psd_d_das = [](const SensingData<double, SensingModality::DAS>& d, double fs) {
        return vector_to_numpy(alakoro::fft::psd<double>(d.data(), d.n_times(), d.n_channels(), fs));
    };
    auto psd_d_dts = [](const SensingData<double, SensingModality::DTS>& d, double fs) {
        return vector_to_numpy(alakoro::fft::psd<double>(d.data(), d.n_times(), d.n_channels(), fs));
    };
    m.def("psd_d", psd_d_das, py::arg("data"), py::arg("sample_rate_hz"), "Compute power spectral density per channel (double, DAS)");
    m.def("psd_d_das", psd_d_das, py::arg("data"), py::arg("sample_rate_hz"), "Compute power spectral density per channel (double, DAS)");
    m.def("psd_d_dts", psd_d_dts, py::arg("data"), py::arg("sample_rate_hz"), "Compute power spectral density per channel (double, DTS)");

    // Wavelet CWT
    auto cwt_d_das = [](const SensingData<double, SensingModality::DAS>& d,
                        const std::vector<double>& scales, double sample_rate_hz, const std::string& wavelet_name) -> py::list {
        auto type = (wavelet_name == "ricker") ? alakoro::wavelet::WaveletType::Ricker : alakoro::wavelet::WaveletType::Morlet;
        auto coefs = alakoro::wavelet::cwt_2d<double>(d.data(), d.n_times(), d.n_channels(), scales, sample_rate_hz, type);
        return vector_of_matrix_to_list(coefs);
    };
    auto cwt_d_dts = [](const SensingData<double, SensingModality::DTS>& d,
                        const std::vector<double>& scales, double sample_rate_hz, const std::string& wavelet_name) -> py::list {
        auto type = (wavelet_name == "ricker") ? alakoro::wavelet::WaveletType::Ricker : alakoro::wavelet::WaveletType::Morlet;
        auto coefs = alakoro::wavelet::cwt_2d<double>(d.data(), d.n_times(), d.n_channels(), scales, sample_rate_hz, type);
        return vector_of_matrix_to_list(coefs);
    };
    m.def("cwt_d", cwt_d_das,
          py::arg("data"), py::arg("scales"), py::arg("sample_rate_hz"), py::arg("wavelet") = "morlet",
          "Compute CWT per channel (double, DAS)");
    m.def("cwt_d_das", cwt_d_das,
          py::arg("data"), py::arg("scales"), py::arg("sample_rate_hz"), py::arg("wavelet") = "morlet",
          "Compute CWT per channel (double, DAS)");
    m.def("cwt_d_dts", cwt_d_dts,
          py::arg("data"), py::arg("scales"), py::arg("sample_rate_hz"), py::arg("wavelet") = "morlet",
          "Compute CWT per channel (double, DTS)");

    // Detecção de eventos
    auto sta_lta_d_das = [](const SensingData<double, SensingModality::DAS>& d, std::size_t n_sta, std::size_t n_lta) {
        return vector_to_numpy(alakoro::event_detection::sta_lta_2d<double>(d.data(), d.n_times(), d.n_channels(), n_sta, n_lta));
    };
    auto sta_lta_d_dts = [](const SensingData<double, SensingModality::DTS>& d, std::size_t n_sta, std::size_t n_lta) {
        return vector_to_numpy(alakoro::event_detection::sta_lta_2d<double>(d.data(), d.n_times(), d.n_channels(), n_sta, n_lta));
    };
    m.def("sta_lta_d", sta_lta_d_das, py::arg("data"), py::arg("n_sta"), py::arg("n_lta"), "Compute STA/LTA ratio per channel (double, DAS)");
    m.def("sta_lta_d_das", sta_lta_d_das, py::arg("data"), py::arg("n_sta"), py::arg("n_lta"), "Compute STA/LTA ratio per channel (double, DAS)");
    m.def("sta_lta_d_dts", sta_lta_d_dts, py::arg("data"), py::arg("n_sta"), py::arg("n_lta"), "Compute STA/LTA ratio per channel (double, DTS)");

    auto hilbert_d_das = [](const SensingData<double, SensingModality::DAS>& d) {
        return vector_to_numpy(alakoro::event_detection::hilbert_envelope_2d<double>(d.data(), d.n_times(), d.n_channels()));
    };
    auto hilbert_d_dts = [](const SensingData<double, SensingModality::DTS>& d) {
        return vector_to_numpy(alakoro::event_detection::hilbert_envelope_2d<double>(d.data(), d.n_times(), d.n_channels()));
    };
    m.def("hilbert_envelope_d", hilbert_d_das, py::arg("data"), "Compute Hilbert envelope per channel (double, DAS)");
    m.def("hilbert_envelope_d_das", hilbert_d_das, py::arg("data"), "Compute Hilbert envelope per channel (double, DAS)");
    m.def("hilbert_envelope_d_dts", hilbert_d_dts, py::arg("data"), "Compute Hilbert envelope per channel (double, DTS)");

    auto teager_d_das = [](const SensingData<double, SensingModality::DAS>& d) {
        return vector_to_numpy(alakoro::event_detection::teager_kaiser_2d<double>(d.data(), d.n_times(), d.n_channels()));
    };
    auto teager_d_dts = [](const SensingData<double, SensingModality::DTS>& d) {
        return vector_to_numpy(alakoro::event_detection::teager_kaiser_2d<double>(d.data(), d.n_times(), d.n_channels()));
    };
    m.def("teager_kaiser_d", teager_d_das, py::arg("data"), "Compute Teager-Kaiser energy operator per channel (double, DAS)");
    m.def("teager_kaiser_d_das", teager_d_das, py::arg("data"), "Compute Teager-Kaiser energy operator per channel (double, DAS)");
    m.def("teager_kaiser_d_dts", teager_d_dts, py::arg("data"), "Compute Teager-Kaiser energy operator per channel (double, DTS)");

    // Denoising
    auto median1d_d_das = [](const SensingData<double, SensingModality::DAS>& d, std::size_t window_size) {
        return vector_to_numpy(alakoro::denoising::median_filter_1d_2d<double>(d.data(), d.n_times(), d.n_channels(), window_size));
    };
    auto median1d_d_dts = [](const SensingData<double, SensingModality::DTS>& d, std::size_t window_size) {
        return vector_to_numpy(alakoro::denoising::median_filter_1d_2d<double>(d.data(), d.n_times(), d.n_channels(), window_size));
    };
    m.def("median_filter_1d_d", median1d_d_das, py::arg("data"), py::arg("window_size"), "Apply 1D median filter per channel (double, DAS)");
    m.def("median_filter_1d_d_das", median1d_d_das, py::arg("data"), py::arg("window_size"), "Apply 1D median filter per channel (double, DAS)");
    m.def("median_filter_1d_d_dts", median1d_d_dts, py::arg("data"), py::arg("window_size"), "Apply 1D median filter per channel (double, DTS)");

    auto median2d_d_das = [](const SensingData<double, SensingModality::DAS>& d, std::size_t window_t, std::size_t window_c) {
        return vector_to_numpy(alakoro::denoising::median_filter_2d<double>(d.data(), d.n_times(), d.n_channels(), window_t, window_c));
    };
    auto median2d_d_dts = [](const SensingData<double, SensingModality::DTS>& d, std::size_t window_t, std::size_t window_c) {
        return vector_to_numpy(alakoro::denoising::median_filter_2d<double>(d.data(), d.n_times(), d.n_channels(), window_t, window_c));
    };
    m.def("median_filter_2d_d", median2d_d_das, py::arg("data"), py::arg("window_t"), py::arg("window_c"), "Apply 2D median filter (double, DAS)");
    m.def("median_filter_2d_d_das", median2d_d_das, py::arg("data"), py::arg("window_t"), py::arg("window_c"), "Apply 2D median filter (double, DAS)");
    m.def("median_filter_2d_d_dts", median2d_d_dts, py::arg("data"), py::arg("window_t"), py::arg("window_c"), "Apply 2D median filter (double, DTS)");

    auto svd_d_das = [](const SensingData<double, SensingModality::DAS>& d, std::size_t n_components) {
        return vector_to_numpy(alakoro::denoising::svd_denoise<double>(d.data(), d.n_times(), d.n_channels(), n_components));
    };
    auto svd_d_dts = [](const SensingData<double, SensingModality::DTS>& d, std::size_t n_components) {
        return vector_to_numpy(alakoro::denoising::svd_denoise<double>(d.data(), d.n_times(), d.n_channels(), n_components));
    };
    m.def("svd_denoise_d", svd_d_das, py::arg("data"), py::arg("n_components"), "Denoise using SVD/PCA (double, DAS)");
    m.def("svd_denoise_d_das", svd_d_das, py::arg("data"), py::arg("n_components"), "Denoise using SVD/PCA (double, DAS)");
    m.def("svd_denoise_d_dts", svd_d_dts, py::arg("data"), py::arg("n_components"), "Denoise using SVD/PCA (double, DTS)");

    auto wdn_d_das = [](const SensingData<double, SensingModality::DAS>& d,
                        const std::vector<double>& scales, double sample_rate_hz, double threshold, const std::string& rule) {
        return vector_to_numpy(alakoro::denoising::wavelet_denoise_2d<double>(d.data(), d.n_times(), d.n_channels(), scales, sample_rate_hz, threshold, rule));
    };
    auto wdn_d_dts = [](const SensingData<double, SensingModality::DTS>& d,
                        const std::vector<double>& scales, double sample_rate_hz, double threshold, const std::string& rule) {
        return vector_to_numpy(alakoro::denoising::wavelet_denoise_2d<double>(d.data(), d.n_times(), d.n_channels(), scales, sample_rate_hz, threshold, rule));
    };
    m.def("wavelet_denoise_d", wdn_d_das,
          py::arg("data"), py::arg("scales"), py::arg("sample_rate_hz"), py::arg("threshold"), py::arg("rule") = "soft",
          "Wavelet thresholding denoising per channel (double, DAS)");
    m.def("wavelet_denoise_d_das", wdn_d_das,
          py::arg("data"), py::arg("scales"), py::arg("sample_rate_hz"), py::arg("threshold"), py::arg("rule") = "soft",
          "Wavelet thresholding denoising per channel (double, DAS)");
    m.def("wavelet_denoise_d_dts", wdn_d_dts,
          py::arg("data"), py::arg("scales"), py::arg("sample_rate_hz"), py::arg("threshold"), py::arg("rule") = "soft",
          "Wavelet thresholding denoising per channel (double, DTS)");

    // Análise tempo-frequência
    auto spec_d_das = [](const SensingData<double, SensingModality::DAS>& d, std::size_t window_size, std::size_t hop_size, std::size_t n_fft) -> py::list {
        return vector_of_matrix_to_list(alakoro::time_frequency::spectrogram_2d<double>(d.data(), d.n_times(), d.n_channels(), window_size, hop_size, n_fft));
    };
    auto spec_d_dts = [](const SensingData<double, SensingModality::DTS>& d, std::size_t window_size, std::size_t hop_size, std::size_t n_fft) -> py::list {
        return vector_of_matrix_to_list(alakoro::time_frequency::spectrogram_2d<double>(d.data(), d.n_times(), d.n_channels(), window_size, hop_size, n_fft));
    };
    m.def("spectrogram_d", spec_d_das,
          py::arg("data"), py::arg("window_size"), py::arg("hop_size"), py::arg("n_fft"),
          "Compute spectrogram per channel (double, DAS)");
    m.def("spectrogram_d_das", spec_d_das,
          py::arg("data"), py::arg("window_size"), py::arg("hop_size"), py::arg("n_fft"),
          "Compute spectrogram per channel (double, DAS)");
    m.def("spectrogram_d_dts", spec_d_dts,
          py::arg("data"), py::arg("window_size"), py::arg("hop_size"), py::arg("n_fft"),
          "Compute spectrogram per channel (double, DTS)");

    auto xcorr_d_das = [](const SensingData<double, SensingModality::DAS>& d, std::size_t max_lag) {
        return vector_to_numpy(alakoro::time_frequency::cross_correlation_channels<double>(d.data(), d.n_times(), d.n_channels(), max_lag));
    };
    auto xcorr_d_dts = [](const SensingData<double, SensingModality::DTS>& d, std::size_t max_lag) {
        return vector_to_numpy(alakoro::time_frequency::cross_correlation_channels<double>(d.data(), d.n_times(), d.n_channels(), max_lag));
    };
    m.def("cross_correlation_d", xcorr_d_das, py::arg("data"), py::arg("max_lag"), "Cross-correlation between adjacent channels (double, DAS)");
    m.def("cross_correlation_d_das", xcorr_d_das, py::arg("data"), py::arg("max_lag"), "Cross-correlation between adjacent channels (double, DAS)");
    m.def("cross_correlation_d_dts", xcorr_d_dts, py::arg("data"), py::arg("max_lag"), "Cross-correlation between adjacent channels (double, DTS)");

    auto coh_d_das = [](const SensingData<double, SensingModality::DAS>& d, std::size_t window_size, std::size_t hop_size, std::size_t n_fft) {
        return vector_to_numpy(alakoro::time_frequency::coherence_channels<double>(d.data(), d.n_times(), d.n_channels(), window_size, hop_size, n_fft));
    };
    auto coh_d_dts = [](const SensingData<double, SensingModality::DTS>& d, std::size_t window_size, std::size_t hop_size, std::size_t n_fft) {
        return vector_to_numpy(alakoro::time_frequency::coherence_channels<double>(d.data(), d.n_times(), d.n_channels(), window_size, hop_size, n_fft));
    };
    m.def("coherence_d", coh_d_das, py::arg("data"), py::arg("window_size"), py::arg("hop_size"), py::arg("n_fft"),
          "Magnitude squared coherence between adjacent channels (double, DAS)");
    m.def("coherence_d_das", coh_d_das, py::arg("data"), py::arg("window_size"), py::arg("hop_size"), py::arg("n_fft"),
          "Magnitude squared coherence between adjacent channels (double, DAS)");
    m.def("coherence_d_dts", coh_d_dts, py::arg("data"), py::arg("window_size"), py::arg("hop_size"), py::arg("n_fft"),
          "Magnitude squared coherence between adjacent channels (double, DTS)");

    // Filtros adaptativos
    auto glc_d_das = [](const SensingData<double, SensingModality::DAS>& d, double gauge_length_m, double channel_spacing_m, double regularization) {
        return vector_to_numpy(alakoro::adaptive::gauge_length_compensation<double>(d.data(), d.n_times(), d.n_channels(), gauge_length_m, channel_spacing_m, regularization));
    };
    auto glc_d_dts = [](const SensingData<double, SensingModality::DTS>& d, double gauge_length_m, double channel_spacing_m, double regularization) {
        return vector_to_numpy(alakoro::adaptive::gauge_length_compensation<double>(d.data(), d.n_times(), d.n_channels(), gauge_length_m, channel_spacing_m, regularization));
    };
    m.def("gauge_length_compensation_d", glc_d_das,
          py::arg("data"), py::arg("gauge_length_m"), py::arg("channel_spacing_m"), py::arg("regularization") = 0.1,
          "Gauge length compensation per channel (double, DAS)");
    m.def("gauge_length_compensation_d_das", glc_d_das,
          py::arg("data"), py::arg("gauge_length_m"), py::arg("channel_spacing_m"), py::arg("regularization") = 0.1,
          "Gauge length compensation per channel (double, DAS)");
    m.def("gauge_length_compensation_d_dts", glc_d_dts,
          py::arg("data"), py::arg("gauge_length_m"), py::arg("channel_spacing_m"), py::arg("regularization") = 0.1,
          "Gauge length compensation per channel (double, DTS)");

    auto lms_d_das = [](const SensingData<double, SensingModality::DAS>& d, double mu, std::size_t filter_order) {
        return vector_to_numpy(alakoro::adaptive::lms_filter_2d<double>(d.data(), d.n_times(), d.n_channels(), mu, filter_order));
    };
    auto lms_d_dts = [](const SensingData<double, SensingModality::DTS>& d, double mu, std::size_t filter_order) {
        return vector_to_numpy(alakoro::adaptive::lms_filter_2d<double>(d.data(), d.n_times(), d.n_channels(), mu, filter_order));
    };
    m.def("lms_filter_d", lms_d_das, py::arg("data"), py::arg("mu"), py::arg("filter_order"), "LMS adaptive filter per channel (double, DAS)");
    m.def("lms_filter_d_das", lms_d_das, py::arg("data"), py::arg("mu"), py::arg("filter_order"), "LMS adaptive filter per channel (double, DAS)");
    m.def("lms_filter_d_dts", lms_d_dts, py::arg("data"), py::arg("mu"), py::arg("filter_order"), "LMS adaptive filter per channel (double, DTS)");

    auto rls_d_das = [](const SensingData<double, SensingModality::DAS>& d, double lambda_, double delta, std::size_t filter_order) {
        return vector_to_numpy(alakoro::adaptive::rls_filter_2d<double>(d.data(), d.n_times(), d.n_channels(), lambda_, delta, filter_order));
    };
    auto rls_d_dts = [](const SensingData<double, SensingModality::DTS>& d, double lambda_, double delta, std::size_t filter_order) {
        return vector_to_numpy(alakoro::adaptive::rls_filter_2d<double>(d.data(), d.n_times(), d.n_channels(), lambda_, delta, filter_order));
    };
    m.def("rls_filter_d", rls_d_das, py::arg("data"), py::arg("lambda_"), py::arg("delta"), py::arg("filter_order"), "RLS adaptive filter per channel (double, DAS)");
    m.def("rls_filter_d_das", rls_d_das, py::arg("data"), py::arg("lambda_"), py::arg("delta"), py::arg("filter_order"), "RLS adaptive filter per channel (double, DAS)");
    m.def("rls_filter_d_dts", rls_d_dts, py::arg("data"), py::arg("lambda_"), py::arg("delta"), py::arg("filter_order"), "RLS adaptive filter per channel (double, DTS)");

    // Decomposições
    auto emd_d_das = [](const SensingData<double, SensingModality::DAS>& d, std::size_t max_imfs) -> py::list {
        return vector_of_matrix_to_list(alakoro::decomposition::emd_2d<double>(d.data(), d.n_times(), d.n_channels(), max_imfs));
    };
    auto emd_d_dts = [](const SensingData<double, SensingModality::DTS>& d, std::size_t max_imfs) -> py::list {
        return vector_of_matrix_to_list(alakoro::decomposition::emd_2d<double>(d.data(), d.n_times(), d.n_channels(), max_imfs));
    };
    m.def("emd_d", emd_d_das, py::arg("data"), py::arg("max_imfs") = 5, "EMD per channel (double, DAS)");
    m.def("emd_d_das", emd_d_das, py::arg("data"), py::arg("max_imfs") = 5, "EMD per channel (double, DAS)");
    m.def("emd_d_dts", emd_d_dts, py::arg("data"), py::arg("max_imfs") = 5, "EMD per channel (double, DTS)");

    auto eemd_d_das = [](const SensingData<double, SensingModality::DAS>& d, std::size_t n_ensembles, double noise_std, std::size_t max_imfs) -> py::list {
        return vector_of_matrix_to_list(alakoro::decomposition::eemd_2d<double>(d.data(), d.n_times(), d.n_channels(), n_ensembles, noise_std, max_imfs));
    };
    auto eemd_d_dts = [](const SensingData<double, SensingModality::DTS>& d, std::size_t n_ensembles, double noise_std, std::size_t max_imfs) -> py::list {
        return vector_of_matrix_to_list(alakoro::decomposition::eemd_2d<double>(d.data(), d.n_times(), d.n_channels(), n_ensembles, noise_std, max_imfs));
    };
    m.def("eemd_d", eemd_d_das, py::arg("data"), py::arg("n_ensembles"), py::arg("noise_std"), py::arg("max_imfs") = 5, "EEMD per channel (double, DAS)");
    m.def("eemd_d_das", eemd_d_das, py::arg("data"), py::arg("n_ensembles"), py::arg("noise_std"), py::arg("max_imfs") = 5, "EEMD per channel (double, DAS)");
    m.def("eemd_d_dts", eemd_d_dts, py::arg("data"), py::arg("n_ensembles"), py::arg("noise_std"), py::arg("max_imfs") = 5, "EEMD per channel (double, DTS)");

    auto nmf_d_das = [](const SensingData<double, SensingModality::DAS>& d, std::size_t n_components, std::size_t max_iter) -> py::tuple {
        auto result_nmf = alakoro::decomposition::nmf<double>(d.data(), d.n_times(), d.n_channels(), n_components, max_iter);
        py::tuple result(2);
        result[0] = vector_to_numpy(result_nmf.first);
        result[1] = vector_to_numpy(result_nmf.second);
        return result;
    };
    auto nmf_d_dts = [](const SensingData<double, SensingModality::DTS>& d, std::size_t n_components, std::size_t max_iter) -> py::tuple {
        auto result_nmf = alakoro::decomposition::nmf<double>(d.data(), d.n_times(), d.n_channels(), n_components, max_iter);
        py::tuple result(2);
        result[0] = vector_to_numpy(result_nmf.first);
        result[1] = vector_to_numpy(result_nmf.second);
        return result;
    };
    m.def("nmf_d", nmf_d_das, py::arg("data"), py::arg("n_components"), py::arg("max_iter") = 100, "NMF factorization V = W * H (double, DAS)");
    m.def("nmf_d_das", nmf_d_das, py::arg("data"), py::arg("n_components"), py::arg("max_iter") = 100, "NMF factorization V = W * H (double, DAS)");
    m.def("nmf_d_dts", nmf_d_dts, py::arg("data"), py::arg("n_components"), py::arg("max_iter") = 100, "NMF factorization V = W * H (double, DTS)");

    // Processadores térmicos (DTS)
    auto thermal_grad_d = [](const SensingData<double, SensingModality::DTS>& d, double depth_step_m) {
        return vector_to_numpy_2d(
            alakoro::thermal::thermal_gradient<double>(d.data(), d.n_times(), d.n_channels(), depth_step_m),
            d.n_times(), d.n_channels());
    };
    m.def("thermal_gradient_d", thermal_grad_d, py::arg("data"), py::arg("depth_step_m"), "Compute thermal gradient dT/dz (double, DTS)");

    auto thermal_base_d = [](const SensingData<double, SensingModality::DTS>& d, double depth_step_m, double surface_temp, double gradient) {
        return vector_to_numpy_2d(
            alakoro::thermal::geothermal_baseline_correction<double>(d.data(), d.n_times(), d.n_channels(), depth_step_m, surface_temp, gradient),
            d.n_times(), d.n_channels());
    };
    m.def("geothermal_baseline_correction_d", thermal_base_d,
          py::arg("data"), py::arg("depth_step_m"), py::arg("surface_temp"), py::arg("gradient"),
          "Remove linear geothermal baseline (double, DTS)");

    auto thermal_anom_d = [](const SensingData<double, SensingModality::DTS>& d, double threshold_sigma) {
        return vector_to_numpy_2d(
            alakoro::thermal::thermal_anomaly_detection<double>(d.data(), d.n_times(), d.n_channels(), threshold_sigma),
            d.n_times(), d.n_channels());
    };
    m.def("thermal_anomaly_detection_d", thermal_anom_d,
          py::arg("data"), py::arg("threshold_sigma"),
          "Detect thermal anomalies per channel using temporal std (double, DTS)");

    auto spatial_median_d = [](const SensingData<double, SensingModality::DTS>& d, std::size_t window_size) {
        return vector_to_numpy_2d(
            alakoro::thermal::spatial_median_filter<double>(d.data(), d.n_times(), d.n_channels(), window_size),
            d.n_times(), d.n_channels());
    };
    m.def("spatial_median_filter_d", spatial_median_d,
          py::arg("data"), py::arg("window_size"),
          "Apply spatial median filter along depth (double, DTS)");

    // =============================================================================
    // Onda 2 — CL-03 desacoplamento tensão-temperatura / CL-07 máscara e atenuação
    // =============================================================================

    // Valida um par de arrays 2D com shapes idênticas; devolve (n_t, n_z).
    auto validate_pair_2d = [](py::array_t<double> a, py::array_t<double> b,
                               const char* name_a, const char* name_b) {
        auto buf_a = a.request();
        auto buf_b = b.request();
        if (buf_a.ndim != 2 || buf_b.ndim != 2) {
            throw std::invalid_argument(
                std::string(name_a) + " and " + name_b +
                " must be 2D arrays (time, channel)");
        }
        if (buf_a.shape[0] != buf_b.shape[0] || buf_a.shape[1] != buf_b.shape[1]) {
            throw std::invalid_argument(
                std::string(name_a) + " and " + name_b +
                " must have the same shape (time, channel)");
        }
        if (buf_a.shape[0] == 0 || buf_a.shape[1] == 0) {
            throw std::invalid_argument(
                std::string(name_a) + " and " + name_b + " must not be empty");
        }
        return std::make_pair(static_cast<std::size_t>(buf_a.shape[0]),
                              static_cast<std::size_t>(buf_a.shape[1]));
    };

    m.def("decouple_strain_temperature_d",
          [validate_pair_2d](py::array_t<double> strain, py::array_t<double> temp,
                             std::size_t win_t, std::size_t win_z, bool constrain_cs) {
              auto [n_t, n_z] = validate_pair_2d(strain, temp, "strain", "temp");
              auto strain_buf = strain.request();
              auto temp_buf = temp.request();
              std::span<const double> strain_span(
                  static_cast<const double*>(strain_buf.ptr), n_t * n_z);
              std::span<const double> temp_span(
                  static_cast<const double*>(temp_buf.ptr), n_t * n_z);

              alakoro::decoupling::DecouplingResult<double> result =
                  constrain_cs
                      ? alakoro::decoupling::decouple_windowed_2d<double, true>(
                            strain_span, temp_span, n_t, n_z, win_t, win_z)
                      : alakoro::decoupling::decouple_windowed_2d<double, false>(
                            strain_span, temp_span, n_t, n_z, win_t, win_z);

              py::dict out;
              out["decoupled"] = vector_to_numpy_2d(
                  std::move(result.decoupled), n_t, n_z);
              out["coefficient_map"] = vector_to_numpy(
                  std::move(result.coefficient_map));
              out["global_coefficient"] = result.global_coefficient;
              out["constrained"] = result.constrained;
              return out;
          },
          py::arg("strain"), py::arg("temp"), py::arg("win_t"), py::arg("win_z"),
          py::arg("constrain_cs") = true,
          "Windowed 2D strain-temperature decoupling (CL-03). strain/temp are "
          "2D (time, channel) float64 arrays with identical shapes. Returns a "
          "dict with keys: 'decoupled' (2D corrected field), 'coefficient_map' "
          "(1D per-position coupling coefficient C), 'global_coefficient' "
          "(Theil-Sen over the whole field) and 'constrained' (True when the "
          "physical constraint C <= 0 was enforced). Windows must be >= 8.");

    m.def("mask_trailing_meters_d",
          [](py::array_t<double> data, double step_m, double mask_m) {
              auto buf = data.request();
              if (buf.ndim != 2) {
                  throw std::invalid_argument(
                      "mask_trailing_meters_d: data must be a 2D array (time, channel)");
              }
              const std::size_t n_t = static_cast<std::size_t>(buf.shape[0]);
              const std::size_t n_z = static_cast<std::size_t>(buf.shape[1]);
              std::vector<double> work(n_t * n_z);
              const double* src = static_cast<const double*>(buf.ptr);
              std::copy(src, src + work.size(), work.begin());
              alakoro::thermal::mask_trailing_meters<double>(
                  std::span<double>(work), n_t, n_z, step_m, mask_m);
              return vector_to_numpy_2d(std::move(work), n_t, n_z);
          },
          py::arg("data"), py::arg("step_m"), py::arg("mask_m"),
          "Mask the trailing mask_m meters of every trace with NaN (CL-07, "
          "dead fiber zone). data is a 2D (time, channel) float64 array.");

    m.def("attenuation_correct_single_ended_d",
          [](py::array_t<double> data, double step_m,
             double ref_start_m, double ref_end_m) {
              auto buf = data.request();
              if (buf.ndim != 2) {
                  throw std::invalid_argument(
                      "attenuation_correct_single_ended_d: data must be a 2D array (time, channel)");
              }
              if (step_m <= 0.0) {
                  throw std::invalid_argument(
                      "attenuation_correct_single_ended_d: step_m must be positive");
              }
              const std::size_t n_t = static_cast<std::size_t>(buf.shape[0]);
              const std::size_t n_z = static_cast<std::size_t>(buf.shape[1]);
              const std::size_t ref_start = static_cast<std::size_t>(
                  std::llround(ref_start_m / step_m));
              const std::size_t ref_end = static_cast<std::size_t>(
                  std::llround(ref_end_m / step_m));
              if (ref_start >= ref_end || ref_end > n_z) {
                  throw std::invalid_argument(
                      "attenuation_correct_single_ended_d: reference zone "
                      "[ref_start_m, ref_end_m) is out of range for the field");
              }
              std::span<const double> data_span(
                  static_cast<const double*>(buf.ptr), n_t * n_z);
              auto result = alakoro::thermal::attenuation_correct_single_ended<double>(
                  data_span, n_t, n_z, step_m, {ref_start, ref_end});
              const double slope = result.slope_per_m;
              const double intercept = result.intercept;
              py::dict out;
              out["corrected"] = vector_to_numpy_2d(std::move(result.corrected), n_t, n_z);
              out["slope_per_m"] = slope;
              out["intercept"] = intercept;
              return out;
          },
          py::arg("data"), py::arg("step_m"), py::arg("ref_start_m"), py::arg("ref_end_m"),
          "Single-ended differential attenuation correction (CL-07): fits a "
          "linear-in-distance drift of the thermal background on the temporal "
          "mean over the reference zone [ref_start_m, ref_end_m) and subtracts "
          "the extrapolated line from the whole field. Returns a dict with "
          "keys: 'corrected' (2D), 'slope_per_m', 'intercept'.");

    m.def("correct_attenuation_double_ended_d",
          [](py::array_t<double> data, double step_m, std::size_t switch_index) {
              auto buf = data.request();
              if (buf.ndim != 2) {
                  throw std::invalid_argument(
                      "correct_attenuation_double_ended_d: data must be a 2D array (time, channel)");
              }
              const std::size_t n_t = static_cast<std::size_t>(buf.shape[0]);
              const std::size_t n_z = static_cast<std::size_t>(buf.shape[1]);
              alakoro::thermal::DoubleEndedConfig config;
              config.switch_index = switch_index;
              config.step_m = step_m;
              config.reference_channel_set = true;
              std::span<const double> data_span(
                  static_cast<const double*>(buf.ptr), n_t * n_z);
              // Extension point documentado (CL-07): levanta std::invalid_argument
              // após validar a configuração.
              return alakoro::thermal::correct_attenuation_double_ended<double>(
                  data_span, n_t, n_z, config);
          },
          py::arg("data"), py::arg("step_m"), py::arg("switch_index"),
          "Documented extension point (CL-07): full double-ended attenuation "
          "correction requires real two-ended data and raises ValueError by design.");

    // Serializacao: metodos por modalidade estao nas classes SensingData.
    // Estes helpers globais permanecem para compatibilidade, orientando o usuario.
    m.def("serialize_avro", []() {
        throw std::runtime_error(
            "Avro serialization is provided by the Python layer (fastavro). "
            "Use AlakoroPatch.to_avro_bytes() or alakoro.io.avro_format.serialize_avro().");
    }, "Avro serialization entry point (Python implementation)");
    m.def("serialize_protobuf", []() {
        throw std::runtime_error(
            "Use DASData/DTSData/DSSData.to_protobuf_bytes() and from_protobuf_bytes(). "
            "Build with -DALAKORO_WITH_PROTOBUF=ON.");
    }, "Protobuf serialization entry point (per-modality methods)");

    // =============================================================================
    // InferenceEngine — motor de inferência com regras canônicas C++20
    // =============================================================================
    using namespace alakoro::inference;

    py::class_<InferenceResult>(m, "InferenceResult")
        .def_readonly("event_type", &InferenceResult::event_type)
        .def_readonly("event_label_pt", &InferenceResult::event_label_pt)
        .def_readonly("event_label_en", &InferenceResult::event_label_en)
        .def_readonly("confidence", &InferenceResult::confidence)
        .def_readonly("depth_md", &InferenceResult::depth_md)
        .def_readonly("severity", &InferenceResult::severity)
        .def_readonly("recommendation", &InferenceResult::recommendation)
        .def_readonly("apparent_velocity_ms", &InferenceResult::apparent_velocity_ms,
                      "Signed apparent velocity in m/s (+=descending); NaN=undetermined")
        .def_readonly("flow_direction", &InferenceResult::flow_direction,
                      "'up' | 'down' | 'undetermined'")
        .def_readonly("discrimination", &InferenceResult::discrimination,
                      "'hydraulic' | 'thermal' | 'inconclusive'; 'none' when not applicable")
        .def("__repr__", [](const InferenceResult& r) {
            std::ostringstream oss;
            oss << "InferenceResult(" << r.event_type
                << ", confidence=" << r.confidence
                << ", depth_md=" << r.depth_md
                << ", severity=" << r.severity << ")";
            return oss.str();
        });

    py::class_<InferenceMetadata>(m, "InferenceMetadata")
        .def(py::init<>())
        .def_readwrite("sampling_rate_hz", &InferenceMetadata::sampling_rate_hz)
        .def_readwrite("depth_step_m", &InferenceMetadata::depth_step_m)
        .def_readwrite("surface_temp_c", &InferenceMetadata::surface_temp_c)
        .def_readwrite("geo_gradient_cpm", &InferenceMetadata::geo_gradient_cpm)
        .def_readwrite("low_freq_band_hz", &InferenceMetadata::low_freq_band_hz,
                       "LF-DAS band lower edge (Hz); below ~0.05 Hz is quasi-static strain")
        .def_readwrite("high_freq_band_hz", &InferenceMetadata::high_freq_band_hz,
                       "LF-DAS band upper edge (Hz); above ~1 Hz is acoustic content")
        .def_readwrite("discrim_low_freq_hz", &InferenceMetadata::discrim_low_freq_hz,
                       "Hydraulic energy band lower edge (Hz) for flow discrimination")
        .def_readwrite("discrim_high_freq_hz", &InferenceMetadata::discrim_high_freq_hz,
                       "Hydraulic energy band upper edge (Hz)")
        .def_readwrite("apply_band_filter", &InferenceMetadata::apply_band_filter,
                       "Apply Butterworth bandpass (low..high freq band) to DAS before rules");

    py::class_<CanonicalInferenceEngine>(m, "CanonicalInferenceEngine")
        .def(py::init<>())
        .def("infer",
             [](const CanonicalInferenceEngine& engine,
                py::array_t<double> dts_array,
                std::optional<py::array_t<double>> das_array,
                const InferenceMetadata& meta) {
                 auto dts_buf = dts_array.request();
                 if (dts_buf.ndim != 2) {
                     throw std::invalid_argument("dts must be a 2D array (time, channel)");
                 }
                 const std::size_t n_times = static_cast<std::size_t>(dts_buf.shape[0]);
                 const std::size_t n_channels = static_cast<std::size_t>(dts_buf.shape[1]);
                 const double* dts_ptr = static_cast<const double*>(dts_buf.ptr);
                 std::span<const double> dts_span(dts_ptr, n_times * n_channels);

                 std::span<const double> das_span;
                 std::vector<double> das_storage;
                 if (das_array.has_value()) {
                     auto das_buf = das_array->request();
                     if (das_buf.size > 0) {
                         if (das_buf.ndim != 2) {
                             throw std::invalid_argument("das must be a 2D array (time, channel)");
                         }
                         if (static_cast<std::size_t>(das_buf.shape[0]) != n_times ||
                             static_cast<std::size_t>(das_buf.shape[1]) != n_channels) {
                             throw std::invalid_argument("dts and das must have the same shape");
                         }
                         das_span = std::span<const double>(static_cast<const double*>(das_buf.ptr),
                                                            n_times * n_channels);
                     }
                 }
                 return engine.infer(dts_span, das_span, n_times, n_channels, meta);
             },
             py::arg("dts"), py::arg("das") = py::none(), py::arg("metadata"),
             "Run all canonical inference rules on DTS (and optional DAS) data.");

    m.def("infer_events_d",
          [](py::array_t<double> dts_array,
             std::optional<py::array_t<double>> das_array,
             const InferenceMetadata& meta) {
              CanonicalInferenceEngine engine;
              auto dts_buf = dts_array.request();
              if (dts_buf.ndim != 2) {
                  throw std::invalid_argument("dts must be a 2D array (time, channel)");
              }
              const std::size_t n_times = static_cast<std::size_t>(dts_buf.shape[0]);
              const std::size_t n_channels = static_cast<std::size_t>(dts_buf.shape[1]);
              std::span<const double> dts_span(static_cast<const double*>(dts_buf.ptr),
                                               n_times * n_channels);
              std::span<const double> das_span;
              if (das_array.has_value()) {
                  auto das_buf = das_array->request();
                  if (das_buf.size > 0) {
                      if (das_buf.ndim != 2) {
                          throw std::invalid_argument("das must be a 2D array (time, channel)");
                      }
                      if (static_cast<std::size_t>(das_buf.shape[0]) != n_times ||
                          static_cast<std::size_t>(das_buf.shape[1]) != n_channels) {
                          throw std::invalid_argument("dts and das must have the same shape");
                      }
                      das_span = std::span<const double>(static_cast<const double*>(das_buf.ptr),
                                                         n_times * n_channels);
                  }
              }
              return engine.infer(dts_span, das_span, n_times, n_channels, meta);
          },
          py::arg("dts"), py::arg("das") = py::none(), py::arg("metadata"),
          "Convenience function: run CanonicalInferenceEngine.infer()");

    // =============================================================================
    // MSE — Monitoramento da Saúde Estrutural (DFOS em edifícios antigos)
    // =============================================================================
    namespace mse = alakoro::mse;

    py::enum_<mse::MaterialAlvenaria>(m, "MaterialAlvenaria",
                                      "Masonry materials for MSE thermal wave analysis")
        .value("Tijolo", mse::MaterialAlvenaria::Tijolo)
        .value("Pedra", mse::MaterialAlvenaria::Pedra)
        .value("Argamassa", mse::MaterialAlvenaria::Argamassa)
        .value("Concreto", mse::MaterialAlvenaria::Concreto);

    m.def("mse_material_traits_d",
          [](const std::string& material) {
              return dispatch_mse_material(material, [](auto material_c) {
                  constexpr auto M = decltype(material_c)::value;
                  return py::make_tuple(
                      mse::MaterialTraits<M>::difusividade_m2_s,
                      mse::MaterialTraits<M>::coef_dilatacao_1_c,
                      mse::penetracao_termica_m<M>(mse::ThermalWaveSolver<M>::kPeriodoDiarioS),
                      mse::penetracao_termica_m<M>(mse::ThermalWaveSolver<M>::kPeriodoAnualS));
              });
          },
          py::arg("material"),
          "Material traits -> (diffusivity_m2_s, expansion_1_per_c, "
          "penetration_daily_m, penetration_annual_m). "
          "material: 'tijolo' | 'pedra' | 'argamassa' | 'concreto'.");

    m.def("mse_thermal_wave_d",
          [](const std::string& material,
             py::array_t<double> profundidades,
             py::array_t<double> tempos,
             py::array_t<double> amplitudes_k,
             double periodo_s,
             bool incluir_anual) {
              auto prof_buf = profundidades.request();
              auto tem_buf = tempos.request();
              auto amp_buf = amplitudes_k.request();
              if (prof_buf.ndim != 1 || tem_buf.ndim != 1 || amp_buf.ndim != 1) {
                  throw std::invalid_argument(
                      "mse_thermal_wave_d: profundidades, tempos and amplitudes_k must be 1D arrays");
              }
              const std::size_t n_pos = static_cast<std::size_t>(prof_buf.shape[0]);
              const std::size_t n_t = static_cast<std::size_t>(tem_buf.shape[0]);
              if (n_pos == 0 || n_t == 0) {
                  throw std::invalid_argument("mse_thermal_wave_d: arrays must not be empty");
              }
              if (amp_buf.shape[0] != tem_buf.shape[0]) {
                  throw std::invalid_argument(
                      "mse_thermal_wave_d: amplitudes_k must have the same size as tempos");
              }
              std::span<const double> prof_span(static_cast<const double*>(prof_buf.ptr), n_pos);
              std::span<const double> tempos_span(static_cast<const double*>(tem_buf.ptr), n_t);
              std::span<const double> amp_span(static_cast<const double*>(amp_buf.ptr), n_t);

              std::vector<double> saida(n_t * n_pos, 0.0);
              std::span<double> saida_span(saida.data(), saida.size());
              dispatch_mse_material(material, [&](auto material_c) {
                  constexpr auto M = decltype(material_c)::value;
                  mse::ThermalWaveSolver<M> solver(prof_span);
                  if (incluir_anual) {
                      solver.template apply<true>(tempos_span, amp_span, saida_span, periodo_s);
                  } else {
                      solver.template apply<false>(tempos_span, amp_span, saida_span, periodo_s);
                  }
              });
              return vector_to_numpy_2d(std::move(saida), n_t, n_pos);
          },
          py::arg("material"), py::arg("profundidades"), py::arg("tempos"),
          py::arg("amplitudes_k"), py::arg("periodo_s"), py::arg("incluir_anual") = false,
          "Analytic Ångström thermal wave T(t, x) for a masonry material. "
          "Returns a 2D array (time, depth) with harmonic daily (periodo_s) plus "
          "optional annual component.");

    m.def("mse_crack_strain_profile_d",
          [](py::array_t<double> posicoes,
             py::array_t<double> posicoes_fissura,
             py::array_t<double> aberturas_mm,
             double comprimento_transferencia_m,
             double resolucao_espacial_m) {
              auto pos_buf = posicoes.request();
              auto fiss_buf = posicoes_fissura.request();
              auto ab_buf = aberturas_mm.request();
              if (pos_buf.ndim != 1 || fiss_buf.ndim != 1 || ab_buf.ndim != 1) {
                  throw std::invalid_argument("mse_crack_strain_profile_d: all arrays must be 1D");
              }
              if (fiss_buf.shape[0] != ab_buf.shape[0]) {
                  throw std::invalid_argument(
                      "mse_crack_strain_profile_d: posicoes_fissura and aberturas_mm sizes differ");
              }
              auto perfil = mse::perfil_deformacao_fissura<double>(
                  std::span<const double>(static_cast<const double*>(pos_buf.ptr),
                                          static_cast<std::size_t>(pos_buf.shape[0])),
                  std::span<const double>(static_cast<const double*>(fiss_buf.ptr),
                                          static_cast<std::size_t>(fiss_buf.shape[0])),
                  std::span<const double>(static_cast<const double*>(ab_buf.ptr),
                                          static_cast<std::size_t>(ab_buf.shape[0])),
                  comprimento_transferencia_m,
                  resolucao_espacial_m);
              return vector_to_numpy(std::move(perfil));
          },
          py::arg("posicoes"), py::arg("posicoes_fissura"), py::arg("aberturas_mm"),
          py::arg("comprimento_transferencia_m"), py::arg("resolucao_espacial_m"),
          "Crack strain profile eps(x) = sum_k (w_k / L_t) * triangle(x; center_k, 2*SR) "
          "with gauge-length moving average (window = L_t / SR samples).");

    m.def("mse_ae_impulse_d",
          [](std::size_t n_amostras, double fs_hz, double f0_hz, double f1_hz,
             double duracao_s, double amplitude_ue, std::uint64_t seed) {
              return vector_to_numpy(
                  mse::impulso_ae(n_amostras, fs_hz, f0_hz, f1_hz,
                                  duracao_s, amplitude_ue, seed));
          },
          py::arg("n_amostras"), py::arg("fs_hz"), py::arg("f0_hz"), py::arg("f1_hz"),
          py::arg("duracao_s"), py::arg("amplitude_ue"), py::arg("seed"),
          "Band-limited AE impulse (f0..f1, deterministic phases from seed) with fast "
          "rise + exponential decay, followed by a permanent crack-opening step "
          "(0.1 * amplitude_ue).");

    m.def("mse_modal_decay_d",
          [](std::size_t n_amostras, double fs_hz, double frequencia_hz,
             double amortecimento, double amplitude) {
              return vector_to_numpy(
                  mse::decaimento_modal(n_amostras, fs_hz, frequencia_hz,
                                        amortecimento, amplitude));
          },
          py::arg("n_amostras"), py::arg("fs_hz"), py::arg("frequencia_hz"),
          py::arg("amortecimento"), py::arg("amplitude"),
          "Damped modal ringing x(t) = A * exp(-zeta*wn*t) * cos(wd*t), "
          "wd = wn*sqrt(1 - zeta^2). Typical 1-5 Hz masonry tower modes.");

    // Re-exporta os nomes MSE e da Onda 2 como atributos do pacote
    // `alakoro_core`. O __init__.py do pacote mantém uma lista fixa de
    // importações (fora do escopo deste módulo C++); sem isso,
    // `from alakoro_core import mse_*` / `decouple_strain_temperature_d`
    // falhariam. PYBIND11_MODULE executa durante o `from ._alakoro_core
    // import (...)` do __init__, então o pacote pai já está em sys.modules.
    if (PyObject* pkg = PyImport_ImportModule("alakoro_core")) {
        py::object pacote = py::reinterpret_steal<py::object>(pkg);
        for (const char* nome : {"mse_thermal_wave_d",
                                 "mse_crack_strain_profile_d",
                                 "mse_ae_impulse_d",
                                 "mse_modal_decay_d",
                                 "mse_material_traits_d",
                                 "MaterialAlvenaria",
                                 "decouple_strain_temperature_d",
                                 "mask_trailing_meters_d",
                                 "attenuation_correct_single_ended_d",
                                 "correct_attenuation_double_ended_d"}) {
            pacote.attr(nome) = m.attr(nome);
        }
    } else {
        // Import standalone do .so (sem o pacote): mantém só o módulo nativo.
        PyErr_Clear();
    }
}
