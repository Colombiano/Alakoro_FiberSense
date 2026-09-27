/**
 * @file wavelet.hpp
 * @brief Transformada Wavelet Contínua (CWT) em C++20.
 *
 * Implementa CWT com wavelets Morlet e Ricker para análise tempo-frequência
 * de sinais DAS. Usa templates e std::span para flexibilidade.
 *
 * Recursos C++20:
 *   - concepts (FloatingPoint)
 *   - if constexpr para seleção de wavelet
 *   - std::span views
 */

#pragma once

#include "alakoro/concepts.hpp"

#include <cmath>
#include <complex>
#include <cstddef>
#include <numbers>
#include <span>
#include <stdexcept>
#include <vector>

namespace alakoro::wavelet {

/**
 * @brief Tipos de wavelet suportadas.
 */
enum class WaveletType {
    Morlet,
    Ricker
};

/**
 * @brief Gera wavelet Morlet complexa para uma escala.
 *
 * A wavelet Morlet é um cosseno Gaussian-windowed, adequado para
 * análise de sinais sísmicos e acústicos.
 */
template <FloatingPoint T>
std::vector<std::complex<T>> morlet_wavelet(std::size_t n_samples, double scale,
                                            double sample_rate_hz,
                                            double central_frequency = 6.0) {
    std::vector<std::complex<T>> wavelet(n_samples);
    const T dt = static_cast<T>(1.0 / sample_rate_hz);
    const T sigma = static_cast<T>(scale) / (std::numbers::pi * 2.0 * central_frequency);
    const T t0 = static_cast<T>(n_samples) / 2.0 * dt;

    for (std::size_t i = 0; i < n_samples; ++i) {
        T t = static_cast<T>(i) * dt - t0;
        T envelope = std::exp(-(t * t) / (2.0 * sigma * sigma));
        T osc = std::numbers::pi * 2.0 * central_frequency * t / static_cast<T>(scale);
        wavelet[i] = std::complex<T>(
            envelope * std::cos(osc),
            envelope * std::sin(osc)
        );
    }

    // Normalização L2
    T norm = 0.0;
    for (const auto& v : wavelet) {
        norm += std::norm(v);
    }
    norm = std::sqrt(norm) + 1e-12;
    for (auto& v : wavelet) {
        v /= norm;
    }

    return wavelet;
}

/**
 * @brief Gera wavelet Ricker (Mexican Hat) para uma escala.
 *
 * A Ricker é a segunda derivada de uma Gaussiana, útil para detectar
 * picos e transientes.
 */
template <FloatingPoint T>
std::vector<T> ricker_wavelet(std::size_t n_samples, double scale, double sample_rate_hz) {
    std::vector<T> wavelet(n_samples);
    const T dt = static_cast<T>(1.0 / sample_rate_hz);
    const T sigma2 = static_cast<T>(scale * scale);
    const T t0 = static_cast<T>(n_samples) / 2.0 * dt;

    for (std::size_t i = 0; i < n_samples; ++i) {
        T t = static_cast<T>(i) * dt - t0;
        T t2 = t * t;
        T envelope = std::exp(-t2 / (2.0 * sigma2));
        wavelet[i] = (1.0 - t2 / sigma2) * envelope;
    }

    // Normalização L2
    T norm = 0.0;
    for (const auto& v : wavelet) {
        norm += v * v;
    }
    norm = std::sqrt(norm) + 1e-12;
    for (auto& v : wavelet) {
        v /= norm;
    }

    return wavelet;
}

/**
 * @brief Convolução 1D circular simples.
 */
template <FloatingPoint T>
std::vector<T> convolve(const std::vector<T>& signal,
                        const std::vector<T>& kernel) {
    std::vector<T> out(signal.size(), T{});
    const std::size_t n = signal.size();
    const std::size_t m = kernel.size();
    const std::size_t half_m = m / 2;

    for (std::size_t i = 0; i < n; ++i) {
        T sum = 0.0;
        for (std::size_t j = 0; j < m; ++j) {
            std::size_t idx = (i + j + n - half_m) % n;
            sum += signal[idx] * kernel[j];
        }
        out[i] = sum;
    }
    return out;
}

/**
 * @brief Convolução 1D circular com kernel complexo.
 */
template <FloatingPoint T>
std::vector<T> convolve_complex(const std::vector<T>& signal,
                                const std::vector<std::complex<T>>& kernel) {
    std::vector<T> out(signal.size(), T{});
    const std::size_t n = signal.size();
    const std::size_t m = kernel.size();
    const std::size_t half_m = m / 2;

    for (std::size_t i = 0; i < n; ++i) {
        std::complex<T> sum{};
        for (std::size_t j = 0; j < m; ++j) {
            std::size_t idx = (i + j + n - half_m) % n;
            sum += std::complex<T>(signal[idx]) * kernel[j];
        }
        out[i] = std::abs(sum);
    }
    return out;
}

/**
 * @brief CWT 1D para um canal temporal.
 *
 * @tparam T Tipo de ponto flutuante
 * @param signal Sinal 1D
 * @param scales Vetor de escalas
 * @param sample_rate_hz Taxa de amostragem
 * @param type Tipo de wavelet
 * @return Matriz (n_scales, n_samples) com coeficientes
 */
template <FloatingPoint T>
std::vector<std::vector<T>> cwt(const std::vector<T>& signal,
                                const std::vector<double>& scales,
                                double sample_rate_hz,
                                WaveletType type = WaveletType::Morlet) {
    std::vector<std::vector<T>> coefficients;
    coefficients.reserve(scales.size());

    for (double scale : scales) {
        std::vector<T> coef;
        if (type == WaveletType::Morlet) {
            auto wavelet = morlet_wavelet<T>(signal.size(), scale, sample_rate_hz);
            coef = convolve_complex(signal, wavelet);
        } else {
            auto wavelet = ricker_wavelet<T>(signal.size(), scale, sample_rate_hz);
            coef = convolve(signal, wavelet);
        }
        coefficients.push_back(std::move(coef));
    }

    return coefficients;
}

/**
 * @brief CWT para cada canal de dados 2D (time, channels).
 *
 * Retorna vetor flat: [channel][scale][time]
 */
template <FloatingPoint T>
std::vector<std::vector<std::vector<T>>> cwt_2d(std::span<const T> data,
                                                  std::size_t n_times,
                                                  std::size_t n_channels,
                                                  const std::vector<double>& scales,
                                                  double sample_rate_hz,
                                                  WaveletType type = WaveletType::Morlet) {
    std::vector<std::vector<std::vector<T>>> result;
    result.reserve(n_channels);

    for (std::size_t c = 0; c < n_channels; ++c) {
        std::vector<T> signal(n_times);
        for (std::size_t t = 0; t < n_times; ++t) {
            signal[t] = data[t * n_channels + c];
        }
        result.push_back(cwt(signal, scales, sample_rate_hz, type));
    }

    return result;
}

} // namespace alakoro::wavelet
