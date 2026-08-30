/**
 * @file denoising.hpp
 * @brief Técnicas de remoção de ruído para dados DAS/DTS/DSS em C++20.
 *
 * Fornece filtros clássicos e decomposições para melhorar a relação sinal/ruído
 * antes da detecção de eventos ou extração de features:
 *   - Median filter 1D/2D: remove spikes impulsivos
 *   - SVD/PCA denoising: mantém apenas os modos de maior energia
 *   - Wavelet thresholding: denoising no domínio tempo-escala
 *
 * Recursos C++20:
 *   - concepts (FloatingPoint)
 *   - templates não-tipo para tamanhos de janela conhecidos
 *   - if constexpr para especialização
 *   - std::span, std::nth_element
 */

#pragma once

#include "alakoro/concepts.hpp"
#include "alakoro/wavelet.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <span>
#include <stdexcept>
#include <vector>

namespace alakoro::denoising {

/**
 * @brief Aplica filtro de mediana 1D a um sinal.
 *
 * Útil para remover spikes impulsivos sem distorcer bordas. A janela deve ser
 * ímpar.
 *
 * @tparam T Tipo de ponto flutuante
 * @param signal Sinal 1D
 * @param window_size Tamanho da janela (ímpar)
 * @return Sinal filtrado
 */
template <FloatingPoint T>
std::vector<T> median_filter_1d(std::span<const T> signal, std::size_t window_size) {
    if (window_size % 2 == 0) {
        throw std::invalid_argument("Janela do median filter deve ser ímpar");
    }
    if (window_size == 0 || signal.size() < window_size) {
        return std::vector<T>(signal.begin(), signal.end());
    }

    const std::size_t n = signal.size();
    const std::size_t half = window_size / 2;
    std::vector<T> result(n);

    std::vector<T> window(window_size);
    for (std::size_t i = 0; i < n; ++i) {
        std::size_t start = (i < half) ? 0 : (i - half);
        std::size_t end = std::min(start + window_size, n);
        if (end - start < window_size && start > 0) {
            start = end - window_size;
        }

        window.clear();
        for (std::size_t j = start; j < end; ++j) {
            window.push_back(signal[j]);
        }

        // Encontra a mediana com nth_element (O(n) médio)
        std::size_t mid = window.size() / 2;
        std::nth_element(window.begin(), window.begin() + mid, window.end());
        result[i] = window[mid];
    }

    return result;
}

/**
 * @brief Aplica filtro de mediana 2D a dados (time, channels).
 *
 * @tparam T Tipo de ponto flutuante
 * @param data Dados 2D contíguos [time * n_channels + channel]
 * @param n_times Número de amostras temporais
 * @param n_channels Número de canais
 * @param window_t Janela temporal (ímpar)
 * @param window_c Janela espacial (ímpar)
 * @return Dados filtrados no mesmo layout
 */
template <FloatingPoint T>
std::vector<T> median_filter_2d(std::span<const T> data,
                                std::size_t n_times,
                                std::size_t n_channels,
                                std::size_t window_t,
                                std::size_t window_c) {
    if (window_t % 2 == 0 || window_c % 2 == 0) {
        throw std::invalid_argument("Janelas do median filter 2D devem ser ímpares");
    }

    const std::size_t half_t = window_t / 2;
    const std::size_t half_c = window_c / 2;
    std::vector<T> result(n_times * n_channels);
    std::vector<T> window;

    for (std::size_t t = 0; t < n_times; ++t) {
        for (std::size_t c = 0; c < n_channels; ++c) {
            window.clear();

            std::size_t t_start = (t < half_t) ? 0 : (t - half_t);
            std::size_t t_end = std::min(t + half_t + 1, n_times);
            std::size_t c_start = (c < half_c) ? 0 : (c - half_c);
            std::size_t c_end = std::min(c + half_c + 1, n_channels);

            for (std::size_t tt = t_start; tt < t_end; ++tt) {
                for (std::size_t cc = c_start; cc < c_end; ++cc) {
                    window.push_back(data[tt * n_channels + cc]);
                }
            }

            std::size_t mid = window.size() / 2;
            std::nth_element(window.begin(), window.begin() + mid, window.end());
            result[t * n_channels + c] = window[mid];
        }
    }

    return result;
}

// ─── SVD/PCA Denoising ───────────────────────────────────────────────────────

/**
 * @brief Multiplicação matricial C = A * B.
 *
 * A: (m x n), B: (n x p), C: (m x p). Layout row-major.
 */
template <FloatingPoint T>
void matmul(const std::vector<T>& A, const std::vector<T>& B, std::vector<T>& C,
            std::size_t m, std::size_t n, std::size_t p) {
    std::fill(C.begin(), C.end(), T{});
    for (std::size_t i = 0; i < m; ++i) {
        for (std::size_t k = 0; k < n; ++k) {
            T a = A[i * n + k];
            for (std::size_t j = 0; j < p; ++j) {
                C[i * p + j] += a * B[k * p + j];
            }
        }
    }
}

/**
 * @brief Transposta de uma matriz.
 */
template <FloatingPoint T>
std::vector<T> transpose(const std::vector<T>& A, std::size_t rows, std::size_t cols) {
    std::vector<T> AT(rows * cols);
    for (std::size_t i = 0; i < rows; ++i) {
        for (std::size_t j = 0; j < cols; ++j) {
            AT[j * rows + i] = A[i * cols + j];
        }
    }
    return AT;
}

/**
 * @brief Decomposição SVD por método de Jacobi (A = U * S * V^T).
 *
 * Implementação simplificada sem dependências externas. Adequada para matrizes
 * de tamanho moderado (centenas de canais/amostras). Retorna U, S (vetor) e V^T.
 *
 * @param A Matriz de entrada (m x n), m >= n
 * @param m Número de linhas
 * @param n Número de colunas
 * @param U Saída: matriz ortogonal (m x n)
 * @param S Saída: valores singulares (n)
 * @param VT Saída: transposta de V (n x n)
 */
template <FloatingPoint T>
void svd_jacobi(const std::vector<T>& A, std::size_t m, std::size_t n,
                std::vector<T>& U, std::vector<T>& S, std::vector<T>& VT) {
    if (m < n) {
        throw std::invalid_argument("svd_jacobi requer m >= n");
    }

    // Inicializa U = A e V = I
    U = A;
    std::vector<T> V(n * n, T{});
    for (std::size_t i = 0; i < n; ++i) {
        V[i * n + i] = T{1.0};
    }

    const std::size_t max_sweeps = 100;
    const T eps = std::numeric_limits<T>::epsilon() * 100;

    for (std::size_t sweep = 0; sweep < max_sweeps; ++sweep) {
        T max_off = T{};
        for (std::size_t p_col = 0; p_col < n; ++p_col) {
            for (std::size_t q_col = p_col + 1; q_col < n; ++q_col) {
                // Calcula colunas p e q de U
                T alpha = T{}, beta = T{}, gamma = T{};
                for (std::size_t i = 0; i < m; ++i) {
                    T up = U[i * n + p_col];
                    T uq = U[i * n + q_col];
                    alpha += up * up;
                    beta += uq * uq;
                    gamma += up * uq;
                }
                max_off = std::max(max_off, std::abs(gamma));

                if (std::abs(gamma) < eps) continue;

                // Ângulo de rotação de Jacobi
                T zeta = (beta - alpha) / (T{2.0} * gamma);
                T t;
                if (zeta >= T{}) {
                    t = T{1.0} / (zeta + std::sqrt(T{1.0} + zeta * zeta));
                } else {
                    t = T{1.0} / (zeta - std::sqrt(T{1.0} + zeta * zeta));
                }
                T c = T{1.0} / std::sqrt(T{1.0} + t * t);
                T s = c * t;

                // Rotaciona colunas de U
                for (std::size_t i = 0; i < m; ++i) {
                    T up = U[i * n + p_col];
                    T uq = U[i * n + q_col];
                    U[i * n + p_col] = c * up - s * uq;
                    U[i * n + q_col] = s * up + c * uq;
                }

                // Atualiza V
                for (std::size_t i = 0; i < n; ++i) {
                    T vp = V[i * n + p_col];
                    T vq = V[i * n + q_col];
                    V[i * n + p_col] = c * vp - s * vq;
                    V[i * n + q_col] = s * vp + c * vq;
                }
            }
        }
        if (max_off < eps) break;
    }

    // Extrai valores singulares (normas das colunas de U)
    S.resize(n);
    for (std::size_t j = 0; j < n; ++j) {
        T norm = T{};
        for (std::size_t i = 0; i < m; ++i) {
            norm += U[i * n + j] * U[i * n + j];
        }
        S[j] = std::sqrt(norm);
        // Normaliza coluna de U
        if (S[j] > T{1e-24}) {
            for (std::size_t i = 0; i < m; ++i) {
                U[i * n + j] /= S[j];
            }
        }
    }

    VT = transpose(V, n, n);
}

/**
 * @brief Denoising por SVD/PCA.
 *
 * Decompõe a matriz de dados e reconstrói usando apenas os n_components
 * componentes principais (maiores valores singulares). Remove ruído incoerente.
 *
 * @tparam T Tipo de ponto flutuante
 * @param data Dados 2D contíguos (n_times x n_channels)
 * @param n_times Número de linhas (tempo)
 * @param n_channels Número de colunas (canais)
 * @param n_components Número de componentes principais a manter
 * @return Dados reconstruídos
 */
template <FloatingPoint T>
std::vector<T> svd_denoise(std::span<const T> data,
                           std::size_t n_times,
                           std::size_t n_channels,
                           std::size_t n_components) {
    std::size_t m = n_times;
    std::size_t n = n_channels;
    bool transpose_input = false;

    // Garante m >= n para o algoritmo de Jacobi
    std::vector<T> A;
    if (m < n) {
        transpose_input = true;
        std::swap(m, n);
        A.resize(m * n);
        for (std::size_t i = 0; i < n_times; ++i) {
            for (std::size_t j = 0; j < n_channels; ++j) {
                A[j * n + i] = data[i * n_channels + j];
            }
        }
    } else {
        A.assign(data.begin(), data.end());
    }

    if (n_components > n) {
        n_components = n;
    }

    std::vector<T> U, S, VT;
    svd_jacobi(A, m, n, U, S, VT);

    // Zera componentes além de n_components
    for (std::size_t k = n_components; k < n; ++k) {
        S[k] = T{};
    }

    // Reconstrói: U * diag(S) * VT
    std::vector<T> US(m * n);
    for (std::size_t i = 0; i < m; ++i) {
        for (std::size_t j = 0; j < n; ++j) {
            US[i * n + j] = U[i * n + j] * S[j];
        }
    }

    std::vector<T> reconstructed(m * n);
    matmul(US, VT, reconstructed, m, n, n);

    if (transpose_input) {
        // Desfaz a transposição
        std::vector<T> result(n_times * n_channels);
        for (std::size_t i = 0; i < m; ++i) {
            for (std::size_t j = 0; j < n; ++j) {
                result[j * n + i] = reconstructed[i * n + j];
            }
        }
        return result;
    }

    return reconstructed;
}

/**
 * @brief Denoising por thresholding de coeficientes wavelet.
 *
 * Aplica CWT Morlet, threshold nos coeficientes e reconstrução aproximada por
 * soma das contribuições de cada escala. O threshold pode ser 'soft' ou 'hard'.
 *
 * @tparam T Tipo de ponto flutuante
 * @param signal Sinal 1D
 * @param scales Escalas da CWT
 * @param sample_rate_hz Taxa de amostragem
 * @param threshold Valor de corte
 * @param rule "soft" ou "hard"
 * @return Sinal denoised
 */
template <FloatingPoint T>
std::vector<T> wavelet_denoise(const std::vector<T>& signal,
                               const std::vector<double>& scales,
                               double sample_rate_hz,
                               double threshold,
                               const std::string& rule = "soft") {
    if (signal.empty() || scales.empty()) {
        return signal;
    }

    auto coefs = wavelet::cwt(signal, scales, sample_rate_hz, wavelet::WaveletType::Morlet);

    std::vector<T> reconstructed(signal.size(), T{});
    for (std::size_t s = 0; s < scales.size(); ++s) {
        for (std::size_t i = 0; i < signal.size(); ++i) {
            T v = coefs[s][i];
            T denoised;
            if (rule == "soft") {
                denoised = (v > threshold) ? (v - threshold) : ((v < -threshold) ? (v + threshold) : T{});
            } else {
                denoised = (std::abs(v) > threshold) ? v : T{};
            }
            reconstructed[i] += denoised;
        }
    }

    return reconstructed;
}

/**
 * @brief Wavelet denoising para cada canal de dados 2D.
 */
template <FloatingPoint T>
std::vector<T> wavelet_denoise_2d(std::span<const T> data,
                                  std::size_t n_times,
                                  std::size_t n_channels,
                                  const std::vector<double>& scales,
                                  double sample_rate_hz,
                                  double threshold,
                                  const std::string& rule = "soft") {
    std::vector<T> result(n_times * n_channels);

    for (std::size_t c = 0; c < n_channels; ++c) {
        std::vector<T> signal(n_times);
        for (std::size_t t = 0; t < n_times; ++t) {
            signal[t] = data[t * n_channels + c];
        }
        auto denoised = wavelet_denoise(signal, scales, sample_rate_hz, threshold, rule);
        for (std::size_t t = 0; t < n_times; ++t) {
            result[t * n_channels + c] = denoised[t];
        }
    }

    return result;
}

/**
 * @brief Median filter 1D para cada canal de dados 2D.
 */
template <FloatingPoint T>
std::vector<T> median_filter_1d_2d(std::span<const T> data,
                                   std::size_t n_times,
                                   std::size_t n_channels,
                                   std::size_t window_size) {
    std::vector<T> result(n_times * n_channels);

    for (std::size_t c = 0; c < n_channels; ++c) {
        std::vector<T> signal(n_times);
        for (std::size_t t = 0; t < n_times; ++t) {
            signal[t] = data[t * n_channels + c];
        }
        auto filtered = median_filter_1d(std::span<const T>(signal), window_size);
        for (std::size_t t = 0; t < n_times; ++t) {
            result[t * n_channels + c] = filtered[t];
        }
    }

    return result;
}

} // namespace alakoro::denoising
