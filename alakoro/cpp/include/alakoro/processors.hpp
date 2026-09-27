/**
 * @file processors.hpp
 * @brief Processadores de sinal C++20 para dados de sensing.
 *
 * Implementações genéricas usando templates, concepts e if constexpr.
 * O objetivo é compilar código especializado para float/double e para
 * cada modalidade, aproveitando otimizações do compilador.
 *
 * Processadores implementados:
 *   - detrend (linear e constante)
 *   - taper (cosine/window)
 *   - decimate (downsampling com filtro passa-baixa Butterworth simples)
 *   - pass_filter (passa-baixa / passa-alta de primeira ordem)
 */

#pragma once

#include "alakoro/concepts.hpp"
#include "alakoro/core.hpp"

#include <algorithm>
#include <cmath>
#include <concepts>
#include <cstddef>
#include <numbers>
#include <span>
#include <stdexcept>
#include <vector>

namespace alakoro {

namespace detail {

/**
 * @brief Aplica uma operação em cada canal (coluna) dos dados.
 *
 * Usamos um functor genérico para evitar duplicação de loops aninhados.
 * O functor recebe um std::span<T> representando uma coluna temporal.
 */
template <NumericScalar T, typename F>
void apply_per_channel(std::span<T> data,
                       std::size_t n_times,
                       std::size_t n_channels,
                       F&& fn) {
    for (std::size_t c = 0; c < n_channels; ++c) {
        // Cria um vetor temporário com a coluna c (time-series do canal)
        std::vector<T> column(n_times);
        for (std::size_t t = 0; t < n_times; ++t) {
            column[t] = data[t * n_channels + c];
        }

        fn(std::span<T>(column));

        for (std::size_t t = 0; t < n_times; ++t) {
            data[t * n_channels + c] = column[t];
        }
    }
}

} // namespace detail

/**
 * @brief Remove a tendência linear de cada canal.
 *
 * Ajusta uma reta y = a*x + b por mínimos quadrados e subtrai.
 * Usa if constexpr para escolher entre precisão dupla no cálculo
 * interno mesmo quando T é float.
 */
template <NumericScalar T>
void detrend(std::span<T> data, std::size_t n_times, std::size_t n_channels) {
    using ComputeT = std::conditional_t<std::is_same_v<T, float>, double, T>;

    detail::apply_per_channel<T>(data, n_times, n_channels,
        [&](std::span<T> column) {
            const std::size_t n = column.size();
            if (n < 2) return;

            ComputeT sum_x = 0;
            ComputeT sum_y = 0;
            ComputeT sum_xx = 0;
            ComputeT sum_xy = 0;

            for (std::size_t i = 0; i < n; ++i) {
                const ComputeT x = static_cast<ComputeT>(i);
                const ComputeT y = static_cast<ComputeT>(column[i]);
                sum_x += x;
                sum_y += y;
                sum_xx += x * x;
                sum_xy += x * y;
            }

            const ComputeT denom = static_cast<ComputeT>(n) * sum_xx - sum_x * sum_x;
            if (std::abs(denom) < 1e-12) return;

            const ComputeT slope =
                (static_cast<ComputeT>(n) * sum_xy - sum_x * sum_y) / denom;
            const ComputeT intercept =
                (sum_y - slope * sum_x) / static_cast<ComputeT>(n);

            for (std::size_t i = 0; i < n; ++i) {
                const ComputeT trend = slope * static_cast<ComputeT>(i) + intercept;
                column[i] = static_cast<T>(static_cast<ComputeT>(column[i]) - trend);
            }
        });
}

/**
 * @brief Subtrai a média de cada canal (detrend constante).
 */
template <NumericScalar T>
void demean(std::span<T> data, std::size_t n_times, std::size_t n_channels) {
    detail::apply_per_channel<T>(data, n_times, n_channels,
        [&](std::span<T> column) {
            T sum{};
            for (const auto& v : column) sum += v;
            const T mean = sum / static_cast<T>(column.size());
            for (auto& v : column) v -= mean;
        });
}

/**
 * @brief Aplica um taper de cosseno em cada canal.
 *
 * alpha=0.0 => janela Hanning (cosseno levantado simétrico)
 * alpha=1.0 => retangular (sem taper)
 */
template <NumericScalar T>
void taper(std::span<T> data,
           std::size_t n_times,
           std::size_t n_channels,
           double alpha = 0.0) {
    if (alpha < 0.0 || alpha > 1.0) {
        throw std::invalid_argument("taper: alpha must be in [0, 1]");
    }

    detail::apply_per_channel<T>(data, n_times, n_channels,
        [&](std::span<T> column) {
            const std::size_t n = column.size();
            if (n < 2) return;

            for (std::size_t i = 0; i < n; ++i) {
                // Normaliza índice para [-1, 1]
                const double x = 2.0 * static_cast<double>(i) / static_cast<double>(n - 1) - 1.0;
                // Cosseno levantado simétrico
                const double window = alpha + (1.0 - alpha) * std::cos(std::numbers::pi * x / 2.0);
                column[i] = static_cast<T>(static_cast<double>(column[i]) * window);
            }
        });
}

/**
 * @brief Passa-baixa de primeira ordem (filtro exponencial/IIR).
 *
 * Útil para decimação rápida antes de downsampling. O parâmetro cutoff
 * é a fração da frequência de Nyquist (0 < cutoff < 1).
 */
template <NumericScalar T>
void lowpass_iir(std::span<T> data,
                 std::size_t n_times,
                 std::size_t n_channels,
                 double cutoff_nyquist) {
    if (cutoff_nyquist <= 0.0 || cutoff_nyquist >= 1.0) {
        throw std::invalid_argument("lowpass_iir: cutoff must be in (0, 1)");
    }

    // Constante de tempo do filtro exponencial
    const double rc = 1.0 / (2.0 * std::numbers::pi * cutoff_nyquist);
    const double dt = 1.0;
    const double alpha = dt / (rc + dt);

    detail::apply_per_channel<T>(data, n_times, n_channels,
        [&](std::span<T> column) {
            if (column.empty()) return;
            double y = static_cast<double>(column[0]);
            column[0] = static_cast<T>(y);
            for (std::size_t i = 1; i < column.size(); ++i) {
                const double x = static_cast<double>(column[i]);
                y += alpha * (x - y);
                column[i] = static_cast<T>(y);
            }
        });
}

/**
 * @brief Decima dados ao longo do tempo.
 *
 * Aplica um passa-baixa simples para evitar aliasing e depois pega
 * 1 a cada `factor` amostras. Retorna um novo vetor com shape reduzido.
 */
template <NumericScalar T>
std::vector<T> decimate(std::span<const T> data,
                        std::size_t n_times,
                        std::size_t n_channels,
                        std::size_t factor) {
    if (factor == 0) throw std::invalid_argument("decimate: factor must be > 0");
    if (factor == 1) return std::vector<T>(data.begin(), data.end());

    // Copia para buffer mutável, aplica filtro anti-aliasing
    std::vector<T> filtered(data.begin(), data.end());
    // cutoff aproximado para preservar banda até Nyquist/factor
    const double cutoff = 1.0 / static_cast<double>(2 * factor);
    lowpass_iir<T>(std::span<T>(filtered), n_times, n_channels, cutoff);

    const std::size_t n_out = (n_times + factor - 1) / factor;
    std::vector<T> out;
    out.reserve(n_out * n_channels);

    for (std::size_t t = 0; t < n_out; ++t) {
        const std::size_t t_in = t * factor;
        if (t_in >= n_times) break;
        for (std::size_t c = 0; c < n_channels; ++c) {
            out.push_back(filtered[t_in * n_channels + c]);
        }
    }

    return out;
}

/**
 * @brief Processador genérico que opera sobre qualquer SensingData.
 *
 * Demonstração de como usar o concept AnySensingData para escrever
 * algoritmos que funcionam para DAS, DTS e DSS sem duplicação.
 */
template <AnySensingData DataT>
void detrend(DataT& data) {
    using T = typename DataT::value_type;
    auto span = data.data();
    detrend<T>(span, data.n_times(), data.n_channels());
}

template <AnySensingData DataT>
void demean(DataT& data) {
    using T = typename DataT::value_type;
    auto span = data.data();
    demean<T>(span, data.n_times(), data.n_channels());
}

template <AnySensingData DataT>
void taper(DataT& data, double alpha = 0.0) {
    using T = typename DataT::value_type;
    auto span = data.data();
    taper<T>(span, data.n_times(), data.n_channels(), alpha);
}

} // namespace alakoro
