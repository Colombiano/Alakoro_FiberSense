/**
 * @file decomposition.hpp
 * @brief Decomposições avançadas de sinais em C++20.
 *
 * Fornece:
 *   - EMD (Empirical Mode Decomposition)
 *   - EEMD (Ensemble EMD)
 *   - NMF (Non-negative Matrix Factorization) simples
 *
 * Recursos C++20:
 *   - concepts (FloatingPoint)
 *   - std::span views
 *   - templates para precisão float/double
 */

#pragma once

#include "alakoro/concepts.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <random>
#include <span>
#include <stdexcept>
#include <vector>

namespace alakoro::decomposition {

// ─── Spline cúbico natural (auxiliar para EMD) ───────────────────────────────

/**
 * @brief Interpolação por spline cúbico natural.
 *
 * Dados n pontos (x[i], y[i]) com x estritamente crescente, avalia o spline
 * nos pontos xi. Implementação simples com condições naturais (segunda
 * derivada zero nas extremidades).
 */
template <FloatingPoint T>
std::vector<T> cubic_spline(const std::vector<T>& x,
                            const std::vector<T>& y,
                            const std::vector<T>& xi) {
    const std::size_t n = x.size();
    if (n < 2 || y.size() != n) {
        throw std::invalid_argument("x e y devem ter o mesmo tamanho >= 2");
    }

    // Diferenças
    std::vector<T> h(n - 1);
    for (std::size_t i = 0; i < n - 1; ++i) {
        h[i] = x[i + 1] - x[i];
    }

    // Sistema tridiagonal para segundas derivadas (condições naturais)
    std::vector<T> alpha(n, T{});
    for (std::size_t i = 1; i < n - 1; ++i) {
        alpha[i] = (T{3.0} / h[i]) * (y[i + 1] - y[i]) -
                   (T{3.0} / h[i - 1]) * (y[i] - y[i - 1]);
    }

    std::vector<T> l(n), mu(n), z(n);
    l[0] = T{1.0};
    mu[0] = T{};
    z[0] = T{};

    for (std::size_t i = 1; i < n - 1; ++i) {
        l[i] = T{2.0} * (x[i + 1] - x[i - 1]) - h[i - 1] * mu[i - 1];
        mu[i] = h[i] / l[i];
        z[i] = (alpha[i] - h[i - 1] * z[i - 1]) / l[i];
    }

    l[n - 1] = T{1.0};
    z[n - 1] = T{};

    std::vector<T> c(n), b(n - 1), d(n - 1);
    c[n - 1] = T{};
    for (std::size_t j = n - 1; j-- > 0;) {
        c[j] = z[j] - mu[j] * c[j + 1];
        b[j] = (y[j + 1] - y[j]) / h[j] - h[j] * (c[j + 1] + T{2.0} * c[j]) / T{3.0};
        d[j] = (c[j + 1] - c[j]) / (T{3.0} * h[j]);
    }

    // Avaliação
    std::vector<T> result(xi.size());
    std::size_t seg = 0;
    for (std::size_t i = 0; i < xi.size(); ++i) {
        T xv = xi[i];
        if (xv <= x.front()) {
            result[i] = y.front();
            continue;
        }
        if (xv >= x.back()) {
            result[i] = y.back();
            continue;
        }
        while (seg < n - 2 && xv > x[seg + 1]) {
            ++seg;
        }
        T dx = xv - x[seg];
        result[i] = y[seg] + b[seg] * dx + c[seg] * dx * dx + d[seg] * dx * dx * dx;
    }

    return result;
}

// ─── EMD ─────────────────────────────────────────────────────────────────────

/**
 * @brief Encontra índices dos máximos e mínimos locais de um sinal.
 */
template <FloatingPoint T>
void find_extrema(const std::vector<T>& signal,
                  std::vector<std::size_t>& maxima,
                  std::vector<std::size_t>& minima) {
    maxima.clear();
    minima.clear();

    for (std::size_t i = 1; i + 1 < signal.size(); ++i) {
        if (signal[i] > signal[i - 1] && signal[i] > signal[i + 1]) {
            maxima.push_back(i);
        } else if (signal[i] < signal[i - 1] && signal[i] < signal[i + 1]) {
            minima.push_back(i);
        }
    }
}

/**
 * @brief Calcula envelopes superior e inferior por spline cúbico.
 */
template <FloatingPoint T>
void compute_envelopes(const std::vector<T>& signal,
                       std::vector<T>& upper,
                       std::vector<T>& lower) {
    std::vector<std::size_t> maxima, minima;
    find_extrema(signal, maxima, minima);

    std::vector<T> x(signal.size());
    for (std::size_t i = 0; i < signal.size(); ++i) {
        x[i] = static_cast<T>(i);
    }

    upper.assign(signal.size(), T{});
    lower.assign(signal.size(), T{});

    if (maxima.size() >= 2) {
        std::vector<T> xm(maxima.size()), ym(maxima.size());
        for (std::size_t i = 0; i < maxima.size(); ++i) {
            xm[i] = static_cast<T>(maxima[i]);
            ym[i] = signal[maxima[i]];
        }
        upper = cubic_spline(xm, ym, x);
    } else {
        std::fill(upper.begin(), upper.end(), T{});
    }

    if (minima.size() >= 2) {
        std::vector<T> xn(minima.size()), yn(minima.size());
        for (std::size_t i = 0; i < minima.size(); ++i) {
            xn[i] = static_cast<T>(minima[i]);
            yn[i] = signal[minima[i]];
        }
        lower = cubic_spline(xn, yn, x);
    } else {
        std::fill(lower.begin(), lower.end(), T{});
    }
}

/**
 * @brief Verifica critério de parada do sifting.
 *
 * Critério simplificado: número de zero-crossings e número de extremos devem
 * diferir no máximo em 1, e a média das envelopes deve ser pequena.
 */
template <FloatingPoint T>
bool is_imf(const std::vector<T>& signal,
            const std::vector<T>& upper,
            const std::vector<T>& lower) {
    std::size_t zero_crossings = 0;
    for (std::size_t i = 0; i + 1 < signal.size(); ++i) {
        if (signal[i] * signal[i + 1] < 0) {
            ++zero_crossings;
        }
    }

    std::vector<std::size_t> maxima, minima;
    find_extrema(signal, maxima, minima);

    std::size_t n_extrema = maxima.size() + minima.size();
    if (std::abs(static_cast<int>(zero_crossings - n_extrema)) > 1) {
        return false;
    }

    T mean_env = T{};
    for (std::size_t i = 0; i < signal.size(); ++i) {
        mean_env += std::abs(upper[i] + lower[i]) / T{2.0};
    }
    mean_env /= static_cast<T>(signal.size());

    T signal_amp = T{};
    for (auto v : signal) signal_amp += std::abs(v);
    signal_amp /= static_cast<T>(signal.size());

    return mean_env < signal_amp * T{0.1};
}

/**
 * @brief Empirical Mode Decomposition (EMD) simplificada.
 *
 * Decompõe o sinal em IMFs (Intrinsic Mode Functions) e um resíduo.
 *
 * @tparam T Tipo de ponto flutuante
 * @param signal Sinal 1D
 * @param max_imfs Número máximo de IMFs
 * @return Vetor de IMFs + resíduo (último elemento)
 */
template <FloatingPoint T>
std::vector<std::vector<T>> emd(const std::vector<T>& signal, std::size_t max_imfs = 5) {
    if (signal.size() < 4) {
        return {signal};
    }

    std::vector<std::vector<T>> imfs;
    std::vector<T> residue = signal;

    for (std::size_t imf_idx = 0; imf_idx < max_imfs; ++imf_idx) {
        std::vector<T> h = residue;

        const std::size_t max_sift = 10;
        for (std::size_t sift = 0; sift < max_sift; ++sift) {
            std::vector<T> upper, lower;
            compute_envelopes(h, upper, lower);

            std::vector<T> mean_env(h.size());
            for (std::size_t i = 0; i < h.size(); ++i) {
                mean_env[i] = (upper[i] + lower[i]) / T{2.0};
            }

            for (std::size_t i = 0; i < h.size(); ++i) {
                h[i] -= mean_env[i];
            }

            if (is_imf(h, upper, lower)) {
                break;
            }
        }

        imfs.push_back(h);
        for (std::size_t i = 0; i < residue.size(); ++i) {
            residue[i] -= h[i];
        }

        // Critério de parada: poucos extremos no resíduo
        std::vector<std::size_t> maxima, minima;
        find_extrema(residue, maxima, minima);
        if (maxima.size() + minima.size() < 2) {
            break;
        }
    }

    imfs.push_back(residue);
    return imfs;
}

/**
 * @brief Ensemble EMD (EEMD) simplificada.
 *
 * Adiciona ruído branco em múltiplas realizações, aplica EMD e tira a média
 * dos IMFs correspondentes para reduzir o modo mixing.
 */
template <FloatingPoint T>
std::vector<std::vector<T>> eemd(const std::vector<T>& signal,
                                  std::size_t n_ensembles,
                                  double noise_std,
                                  std::size_t max_imfs = 5) {
    if (signal.empty() || n_ensembles == 0) {
        return {signal};
    }

    std::vector<std::vector<std::vector<T>>> ensemble_imfs(n_ensembles);
    std::mt19937 rng(42);
    std::normal_distribution<double> dist(0.0, noise_std);

    for (std::size_t e = 0; e < n_ensembles; ++e) {
        std::vector<T> noisy = signal;
        for (auto& v : noisy) {
            v += static_cast<T>(dist(rng));
        }
        ensemble_imfs[e] = emd(noisy, max_imfs);
    }

    // Encontra número mínimo de componentes entre realizações
    std::size_t min_components = ensemble_imfs[0].size();
    for (const auto& imfs : ensemble_imfs) {
        min_components = std::min(min_components, imfs.size());
    }

    std::vector<std::vector<T>> result(min_components, std::vector<T>(signal.size(), T{}));
    for (std::size_t c = 0; c < min_components; ++c) {
        for (std::size_t e = 0; e < n_ensembles; ++e) {
            for (std::size_t i = 0; i < signal.size(); ++i) {
                result[c][i] += ensemble_imfs[e][c][i];
            }
        }
        for (std::size_t i = 0; i < signal.size(); ++i) {
            result[c][i] /= static_cast<T>(n_ensembles);
        }
    }

    return result;
}

// ─── NMF ─────────────────────────────────────────────────────────────────────

/**
 * @brief NMF simples por algoritmo multiplicativo (Lee & Seung).
 *
 * Fatora a matriz não-negativa V (m x n) em W (m x k) e H (k x n), onde k é
 * o número de componentes. Layout row-major.
 *
 * @tparam T Tipo de ponto flutuante
 * @param data Matriz V como vetor flat (m x n)
 * @param m Número de linhas
 * @param n Número de colunas
 * @param n_components Número de componentes k
 * @param max_iter Número máximo de iterações
 * @return Par {W, H} como vetores flat
 */
template <FloatingPoint T>
std::pair<std::vector<T>, std::vector<T>> nmf(std::span<const T> data,
                                               std::size_t m,
                                               std::size_t n,
                                               std::size_t n_components,
                                               std::size_t max_iter = 100) {
    if (n_components == 0 || n_components > m || n_components > n) {
        throw std::invalid_argument("n_components inválido");
    }

    std::mt19937 rng(123);
    std::uniform_real_distribution<T> dist(T{0.0}, T{1.0});

    std::vector<T> W(m * n_components);
    std::vector<T> H(n_components * n);
    for (auto& v : W) v = dist(rng) + T{0.01};
    for (auto& v : H) v = dist(rng) + T{0.01};

    auto idx = [n_components](std::size_t i, std::size_t j) {
        return i * n_components + j;
    };
    auto idx_h = [n](std::size_t i, std::size_t j) {
        return i * n + j;
    };
    auto idx_v = [n](std::size_t i, std::size_t j) {
        return i * n + j;
    };

    for (std::size_t iter = 0; iter < max_iter; ++iter) {
        // Atualiza H: H *= (W^T * V) ./ (W^T * W * H + eps)
        std::vector<T> wh(m * n);
        for (std::size_t i = 0; i < m; ++i) {
            for (std::size_t j = 0; j < n; ++j) {
                T sum = T{};
                for (std::size_t k = 0; k < n_components; ++k) {
                    sum += W[idx(i, k)] * H[idx_h(k, j)];
                }
                wh[idx_v(i, j)] = sum;
            }
        }

        std::vector<T> wtv(n_components * n, T{});
        for (std::size_t k = 0; k < n_components; ++k) {
            for (std::size_t j = 0; j < n; ++j) {
                T sum = T{};
                for (std::size_t i = 0; i < m; ++i) {
                    sum += W[idx(i, k)] * data[idx_v(i, j)];
                }
                wtv[idx_h(k, j)] = sum;
            }
        }

        std::vector<T> wtwh(n_components * n, T{});
        for (std::size_t k = 0; k < n_components; ++k) {
            for (std::size_t j = 0; j < n; ++j) {
                T sum = T{};
                for (std::size_t l = 0; l < n_components; ++l) {
                    T wtw = T{};
                    for (std::size_t i = 0; i < m; ++i) {
                        wtw += W[idx(i, k)] * W[idx(i, l)];
                    }
                    sum += wtw * H[idx_h(l, j)];
                }
                wtwh[idx_h(k, j)] = sum;
            }
        }

        for (std::size_t k = 0; k < n_components; ++k) {
            for (std::size_t j = 0; j < n; ++j) {
                T num = wtv[idx_h(k, j)];
                T den = wtwh[idx_h(k, j)] + T{1e-9};
                H[idx_h(k, j)] *= num / den;
                if (H[idx_h(k, j)] < T{}) H[idx_h(k, j)] = T{};
            }
        }

        // Atualiza W: W *= (V * H^T) ./ (W * H * H^T + eps)
        std::vector<T> vht(m * n_components, T{});
        for (std::size_t i = 0; i < m; ++i) {
            for (std::size_t k = 0; k < n_components; ++k) {
                T sum = T{};
                for (std::size_t j = 0; j < n; ++j) {
                    sum += data[idx_v(i, j)] * H[idx_h(k, j)];
                }
                vht[idx(i, k)] = sum;
            }
        }

        std::vector<T> whht(m * n_components, T{});
        for (std::size_t i = 0; i < m; ++i) {
            for (std::size_t k = 0; k < n_components; ++k) {
                T sum = T{};
                for (std::size_t l = 0; l < n_components; ++l) {
                    T hht = T{};
                    for (std::size_t j = 0; j < n; ++j) {
                        hht += H[idx_h(k, j)] * H[idx_h(l, j)];
                    }
                    sum += W[idx(i, l)] * hht;
                }
                whht[idx(i, k)] = sum;
            }
        }

        for (std::size_t i = 0; i < m; ++i) {
            for (std::size_t k = 0; k < n_components; ++k) {
                T num = vht[idx(i, k)];
                T den = whht[idx(i, k)] + T{1e-9};
                W[idx(i, k)] *= num / den;
                if (W[idx(i, k)] < T{}) W[idx(i, k)] = T{};
            }
        }
    }

    return {W, H};
}

// ─── Helpers 2D ──────────────────────────────────────────────────────────────

template <FloatingPoint T>
std::vector<std::vector<std::vector<T>>> emd_2d(std::span<const T> data,
                                                 std::size_t n_times,
                                                 std::size_t n_channels,
                                                 std::size_t max_imfs = 5) {
    std::vector<std::vector<std::vector<T>>> result(n_channels);

    for (std::size_t c = 0; c < n_channels; ++c) {
        std::vector<T> signal(n_times);
        for (std::size_t t = 0; t < n_times; ++t) {
            signal[t] = data[t * n_channels + c];
        }
        result[c] = emd(signal, max_imfs);
    }

    return result;
}

template <FloatingPoint T>
std::vector<std::vector<std::vector<T>>> eemd_2d(std::span<const T> data,
                                                  std::size_t n_times,
                                                  std::size_t n_channels,
                                                  std::size_t n_ensembles,
                                                  double noise_std,
                                                  std::size_t max_imfs = 5) {
    std::vector<std::vector<std::vector<T>>> result(n_channels);

    for (std::size_t c = 0; c < n_channels; ++c) {
        std::vector<T> signal(n_times);
        for (std::size_t t = 0; t < n_times; ++t) {
            signal[t] = data[t * n_channels + c];
        }
        result[c] = eemd(signal, n_ensembles, noise_std, max_imfs);
    }

    return result;
}

} // namespace alakoro::decomposition
