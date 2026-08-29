/**
 * @file core.hpp
 * @brief Estruturas de dados C++20 para DAS, DTS e DSS.
 *
 * Usamos templates e metaprogramação para compartilhar código entre as
 * três modalidades de sensing, permitindo especializações onde o domínio
 * exige (por exemplo, unidades físicas diferentes).
 *
 * Destaques de C++20:
 *   - concepts (NumericScalar)
 *   - if constexpr para especialização em tempo de compilação
 *   - std::span para views zero-copy sobre buffers externos
 *   - std::optional para metadados opcionais
 */

#pragma once

#include "alakoro/concepts.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <memory>
#include <optional>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>
#include <vector>

namespace alakoro {

/**
 * @brief Enum para identificar a modalidade de sensing em tempo de compilação.
 *
 * Usamos um enum class forte em vez de strings para permitir switch
 * estático e especializações de template.
 */
enum class SensingModality : std::uint8_t {
    DAS, ///< Distributed Acoustic Sensing
    DTS, ///< Distributed Temperature Sensing
    DSS  ///< Distributed Strain Sensing
};

/**
 * @brief Converte a modalidade em string_view constexpr.
 *
 * constexpr permite usar essa função em contextos de compilação,
 * como em static_assert ou em mensagens de erro de concepts.
 */
constexpr std::string_view modality_name(SensingModality m) noexcept {
    switch (m) {
        case SensingModality::DAS: return "DAS";
        case SensingModality::DTS: return "DTS";
        case SensingModality::DSS: return "DSS";
    }
    return "unknown"; // necessário para compilers não terem warning
}

/**
 * @brief Trait para unidades padrão de cada modalidade.
 *
 * Usamos um type trait em vez de herança virtual para obter o valor
 * em tempo de compilação sem overhead de polimorfismo dinâmico.
 */
template <SensingModality M>
struct ModalityTraits {
    static constexpr std::string_view default_units = "unknown";
};

template <>
struct ModalityTraits<SensingModality::DAS> {
    static constexpr std::string_view default_units = "strain_rate";
};

template <>
struct ModalityTraits<SensingModality::DTS> {
    static constexpr std::string_view default_units = "degC";
};

template <>
struct ModalityTraits<SensingModality::DSS> {
    static constexpr std::string_view default_units = "strain";
};

/**
 * @brief Metadados comuns a todas as modalidades.
 *
 * Mantemos metadados como struct simples (POD-friendly) para facilitar
 * interoperabilidade com Python via pybind11.
 */
struct AcquisitionMetadata {
    double sampling_rate_hz = 0.0;      ///< Taxa de amostragem no tempo
    double spatial_resolution_m = 0.0;  ///< Resolução espacial entre canais
    double gauge_length_m = 0.0;        ///< Comprimento gauge do interrogador
    std::string units;                  ///< Unidades dos dados
    std::string start_time;             ///< Timestamp ISO8601 de início
};

/**
 * @brief Classe template base para dados de sensing.
 *
 * @tparam T   Tipo numérico dos dados (float, double, etc.)
 * @tparam M   Modalidade de sensing (DAS, DTS, DSS)
 *
 * A classe armazena dados em um std::vector<T> com layout row-major
 * [time][channel]. Usamos templates para que o compilador gere código
 * otimizado para cada combinação (float/DAS, double/DTS, etc.).
 */
template <NumericScalar T, SensingModality M>
class SensingData {
public:
    using value_type = T;
    static constexpr SensingModality modality = M;

    /**
     * @brief Constrói dados vazios com shape conhecido.
     */
    SensingData(std::size_t n_times, std::size_t n_channels)
        : n_times_(n_times),
          n_channels_(n_channels),
          data_(n_times * n_channels, T{}) {
        metadata_.units = std::string(ModalityTraits<M>::default_units);
    }

    /**
     * @brief Constrói a partir de um span contíguo (zero-copy view não é
     *        possível aqui porque precisamos owned data, mas aceitamos
     *        span para inicialização).
     */
    SensingData(std::size_t n_times, std::size_t n_channels, std::span<const T> src)
        : SensingData(n_times, n_channels) {
        if (src.size() != data_.size()) {
            throw std::invalid_argument("SensingData: span size does not match shape");
        }
        std::copy(src.begin(), src.end(), data_.begin());
    }

    // ─── Acesso a elementos ───

    T& operator()(std::size_t t, std::size_t c) {
        return data_[index(t, c)];
    }

    const T& operator()(std::size_t t, std::size_t c) const {
        return data_[index(t, c)];
    }

    // ─── Views zero-copy ───

    std::span<T> data() { return std::span<T>(data_); }
    std::span<const T> data() const { return std::span<const T>(data_); }

    std::span<T> row(std::size_t t) {
        return std::span<T>(data_.data() + t * n_channels_, n_channels_);
    }

    std::span<const T> row(std::size_t t) const {
        return std::span<const T>(data_.data() + t * n_channels_, n_channels_);
    }

    // ─── Metadados ───

    AcquisitionMetadata& metadata() { return metadata_; }
    const AcquisitionMetadata& metadata() const { return metadata_; }

    std::size_t n_times() const noexcept { return n_times_; }
    std::size_t n_channels() const noexcept { return n_channels_; }
    std::size_t size() const noexcept { return data_.size(); }

    /**
     * @brief Nome da modalidade em tempo de execução.
     *
     * Usamos if constexpr para retornar a string correta sem custo de
     * polimorfismo. O compilador elimina os branches não utilizados.
     *
     * Não é static para permitir binding direto como property no pybind11.
     */
    constexpr std::string_view modality_str() const noexcept {
        if constexpr (M == SensingModality::DAS) return "DAS";
        else if constexpr (M == SensingModality::DTS) return "DTS";
        else return "DSS";
    }

private:
    std::size_t index(std::size_t t, std::size_t c) const {
        return t * n_channels_ + c;
    }

    std::size_t n_times_;
    std::size_t n_channels_;
    std::vector<T> data_;
    AcquisitionMetadata metadata_;
};

/**
 * @brief Alias de template para as três modalidades.
 *
 * Isso torna o código Pythonico no C++: DASData<float>, DTSData<double>, etc.
 */
template <NumericScalar T>
using DASData = SensingData<T, SensingModality::DAS>;

template <NumericScalar T>
using DTSData = SensingData<T, SensingModality::DTS>;

template <NumericScalar T>
using DSSData = SensingData<T, SensingModality::DSS>;

/**
 * @brief Concept para verificar se um tipo é alguma SensingData.
 *
 * Útil em processadores genéricos que operam sobre qualquer modalidade.
 */
template <typename U>
concept AnySensingData = requires(U u) {
    { U::modality } -> std::convertible_to<SensingModality>;
    { u.n_times() } -> std::convertible_to<std::size_t>;
    { u.n_channels() } -> std::convertible_to<std::size_t>;
    { u.data() } -> std::convertible_to<std::span<typename U::value_type>>;
};

} // namespace alakoro
