/**
 * @file event_detection.hpp
 * @brief Detectores de eventos e operadores de energia em C++20.
 *
 * Fornece ferramentas clássicas de processamento sísmico aplicadas a dados
 * DAS/DTS/DSS:
 *   - STA/LTA: detector de chegada de eventos
 *   - Hilbert envelope: envoltória de amplitude do sinal analítico
 *   - Teager-Kaiser Energy Operator (TKEO): realce de transientes
 *
 * Recursos C++20:
 *   - concepts (FloatingPoint)
 *   - templates não-tipo para janelas conhecidas em compile-time
 *   - if constexpr para especialização
 *   - std::span views
 */

#pragma once

#include "alakoro/concepts.hpp"
#include "alakoro/fft.hpp"

#include <algorithm>
#include <cmath>
#include <complex>
#include <cstddef>
#include <numbers>
#include <span>
#include <stdexcept>
#include <vector>

namespace alakoro::event_detection {

/**
 * @brief Calcula a razão STA/LTA (Short-Term / Long-Term Average).
 *
 * A razão STA/LTA é um detector clássico de chegada de eventos. Quando a
 * energia de curto prazo ultrapassa significativamente a de longo prazo,
 * indica o início de um evento (microsísmico, chatter de válvula, etc.).
 *
 * @tparam T Tipo de ponto flutuante
 * @param signal Sinal 1D
 * @param n_sta Número de amostras da janela curta (STA)
 * @param n_lta Número de amostras da janela longa (LTA)
 * @return Vetor com razão STA/LTA (mesmo tamanho do sinal)
 */
template <FloatingPoint T>
std::vector<T> sta_lta(std::span<const T> signal,
                       std::size_t n_sta,
                       std::size_t n_lta) {
    if (n_sta == 0 || n_lta == 0) {
        throw std::invalid_argument("STA e LTA devem ser maiores que zero");
    }
    if (n_sta >= n_lta) {
        throw std::invalid_argument("STA deve ser menor que LTA");
    }
    if (signal.size() < n_lta + n_sta) {
        throw std::invalid_argument("Sinal muito curto para janelas STA/LTA escolhidas");
    }

    const std::size_t n = signal.size();
    std::vector<T> ratio(n, T{});

    // Energia do sinal ao quadrado
    std::vector<T> energy(n);
    for (std::size_t i = 0; i < n; ++i) {
        energy[i] = signal[i] * signal[i];
    }

    // Média móvel simples (soma acumulada para O(n))
    std::vector<T> cumsum(n + 1, T{});
    for (std::size_t i = 0; i < n; ++i) {
        cumsum[i + 1] = cumsum[i] + energy[i];
    }

    auto window_sum = [&](std::size_t start, std::size_t len) -> T {
        if (start + len > n) return T{};
        return cumsum[start + len] - cumsum[start];
    };

    // A LTA precede a STA: evita que o próprio evento contamine a baseline
    for (std::size_t i = n_lta; i + n_sta <= n; ++i) {
        T sta = window_sum(i, n_sta) / static_cast<T>(n_sta);
        T lta = window_sum(i - n_lta, n_lta) / static_cast<T>(n_lta);
        // Evita divisão por zero
        ratio[i] = (lta > 1e-24) ? (sta / lta) : T{};
    }

    return ratio;
}

/**
 * @brief Calcula a envoltória de Hilbert de um sinal 1D.
 *
 * A transformada de Hilbert produz o sinal analítico z(t) = x(t) + i*H[x(t)].
 * O módulo |z(t)| é a envoltória de amplitude, útil para detectar pacotes
 * de energia em sinais oscilatórios (chatter, vibração, etc.).
 *
 * Implementação via FFT: calcula FFT, zera frequências negativas, dobra as
 * positivas e faz IFFT.
 *
 * @tparam T Tipo de ponto flutuante
 * @param signal Sinal 1D
 * @return Vetor com a envoltória de Hilbert
 */
template <FloatingPoint T>
std::vector<T> hilbert_envelope(std::span<const T> signal) {
    const std::size_t n = signal.size();
    if (n == 0) return {};
    if (n == 1) return { std::abs(signal[0]) };

    // Prepara vetor complexo para FFT (próxima potência de 2)
    std::size_t n_fft = n;
    if (!fft::is_power_of_two(n_fft)) {
        n_fft = static_cast<std::size_t>(1) << (std::bit_width(n_fft - 1) + 1);
    }

    std::vector<std::complex<T>> x(n_fft);
    for (std::size_t i = 0; i < n; ++i) {
        x[i] = std::complex<T>(signal[i], T{});
    }
    for (std::size_t i = n; i < n_fft; ++i) {
        x[i] = std::complex<T>(T{}, T{});
    }

    fft::fft(x, false);

    // Constrói sinal analítico no domínio da frequência
    // DC e Nyquist (quando presente) permanecem; demais positivas dobram;
    // negativas vão para zero.
    x[0] *= T{2.0};
    const std::size_t half = n_fft / 2;
    if (fft::is_power_of_two(n_fft)) {
        // Nyquist em n_fft/2 permanece inalterado
        for (std::size_t i = half + 1; i < n_fft; ++i) {
            x[i] = std::complex<T>(T{}, T{});
        }
    }

    fft::fft(x, true);

    std::vector<T> envelope(n);
    for (std::size_t i = 0; i < n; ++i) {
        // O sinal analítico tem o dobro da amplitude original; normalizamos
        envelope[i] = std::abs(x[i]) / T{2.0};
    }

    return envelope;
}

/**
 * @brief Calcula o Teager-Kaiser Energy Operator (TKEO).
 *
 * O TKEO estima a energia instantânea de um sinal semelhante a um oscilador
 * amortecido. Picos no TKEO indicam mudanças rápidas de amplitude e frequência,
 * sendo úteis para detectar transientes em dados DAS.
 *
 * Fórmula: y[n] = x[n]^2 - x[n-1] * x[n+1]
 *
 * @tparam T Tipo de ponto flutuante
 * @param signal Sinal 1D
 * @return Vetor com energia TKEO (mesmo tamanho do sinal; bordas = 0)
 */
template <FloatingPoint T>
std::vector<T> teager_kaiser(std::span<const T> signal) {
    const std::size_t n = signal.size();
    std::vector<T> energy(n, T{});

    if (n < 3) return energy;

    for (std::size_t i = 1; i + 1 < n; ++i) {
        energy[i] = signal[i] * signal[i] - signal[i - 1] * signal[i + 1];
    }

    return energy;
}

/**
 * @brief Calcula STA/LTA para cada canal de dados 2D (time, channels).
 *
 * Layout de entrada: [t * n_channels + c]
 * Retorno flat: [freq_sample * n_channels + c], onde freq_sample = n_times - n_lta - n_sta + 1
 * (mantemos apenas as amostras válidas).
 */
template <FloatingPoint T>
std::vector<T> sta_lta_2d(std::span<const T> data,
                          std::size_t n_times,
                          std::size_t n_channels,
                          std::size_t n_sta,
                          std::size_t n_lta) {
    if (n_times < n_lta + n_sta) {
        throw std::invalid_argument("n_times muito pequeno para janelas STA/LTA");
    }

    const std::size_t n_valid = n_times - n_lta - n_sta + 1;
    std::vector<T> result(n_valid * n_channels);

    for (std::size_t c = 0; c < n_channels; ++c) {
        std::vector<T> signal(n_times);
        for (std::size_t t = 0; t < n_times; ++t) {
            signal[t] = data[t * n_channels + c];
        }
        auto ratio = sta_lta(std::span<const T>(signal), n_sta, n_lta);
        // Copia apenas as amostras válidas (a partir de n_lta)
        for (std::size_t i = 0; i < n_valid; ++i) {
            result[i * n_channels + c] = ratio[n_lta + i];
        }
    }

    return result;
}

/**
 * @brief Calcula envoltória de Hilbert para cada canal de dados 2D.
 */
template <FloatingPoint T>
std::vector<T> hilbert_envelope_2d(std::span<const T> data,
                                   std::size_t n_times,
                                   std::size_t n_channels) {
    std::vector<T> result(n_times * n_channels);

    for (std::size_t c = 0; c < n_channels; ++c) {
        std::vector<T> signal(n_times);
        for (std::size_t t = 0; t < n_times; ++t) {
            signal[t] = data[t * n_channels + c];
        }
        auto envelope = hilbert_envelope(std::span<const T>(signal));
        for (std::size_t t = 0; t < n_times; ++t) {
            result[t * n_channels + c] = envelope[t];
        }
    }

    return result;
}

/**
 * @brief Calcula TKEO para cada canal de dados 2D.
 */
template <FloatingPoint T>
std::vector<T> teager_kaiser_2d(std::span<const T> data,
                                std::size_t n_times,
                                std::size_t n_channels) {
    std::vector<T> result(n_times * n_channels);

    for (std::size_t c = 0; c < n_channels; ++c) {
        std::vector<T> signal(n_times);
        for (std::size_t t = 0; t < n_times; ++t) {
            signal[t] = data[t * n_channels + c];
        }
        auto energy = teager_kaiser(std::span<const T>(signal));
        for (std::size_t t = 0; t < n_times; ++t) {
            result[t * n_channels + c] = energy[t];
        }
    }

    return result;
}

} // namespace alakoro::event_detection
