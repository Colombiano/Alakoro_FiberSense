/**
 * @file decoupling.hpp
 * @brief Desacoplamento tensão-temperatura (strain–temperature decoupling) em C++20.
 *
 * Em DSS/Brillouin a deformação aparente medida contém uma contribuição
 * térmica: ε_apparent = ε_true + C·ΔT, onde C (coeficiente de acoplamento,
 * tipicamente ~ −0.0028 µε/°C em fibra padrão a 1550 nm) representa o efeito
 * da expansão térmica sobre a strain aparente. Este header estima C localmente
 * (regressão Theil–Sen robusta a outliers, em janelas 2D deslizantes com
 * sobreposição suave) e corrige o campo via ε̂ = ε − C·ΔT.
 *
 * In DSS/Brillouin sensing the measured apparent strain contains a thermal
 * contribution ε_apparent = ε_true + C·ΔT. This header estimates the coupling
 * coefficient C locally (outlier-robust Theil–Sen regression over sliding 2D
 * windows with smooth overlap) and corrects the field via ε̂ = ε − C·ΔT.
 *
 * Recursos C++20:
 *   - concepts (std::floating_point) nas APIs template
 *   - if constexpr na regressão via CouplingPolicy<ConstrainCS> (restrição C ≤ 0)
 *   - move semantics explícito: DecouplingResult é move-only (noexcept)
 *   - fold expression no acúmulo ponderado das janelas sobrepostas
 *   - std::span para views zero-copy sobre buffers externos
 */

#pragma once

#include <algorithm>
#include <cmath>
#include <concepts>
#include <cstddef>
#include <limits>
#include <span>
#include <stdexcept>
#include <utility>
#include <vector>

namespace alakoro::decoupling {

/**
 * @brief Resultado do desacoplamento tensão-temperatura (CL-03).
 *
 * Objeto pesado (dois campos O(n_t·n_z)): move-only por construção.
 * Heavy object (two O(n_t·n_z) fields): move-only by design.
 *
 * Campos / Fields:
 *   - decoupled: campo corrigido ε̂ = ε − C·ΔT, row-major (t × z)
 *   - coefficient_map: coeficiente C estimado por posição (t × z), flat
 *   - global_coefficient: Theil–Sen sobre o campo inteiro
 *   - constrained: true se a restrição física C ≤ 0 foi aplicada em alguma
 *     janela (C espúrio positivo desviado para min(C, 0))
 */
template <std::floating_point T>
struct DecouplingResult {
    std::vector<T> decoupled;        ///< Campo corrigido, row-major t×z
    std::vector<T> coefficient_map;  ///< C estimado por posição (flat, t×z)
    T global_coefficient = T{};      ///< Coeficiente global (Theil–Sen)
    bool constrained = false;        ///< Restrição C ≤ 0 aplicada em alguma janela

    DecouplingResult() = default;
    ~DecouplingResult() = default;

    // Move-only: cópia deletada (objeto pesado), move noexcept.
    DecouplingResult(DecouplingResult&&) noexcept = default;
    DecouplingResult& operator=(DecouplingResult&&) noexcept = default;
    DecouplingResult(const DecouplingResult&) = delete;
    DecouplingResult& operator=(const DecouplingResult&) = delete;
};

/**
 * @brief Política de restrição física do coeficiente de acoplamento.
 *
 * CS (cross-sensitivity): a expansão térmica reduz a strain aparente, logo
 * C fisicamente válido é ≤ 0. Quando ConstrainCS é true, estimativas
 * positivas (espúrias, ex.: por correlação inversa ruído×temperatura) são
 * desviadas para min(C, 0) e o resultado é marcado como constrained.
 *
 * Physical constraint policy: thermal expansion reduces apparent strain, so
 * valid C ≤ 0. If constexpr dispatches the clamp at compile time.
 */
template <bool ConstrainCS>
struct CouplingPolicy {
    static constexpr bool constrain_cs = ConstrainCS;
};

/**
 * @brief Estimador Theil–Sen da inclinação entre Δstrain e Δtemperature.
 *
 * Mediana das inclinações (y_i − y_j)/(x_i − x_j) de todos os pares i < j
 * com |x_i − x_j| > eps. É robusta a até ~29% de outliers. Para n pequeno
 * (≤ 256) usa todos os pares O(n²); para n grande usa amostragem
 * determinística de pares (i, i+h) com h em {1,2,4,…} — O(n log n).
 *
 * Theil–Sen slope estimator: median of pairwise slopes. Deterministic pair
 * sampling for large n keeps the cost at O(n log n).
 *
 * @tparam T Tipo de ponto flutuante
 * @param dstrain Variações de strain (dependente y)
 * @param dtemp Variações de temperatura (independente x)
 * @param min_x_span Tolerância mínima de variação em x para aceitar um par
 * @return Mediana das inclinações (0.0 se não houver pares válidos)
 */
template <std::floating_point T>
T estimate_coefficient(std::span<const T> dstrain,
                       std::span<const T> dtemp,
                       T min_x_span = T{1e-9}) {
    if (dstrain.size() != dtemp.size()) {
        throw std::invalid_argument(
            "estimate_coefficient: dstrain and dtemp sizes differ");
    }
    const std::size_t n = dstrain.size();
    if (n < 2) return T{};

    std::vector<T> slopes;
    const std::size_t kAllPairsCap = 256;  // acima disso: amostragem O(n log n)
    if (n <= kAllPairsCap) {
        slopes.reserve(n * (n - 1) / 2);
        for (std::size_t i = 0; i + 1 < n; ++i) {
            for (std::size_t j = i + 1; j < n; ++j) {
                const T dx = dtemp[i] - dtemp[j];
                if (std::abs(dx) > min_x_span) {
                    slopes.push_back((dstrain[i] - dstrain[j]) / dx);
                }
            }
        }
    } else {
        // Amostragem determinística: deslocamentos em potências de 2.
        std::size_t cap = 0;
        for (std::size_t h = 1; h < n; h <<= 1) cap += n - h;
        slopes.reserve(cap);
        for (std::size_t h = 1; h < n; h <<= 1) {
            for (std::size_t i = 0; i + h < n; ++i) {
                const T dx = dtemp[i] - dtemp[i + h];
                if (std::abs(dx) > min_x_span) {
                    slopes.push_back((dstrain[i] - dstrain[i + h]) / dx);
                }
            }
        }
    }

    if (slopes.empty()) return T{};
    const std::size_t mid = slopes.size() / 2;
    std::nth_element(slopes.begin(), slopes.begin() + mid, slopes.end());
    return slopes[mid];
}

namespace detail {

/**
 * @brief Peso triangular de sobreposição: 1 no centro, 0 na borda da janela.
 *
 * Fold expression (unário à direita) acumula o produto dos fatores — aqui
 * usado para combinar os pesos temporal e espacial de uma janela 2D.
 */
template <std::floating_point T, typename... Factors>
constexpr T overlap_weight_product(Factors... factors) {
    return (static_cast<T>(factors) * ...);
}

/**
 * @brief Peso triangular 1D da posição local dentro da janela.
 */
template <std::floating_point T>
constexpr T triangular_weight(std::size_t local, std::size_t extent) noexcept {
    if (extent <= 1) return T{1};
    const T x = static_cast<T>(local) / static_cast<T>(extent - 1);
    return T{1} - std::abs(T{2} * x - T{1});
}

} // namespace detail

/**
 * @brief Desacoplamento janelado 2D strain × temperatura (CL-03).
 *
 * Para cada janela deslizante (win_t × win_z, passo = metade da janela):
 *   1. estima C local por Theil–Sen entre as amostras da janela;
 *   2. aplica a política CouplingPolicy<ConstrainCS> (if constexpr):
 *      se constrain_cs e C > 0 → C = min(C, 0), marca constrained;
 *   3. acumula a correção ε − C·ΔT e o próprio C com peso triangular de
 *      sobreposição (fold expression no produto dos pesos t × z).
 *
 * Ao final normaliza pela soma dos pesos (média suave nas bordas de
 * sobreposição). ΔT é referenciado à primeira linha temporal (baseline):
 * ΔT(t,z) = temp(t,z) − temp(0,z).
 *
 * Sliding 2D window decoupling: local Theil–Sen coefficient per window,
 * physical constraint via if constexpr policy, smooth triangular overlap.
 * Windows with weak (but non-degenerate) temperature spans fall back to the
 * global coefficient, which is estimated over the whole field and is much
 * less noisy.
 *
 * Validações / Validation (std::invalid_argument):
 *   - strain e temp com mesmas dimensões n_t × n_z
 *   - win_t ≥ 8 e win_z ≥ 8
 *   - n_t ≥ win_t, n_z ≥ win_z
 *   - janela contém variação de temperatura > 0
 *
 * @tparam T Tipo de ponto flutuante
 * @tparam ConstrainCS true para restringir C ≤ 0 (política física CS)
 * @param strain Campo de strain aparente (flat, row-major t×z)
 * @param temp Campo de temperatura (flat, row-major t×z)
 * @param n_t Número de amostras temporais
 * @param n_z Número de posições (canais/profundidades)
 * @param win_t Janela temporal (≥ 8)
 * @param win_z Janela espacial (≥ 8)
 * @return DecouplingResult move-only com campo corrigido e mapa de coeficientes
 */
template <std::floating_point T, bool ConstrainCS = true>
DecouplingResult<T> decouple_windowed_2d(std::span<const T> strain,
                                         std::span<const T> temp,
                                         std::size_t n_t,
                                         std::size_t n_z,
                                         std::size_t win_t,
                                         std::size_t win_z) {
    if (strain.size() != temp.size() || strain.size() != n_t * n_z ||
        n_t == 0 || n_z == 0) {
        throw std::invalid_argument(
            "decouple_windowed_2d: strain/temp size does not match n_t*n_z");
    }
    if (win_t < 8 || win_z < 8) {
        throw std::invalid_argument(
            "decouple_windowed_2d: win_t and win_z must be >= 8");
    }
    if (n_t < win_t || n_z < win_z) {
        throw std::invalid_argument(
            "decouple_windowed_2d: window larger than data field");
    }

    DecouplingResult<T> result;
    result.decoupled.assign(strain.size(), T{});
    result.coefficient_map.assign(strain.size(), T{});
    std::vector<double> weight_sum(strain.size(), 0.0);

    // Coeficiente global (Theil–Sen sobre o campo inteiro, amostras de
    // colunas completas; diferenças tomadas contra a linha de referência).
    {
        std::vector<T> gs, gt;
        gs.reserve(n_t * n_z);
        gt.reserve(n_t * n_z);
        for (std::size_t t = 1; t < n_t; ++t) {
            for (std::size_t z = 0; z < n_z; ++z) {
                const T dtemp = temp[t * n_z + z] - temp[z];
                if (std::abs(dtemp) > T{1e-9}) {
                    gt.push_back(dtemp);
                    gs.push_back(strain[t * n_z + z] - strain[z]);
                }
            }
        }
        result.global_coefficient =
            estimate_coefficient<T>(std::span<const T>(gs), std::span<const T>(gt));
    }

    const std::size_t step_t = win_t / 2;
    const std::size_t step_z = win_z / 2;

    for (std::size_t t0 = 0; t0 + win_t <= n_t; t0 += step_t) {
        for (std::size_t z0 = 0; z0 + win_z <= n_z; z0 += step_z) {
            // Coleta amostras da janela (strain e ΔT contra a linha base).
            std::vector<T> ds, dt;
            ds.reserve(win_t * win_z);
            dt.reserve(win_t * win_z);
            T dtemp_range = T{};
            {
                T dtemp_min = std::numeric_limits<T>::max();
                T dtemp_max = std::numeric_limits<T>::lowest();
                for (std::size_t t = t0; t < t0 + win_t; ++t) {
                    for (std::size_t z = z0; z < z0 + win_z; ++z) {
                        const T d = temp[t * n_z + z] - temp[z];
                        dt.push_back(d);
                        ds.push_back(strain[t * n_z + z] - strain[z]);
                        dtemp_min = std::min(dtemp_min, d);
                        dtemp_max = std::max(dtemp_max, d);
                    }
                }
                dtemp_range = dtemp_max - dtemp_min;
            }
            if (dtemp_range <= T{1e-9}) {
                throw std::invalid_argument(
                    "decouple_windowed_2d: window has no temperature variation");
            }

            // Janelas com variação de temperatura fraca são pouco
            // informativas: a mediana das inclinações de pares fica ruidosa.
            // Para spans acima do limiar usa-se Theil–Sen; abaixo dele
            // (porém não degenerados) recai-se no coeficiente global —
            // estimado sobre o campo inteiro, muito mais amostras.
            T c_local;
            if (dtemp_range > T{1e-3}) {
                c_local = estimate_coefficient<T>(std::span<const T>(ds),
                                                  std::span<const T>(dt));
            } else {
                c_local = result.global_coefficient;
            }

            // if constexpr: a política de restrição é resolvida em tempo de
            // compilação; o ramo não selecionado nem é instanciado.
            if constexpr (CouplingPolicy<ConstrainCS>::constrain_cs) {
                if (c_local > T{}) {
                    c_local = T{};  // min(C, 0): desvia C espúrio para zero
                    result.constrained = true;
                }
            }

            // Acumula correção e coeficiente com sobreposição suave.
            for (std::size_t t = t0; t < t0 + win_t; ++t) {
                const T wt = detail::triangular_weight<T>(t - t0, win_t);
                for (std::size_t z = z0; z < z0 + win_z; ++z) {
                    const T wz = detail::triangular_weight<T>(z - z0, win_z);
                    // Fold expression: produto dos pesos t × z.
                    const T w = detail::overlap_weight_product<T>(wt, wz);
                    const std::size_t idx = t * n_z + z;
                    const T dtemp = temp[idx] - temp[z];
                    result.decoupled[idx] += w * (strain[idx] - c_local * dtemp);
                    result.coefficient_map[idx] += w * c_local;
                    weight_sum[idx] += static_cast<double>(w);
                }
            }
        }
    }

    // Normalização pela soma de pesos (média suave nas bordas).
    for (std::size_t i = 0; i < strain.size(); ++i) {
        if (weight_sum[i] > 0.0) {
            const T inv = static_cast<T>(1.0 / weight_sum[i]);
            result.decoupled[i] *= inv;
            result.coefficient_map[i] *= inv;
        }
    }

    return result;
}

} // namespace alakoro::decoupling
