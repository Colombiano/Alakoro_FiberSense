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

} // namespace alakoro::thermal
