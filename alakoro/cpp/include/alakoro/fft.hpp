/**
 * @file fft.hpp
 * @brief Transformada Rápida de Fourier (FFT) em C++20.
 *
 * Implementação iterativa do algoritmo Cooley-Tukey para tamanhos
 * potência de 2. Usa std::complex e concepts para tipos numéricos.
 *
 * Recursos C++20:
 *   - concepts (NumericScalar)
 *   - std::complex<T>
 *   - if constexpr para casos base
 *   - constexpr constantes twiddle
 */

#pragma once

#include "alakoro/concepts.hpp"

#include <bit>
#include <cmath>
#include <complex>
#include <cstddef>
#include <numbers>
#include <span>
#include <stdexcept>
#include <vector>

namespace alakoro::fft {

/**
 * @brief Verifica se n é potência de 2.
 */
constexpr bool is_power_of_two(std::size_t n) noexcept {
    return n > 0 && (n & (n - 1)) == 0;
}

/**
 * @brief Reordena um vetor na ordem bit-reversa.
 *
 * Necessária para a FFT iterativa in-place.
 */
template <typename T>
void bit_reverse_reorder(std::vector<std::complex<T>>& x) {
    const std::size_t n = x.size();
    const int log_n = std::countr_zero(n);

    for (std::size_t i = 0; i < n; ++i) {
        std::size_t j = 0;
        for (int bit = 0; bit < log_n; ++bit) {
            j |= ((i >> bit) & 1) << (log_n - 1 - bit);
        }
        if (j > i) {
            std::swap(x[i], x[j]);
        }
    }
}

/**
 * @brief FFT in-place (Cooley-Tukey iterativo).
 *
 * @tparam T Tipo de ponto flutuante
 * @param x Vetor complexo de tamanho potência de 2
 * @param inverse Se true, calcula IFFT
 */
template <FloatingPoint T>
void fft(std::vector<std::complex<T>>& x, bool inverse = false) {
    const std::size_t n = x.size();
    if (!is_power_of_two(n)) {
        throw std::invalid_argument("FFT size must be a power of 2");
    }
    if (n <= 1) return;

    bit_reverse_reorder(x);

    const int log_n = std::countr_zero(n);
    const T sign = inverse ? 1.0 : -1.0;

    for (int s = 1; s <= log_n; ++s) {
        const std::size_t m = static_cast<std::size_t>(1) << s;
        const T angle = sign * 2.0 * std::numbers::pi / static_cast<T>(m);
        const std::complex<T> wm(std::cos(angle), std::sin(angle));

        for (std::size_t k = 0; k < n; k += m) {
            std::complex<T> w(1.0, 0.0);
            for (std::size_t j = 0; j < m / 2; ++j) {
                const std::complex<T> t = w * x[k + j + m / 2];
                const std::complex<T> u = x[k + j];
                x[k + j] = u + t;
                x[k + j + m / 2] = u - t;
                w *= wm;
            }
        }
    }

    if (inverse) {
        for (auto& v : x) {
            v /= static_cast<T>(n);
        }
    }
}

/**
 * @brief Calcula a magnitude do espectro de cada canal (2D).
 *
 * Entrada: dados 2D (time, channels) contíguos.
 * Saída: magnitude do espectro (n/2+1, channels) para cada canal.
 */
template <FloatingPoint T>
std::vector<T> magnitude_spectrum(std::span<const T> data,
                                   std::size_t n_times,
                                   std::size_t n_channels) {
    std::vector<T> result;
    result.reserve((n_times / 2 + 1) * n_channels);

    for (std::size_t c = 0; c < n_channels; ++c) {
        std::size_t n = n_times;
        if (!is_power_of_two(n)) {
            // Encontra próxima potência de 2
            n = static_cast<std::size_t>(1) << (std::bit_width(n - 1) + 1);
        }

        std::vector<std::complex<T>> x(n);
        for (std::size_t t = 0; t < n_times; ++t) {
            x[t] = std::complex<T>(data[t * n_channels + c], T{});
        }
        for (std::size_t t = n_times; t < n; ++t) {
            x[t] = std::complex<T>(T{}, T{});
        }

        fft(x, false);

        for (std::size_t k = 0; k <= n / 2; ++k) {
            result.push_back(std::abs(x[k]));
        }
    }

    return result;
}

/**
 * @brief Calcula densidade espectral de potência (PSD) via periodograma.
 */
template <FloatingPoint T>
std::vector<T> psd(std::span<const T> data,
                   std::size_t n_times,
                   std::size_t n_channels,
                   double sample_rate_hz) {
    auto spectrum = magnitude_spectrum<T>(data, n_times, n_channels);
    const std::size_t n_freq = n_times / 2 + 1;
    const T scale = static_cast<T>(2.0 / (n_times * sample_rate_hz));

    for (auto& v : spectrum) {
        v = v * v * scale;
    }
    return spectrum;
}

} // namespace alakoro::fft
