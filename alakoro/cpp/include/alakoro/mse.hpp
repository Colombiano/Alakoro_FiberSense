/**
 * @file mse.hpp
 * @brief Núcleo C++20 do módulo MSE — Monitoramento da Saúde Estrutural.
 *
 * DFOS aplicado a edifícios antigos de alvenaria: penetração de ondas
 * térmicas harmônicas (método de Ångström), perfis de deformação por
 * abertura de fissuras, transientes de emissão acústica (AE) banda-limitados
 * e decaimento modal de torres de alvenaria.
 *
 * Structural Health Monitoring core for old masonry buildings: harmonic
 * thermal wave penetration (Ångström method), crack strain profiles with
 * gauge-length averaging, band-limited acoustic emission impulses and
 * damped structural modal ringing.
 *
 * Recursos C++20:
 *   - concepts (FloatingPoint)
 *   - traits em tempo de compilação (MaterialTraits<M>)
 *   - if constexpr (seleção por material e por harmônico)
 *   - fold expressions sobre blocos de fissuras (std::index_sequence)
 *   - move semantics explícito (solver move-only, noexcept)
 *   - std::span em toda a API pública
 *   - designated initializers no agregado Fissura<T>
 */

#pragma once

#include "alakoro/concepts.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <numbers>
#include <random>
#include <span>
#include <stdexcept>
#include <string_view>
#include <utility>
#include <vector>

namespace alakoro::mse {

/**
 * @brief Materiais de alvenaria típicos de edifícios antigos.
 *
 * Enum class forte: evita conversões implícitas e permite especialização
 * total de MaterialTraits<M> em tempo de compilação.
 */
enum class MaterialAlvenaria {
    Tijolo,     ///< Tijolo cerâmico/macliço (α = 5.0e-7 m²/s)
    Pedra,      ///< Alvenaria de pedra aparente (α = 1.2e-6 m²/s)
    Argamassa,  ///< Argamassa de cal/areia (α = 3.0e-7 m²/s)
    Concreto,   ///< Concreto simples/armado (α = 5.0e-6 m²/s)
};

/**
 * @brief Nome legível do material, resolvido em tempo de compilação.
 *
 * Exemplo de if constexpr: cada ramo descarta os demais na instanciação.
 * Compile-time material name lookup via if constexpr.
 */
template <MaterialAlvenaria M>
[[nodiscard]] constexpr std::string_view material_nome() noexcept {
    if constexpr (M == MaterialAlvenaria::Tijolo) {
        return "Tijolo";
    } else if constexpr (M == MaterialAlvenaria::Pedra) {
        return "Pedra";
    } else if constexpr (M == MaterialAlvenaria::Argamassa) {
        return "Argamassa";
    } else {
        static_assert(M == MaterialAlvenaria::Concreto, "material desconhecido");
        return "Concreto";
    }
}

/**
 * @brief Propriedades físicas do material em tempo de compilação.
 *
 * Traits clássicos: especializações completas fornecem constantes constexpr
 * sem custo em runtime. Valores típicos de literatura para alvenaria
 * (difusividade térmica α e coeficiente de dilatação linear).
 *
 * Compile-time traits: full specializations provide constexpr constants.
 * Typical literature values for masonry (thermal diffusivity α and
 * coefficient of linear thermal expansion).
 */
template <MaterialAlvenaria M>
struct MaterialTraits;

template <>
struct MaterialTraits<MaterialAlvenaria::Tijolo> {
    static constexpr double difusividade_m2_s   = 5.0e-7;   ///< α típico do tijolo [m²/s]
    static constexpr double coef_dilatacao_1_c  = 5.6e-6;   ///< dilatação linear [1/°C]
};

template <>
struct MaterialTraits<MaterialAlvenaria::Pedra> {
    static constexpr double difusividade_m2_s   = 1.2e-6;
    static constexpr double coef_dilatacao_1_c  = 6.5e-6;
};

template <>
struct MaterialTraits<MaterialAlvenaria::Argamassa> {
    static constexpr double difusividade_m2_s   = 3.0e-7;
    static constexpr double coef_dilatacao_1_c  = 4.5e-6;
};

template <>
struct MaterialTraits<MaterialAlvenaria::Concreto> {
    static constexpr double difusividade_m2_s   = 5.0e-6;
    static constexpr double coef_dilatacao_1_c  = 10.0e-6;
};

/**
 * @brief Profundidade de penetração térmica δ = sqrt(2α/ω) [m].
 *
 * ω = 2π/periodo_s. Para o ciclo diário (periodo_s = 86400 s) o tijolo tem
 * δ ≈ 0.117 m; para o ciclo anual (365.25 d) δ ≈ 2.24 m.
 *
 * Thermal penetration depth δ = sqrt(2α/ω), ω = 2π/periodo_s. Daily cycle
 * gives δ ≈ 0.117 m for brick; annual cycle δ ≈ 2.24 m.
 */
template <MaterialAlvenaria M>
[[nodiscard]] constexpr double penetracao_termica_m(double periodo_s) {
    if (!(periodo_s > 0.0)) {
        throw std::invalid_argument("penetracao_termica_m: periodo_s must be positive");
    }
    const double omega = 2.0 * std::numbers::pi_v<double> / periodo_s;
    return std::sqrt(2.0 * MaterialTraits<M>::difusividade_m2_s / omega);
}

/**
 * @brief Solver da onda térmica harmônica 1D (método de Ångström).
 *
 * Resolve a equação de calor 1D para oscilação harmônica superficial,
 * pré-computando caches de amplitude exp(−x/δ) e de fase temporal
 * x/(δω) para os harmônicos diário e anual:
 *
 *   T(t, x) = Σ_j A(t)·exp(−x/δ_j)·cos(ω_j·t − x/δ_j)
 *
 * Harmonic 1D heat equation solver (Ångström method). Precomputes
 * amplitude exp(−x/δ) and phase lag x/(δω) caches for the daily and
 * annual harmonics.
 *
 * Move-only de propósito: é um objeto pesado de configuração — cópias
 * duplicariam silenciosamente os caches, enquanto o move transfere a
 * propriedade explicitamente e barato (noexcept).
 * Move-only by design: heavy configuration object; copying would silently
 * duplicate caches, while moving transfers ownership cheaply (noexcept).
 */
template <MaterialAlvenaria M>
class ThermalWaveSolver {
public:
    static constexpr double kPeriodoDiarioS = 86400.0;            ///< ciclo diário [s]
    static constexpr double kPeriodoAnualS  = 365.25 * 86400.0;   ///< ciclo anual [s]

    /**
     * @brief Constrói o solver e pré-computa os caches harmônicos.
     *
     * @param profundidades_m Posições x (não negativas, em metros) onde a
     *                        temperatura será avaliada.
     */
    explicit ThermalWaveSolver(std::span<const double> profundidades_m)
        : profundidades_(profundidades_m.begin(), profundidades_m.end()),
          amp_diaria_(profundidades_m.size()),
          fase_diaria_s_(profundidades_m.size()),
          amp_anual_(profundidades_m.size()),
          fase_anual_s_(profundidades_m.size()) {
        if (profundidades_m.empty()) {
            throw std::invalid_argument("ThermalWaveSolver: profundidades_m must not be empty");
        }
        const double delta_d = penetracao_termica_m<M>(kPeriodoDiarioS);
        const double omega_d = 2.0 * std::numbers::pi_v<double> / kPeriodoDiarioS;
        const double delta_a = penetracao_termica_m<M>(kPeriodoAnualS);
        const double omega_a = 2.0 * std::numbers::pi_v<double> / kPeriodoAnualS;
        for (std::size_t z = 0; z < profundidades_m.size(); ++z) {
            const double x = profundidades_m[z];
            if (!std::isfinite(x) || x < 0.0) {
                throw std::invalid_argument("ThermalWaveSolver: profundidades_m must be finite and non-negative");
            }
            amp_diaria_[z]    = std::exp(-x / delta_d);
            fase_diaria_s_[z] = x / (delta_d * omega_d);
            amp_anual_[z]     = std::exp(-x / delta_a);
            fase_anual_s_[z]  = x / (delta_a * omega_a);
        }
    }

    // Move-only: transferência barata e explícita dos caches (sem cópia acidental).
    ThermalWaveSolver(ThermalWaveSolver&&) noexcept = default;
    ThermalWaveSolver& operator=(ThermalWaveSolver&&) noexcept = default;
    ThermalWaveSolver(const ThermalWaveSolver&) = delete;
    ThermalWaveSolver& operator=(const ThermalWaveSolver&) = delete;

    [[nodiscard]] std::size_t n_pos() const noexcept { return profundidades_.size(); }

    /**
     * @brief Preenche `saida` com T(t, x) (layout row-major: saida[t*n_pos + z]).
     *
     * Harmônico principal usa periodo_s (com cache quando coincide com o
     * ciclo diário canônico); o harmônico anual é opcional via if constexpr
     * no parâmetro de template. O mesmo vetor de amplitudes modula ambos.
     *
     * Fills `saida` with T(t, x), row-major layout saida[t*n_pos + z]. The
     * principal harmonic uses periodo_s (cached when it matches the canonical
     * daily cycle); the annual harmonic is compile-time optional. The same
     * amplitude series modulates both harmonics.
     *
     * @tparam IncluirAnual Acrescenta o harmônico anual em tempo de compilação.
     * @param tempos_s Amostras temporais [s].
     * @param amplitudes_superficiais_k Amplitude superficial A(t) [°C], mesmo tamanho de tempos_s.
     * @param saida Saída 2D flat (tempos × posições).
     * @param periodo_s Período do harmônico principal [s] (padrão físico: 86400 s).
     */
    template <bool IncluirAnual = false>
    void apply(std::span<const double> tempos_s,
               std::span<const double> amplitudes_superficiais_k,
               std::span<double> saida,
               double periodo_s) const {
        if (!(periodo_s > 0.0) || !std::isfinite(periodo_s)) {
            throw std::invalid_argument("ThermalWaveSolver::apply: periodo_s must be positive and finite");
        }
        if (tempos_s.empty()) {
            throw std::invalid_argument("ThermalWaveSolver::apply: tempos_s must not be empty");
        }
        if (tempos_s.size() != amplitudes_superficiais_k.size()) {
            throw std::invalid_argument("ThermalWaveSolver::apply: tempos_s and amplitudes_superficiais_k sizes differ");
        }
        if (saida.size() != tempos_s.size() * profundidades_.size()) {
            throw std::invalid_argument("ThermalWaveSolver::apply: saida size must be tempos_s.size() * n_pos");
        }

        const double omega = 2.0 * std::numbers::pi_v<double> / periodo_s;
        const bool usa_cache = std::abs(periodo_s - kPeriodoDiarioS) < 1.0e-9;
        // Fora do ciclo canônico o cache não é válido: recalcula δ/ω do período pedido.
        const double delta = usa_cache ? 0.0 : penetracao_termica_m<M>(periodo_s);

        const std::size_t n_pos = profundidades_.size();
        for (std::size_t t = 0; t < tempos_s.size(); ++t) {
            const double a_t = amplitudes_superficiais_k[t];
            for (std::size_t z = 0; z < n_pos; ++z) {
                double amp;
                double fase_s;
                if (usa_cache) {
                    amp = amp_diaria_[z];
                    fase_s = fase_diaria_s_[z];
                } else {
                    const double x = profundidades_[z];
                    amp = std::exp(-x / delta);
                    fase_s = x / (delta * omega);
                }
                double valor = a_t * amp * std::cos(omega * (tempos_s[t] - fase_s));
                if constexpr (IncluirAnual) {
                    const double omega_a = 2.0 * std::numbers::pi_v<double> / kPeriodoAnualS;
                    valor += a_t * amp_anual_[z] * std::cos(omega_a * (tempos_s[t] - fase_anual_s_[z]));
                }
                saida[t * n_pos + z] = valor;
            }
        }
    }

private:
    std::vector<double> profundidades_;   ///< Posições de avaliação [m]
    std::vector<double> amp_diaria_;      ///< Cache exp(−x/δ_d)
    std::vector<double> fase_diaria_s_;   ///< Cache x/(δ_d·ω_d) [s]
    std::vector<double> amp_anual_;       ///< Cache exp(−x/δ_a)
    std::vector<double> fase_anual_s_;    ///< Cache x/(δ_a·ω_a) [s]
};

/**
 * @brief Fissura interna: centro e base triangular (largura = 2·resolução).
 *
 * Aggregate C++20 — permite designated initializers na construção.
 */
template <FloatingPoint T>
struct Fissura {
    T posicao;  ///< Centro da fissura ao longo do cabo [m]
    T largura;  ///< Base total do triângulo (2× resolução espacial) [m]
};

namespace detail {

/**
 * @brief Triângulo unitário: 1 no centro, 0 em |x−centro| ≥ largura/2.
 */
template <FloatingPoint T>
[[nodiscard]] constexpr T triangulo(T x, T centro, T largura) noexcept {
    if (!(largura > T{})) {
        return T{};
    }
    const T meia = largura * T{0.5};
    const T d = std::abs(x - centro);
    if (d >= meia) {
        return T{};
    }
    return T{1} - d / meia;
}

/**
 * @brief Soma das contribuições triangulares de um bloco de fissuras.
 *
 * Fold expression sobre o pacote de índices: desenrola em tempo de
 * compilação a soma Σ_k peso_k·triângulo(x; f_k). Blocos com padding têm
 * largura/peso zero e contribuem nada.
 *
 * Fold expression over the index pack: compile-time unrolled sum of the
 * triangular crack contributions. Padded entries have zero width/weight.
 */
template <FloatingPoint T, std::size_t... Is>
[[nodiscard]] T soma_fissuras_no_ponto(std::index_sequence<Is...>,
                                       std::span<const Fissura<T>> bloco,
                                       std::span<const T> pesos,
                                       T x) {
    return ((triangulo(x, bloco[Is].posicao, bloco[Is].largura) * pesos[Is]) + ... + T{});
}

} // namespace detail

/**
 * @brief Perfil de deformação ε(x) por abertura de fissuras (DSS).
 *
 *   ε(x) = Σ_k (w_k/L_t)·triângulo(x; centro_k, largura = 2·resolução)
 *
 * As aberturas w_k chegam em mm e são convertidas para metros; L_t é o
 * comprimento de transferência (gauge) do interrogador. Ao final aplica-se
 * uma média-móvel de janela L_t/resolução (em amostras) modelando o gauge.
 *
 * Crack strain profile ε(x) = Σ_k (w_k/L_t)·triangle(x; center_k, 2·SR),
 * followed by a gauge-length moving average (window = L_t/SR samples).
 *
 * @tparam T Tipo de ponto flutuante.
 * @param posicoes_m Posições de avaliação ao longo do cabo [m].
 * @param posicoes_fissura_m Centros das fissuras [m].
 * @param aberturas_mm Aberturas w_k [mm], mesmo tamanho de posicoes_fissura_m.
 * @param comprimento_transferencia_m Comprimento de transferência L_t [m] (> 0).
 * @param resolucao_espacial_m Resolução espacial SR [m] (> 0).
 * @return Vetor ε(x) com média-móvel de gauge aplicada.
 */
template <FloatingPoint T>
[[nodiscard]] std::vector<T> perfil_deformacao_fissura(std::span<const T> posicoes_m,
                                                       std::span<const T> posicoes_fissura_m,
                                                       std::span<const T> aberturas_mm,
                                                       T comprimento_transferencia_m,
                                                       T resolucao_espacial_m) {
    if (posicoes_m.empty()) {
        throw std::invalid_argument("perfil_deformacao_fissura: posicoes_m must not be empty");
    }
    if (posicoes_fissura_m.size() != aberturas_mm.size()) {
        throw std::invalid_argument("perfil_deformacao_fissura: posicoes_fissura_m and aberturas_mm sizes differ");
    }
    if (!(comprimento_transferencia_m > T{})) {
        throw std::invalid_argument("perfil_deformacao_fissura: comprimento_transferencia_m must be positive");
    }
    if (!(resolucao_espacial_m > T{})) {
        throw std::invalid_argument("perfil_deformacao_fissura: resolucao_espacial_m must be positive");
    }
    for (const T w : aberturas_mm) {
        if (!(w >= T{})) {
            throw std::invalid_argument("perfil_deformacao_fissura: aberturas_mm must be non-negative");
        }
    }

    // Zip manual (C++20 não tem std::views::zip) + padding em blocos de kBloco
    // para o fold expression: fissuras-pad têm largura/peso zero.
    constexpr std::size_t kBloco = 8;
    const std::size_t n_fissuras = posicoes_fissura_m.size();
    const std::size_t n_blocos = (n_fissuras + kBloco - 1) / kBloco;

    std::vector<Fissura<T>> fissuras(n_blocos * kBloco, Fissura<T>{});
    std::vector<T> pesos(n_blocos * kBloco, T{});
    const T inv_lt = T{1} / comprimento_transferencia_m;
    for (std::size_t k = 0; k < n_fissuras; ++k) {
        fissuras[k] = Fissura<T>{.posicao = posicoes_fissura_m[k],
                                .largura = T{2} * resolucao_espacial_m};
        pesos[k] = aberturas_mm[k] * static_cast<T>(1.0e-3) * inv_lt;
    }

    std::vector<T> bruto(posicoes_m.size(), T{});
    for (std::size_t i = 0; i < posicoes_m.size(); ++i) {
        const T x = posicoes_m[i];
        T acc = T{};
        for (std::size_t b = 0; b < n_blocos; ++b) {
            const std::size_t off = b * kBloco;
            acc += detail::soma_fissuras_no_ponto(
                std::make_index_sequence<kBloco>{},
                std::span<const Fissura<T>>(fissuras.data() + off, kBloco),
                std::span<const T>(pesos.data() + off, kBloco),
                x);
        }
        bruto[i] = acc;
    }

    // Média-móvel do gauge: janela em amostras = L_t / resolução espacial.
    const auto janela = static_cast<std::size_t>(
        std::llround(comprimento_transferencia_m / resolucao_espacial_m));
    const std::size_t w = janela < 1 ? 1 : janela;
    if (w == 1) {
        return bruto;
    }
    const std::size_t meia = w / 2;
    std::vector<T> suavizado(posicoes_m.size(), T{});
    for (std::size_t i = 0; i < posicoes_m.size(); ++i) {
        const std::size_t lo = (i > meia) ? i - meia : 0;
        const std::size_t hi = (i + meia + 1 < posicoes_m.size()) ? i + meia + 1 : posicoes_m.size();
        T soma = T{};
        for (std::size_t j = lo; j < hi; ++j) {
            soma += bruto[j];
        }
        suavizado[i] = soma / static_cast<T>(hi - lo);
    }
    return suavizado;
}

/**
 * @brief Impulso de emissão acústica banda-limitado com degrau permanente.
 *
 * Transiente na faixa [f0, f1] construído como soma de tons ortogonais
 * (espaçados de 1/duracao_s) com fases aleatórias determinísticas:
 *
 *   s(t) = A·env(t)·(1/√K)·Σ_k sin(2π f_k t + φ_k),  φ_k ~ U(0, 2π) com mt19937_64(seed)
 *
 * Envelope: subida linear em 5% da duração (< 10%) e decaimento
 * exponencial e^−4 até o fim do evento. Após o evento o sinal permanece
 * em amplitude_ue·kFatorDegrau (offset permanente de abertura da fissura).
 *
 * Band-limited AE impulse (orthogonal tones with deterministic random
 * phases, mt19937_64(seed)), fast rise (<10% of duration) + exponential
 * decay, followed by a permanent crack-opening step of
 * amplitude_ue·kFatorDegrau (kFatorDegrau = 0.1).
 *
 * @param n_amostras Comprimento total do registro [amostras].
 * @param fs_hz Taxa de amostragem [Hz].
 * @param f0_hz Frequência inferior da faixa [Hz] (> 0, < f1).
 * @param f1_hz Frequência superior da faixa [Hz] (< Nyquist).
 * @param duracao_s Duração do evento [s] (> 0).
 * @param amplitude_ue Amplitude de pico do evento [µε].
 * @param seed Semente do gerador (determinismo).
 * @return Registro com evento + degrau permanente.
 */
[[nodiscard]] inline std::vector<double> impulso_ae(std::size_t n_amostras,
                                                    double fs_hz,
                                                    double f0_hz,
                                                    double f1_hz,
                                                    double duracao_s,
                                                    double amplitude_ue,
                                                    std::uint64_t seed) {
    if (n_amostras == 0) {
        throw std::invalid_argument("impulso_ae: n_amostras must be positive");
    }
    if (!(fs_hz > 0.0) || !std::isfinite(fs_hz)) {
        throw std::invalid_argument("impulso_ae: fs_hz must be positive and finite");
    }
    if (!(duracao_s > 0.0) || !std::isfinite(duracao_s)) {
        throw std::invalid_argument("impulso_ae: duracao_s must be positive and finite");
    }
    if (!(0.0 < f0_hz && f0_hz < f1_hz)) {
        throw std::invalid_argument("impulso_ae: require 0 < f0_hz < f1_hz");
    }
    if (!(f1_hz < 0.5 * fs_hz)) {
        throw std::invalid_argument("impulso_ae: f1_hz must be below the Nyquist frequency (fs_hz/2)");
    }

    constexpr double kFatorDegrau   = 0.1;    ///< degrau pós-evento = 10% da amplitude
    constexpr double kFracaoSubida  = 0.05;   ///< subida em 5% da duração (< 10%)

    std::mt19937_64 rng(seed);
    std::uniform_real_distribution<double> fase(0.0, 2.0 * std::numbers::pi_v<double>);

    // Tons ortogonais espaçados de 1/duracao na faixa [f0, f1].
    std::vector<double> frequencias;
    std::vector<double> fases;
    const double df = 1.0 / duracao_s;
    for (double f = f0_hz; f <= f1_hz + 1.0e-9; f += df) {
        frequencias.push_back(f);
        fases.push_back(fase(rng));
    }
    const double norma = 1.0 / std::sqrt(static_cast<double>(frequencias.size()));

    std::vector<double> s(n_amostras, 0.0);
    const std::size_t n_evento = std::min(
        n_amostras,
        static_cast<std::size_t>(std::llround(duracao_s * fs_hz)));
    const double t_subida = kFracaoSubida * duracao_s;
    const double tau = (duracao_s - t_subida) / 4.0;  // envelope cai a e^−4 no fim
    for (std::size_t n = 0; n < n_evento; ++n) {
        const double t = static_cast<double>(n) / fs_hz;
        const double env = (t < t_subida) ? (t / t_subida)
                                          : std::exp(-(t - t_subida) / tau);
        double soma = 0.0;
        for (std::size_t k = 0; k < frequencias.size(); ++k) {
            soma += std::sin(2.0 * std::numbers::pi_v<double> * frequencias[k] * t + fases[k]);
        }
        s[n] = amplitude_ue * env * norma * soma;
    }

    // Degrau permanente: offset de abertura da fissura após o evento.
    const double nivel = amplitude_ue * kFatorDegrau;
    std::fill(s.begin() + static_cast<std::ptrdiff_t>(n_evento), s.end(), nivel);
    return s;
}

/**
 * @brief Sinusoide amortecida pós-evento (ringing modal 1–5 Hz).
 *
 * Modela o decaimento dos modos estruturais de torres de alvenaria após
 * um evento (abertura de fissura, impacto):
 *
 *   x(t) = A·exp(−ζ·ω_n·t)·cos(ω_d·t),  ω_d = ω_n·sqrt(1 − ζ²)
 *
 * Damped modal ringing after a structural event, typical of masonry
 * towers: x(t) = A·exp(−ζ·ω_n·t)·cos(ω_d·t).
 *
 * @param n_amostras Comprimento do registro [amostras].
 * @param fs_hz Taxa de amostragem [Hz].
 * @param frequencia_hz Frequência natural f_n [Hz] (> 0, < Nyquist).
 * @param amortecimento Razão de amortecimento ζ [0, 1).
 * @param amplitude Amplitude inicial A.
 * @return Registro do decaimento modal.
 */
[[nodiscard]] inline std::vector<double> decaimento_modal(std::size_t n_amostras,
                                                          double fs_hz,
                                                          double frequencia_hz,
                                                          double amortecimento,
                                                          double amplitude) {
    if (n_amostras == 0) {
        throw std::invalid_argument("decaimento_modal: n_amostras must be positive");
    }
    if (!(fs_hz > 0.0) || !std::isfinite(fs_hz)) {
        throw std::invalid_argument("decaimento_modal: fs_hz must be positive and finite");
    }
    if (!(frequencia_hz > 0.0) || !(frequencia_hz < 0.5 * fs_hz)) {
        throw std::invalid_argument("decaimento_modal: frequencia_hz must be in (0, fs_hz/2)");
    }
    if (!(amortecimento >= 0.0) || !(amortecimento < 1.0)) {
        throw std::invalid_argument("decaimento_modal: amortecimento must be in [0, 1)");
    }

    const double wn = 2.0 * std::numbers::pi_v<double> * frequencia_hz;
    const double sigma = amortecimento * wn;
    const double wd = wn * std::sqrt(1.0 - amortecimento * amortecimento);

    std::vector<double> x(n_amostras, 0.0);
    for (std::size_t n = 0; n < n_amostras; ++n) {
        const double t = static_cast<double>(n) / fs_hz;
        x[n] = amplitude * std::exp(-sigma * t) * std::cos(wd * t);
    }
    return x;
}

} // namespace alakoro::mse
