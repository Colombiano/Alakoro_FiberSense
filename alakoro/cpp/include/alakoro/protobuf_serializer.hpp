/**
 * @file protobuf_serializer.hpp
 * @brief Serializacao Protobuf para SensingData usando C++20 metaprogramacao.
 *
 * Usamos concepts, if constexpr e templates para compartilhar codigo entre
 * as tres modalidades (DAS, DTS, DSS) e dois tipos numericos (float, double).
 *
 * Compila apenas quando ALAKORO_WITH_PROTOBUF esta definido.
 */

#pragma once

#ifdef ALAKORO_WITH_PROTOBUF

#include "alakoro/concepts.hpp"
#include "alakoro/core.hpp"
#include "alakoro_sensing.pb.h"

#include <concepts>
#include <cstddef>
#include <span>
#include <stdexcept>
#include <string>
#include <vector>

namespace alakoro {
namespace protobuf {

/**
 * @brief Mapeia SensingModality para enum Modality do Protobuf em tempo de compilacao.
 */
constexpr ::alakoro::pb::Modality to_proto_modality(SensingModality m) noexcept {
    if (m == SensingModality::DAS) return ::alakoro::pb::Modality::DAS;
    if (m == SensingModality::DTS) return ::alakoro::pb::Modality::DTS;
    return ::alakoro::pb::Modality::DSS;
}

/**
 * @brief Mapeia enum Modality do Protobuf de volta para SensingModality.
 */
constexpr SensingModality from_proto_modality(::alakoro::pb::Modality m) {
    switch (m) {
        case ::alakoro::pb::Modality::DAS: return SensingModality::DAS;
        case ::alakoro::pb::Modality::DTS: return SensingModality::DTS;
        case ::alakoro::pb::Modality::DSS: return SensingModality::DSS;
        default: throw std::invalid_argument("Unknown Protobuf modality");
    }
}

/**
 * @brief Trait para escolher campo de dados do Protobuf em tempo de compilacao.
 *
 * Usamos if constexpr dentro do serializer, mas este trait deixa explicito
 * o mapeamento tipo -> repeated field da mensagem.
 */
template <typename T>
struct ProtoDataField;

template <>
struct ProtoDataField<float> {
    static constexpr const char* dtype_name = "float32";
    static auto& get(::alakoro::pb::SensingData& msg) { return *msg.mutable_data_f32(); }
    static const auto& get(const ::alakoro::pb::SensingData& msg) { return msg.data_f32(); }
};

template <>
struct ProtoDataField<double> {
    static constexpr const char* dtype_name = "float64";
    static auto& get(::alakoro::pb::SensingData& msg) { return *msg.mutable_data_f64(); }
    static const auto& get(const ::alakoro::pb::SensingData& msg) { return msg.data_f64(); }
};

/**
 * @brief Serializador Protobuf generico para SensingData.
 *
 * @tparam T Tipo numerico dos dados (float ou double)
 * @tparam M Modalidade de sensing (DAS, DTS, DSS)
 *
 * Restricoes sao expressas via concepts para produzir erros claros.
 */
template <NumericScalar T, SensingModality M>
    requires FloatingPoint<T>
class ProtobufSerializer {
public:
    using DataT = SensingData<T, M>;

    /**
     * @brief Serializa SensingData em bytes Protobuf.
     */
    std::string serialize(const DataT& data) const {
        ::alakoro::pb::SensingData msg;

        msg.set_modality(to_proto_modality(M));
        msg.set_n_times(data.n_times());
        msg.set_n_channels(data.n_channels());
        msg.set_dtype(ProtoDataField<T>::dtype_name);

        // Metadados
        const auto& meta = data.metadata();
        auto* pm = msg.mutable_metadata();
        pm->set_sampling_rate_hz(meta.sampling_rate_hz);
        pm->set_spatial_resolution_m(meta.spatial_resolution_m);
        pm->set_gauge_length_m(meta.gauge_length_m);
        pm->set_units(meta.units);
        pm->set_start_time(meta.start_time);

        // Dados: copiamos do span para o repeated field correto
        auto& field = ProtoDataField<T>::get(msg);
        const std::span<const T> values = data.data();
        field.Reserve(static_cast<int>(values.size()));
        for (T v : values) {
            field.AddAlreadyReserved(v);
        }

        return msg.SerializeAsString();
    }

    /**
     * @brief Desserializa bytes Protobuf em SensingData.
     */
    DataT deserialize(std::span<const std::byte> bytes) const {
        ::alakoro::pb::SensingData msg;
        if (!msg.ParseFromArray(bytes.data(), static_cast<int>(bytes.size()))) {
            throw std::runtime_error("Failed to parse Protobuf SensingData");
        }

        // Valida modalidade em tempo de execucao (o template fixa M, mas
        // o arquivo pode ter sido gerado por outra especializacao).
        if (from_proto_modality(msg.modality()) != M) {
            throw std::runtime_error("Modality mismatch in Protobuf deserialization");
        }

        // Valida dtype
        const std::string dtype = msg.dtype();
        if constexpr (std::is_same_v<T, float>) {
            if (dtype != "float32") {
                throw std::runtime_error("Dtype mismatch: expected float32");
            }
        } else {
            if (dtype != "float64") {
                throw std::runtime_error("Dtype mismatch: expected float64");
            }
        }

        const std::size_t n_t = msg.n_times();
        const std::size_t n_c = msg.n_channels();
        const std::size_t expected = n_t * n_c;

        std::vector<T> buffer;
        buffer.reserve(expected);

        const auto& field = ProtoDataField<T>::get(msg);
        if (static_cast<std::size_t>(field.size()) != expected) {
            throw std::runtime_error("Data size mismatch in Protobuf deserialization");
        }

        for (const auto& v : field) {
            buffer.push_back(static_cast<T>(v));
        }

        DataT result(n_t, n_c, std::span<const T>(buffer));

        // Restaura metadados
        auto& meta = result.metadata();
        meta.sampling_rate_hz = msg.metadata().sampling_rate_hz();
        meta.spatial_resolution_m = msg.metadata().spatial_resolution_m();
        meta.gauge_length_m = msg.metadata().gauge_length_m();
        meta.units = msg.metadata().units();
        meta.start_time = msg.metadata().start_time();

        return result;
    }

    /**
     * @brief Sobrecarga conveniente que aceita std::string.
     */
    DataT deserialize(const std::string& s) const {
        return deserialize(std::span<const std::byte>(
            reinterpret_cast<const std::byte*>(s.data()), s.size()));
    }
};

/**
 * @brief Funcoes free-standing para uso direto em bindings e tests.
 */
template <NumericScalar T, SensingModality M>
    requires FloatingPoint<T>
std::string to_protobuf(const SensingData<T, M>& data) {
    return ProtobufSerializer<T, M>{}.serialize(data);
}

template <NumericScalar T, SensingModality M>
    requires FloatingPoint<T>
SensingData<T, M> from_protobuf(std::span<const std::byte> bytes) {
    return ProtobufSerializer<T, M>{}.deserialize(bytes);
}

template <NumericScalar T, SensingModality M>
    requires FloatingPoint<T>
SensingData<T, M> from_protobuf(const std::string& s) {
    return ProtobufSerializer<T, M>{}.deserialize(s);
}

} // namespace protobuf
} // namespace alakoro

#endif // ALAKORO_WITH_PROTOBUF
