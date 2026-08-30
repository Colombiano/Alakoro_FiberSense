/**
 * @file time_frequency.hpp
 * @brief Análise tempo-frequência e medidas de similaridade entre canais.
 *
 * Recursos C++20:
 *   - concepts (FloatingPoint)
 *   - std::span views
 *   - if constexpr para casos especiais
 *   - reutilização da FFT iterativa existente
 */

#pragma once

#include "alakoro/concepts.hpp"
#include "alakoro/fft.hpp"

#include <cmath>
#include <complex>
#include <cstddef>
#include <numbers>
#include <span>
#include <stdexcept>
#include <vector>

namespace alakoro::time_frequency {

/**
 * @brief Janela de Hann de tamanho n.
 */
template <FloatingPoint T>
std::vector<T> hann_window(std::size_t n) {
    std::vector<T> window(n);
    for (std::size_t i = 0; i < n; ++i) {
        T x = static_cast<T>(i) / static_cast<T>(n - 1);
        window[i] = static_cast<T>(0.5) * (T{1.0} - std::cos(T{2.0} * std::numbers::pi * x));
    }
    return window;
}

/**
 * @brief Short-Time Fourier Transform (STFT) de um sinal 1D.
 *
 * @tparam T Tipo de ponto flutuante
 * @param signal Sinal 1D
 * @param window_size Tamanho da janela de análise
 * @param hop_size Deslocamento entre janelas consecutivas
 * @param n_fft Tamanho da FFT (>= window_size, potência de 2)
 * @return Matriz complexa (n_frames x n_fft/2+1)
 */
template <FloatingPoint T>
std::vector<std::vector<std::complex<T>>> stft(std::span<const T> signal,
                                               std::size_t window_size,
                                               std::size_t hop_size,
                                               std::size_t n_fft) {
    if (hop_size == 0) {
        throw std::invalid_argument("hop_size deve ser maior que zero");
    }
    if (!fft::is_power_of_two(n_fft)) {
        throw std::invalid_argument("n_fft deve ser potência de 2");
    }
    if (window_size > n_fft) {
        throw std::invalid_argument("window_size não pode ser maior que n_fft");
    }

    const std::size_t n = signal.size();
    if (n < window_size) {
        return {};
    }

    const std::size_t n_frames = (n - window_size) / hop_size + 1;
    const std::size_t n_freq = n_fft / 2 + 1;

    auto window = hann_window<T>(window_size);
    std::vector<std::vector<std::complex<T>>> result;
    result.reserve(n_frames);

    for (std::size_t frame = 0; frame < n_frames; ++frame) {
        std::size_t start = frame * hop_size;
        std::vector<std::complex<T>> x(n_fft);
        for (std::size_t i = 0; i < window_size; ++i) {
            x[i] = std::complex<T>(signal[start + i] * window[i], T{});
        }
        for (std::size_t i = window_size; i < n_fft; ++i) {
            x[i] = std::complex<T>(T{}, T{});
        }

        fft::fft(x, false);

        std::vector<std::complex<T>> frame_spectrum(n_freq);
        for (std::size_t k = 0; k < n_freq; ++k) {
            frame_spectrum[k] = x[k];
        }
        result.push_back(std::move(frame_spectrum));
    }

    return result;
}

/**
 * @brief Espectrograma (magnitude ao quadrado da STFT).
 *
 * @return Matriz (n_frames x n_freq)
 */
template <FloatingPoint T>
std::vector<std::vector<T>> spectrogram(std::span<const T> signal,
                                        std::size_t window_size,
                                        std::size_t hop_size,
                                        std::size_t n_fft) {
    auto stft_result = stft(signal, window_size, hop_size, n_fft);
    std::vector<std::vector<T>> result;
    result.reserve(stft_result.size());

    for (const auto& frame : stft_result) {
        std::vector<T> power(frame.size());
        for (std::size_t k = 0; k < frame.size(); ++k) {
            power[k] = std::norm(frame[k]);
        }
        result.push_back(std::move(power));
    }

    return result;
}

/**
 * @brief Correlação cruzada 1D com atraso máximo.
 *
 * Usa definição direta no domínio do tempo: robusta para sinais curtos.
 *
 * @return Vetor de correlações para atrasos em [-max_lag, +max_lag]
 */
template <FloatingPoint T>
std::vector<T> cross_correlation(std::span<const T> x,
                                  std::span<const T> y,
                                  std::size_t max_lag) {
    if (x.size() != y.size()) {
        throw std::invalid_argument("x e y devem ter o mesmo tamanho");
    }

    const std::size_t n = x.size();
    const std::size_t result_size = 2 * max_lag + 1;
    std::vector<T> result(result_size, T{});

    // Normalização pelo produto dos desvios padrão
    T mean_x = T{}, mean_y = T{};
    for (std::size_t i = 0; i < n; ++i) {
        mean_x += x[i];
        mean_y += y[i];
    }
    mean_x /= static_cast<T>(n);
    mean_y /= static_cast<T>(n);

    T var_x = T{}, var_y = T{};
    for (std::size_t i = 0; i < n; ++i) {
        var_x += (x[i] - mean_x) * (x[i] - mean_x);
        var_y += (y[i] - mean_y) * (y[i] - mean_y);
    }
    T denom = std::sqrt(var_x * var_y) + T{1e-24};

    for (std::size_t lag_idx = 0; lag_idx < result_size; ++lag_idx) {
        int lag = static_cast<int>(lag_idx) - static_cast<int>(max_lag);
        T sum = T{};
        std::size_t count = 0;
        for (std::size_t i = 0; i < n; ++i) {
            std::size_t j;
            if (lag >= 0) {
                j = i + static_cast<std::size_t>(lag);
            } else {
                if (i < static_cast<std::size_t>(-lag)) continue;
                j = i - static_cast<std::size_t>(-lag);
            }
            if (j >= n) continue;
            sum += (x[i] - mean_x) * (y[j] - mean_y);
            ++count;
        }
        if (count > 0) {
            result[lag_idx] = sum / denom;
        }
    }

    return result;
}

/**
 * @brief Correlação cruzada entre canais adjacentes de dados 2D.
 *
 * Retorna matriz (n_channels x (2*max_lag+1)) com correlação de cada canal
 * com seu vizinho à direita. O último canal é correlacionado com o primeiro.
 */
template <FloatingPoint T>
std::vector<T> cross_correlation_channels(std::span<const T> data,
                                          std::size_t n_times,
                                          std::size_t n_channels,
                                          std::size_t max_lag) {
    const std::size_t lag_size = 2 * max_lag + 1;
    std::vector<T> result(n_channels * lag_size);

    for (std::size_t c = 0; c < n_channels; ++c) {
        std::size_t next_c = (c + 1) % n_channels;
        std::vector<T> x(n_times), y(n_times);
        for (std::size_t t = 0; t < n_times; ++t) {
            x[t] = data[t * n_channels + c];
            y[t] = data[t * n_channels + next_c];
        }
        auto corr = cross_correlation(std::span<const T>(x), std::span<const T>(y), max_lag);
        for (std::size_t i = 0; i < lag_size; ++i) {
            result[c * lag_size + i] = corr[i];
        }
    }

    return result;
}

/**
 * @brief Magnitude squared coherence entre canais adjacentes.
 *
 * Estimada via STFT: Cxy(f)^2 = |Sxy(f)|^2 / (Sxx(f) * Syy(f))
 *
 * Retorna matriz (n_channels x n_freq) com coerência média de cada canal
 * com seu vizinho à direita.
 */
template <FloatingPoint T>
std::vector<T> coherence_channels(std::span<const T> data,
                                  std::size_t n_times,
                                  std::size_t n_channels,
                                  std::size_t window_size,
                                  std::size_t hop_size,
                                  std::size_t n_fft) {
    const std::size_t n_freq = n_fft / 2 + 1;
    std::vector<T> result(n_channels * n_freq, T{});

    for (std::size_t c = 0; c < n_channels; ++c) {
        std::size_t next_c = (c + 1) % n_channels;
        std::vector<T> x(n_times), y(n_times);
        for (std::size_t t = 0; t < n_times; ++t) {
            x[t] = data[t * n_channels + c];
            y[t] = data[t * n_channels + next_c];
        }

        auto stft_x = stft(std::span<const T>(x), window_size, hop_size, n_fft);
        auto stft_y = stft(std::span<const T>(y), window_size, hop_size, n_fft);

        if (stft_x.empty() || stft_y.empty()) {
            continue;
        }

        std::vector<T> sxx(n_freq, T{}), syy(n_freq, T{}), sxy_real(n_freq, T{}), sxy_imag(n_freq, T{});
        const std::size_t n_frames = std::min(stft_x.size(), stft_y.size());

        for (std::size_t f = 0; f < n_frames; ++f) {
            for (std::size_t k = 0; k < n_freq; ++k) {
                auto xv = stft_x[f][k];
                auto yv = stft_y[f][k];
                sxx[k] += std::norm(xv);
                syy[k] += std::norm(yv);
                auto cxy = xv * std::conj(yv);
                sxy_real[k] += cxy.real();
                sxy_imag[k] += cxy.imag();
            }
        }

        for (std::size_t k = 0; k < n_freq; ++k) {
            T sxx_k = sxx[k] / static_cast<T>(n_frames);
            T syy_k = syy[k] / static_cast<T>(n_frames);
            T sxy_mag2 = (sxy_real[k] * sxy_real[k] + sxy_imag[k] * sxy_imag[k])
                         / (static_cast<T>(n_frames) * static_cast<T>(n_frames));
            T denom = sxx_k * syy_k + T{1e-24};
            result[c * n_freq + k] = sxy_mag2 / denom;
        }
    }

    return result;
}

/**
 * @brief STFT para cada canal de dados 2D.
 *
 * Retorna lista de espectrogramas (um por canal).
 */
template <FloatingPoint T>
std::vector<std::vector<std::vector<T>>> spectrogram_2d(std::span<const T> data,
                                                         std::size_t n_times,
                                                         std::size_t n_channels,
                                                         std::size_t window_size,
                                                         std::size_t hop_size,
                                                         std::size_t n_fft) {
    std::vector<std::vector<std::vector<T>>> result;
    result.reserve(n_channels);

    for (std::size_t c = 0; c < n_channels; ++c) {
        std::vector<T> signal(n_times);
        for (std::size_t t = 0; t < n_times; ++t) {
            signal[t] = data[t * n_channels + c];
        }
        result.push_back(spectrogram(std::span<const T>(signal), window_size, hop_size, n_fft));
    }

    return result;
}

} // namespace alakoro::time_frequency
