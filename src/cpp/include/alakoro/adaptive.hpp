/**
 * @file adaptive.hpp
 * @brief Filtros adaptativos e compensação de hardware para DAS/DTS/DSS.
 *
 * Recursos C++20:
 *   - concepts (FloatingPoint)
 *   - std::span views
 *   - templates para precisão float/double
 */

#pragma once

#include "alakoro/concepts.hpp"

#include <cmath>
#include <cstddef>
#include <limits>
#include <span>
#include <stdexcept>
#include <vector>

namespace alakoro::adaptive {

/**
 * @brief Compensação aproximada de gauge length.
 *
 * O gauge length do interrogador age como uma média móvel espacial, suavizando
 * variações rápidas ao longo do poço. Esta função aplica uma deconvolução
 * espacial simples (filtro inverso regularizado) para recuperar resolução.
 *
 * A resposta do gauge length é aproximada por uma média móvel uniforme de
 * comprimento L = gauge_length_m / channel_spacing_m canais. O filtro inverso
 * é regularizado para evitar amplificação excessiva de ruído de alta frequência.
 *
 * @tparam T Tipo de ponto flutuante
 * @param data Dados 2D contíguos (n_times x n_channels)
 * @param n_times Número de amostras temporais
 * @param n_channels Número de canais
 * @param gauge_length_m Comprimento gauge do interrogador (m)
 * @param channel_spacing_m Espaçamento entre canais (m)
 * @param regularization Fator de regularização (padrão: 0.1)
 * @return Dados compensados
 */
template <FloatingPoint T>
std::vector<T> gauge_length_compensation(std::span<const T> data,
                                         std::size_t n_times,
                                         std::size_t n_channels,
                                         double gauge_length_m,
                                         double channel_spacing_m,
                                         double regularization = 0.1) {
    if (n_channels < 3) {
        throw std::invalid_argument("n_channels deve ser >= 3");
    }
    if (channel_spacing_m <= 0.0) {
        throw std::invalid_argument("channel_spacing_m deve ser positivo");
    }

    // Número de canais cobertos pelo gauge length
    std::size_t L = static_cast<std::size_t>(std::max(1.0, std::round(gauge_length_m / channel_spacing_m)));
    if (L > n_channels) L = n_channels;
    if (L % 2 == 0) L += 1;  // garante ímpar

    std::vector<T> result(n_times * n_channels);

    for (std::size_t t = 0; t < n_times; ++t) {
        for (std::size_t c = 0; c < n_channels; ++c) {
            // Média móvel local (efeito do gauge)
            std::size_t half = L / 2;
            std::size_t start = (c < half) ? 0 : (c - half);
            std::size_t end = std::min(c + half + 1, n_channels);

            T local_mean = T{};
            for (std::size_t cc = start; cc < end; ++cc) {
                local_mean += data[t * n_channels + cc];
            }
            local_mean /= static_cast<T>(end - start);

            // Filtro inverso regularizado: valor compensado = valor + lambda * (valor - média local)
            T value = data[t * n_channels + c];
            T compensated = value + static_cast<T>(regularization) * (value - local_mean);
            result[t * n_channels + c] = compensated;
        }
    }

    return result;
}

/**
 * @brief Filtro adaptativo LMS (Least Mean Squares).
 *
 * Cancela interferência presente em um sinal de referência usando o algoritmo
 * LMS de Widrow-Hoff. Útil para remover ruído periódico conhecido (bombas,
 * compressores, etc.) de canais DAS.
 *
 * @tparam T Tipo de ponto flutuante
 * @param primary Sinal primário (com ruído desejado)
 * @param reference Sinal de referência (ruído correlacionado)
 * @param mu Passo de adaptação
 * @param filter_order Ordem do filtro adaptativo
 * @return Par {sinal_filtrado, erro}
 */
template <FloatingPoint T>
std::pair<std::vector<T>, std::vector<T>> lms_filter(std::span<const T> primary,
                                                      std::span<const T> reference,
                                                      double mu,
                                                      std::size_t filter_order) {
    if (primary.size() != reference.size()) {
        throw std::invalid_argument("primary e reference devem ter o mesmo tamanho");
    }
    if (filter_order == 0 || filter_order > primary.size()) {
        throw std::invalid_argument("filter_order inválido");
    }

    const std::size_t n = primary.size();
    std::vector<T> weights(filter_order, T{});
    std::vector<T> filtered(n, T{});
    std::vector<T> error(n, T{});

    for (std::size_t i = filter_order; i < n; ++i) {
        // Vetor de entrada de referência (atrasos)
        std::vector<T> x(filter_order);
        for (std::size_t j = 0; j < filter_order; ++j) {
            x[j] = reference[i - j];
        }

        // Saída do filtro
        T y = T{};
        for (std::size_t j = 0; j < filter_order; ++j) {
            y += weights[j] * x[j];
        }

        T e = primary[i] - y;
        filtered[i] = y;
        error[i] = e;

        // Atualização LMS
        for (std::size_t j = 0; j < filter_order; ++j) {
            weights[j] += static_cast<T>(mu) * e * x[j];
        }
    }

    return {filtered, error};
}

/**
 * @brief Filtro adaptativo RLS (Recursive Least Squares).
 *
 * Versão recursiva de mínimos quadrados com matriz de correlação inversa.
 * Converge mais rápido que LMS mas com maior custo computacional.
 *
 * @tparam T Tipo de ponto flutuante
 * @param primary Sinal primário
 * @param reference Sinal de referência
 * @param lambda_ Fator de esquecimento (0 < lambda <= 1)
 * @param delta Valor inicial da diagonal da matriz P
 * @param filter_order Ordem do filtro
 * @return Par {sinal_filtrado, erro}
 */
template <FloatingPoint T>
std::pair<std::vector<T>, std::vector<T>> rls_filter(std::span<const T> primary,
                                                      std::span<const T> reference,
                                                      double lambda_,
                                                      double delta,
                                                      std::size_t filter_order) {
    if (primary.size() != reference.size()) {
        throw std::invalid_argument("primary e reference devem ter o mesmo tamanho");
    }
    if (filter_order == 0 || filter_order > primary.size()) {
        throw std::invalid_argument("filter_order inválido");
    }
    if (lambda_ <= 0.0 || lambda_ > 1.0) {
        throw std::invalid_argument("lambda deve estar em (0, 1]");
    }

    const std::size_t n = primary.size();
    std::vector<T> weights(filter_order, T{});
    std::vector<T> filtered(n, T{});
    std::vector<T> error(n, T{});

    // Matriz de correlação inversa P = delta * I
    std::vector<T> P(filter_order * filter_order, T{});
    for (std::size_t i = 0; i < filter_order; ++i) {
        P[i * filter_order + i] = static_cast<T>(1.0 / delta);
    }

    for (std::size_t i = filter_order; i < n; ++i) {
        std::vector<T> x(filter_order);
        for (std::size_t j = 0; j < filter_order; ++j) {
            x[j] = reference[i - j];
        }

        // g = P * x / (lambda + x^T * P * x)
        std::vector<T> Px(filter_order);
        for (std::size_t j = 0; j < filter_order; ++j) {
            T sum = T{};
            for (std::size_t k = 0; k < filter_order; ++k) {
                sum += P[j * filter_order + k] * x[k];
            }
            Px[j] = sum;
        }

        T xTPx = T{};
        for (std::size_t j = 0; j < filter_order; ++j) {
            xTPx += x[j] * Px[j];
        }
        T denom = static_cast<T>(lambda_) + xTPx;

        std::vector<T> g(filter_order);
        for (std::size_t j = 0; j < filter_order; ++j) {
            g[j] = Px[j] / denom;
        }

        // y = w^T * x
        T y = T{};
        for (std::size_t j = 0; j < filter_order; ++j) {
            y += weights[j] * x[j];
        }

        T e = primary[i] - y;
        filtered[i] = y;
        error[i] = e;

        // Atualização dos pesos
        for (std::size_t j = 0; j < filter_order; ++j) {
            weights[j] += g[j] * e;
        }

        // Atualização de P: P = (P - g * x^T * P) / lambda
        std::vector<T> gxT_P(filter_order * filter_order, T{});
        for (std::size_t j = 0; j < filter_order; ++j) {
            for (std::size_t k = 0; k < filter_order; ++k) {
                gxT_P[j * filter_order + k] = g[j] * Px[k];
            }
        }

        for (std::size_t j = 0; j < filter_order; ++j) {
            for (std::size_t k = 0; k < filter_order; ++k) {
                P[j * filter_order + k] = (P[j * filter_order + k] - gxT_P[j * filter_order + k]) / static_cast<T>(lambda_);
            }
        }
    }

    return {filtered, error};
}

/**
 * @brief Aplica LMS canal-a-canal em dados 2D.
 *
 * Usa o canal vizinho à direita como referência para cada canal.
 */
template <FloatingPoint T>
std::vector<T> lms_filter_2d(std::span<const T> data,
                             std::size_t n_times,
                             std::size_t n_channels,
                             double mu,
                             std::size_t filter_order) {
    std::vector<T> result(n_times * n_channels);

    for (std::size_t c = 0; c < n_channels; ++c) {
        std::size_t ref_c = (c + 1) % n_channels;
        std::vector<T> primary(n_times), reference(n_times);
        for (std::size_t t = 0; t < n_times; ++t) {
            primary[t] = data[t * n_channels + c];
            reference[t] = data[t * n_channels + ref_c];
        }

        auto [filtered, error] = lms_filter(
            std::span<const T>(primary),
            std::span<const T>(reference),
            mu, filter_order);

        for (std::size_t t = 0; t < n_times; ++t) {
            result[t * n_channels + c] = error[t];
        }
    }

    return result;
}

/**
 * @brief Aplica RLS canal-a-canal em dados 2D.
 */
template <FloatingPoint T>
std::vector<T> rls_filter_2d(std::span<const T> data,
                             std::size_t n_times,
                             std::size_t n_channels,
                             double lambda_,
                             double delta,
                             std::size_t filter_order) {
    std::vector<T> result(n_times * n_channels);

    for (std::size_t c = 0; c < n_channels; ++c) {
        std::size_t ref_c = (c + 1) % n_channels;
        std::vector<T> primary(n_times), reference(n_times);
        for (std::size_t t = 0; t < n_times; ++t) {
            primary[t] = data[t * n_channels + c];
            reference[t] = data[t * n_channels + ref_c];
        }

        auto [filtered, error] = rls_filter(
            std::span<const T>(primary),
            std::span<const T>(reference),
            lambda_, delta, filter_order);

        for (std::size_t t = 0; t < n_times; ++t) {
            result[t * n_channels + c] = error[t];
        }
    }

    return result;
}

} // namespace alakoro::adaptive
