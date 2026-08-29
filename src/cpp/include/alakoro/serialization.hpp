/**
 * @file serialization.hpp
 * @brief Serialização de dados de sensing.
 *
 * A Fase 1 prevê três formatos: Avro, Protobuf e JSON-LD.
 * Para não introduzir dependências externas pesadas nesta etapa,
 * implementamos JSON-LD manualmente e deixamos stubs para Avro/Protobuf
 * (com mensagens de erro claras).
 *
 * Em fases futuras, Avro e Protobuf podem ser ligados via CMake
 * options (find_package(Avro), find_package(Protobuf)).
 */

#pragma once

#include "alakoro/core.hpp"

#include <cmath>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace alakoro {
namespace serialization {

/**
 * @brief Escapa uma string para JSON válido.
 *
 * Função simples mas suficiente para metadados sem caracteres de controle.
 */
inline std::string json_escape(std::string_view s) {
    std::ostringstream oss;
    oss << '"';
    for (char c : s) {
        switch (c) {
            case '"':  oss << "\\\""; break;
            case '\\': oss << "\\\\"; break;
            case '\b': oss << "\\b";  break;
            case '\f': oss << "\\f";  break;
            case '\n': oss << "\\n";  break;
            case '\r': oss << "\\r";  break;
            case '\t': oss << "\\t";  break;
            default:   oss << c;      break;
        }
    }
    oss << '"';
    return oss.str();
}

/**
 * @brief Converte número para string JSON, tratando NaN/Inf.
 */
template <typename T>
std::string json_number(T v) {
    if constexpr (std::is_floating_point_v<T>) {
        if (std::isnan(v)) return "null";
        if (std::isinf(v)) return v > 0 ? "null" : "null";
    }
    return std::to_string(v);
}

/**
 * @brief Serializa SensingData como JSON-LD.
 *
 * O JSON-LD (JavaScript Object Notation for Linked Data) adiciona um
 * contexto semântico (@context) para que os dados possam ser ingeridos
 * pela ontologia Alakoro em Python.
 */
template <NumericScalar T, SensingModality M>
std::string to_jsonld(const SensingData<T, M>& data) {
    const auto& meta = data.metadata();

    std::ostringstream oss;
    oss << "{\n";
    oss << "  \"@context\": \"https://alakoro.io/schema/v1\",\n";
    oss << "  \"@type\": " << json_escape(std::string(modality_name(M))) << ",\n";
    oss << "  \"modality\": " << json_escape(std::string(modality_name(M))) << ",\n";
    oss << "  \"shape\": [" << data.n_times() << ", " << data.n_channels() << "],\n";

    // Metadados
    oss << "  \"metadata\": {\n";
    oss << "    \"sampling_rate_hz\": " << json_number(meta.sampling_rate_hz) << ",\n";
    oss << "    \"spatial_resolution_m\": " << json_number(meta.spatial_resolution_m) << ",\n";
    oss << "    \"gauge_length_m\": " << json_number(meta.gauge_length_m) << ",\n";
    oss << "    \"units\": " << json_escape(meta.units) << ",\n";
    oss << "    \"start_time\": " << json_escape(meta.start_time) << "\n";
    oss << "  },\n";

    // Dados como array 2D (podemos oferecer base64 em versões futuras)
    oss << "  \"data\": [\n";
    const std::size_t n_t = data.n_times();
    const std::size_t n_c = data.n_channels();
    for (std::size_t t = 0; t < n_t; ++t) {
        oss << "    [";
        for (std::size_t c = 0; c < n_c; ++c) {
            oss << json_number(data(t, c));
            if (c + 1 < n_c) oss << ", ";
        }
        oss << "]";
        if (t + 1 < n_t) oss << ",";
        oss << "\n";
    }
    oss << "  ]\n";
    oss << "}\n";

    return oss.str();
}

/**
 * @brief Stub para serialização Avro.
 *
 * Implementação futura requer Apache Avro C++.
 */
template <NumericScalar T, SensingModality M>
std::vector<std::byte> to_avro(const SensingData<T, M>&) {
    throw std::runtime_error(
        "Avro serialization not implemented in Phase 1. "
        "Build with -DALAKORO_WITH_AVRO=ON and Apache Avro C++ installed.");
}

/**
 * @brief Stub para serialização Protobuf.
 *
 * Implementação futura requer Google Protocol Buffers.
 */
template <NumericScalar T, SensingModality M>
std::vector<std::byte> to_protobuf(const SensingData<T, M>&) {
    throw std::runtime_error(
        "Protobuf serialization not implemented in Phase 1. "
        "Build with -DALAKORO_WITH_PROTOBUF=ON and protobuf installed.");
}

} // namespace serialization
} // namespace alakoro
