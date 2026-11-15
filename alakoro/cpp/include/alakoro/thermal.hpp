/**
 * @file thermal.hpp
 * @brief Processadores térmicos específicos para DTS em C++20.
 *
 * Algoritmos para análise de perfis de temperatura distribuída:
 *   - gradiente térmico com profundidade (dT/dz)
 *   - correção de baseline geotérmico
 *   - detecção de anomalias térmicas
 *   - filtro de mediana espacial ao longo da profundidade
 *
 * Thermal processors for distributed temperature profiles:
 *   - thermal gradient with depth (dT/dz)
 *   - geothermal baseline correction
 *   - thermal anomaly detection
 *   - spatial median filter along depth
 *
 * Recursos C++20:
 *   - concepts (FloatingPoint)
 *   - templates genéricos independentes de modalidade
 *   - std::span para processamento eficiente
 */

#pragma once

#include "alakoro/concepts.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <span>
#include <stdexcept>
#include <utility>
#include <vector>

namespace alakoro::thermal {

/**
 * @brief Calcula o gradiente térmico dT/dz para cada perfil temporal.
 *
 * Usa diferenças centradas no interior e forward/backward nas bordas.
 * Compute thermal gradient dT/dz for each time profile using central
 * differences internally and one-sided differences at edges.
 *
 * @tparam T Tipo de ponto flutuante
 * @param data Dados 2D (time, channels) em graus Celsius
 * @param n_times Número de amostras no tempo
 * @param n_channels Número de canais / profundidades
 * @param depth_step_m Passo entre canais em metros
 * @return Vetor 2D flat com gradiente (mesmo shape dos dados)
 */
template <FloatingPoint T>
std::vector<T> thermal_gradient(std::span<const T> data,
                                std::size_t n_times,
                                std::size_t n_channels,
                                double depth_step_m) {
    if (depth_step_m <= 0.0) {
        throw std::invalid_argument("thermal_gradient: depth_step_m must be positive");
    }
    if (data.size() != n_times * n_channels) {
        throw std::invalid_argument("thermal_gradient: data size does not match shape");
    }

    std::vector<T> gradient(data.size(), T{});
    const double inv_dz = 1.0 / depth_step_m;

    for (std::size_t t = 0; t < n_times; ++t) {
        const std::size_t base = t * n_channels;
        for (std::size_t c = 0; c < n_channels; ++c) {
            if (c == 0) {
                // Forward difference
                gradient[base + c] = static_cast<T>(
                    (data[base + c + 1] - data[base + c]) * inv_dz);
            } else if (c == n_channels - 1) {
                // Backward difference
                gradient[base + c] = static_cast<T>(
                    (data[base + c] - data[base + c - 1]) * inv_dz);
            } else {
                // Central difference
                gradient[base + c] = static_cast<T>(
                    (data[base + c + 1] - data[base + c - 1]) * inv_dz * 0.5);
            }
        }
    }
    return gradient;
}

/**
 * @brief Remove um perfil geotérmico linear dos dados.
 *
 * Baseline = surface_temp + gradient * depth. Retorna os dados corrigidos.
 * Remove a linear geothermal baseline from data.
 *
 * @tparam T Tipo de ponto flutuante
 * @param data Dados 2D (time, channels)
 * @param n_times Número de amostras no tempo
 * @param n_channels Número de canais
 * @param depth_step_m Passo entre canais em metros
 * @param surface_temp Temperatura superficial em °C
 * @param gradient Gradiente geotérmico em °C/m
 * @return Dados corrigidos (flat)
 */
template <FloatingPoint T>
std::vector<T> geothermal_baseline_correction(std::span<const T> data,
                                               std::size_t n_times,
                                               std::size_t n_channels,
                                               double depth_step_m,
                                               double surface_temp,
                                               double gradient) {
    if (data.size() != n_times * n_channels) {
        throw std::invalid_argument("geothermal_baseline_correction: data size does not match shape");
    }

    std::vector<T> corrected(data.size(), T{});
    for (std::size_t t = 0; t < n_times; ++t) {
        const std::size_t base = t * n_channels;
        for (std::size_t c = 0; c < n_channels; ++c) {
            const double depth = static_cast<double>(c) * depth_step_m;
            const double baseline = surface_temp + gradient * depth;
            corrected[base + c] = static_cast<T>(data[base + c] - baseline);
        }
    }
    return corrected;
}

/**
 * @brief Estima o perfil geotérmico linear por regressão nos dados.
 *
 * Calcula a média temporal por canal e ajusta reta depth vs temperature.
 * Estimates linear geothermal profile by temporal averaging and linear fit.
 *
 * @return Par (surface_temp, gradient) em °C e °C/m.
 */
template <FloatingPoint T>
std::pair<double, double> estimate_geothermal_gradient(std::span<const T> data,
                                                        std::size_t n_times,
                                                        std::size_t n_channels,
                                                        double depth_step_m) {
    if (n_times == 0 || n_channels < 2) {
        throw std::invalid_argument("estimate_geothermal_gradient: invalid shape");
    }

    // Média temporal por canal
    std::vector<double> mean_temp(n_channels, 0.0);
    for (std::size_t c = 0; c < n_channels; ++c) {
        double sum = 0.0;
        for (std::size_t t = 0; t < n_times; ++t) {
            sum += static_cast<double>(data[t * n_channels + c]);
        }
        mean_temp[c] = sum / static_cast<double>(n_times);
    }

    // Regressão linear: T = a + b * depth
    double sum_x = 0.0, sum_y = 0.0, sum_xx = 0.0, sum_xy = 0.0;
    const double n = static_cast<double>(n_channels);
    for (std::size_t c = 0; c < n_channels; ++c) {
        const double x = static_cast<double>(c) * depth_step_m;
        const double y = mean_temp[c];
        sum_x += x;
        sum_y += y;
        sum_xx += x * x;
        sum_xy += x * y;
    }

    const double denom = n * sum_xx - sum_x * sum_x;
    if (std::abs(denom) < 1e-12) {
        return {sum_y / n, 0.0};
    }
    const double gradient = (n * sum_xy - sum_x * sum_y) / denom;
    const double surface_temp = (sum_y - gradient * sum_x) / n;
    return {surface_temp, gradient};
}

/**
 * @brief Detecta anomalias térmicas usando desvio padrão por canal.
 *
 * Para cada canal, calcula a média e o desvio ao longo do tempo e marca
 * como anomalia quando |x - mean| > threshold_sigma * std.
 * Detects thermal anomalies using per-channel temporal standard deviation.
 *
 * @tparam T Tipo de ponto flutuante
 * @param data Dados 2D (time, channels)
 * @param n_times Número de amostras no tempo
 * @param n_channels Número de canais
 * @param threshold_sigma Limiar em número de desvios padrão
 * @return Máscara binária 2D (1.0 = anomalia, 0.0 = normal)
 */
template <FloatingPoint T>
std::vector<T> thermal_anomaly_detection(std::span<const T> data,
                                          std::size_t n_times,
                                          std::size_t n_channels,
                                          double threshold_sigma) {
    if (threshold_sigma <= 0.0) {
        throw std::invalid_argument("thermal_anomaly_detection: threshold_sigma must be positive");
    }
    if (data.size() != n_times * n_channels) {
        throw std::invalid_argument("thermal_anomaly_detection: data size does not match shape");
    }

    std::vector<T> mask(data.size(), T{});

    for (std::size_t c = 0; c < n_channels; ++c) {
        // Estatísticas temporais do canal
        double sum = 0.0;
        for (std::size_t t = 0; t < n_times; ++t) {
            sum += static_cast<double>(data[t * n_channels + c]);
        }
        const double mean = sum / static_cast<double>(n_times);

        double sum_sq = 0.0;
        for (std::size_t t = 0; t < n_times; ++t) {
            const double diff = static_cast<double>(data[t * n_channels + c]) - mean;
            sum_sq += diff * diff;
        }
        const double std = std::sqrt(sum_sq / static_cast<double>(n_times));
        const double limit = threshold_sigma * std;

        for (std::size_t t = 0; t < n_times; ++t) {
            const double diff = std::abs(static_cast<double>(data[t * n_channels + c]) - mean);
            mask[t * n_channels + c] = (diff > limit) ? T{1} : T{};
        }
    }
    return mask;
}

/**
 * @brief Filtro de mediana espacial ao longo da profundidade.
 *
 * Para cada amostra temporal, aplica mediana 1D nos vizinhos espaciais.
 * Useful for removing isolated noisy channels in DTS profiles.
 *
 * @tparam T Tipo de ponto flutuante
 * @param data Dados 2D (time, channels)
 * @param n_times Número de amostras no tempo
 * @param n_channels Número de canais
 * @param window_size Tamanho da janela espacial (ímpar)
 * @return Dados filtrados (flat)
 */
template <FloatingPoint T>
std::vector<T> spatial_median_filter(std::span<const T> data,
                                     std::size_t n_times,
                                     std::size_t n_channels,
                                     std::size_t window_size) {
    if (window_size % 2 == 0) {
        throw std::invalid_argument("spatial_median_filter: window_size must be odd");
    }
    if (window_size == 0 || n_channels < window_size) {
        return std::vector<T>(data.begin(), data.end());
    }
    if (data.size() != n_times * n_channels) {
        throw std::invalid_argument("spatial_median_filter: data size does not match shape");
    }

    const std::size_t half = window_size / 2;
    std::vector<T> filtered(data.size(), T{});
    std::vector<T> window;
    window.reserve(window_size);

    for (std::size_t t = 0; t < n_times; ++t) {
        const std::size_t base = t * n_channels;
        for (std::size_t c = 0; c < n_channels; ++c) {
            window.clear();
            const std::size_t start = (c < half) ? 0 : (c - half);
            const std::size_t end = std::min(c + half + 1, n_channels);
            for (std::size_t k = start; k < end; ++k) {
                window.push_back(data[base + k]);
            }
            const std::size_t mid = window.size() / 2;
            std::nth_element(window.begin(), window.begin() + mid, window.end());
            filtered[base + c] = window[mid];
        }
    }
    return filtered;
}

/**
 * @brief Zera (NaN) os últimos `mask_m` metros de cada traço DTS/DAS.
 *
 * A ponta do cabo (região morta / dead zone) frequentemente produz valores
 * sem significado físico. Esta função mascara essa região in-place,
 * preenchendo com quiet_NaN para que regras downstream ignorem a zona.
 *
 * Masks the trailing `mask_m` meters of every trace with quiet_NaN
 * (dead fiber zone), in place.
 *
 * Recursos C++20: concepts (FloatingPoint), std::span in-place, if constexpr
 * para seleção de política de preenchimento (NaN vs. zero).
 *
 * @tparam T Tipo de ponto flutuante
 * @param data Dados 2D (time, channels) — modificado in-place
 * @param n_times Número de amostras no tempo
 * @param n_channels Número de canais
 * @param step_m Passo entre canais em metros
 * @param mask_m Extensão a mascarar a partir da ponta, em metros
 * @param use_nan Se true preenche com NaN; se false, com zero
 */
template <FloatingPoint T>
void mask_trailing_meters(std::span<T> data,
                          std::size_t n_times,
                          std::size_t n_channels,
                          double step_m,
                          double mask_m,
                          bool use_nan = true) {
    if (step_m <= 0.0) {
        throw std::invalid_argument("mask_trailing_meters: step_m must be positive");
    }
    if (mask_m < 0.0) {
        throw std::invalid_argument("mask_trailing_meters: mask_m must be >= 0");
    }
    if (data.size() != n_times * n_channels) {
        throw std::invalid_argument("mask_trailing_meters: data size does not match shape");
    }

    // Número de canais a partir da ponta que ficam mascarados.
    const std::size_t n_mask = std::min<std::size_t>(
        n_channels, static_cast<std::size_t>(std::ceil(mask_m / step_m)));
    if (n_mask == 0) return;

    const T fill = [&] {
        if constexpr (std::numeric_limits<T>::has_quiet_NaN) {
            return use_nan ? std::numeric_limits<T>::quiet_NaN() : T{};
        } else {
            return T{};
        }
    }();

    for (std::size_t t = 0; t < n_times; ++t) {
        const std::size_t base = t * n_channels;
        for (std::size_t k = 0; k < n_mask; ++k) {
            data[base + (n_channels - 1 - k)] = fill;
        }
    }
}

/**
 * @brief Resultado da correção de atenuação single-ended.
 *
 * Aggregate simples para interoperar com pybind11 (dict em Python).
 */
template <FloatingPoint T>
struct AttenuationCorrectionResult {
    std::vector<T> corrected;  ///< Campo corrigido (flat, mesmo shape da entrada)
    double slope_per_m = 0.0;  ///< Deriva linear-in-distância estimada (unidades/m)
    double intercept = 0.0;    ///< Offset no início da fibra (unidades)
};

/**
 * @brief Correção de atenuação diferencial single-ended (CL-07).
 *
 * Em DTS single-ended, a perda diferencial Stokes/anti-Stokes ao longo da
 * fibra aparece como uma deriva aproximadamente linear da temperatura
 * medida com a distância. Esta função estima essa deriva ajustando uma reta
 * sobre o perfil médio temporal restrito a uma zona de referência
 * (`reference_zone`, em índices de canal [início, fim)) assumida isotérmica
 * (fundo térmico estável), e corrige o campo inteiro subtraindo a reta
 * extrapolada: corrected = data − (slope·z + intercept).
 *
 * Single-ended differential attenuation correction: fits a linear-in-distance
 * drift on the time-averaged profile over a configurable isothermal reference
 * zone and subtracts the extrapolated line from the whole field.
 *
 * Simplificação documentada (vs. double-ended completo): com um único extremo
 * não é possível separar perda diferencial de temperatura verdadeira; a deriva
 * residual é modelada como linear e ancorada na zona de referência. A versão
 * double-ended (Stokes+anti-Stokes dos dois extremos) fica como extension
 * point documentado em DoubleEndedConfig.
 *
 * @tparam T Tipo de ponto flutuante
 * @param data Dados 2D (time, channels)
 * @param n_times Número de amostras no tempo
 * @param n_channels Número de canais
 * @param step_m Passo entre canais em metros
 * @param reference_zone Zona de referência [start, end) em índices de canal
 * @return AttenuationCorrectionResult com campo corrigido e coeficientes
 * @throws std::invalid_argument Se step_m <= 0, zona inválida ou shape incompatível
 */
template <FloatingPoint T>
AttenuationCorrectionResult<T>
attenuation_correct_single_ended(std::span<const T> data,
                                 std::size_t n_times,
                                 std::size_t n_channels,
                                 double step_m,
                                 std::pair<std::size_t, std::size_t> reference_zone) {
    if (step_m <= 0.0) {
        throw std::invalid_argument(
            "attenuation_correct_single_ended: step_m must be positive");
    }
    if (data.size() != n_times * n_channels || n_times == 0 || n_channels == 0) {
        throw std::invalid_argument(
            "attenuation_correct_single_ended: data size does not match shape");
    }
    if (reference_zone.first >= reference_zone.second ||
        reference_zone.second > n_channels) {
        throw std::invalid_argument(
            "attenuation_correct_single_ended: reference_zone must satisfy "
            "0 <= start < end <= n_channels");
    }

    // Perfil médio temporal na zona de referência.
    const std::size_t zone_len = reference_zone.second - reference_zone.first;
    std::vector<double> zone_mean(zone_len, 0.0);
    for (std::size_t k = 0; k < zone_len; ++k) {
        const std::size_t c = reference_zone.first + k;
        double sum = 0.0;
        for (std::size_t t = 0; t < n_times; ++t) {
            sum += static_cast<double>(data[t * n_channels + c]);
        }
        zone_mean[k] = sum / static_cast<double>(n_times);
    }

    // Regressão linear mínimos quadrados: z vs. zone_mean.
    double sum_x = 0.0, sum_y = 0.0, sum_xx = 0.0, sum_xy = 0.0;
    for (std::size_t k = 0; k < zone_len; ++k) {
        const double x = static_cast<double>(reference_zone.first + k) * step_m;
        const double y = zone_mean[k];
        sum_x += x;
        sum_y += y;
        sum_xx += x * x;
        sum_xy += x * y;
    }
    const double n = static_cast<double>(zone_len);
    const double denom = n * sum_xx - sum_x * sum_x;
    double slope = 0.0;
    double intercept = sum_y / n;
    if (std::abs(denom) > 1e-12) {
        slope = (n * sum_xy - sum_x * sum_y) / denom;
        intercept = (sum_y - slope * sum_x) / n;
    }

    AttenuationCorrectionResult<T> result;
    result.slope_per_m = slope;
    result.intercept = intercept;
    result.corrected.resize(data.size());
    for (std::size_t t = 0; t < n_times; ++t) {
        for (std::size_t c = 0; c < n_channels; ++c) {
            const double z = static_cast<double>(c) * step_m;
            result.corrected[t * n_channels + c] = static_cast<T>(
                static_cast<double>(data[t * n_channels + c]) - (slope * z + intercept));
        }
    }
    return result;
}

/**
 * @brief Configuração para correção de atenuação double-ended.
 *
 * Extension point documentado (CL-07): a correção double-ended completa
 * requer dados reais dos dois extremos da fibra (configuração loop), com
 * Stokes/anti-Stokes medidos em ambas as direções. Sem esses dados, a
 * função `correct_attenuation_double_ended` valida a configuração e levanta
 * std::invalid_argument — decisão de escopo da auditoria técnica.
 *
 * Documented extension point: full double-ended correction needs real
 * two-ended fiber data; without it the function throws by design.
 */
struct DoubleEndedConfig {
    std::size_t switch_index = 0;  ///< Índice do canal onde o loop inverte
    double step_m = 1.0;           ///< Passo entre canais em metros
    bool reference_channel_set = false;  ///< Zona de referência configurada
};

/**
 * @brief Placeholder validado para correção double-ended (experimental).
 *
 * @throws std::invalid_argument Sempre, com mensagem explicativa, após
 *         validar os parâmetros da configuração.
 */
template <FloatingPoint T>
std::vector<T> correct_attenuation_double_ended(
    std::span<const T> data,
    std::size_t n_times,
    std::size_t n_channels,
    const DoubleEndedConfig& config) {
    if (config.step_m <= 0.0) {
        throw std::invalid_argument(
            "correct_attenuation_double_ended: step_m must be positive");
    }
    if (data.size() != n_times * n_channels || n_times == 0 || n_channels == 0) {
        throw std::invalid_argument(
            "correct_attenuation_double_ended: data size does not match shape");
    }
    if (config.switch_index >= n_channels) {
        throw std::invalid_argument(
            "correct_attenuation_double_ended: switch_index out of range");
    }
    throw std::invalid_argument(
        "double-ended attenuation correction is experimental and not "
        "implemented: it requires real two-ended Stokes/anti-Stokes data "
        "(see DoubleEndedConfig). Use attenuation_correct_single_ended as a "
        "documented simplification anchored on a reference zone.");
}

} // namespace alakoro::thermal
