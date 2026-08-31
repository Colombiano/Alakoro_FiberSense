/**
 * @file inference_engine.hpp
 * @brief Motor de inferência C++20 com metaprogramação e corrotinas internas.
 *
 * Prova de conceito do InferenceEngine do Alakoro. O objetivo é demonstrar
 * como C++20 moderno (concepts, if constexpr, variadic templates, fold
 * expressions e corrotinas) pode ser usado para implementar regras de
 * inferência tipadas por evento, depois expostas ao Python via pybind11.
 *
 * Design:
 *   - Cada evento canônico é um valor de enum (CanonicalEvent).
 *   - EventTraits<E> fornece nome, rótulos PT/EN e recomendação em tempo de
 *     compilação (constexpr std::string_view).
 *   - Cada regra é uma corrotina que produz InferenceResult via co_yield,
 *     permitindo pausar/resumir o processamento internamente.
 *   - A engine é um template variádico InferenceEngine<Events...> que, em
 *     tempo de compilação, registra quais regras executar. Usamos fold
 *     expressions para percorrer todas as regras.
 *   - Do ponto de vista do Python, a API exposta é síncrona: a engine
 *     consome o generator C++ internamente e devolve um vector de resultados.
 */

#pragma once

#include "alakoro/concepts.hpp"
#include "alakoro/core.hpp"

#include <algorithm>
#include <cmath>
#include <concepts>
#include <coroutine>
#include <cstdint>
#include <limits>
#include <numeric>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace alakoro {
namespace inference {

/**
 * @brief Resultado de uma regra de inferência.
 *
 * Estrutura simples e POD-friendly para facilitar o binding com pybind11.
 */
struct InferenceResult {
    std::string event_type;      ///< Código do evento (ex: "joule_thomson")
    std::string event_label_pt;  ///< Rótulo em português
    std::string event_label_en;  ///< Rótulo em inglês
    double confidence = 0.0;     ///< Confiança entre 0.0 e 1.0
    double depth_md = 0.0;       ///< Profundidade estimada (m)
    std::string severity;        ///< "Low", "Medium", "High"
    std::string recommendation;  ///< Recomendação operacional
};

/**
 * @brief Os 15 eventos canônicos do Alakoro.
 *
 * Enum class forte evita conversões implícitas acidentais e permite switch
 * estático em templates.
 */
enum class CanonicalEvent : std::uint8_t {
    JouleThomson,
    SlopeVelocity,
    WarmBack,
    ValveChatter,
    SluggingCycle,
    LeakPath,
    GlvBellowRupture,
    PerforationEffectiveness,
    FracScreenout,
    FracProppantDistribution,
    FracHeightGrowth,
    CementBondEvaluation,
    ReCementingAssessment,
    CrossflowZonal,
    CementChanneling,
};

/**
 * @brief Metadados de aquisição necessários para as heurísticas.
 *
 * Usamos uma struct independente para não acoplar a engine a
 * AcquisitionMetadata do core.hpp, facilitando testes unitários.
 */
struct InferenceMetadata {
    double sampling_rate_hz = 0.0; ///< Taxa de amostragem no tempo (DAS/DTS)
    double depth_step_m = 1.0;     ///< Espaçamento entre canais/profundidades
    double surface_temp_c = 20.0;  ///< Temperatura superficial para baseline
    double geo_gradient_cpm = 0.03;///< Gradiente geotérmico (°C/m)
};

// =============================================================================
// Metaprogramação: traits por evento
// =============================================================================

/**
 * @brief Traits padrão para cada evento canônico.
 *
 * Especializações explícitas abaixo. Usar constexpr std::string_view permite
 * que esses valores sejam resolvidos em tempo de compilação.
 */
template <CanonicalEvent E>
struct EventTraits {
    static constexpr std::string_view code = "unknown";
    static constexpr std::string_view label_pt = "Desconhecido";
    static constexpr std::string_view label_en = "Unknown";
    static constexpr std::string_view recommendation = "Investigar manualmente.";
};

#define ALAKORO_EVENT_TRAITS(EVENT, CODE, PT, EN, RECO) \
    template <>                                          \
    struct EventTraits<CanonicalEvent::EVENT> {          \
        static constexpr std::string_view code = CODE;   \
        static constexpr std::string_view label_pt = PT; \
        static constexpr std::string_view label_en = EN; \
        static constexpr std::string_view recommendation = RECO; \
    }

ALAKORO_EVENT_TRAITS(JouleThomson,
    "joule_thomson",
    "Dipolo Térmico Joule-Thomson",
    "Joule-Thomson Thermal Dipole",
    "Verificar passagem de gas/líquido na interface e validar PVT local.");

ALAKORO_EVENT_TRAITS(SlopeVelocity,
    "slope_velocity",
    "Rastreamento de Inclinação (Velocidade)",
    "Slope Tracking (Velocity)",
    "Acompanhar fronte móvel para estimativa de velocidade de escoamento.");

ALAKORO_EVENT_TRAITS(WarmBack,
    "warm_back",
    "Recuperação Térmica (Warm-Back)",
    "Thermal Recovery (Warm-Back)",
    "Identificar zonas de injeção e acompanhar recuperação térmica.");

ALAKORO_EVENT_TRAITS(ValveChatter,
    "valve_chatter",
    "Chatter/Multipointing de Válvula",
    "Valve Chatter/Multipointing",
    "Inspecionar válvula de gás-lift e ajustar frequência de operação.");

ALAKORO_EVENT_TRAITS(SluggingCycle,
    "slugging_cycle",
    "Ciclo de Slugging",
    "Slugging Cycle",
    "Avaliar separador e controle de produção para mitigar slugging.");

ALAKORO_EVENT_TRAITS(LeakPath,
    "leak_path",
    "Caminho de Vazamento Tubing-Ânulo",
    "Leak Path Tubing-Annulus",
    "Verificar integridade de tubos e vedacao do ânulo.");

ALAKORO_EVENT_TRAITS(GlvBellowRupture,
    "glv_bellow_rupture",
    "Fole Furado de Válvula de Gás Lift",
    "Gas Lift Valve Bellow Rupture",
    "Substituir ou reparar o GLV com fole comprometido.");

ALAKORO_EVENT_TRAITS(PerforationEffectiveness,
    "perforation_effectiveness",
    "Efetividade de Canhoneio",
    "Perforation Effectiveness",
    "Comparar resfriamento entre intervalos perfurados.");

ALAKORO_EVENT_TRAITS(FracScreenout,
    "frac_screenout",
    "Embuchamento de Fratura (Screen-out)",
    "Fracture Screen-out",
    "Monitorar pressão de superfície e considerar flush.");

ALAKORO_EVENT_TRAITS(FracProppantDistribution,
    "frac_proppant_distribution",
    "Distribuição de Propante",
    "Proppant Distribution",
    "Avaliar distribuição vertical de propante e ajustar estágios.");

ALAKORO_EVENT_TRAITS(FracHeightGrowth,
    "frac_height_growth",
    "Crescimento de Altura de Fratura",
    "Fracture Height Growth",
    "Verificar barreiras geomecânicas e altura efetiva da fratura.");

ALAKORO_EVENT_TRAITS(CementBondEvaluation,
    "cement_bond_evaluation",
    "Avaliação de Cimentação (CBL/VDL)",
    "Cement Bond Evaluation (CBL/VDL)",
    "Correlacionar com log CBL/VDL para mapear qualidade do cimento.");

ALAKORO_EVENT_TRAITS(ReCementingAssessment,
    "re_cementing_assessment",
    "Avaliação de Recimentação",
    "Re-Cementing Assessment",
    "Validar efetividade do squeeze e comparar com cimentação original.");

ALAKORO_EVENT_TRAITS(CrossflowZonal,
    "crossflow_zonal",
    "Fluxo Cruzado Zonal",
    "Zonal Crossflow",
    "Investigar comunicação entre zonas e possíveis falhas de isolamento.");

ALAKORO_EVENT_TRAITS(CementChanneling,
    "cement_channeling",
    "Canalização de Cimento",
    "Cement Channeling",
    "Avaliar necessidade de squeeze para eliminar canais no cimento.");

#undef ALAKORO_EVENT_TRAITS

// =============================================================================
// Corrotinas C++20 internas
// =============================================================================

/**
 * @brief Generator simples que produz InferenceResult via co_yield.
 *
 * Em vez de retornar um vector enorme de uma só vez, cada regra pode pausar
 * após processar um canal ou uma etapa. Isso demonstra o uso de corrotinas
 * sem expor complexidade ao Python.
 *
 * Implementação mínima de generator sem dependências externas.
 */
struct ResultGenerator {
    struct promise_type {
        InferenceResult current_value;

        ResultGenerator get_return_object() {
            return ResultGenerator{std::coroutine_handle<promise_type>::from_promise(*this)};
        }

        std::suspend_always initial_suspend() noexcept { return {}; }
        std::suspend_always final_suspend() noexcept { return {}; }
        void unhandled_exception() { std::terminate(); }
        void return_void() noexcept {}

        std::suspend_always yield_value(InferenceResult value) noexcept {
            current_value = std::move(value);
            return {};
        }
    };

    using handle_type = std::coroutine_handle<promise_type>;

    explicit ResultGenerator(handle_type h) : handle_(h) {}

    // Não copiável: coroutine_handle é um recurso único.
    ResultGenerator(const ResultGenerator&) = delete;
    ResultGenerator& operator=(const ResultGenerator&) = delete;

    ResultGenerator(ResultGenerator&& other) noexcept : handle_(other.handle_) {
        other.handle_ = nullptr;
    }

    ResultGenerator& operator=(ResultGenerator&& other) noexcept {
        if (this != &other) {
            if (handle_) handle_.destroy();
            handle_ = other.handle_;
            other.handle_ = nullptr;
        }
        return *this;
    }

    ~ResultGenerator() {
        if (handle_) handle_.destroy();
    }

    bool done() const noexcept { return handle_.done(); }
    void resume() { if (handle_) handle_.resume(); }

    const InferenceResult& value() const noexcept {
        return handle_.promise().current_value;
    }

private:
    handle_type handle_;
};

// =============================================================================
// Helpers numéricos
// =============================================================================

namespace detail {

/**
 * @brief Extrai o perfil médio no tempo (média sobre as amostras temporais).
 */
inline std::vector<double> temporal_mean(std::span<const double> data,
                                          std::size_t n_times,
                                          std::size_t n_channels) {
    std::vector<double> mean(n_channels, 0.0);
    if (n_times == 0 || n_channels == 0) return mean;
    for (std::size_t c = 0; c < n_channels; ++c) {
        double sum = 0.0;
        for (std::size_t t = 0; t < n_times; ++t) {
            sum += data[t * n_channels + c];
        }
        mean[c] = sum / static_cast<double>(n_times);
    }
    return mean;
}

/**
 * @brief Subtrai baseline geotérmico linear.
 */
inline std::vector<double> remove_geobaseline(const std::vector<double>& profile,
                                               double depth_step_m,
                                               double surface_temp_c,
                                               double geo_gradient_cpm) {
    std::vector<double> anomaly(profile.size());
    for (std::size_t i = 0; i < profile.size(); ++i) {
        double depth = static_cast<double>(i) * depth_step_m;
        double baseline = surface_temp_c + geo_gradient_cpm * depth;
        anomaly[i] = profile[i] - baseline;
    }
    return anomaly;
}

/**
 * @brief Subtrai baseline local ajustado pelas bordas do perfil.
 *
 * Útil quando o gradiente geotérmico global não se ajusta bem devido a
 * offset ou ruído. Ajusta uma reta usando médias das bordas (10% iniciais
 * e 10% finais) e subtrai do perfil inteiro.
 */
inline std::vector<double> remove_edge_baseline(const std::vector<double>& profile) {
    if (profile.size() < 10) return profile;
    std::size_t edge = profile.size() / 10;
    if (edge < 2) edge = 2;

    double mean_start = std::accumulate(profile.begin(), profile.begin() + edge, 0.0) /
                        static_cast<double>(edge);
    double mean_end = std::accumulate(profile.end() - edge, profile.end(), 0.0) /
                      static_cast<double>(edge);

    double slope = (mean_end - mean_start) / static_cast<double>(profile.size() - 1);
    std::vector<double> anomaly(profile.size());
    for (std::size_t i = 0; i < profile.size(); ++i) {
        double baseline = mean_start + slope * static_cast<double>(i);
        anomaly[i] = profile[i] - baseline;
    }
    return anomaly;
}

/**
 * @brief Ajusta um polinômio de grau N por mínimos quadrados e retorna
 *        o perfil com baseline subtraído.
 *
 * Usamos o método dos mínimos quadrados lineares via sistema normal.
 * Grau 2 ou 3 é suficiente para capturar tendências geotérmicas não-lineares
 * sem absorver anomalias localizadas de interesse.
 */
inline std::vector<double> remove_polynomial_baseline(const std::vector<double>& profile,
                                                       std::size_t degree = 2) {
    if (profile.size() < degree + 2) return profile;
    const std::size_t n = profile.size();
    const std::size_t m = degree + 1;

    // Monta A^T A e A^T b para o sistema normal.
    std::vector<std::vector<double>> ata(m, std::vector<double>(m, 0.0));
    std::vector<double> atb(m, 0.0);

    for (std::size_t i = 0; i < n; ++i) {
        double x = static_cast<double>(i) / static_cast<double>(n - 1); // normalizado [0,1]
        double power = 1.0;
        std::vector<double> row(m, 1.0);
        for (std::size_t j = 1; j < m; ++j) {
            power *= x;
            row[j] = power;
        }
        for (std::size_t j = 0; j < m; ++j) {
            atb[j] += row[j] * profile[i];
            for (std::size_t k = 0; k < m; ++k) {
                ata[j][k] += row[j] * row[k];
            }
        }
    }

    // Resolução por eliminação de Gauss simples (sistema pequeno: grau <= 3).
    std::vector<double> coeffs(m, 0.0);
    std::vector<std::vector<double>> aug(m, std::vector<double>(m + 1));
    for (std::size_t i = 0; i < m; ++i) {
        for (std::size_t j = 0; j < m; ++j) aug[i][j] = ata[i][j];
        aug[i][m] = atb[i];
    }

    for (std::size_t col = 0; col < m; ++col) {
        // Pivoteamento parcial.
        std::size_t pivot = col;
        for (std::size_t row = col + 1; row < m; ++row) {
            if (std::abs(aug[row][col]) > std::abs(aug[pivot][col])) pivot = row;
        }
        std::swap(aug[col], aug[pivot]);
        if (std::abs(aug[col][col]) < 1e-12) continue;
        for (std::size_t row = col + 1; row < m; ++row) {
            double factor = aug[row][col] / aug[col][col];
            for (std::size_t j = col; j <= m; ++j) {
                aug[row][j] -= factor * aug[col][j];
            }
        }
    }

    for (int i = static_cast<int>(m) - 1; i >= 0; --i) {
        double sum = aug[i][m];
        for (std::size_t j = i + 1; j < m; ++j) {
            sum -= aug[i][j] * coeffs[j];
        }
        coeffs[i] = (std::abs(aug[i][i]) > 1e-12) ? sum / aug[i][i] : 0.0;
    }

    // Subtrai o polinômio ajustado.
    std::vector<double> anomaly(n);
    for (std::size_t i = 0; i < n; ++i) {
        double x = static_cast<double>(i) / static_cast<double>(n - 1);
        double baseline = 0.0;
        double power = 1.0;
        for (std::size_t j = 0; j < m; ++j) {
            baseline += coeffs[j] * power;
            power *= x;
        }
        anomaly[i] = profile[i] - baseline;
    }
    return anomaly;
}

/**
 * @brief Subtrai baseline de mediana móvel.
 *
 * A mediana é robusta a outliers, preservando anomalias localizadas.
 * A janela é simétrica; nas bordas, usa a mediana disponível.
 */
inline std::vector<double> remove_median_baseline(const std::vector<double>& profile,
                                                   std::size_t window = 51) {
    if (profile.size() < window) return profile;
    std::vector<double> baseline(profile.size());
    std::size_t half = window / 2;
    std::vector<double> window_vals;
    window_vals.reserve(window);

    for (std::size_t i = 0; i < profile.size(); ++i) {
        window_vals.clear();
        std::size_t start = (i > half) ? i - half : 0;
        std::size_t end = std::min(i + half + 1, profile.size());
        for (std::size_t j = start; j < end; ++j) {
            window_vals.push_back(profile[j]);
        }
        std::nth_element(window_vals.begin(),
                         window_vals.begin() + window_vals.size() / 2,
                         window_vals.end());
        baseline[i] = window_vals[window_vals.size() / 2];
    }

    std::vector<double> anomaly(profile.size());
    for (std::size_t i = 0; i < profile.size(); ++i) {
        anomaly[i] = profile[i] - baseline[i];
    }
    return anomaly;
}

/**
 * @brief Calcula o p-ésimo percentil de um vetor (0 <= p <= 100).
 *
 * Usa std::nth_element para eficiência O(N) em média.
 */
inline double percentile(const std::vector<double>& v, double p) {
    if (v.empty()) return 0.0;
    if (p <= 0.0) return *std::min_element(v.begin(), v.end());
    if (p >= 100.0) return *std::max_element(v.begin(), v.end());
    std::vector<double> copy(v);
    std::size_t idx = static_cast<std::size_t>(p / 100.0 * static_cast<double>(copy.size() - 1));
    std::nth_element(copy.begin(), copy.begin() + idx, copy.end());
    return copy[idx];
}

/**
 * @brief Mediana absoluta dos desvios (MAD), estimativa robusta de dispersão.
 */
inline double mad(const std::vector<double>& v) {
    if (v.empty()) return 0.0;
    double med = percentile(v, 50.0);
    std::vector<double> abs_dev;
    abs_dev.reserve(v.size());
    for (double x : v) abs_dev.push_back(std::abs(x - med));
    return percentile(abs_dev, 50.0);
}

/**
 * @brief Amplitude interquartil (IQR).
 */
inline double iqr(const std::vector<double>& v) {
    return percentile(v, 75.0) - percentile(v, 25.0);
}

/**
 * @brief Threshold adaptativo robusto.
 *
 * Usa MAD ou IQR para definir um threshold que não depende de hipóteses
 * gaussianas. O fator k controla a sensibilidade (padrão 2.0).
 */
enum class AdaptiveMethod { Mad, Iqr };

inline double adaptive_threshold(const std::vector<double>& v,
                                  AdaptiveMethod method = AdaptiveMethod::Mad,
                                  double k = 2.0) {
    if (method == AdaptiveMethod::Iqr) {
        return k * iqr(v);
    }
    // MAD: fator de escala 1.4826 para consistência com desvio padrão gaussiano.
    return k * 1.4826 * mad(v);
}

/**
 * @brief Encontra índices de picos locais com amplitude mínima.
 */
inline std::vector<std::size_t> find_peaks(const std::vector<double>& signal,
                                            double min_height,
                                            std::size_t min_distance = 1) {
    std::vector<std::size_t> peaks;
    if (signal.size() < 3) return peaks;
    for (std::size_t i = 1; i + 1 < signal.size(); ++i) {
        if (signal[i] > signal[i - 1] && signal[i] > signal[i + 1] &&
            std::abs(signal[i]) >= min_height) {
            peaks.push_back(i);
        }
    }
    // Aplica min_distance de forma simples (ordem crescente).
    if (min_distance > 1 && !peaks.empty()) {
        std::vector<std::size_t> filtered{peaks.front()};
        for (std::size_t i = 1; i < peaks.size(); ++i) {
            if (peaks[i] - filtered.back() >= min_distance) {
                filtered.push_back(peaks[i]);
            }
        }
        peaks = std::move(filtered);
    }
    return peaks;
}

/**
 * @brief Encontra índices de vales (mínimos locais) com amplitude mínima.
 */
inline std::vector<std::size_t> find_valleys(const std::vector<double>& signal,
                                              double min_depth,
                                              std::size_t min_distance = 1) {
    std::vector<std::size_t> valleys;
    if (signal.size() < 3) return valleys;
    for (std::size_t i = 1; i + 1 < signal.size(); ++i) {
        if (signal[i] < signal[i - 1] && signal[i] < signal[i + 1] &&
            std::abs(signal[i]) >= min_depth) {
            valleys.push_back(i);
        }
    }
    if (min_distance > 1 && !valleys.empty()) {
        std::vector<std::size_t> filtered{valleys.front()};
        for (std::size_t i = 1; i < valleys.size(); ++i) {
            if (valleys[i] - filtered.back() >= min_distance) {
                filtered.push_back(valleys[i]);
            }
        }
        valleys = std::move(filtered);
    }
    return valleys;
}

/**
 * @brief Calcula energia média do DAS ao longo do tempo para cada canal.
 */
inline std::vector<double> das_energy_profile(std::span<const double> data,
                                               std::size_t n_times,
                                               std::size_t n_channels) {
    std::vector<double> energy(n_channels, 0.0);
    if (n_times == 0 || n_channels == 0) return energy;
    for (std::size_t c = 0; c < n_channels; ++c) {
        double sum_sq = 0.0;
        for (std::size_t t = 0; t < n_times; ++t) {
            double v = data[t * n_channels + c];
            sum_sq += v * v;
        }
        energy[c] = sum_sq / static_cast<double>(n_times);
    }
    return energy;
}

/**
 * @brief Desvio padrão amostral.
 */
inline double std_dev(const std::vector<double>& v) {
    if (v.size() < 2) return 0.0;
    double mean = std::accumulate(v.begin(), v.end(), 0.0) / v.size();
    double sq = 0.0;
    for (double x : v) sq += (x - mean) * (x - mean);
    return std::sqrt(sq / static_cast<double>(v.size() - 1));
}

/**
 * @brief Converte índice de canal em profundidade MD.
 */
inline double channel_to_depth(std::size_t channel, double depth_step_m) {
    return static_cast<double>(channel) * depth_step_m;
}

} // namespace detail

// =============================================================================
// Regras de inferência tipadas por evento
// =============================================================================

/**
 * @brief Concept para uma regra de inferência válida.
 *
 * Requer uma função estática apply que recebe dados DTS/DAS + metadados e
 * retorna um ResultGenerator.
 */
template <typename R>
concept InferenceRule = requires(std::span<const double> dts,
                                  std::span<const double> das,
                                  std::size_t n_times,
                                  std::size_t n_channels,
                                  const InferenceMetadata& meta) {
    { R::apply(dts, das, n_times, n_channels, meta) } -> std::same_as<ResultGenerator>;
};

/**
 * @brief Cria um InferenceResult preenchido a partir dos traits de evento.
 */
template <CanonicalEvent E>
InferenceResult make_result(double confidence, double depth_md,
                            std::string_view severity) {
    return InferenceResult{
        std::string(EventTraits<E>::code),
        std::string(EventTraits<E>::label_pt),
        std::string(EventTraits<E>::label_en),
        confidence,
        depth_md,
        std::string(severity),
        std::string(EventTraits<E>::recommendation)
    };
}

/**
 * @brief Regra 1: Joule-Thomson.
 *
 * Heurística: detectar um dipolo térmico (região fria seguida de quente)
 * no perfil médio de temperatura após remoção da baseline geotérmica.
 */
struct JouleThomsonRule {
    static ResultGenerator apply(std::span<const double> dts,
                                 std::span<const double>,
                                 std::size_t n_times,
                                 std::size_t n_channels,
                                 const InferenceMetadata& meta) {
        auto mean_profile = detail::temporal_mean(dts, n_times, n_channels);
        // Baseline polinomial grau 2: mais robusto que reta geotérmica pura.
        auto anomaly = detail::remove_polynomial_baseline(mean_profile, 2);
        if (anomaly.size() < 20) co_return;

        double threshold = detail::adaptive_threshold(anomaly, detail::AdaptiveMethod::Mad, 1.5);

        // Janela deslizante: encontra o ponto de maior contraste entre
        // região anterior (espera-se fria) e posterior (espera-se quente).
        std::size_t window = anomaly.size() / 20;
        if (window < 5) window = 5;

        double best_score = 0.0;
        std::size_t best_idx = 0;
        for (std::size_t i = window; i + window < anomaly.size(); ++i) {
            double before = std::accumulate(anomaly.begin() + i - window,
                                            anomaly.begin() + i, 0.0) /
                            static_cast<double>(window);
            double after = std::accumulate(anomaly.begin() + i,
                                           anomaly.begin() + i + window, 0.0) /
                           static_cast<double>(window);
            double score = after - before;
            if (score > best_score) {
                best_score = score;
                best_idx = i;
            }
        }

        if (best_score > threshold) {
            double depth = detail::channel_to_depth(best_idx, meta.depth_step_m);
            double conf = std::min(best_score / (5.0 * threshold), 1.0);
            co_yield make_result<CanonicalEvent::JouleThomson>(
                conf, depth, conf > 0.7 ? "High" : (conf > 0.4 ? "Medium" : "Low"));
        }
        co_return;
    }
};

/**
 * @brief Regra 2: Slope Velocity.
 *
 * Heurística: detectar deslocamento de frente térmica comparando metades
 * temporais do perfil médio.
 */
struct SlopeVelocityRule {
    static ResultGenerator apply(std::span<const double> dts,
                                 std::span<const double>,
                                 std::size_t n_times,
                                 std::size_t n_channels,
                                 const InferenceMetadata& meta) {
        if (n_times < 10 || n_channels == 0) co_return;
        std::size_t mid_t = n_times / 2;

        auto first_half = detail::temporal_mean(dts.subspan(0, mid_t * n_channels),
                                                 mid_t, n_channels);
        auto second_half = detail::temporal_mean(
            dts.subspan(mid_t * n_channels, (n_times - mid_t) * n_channels),
            n_times - mid_t, n_channels);

        auto anom1 = detail::remove_polynomial_baseline(std::move(first_half), 2);
        auto anom2 = detail::remove_polynomial_baseline(std::move(second_half), 2);

        // Encontra o frente móvel pela máxima diferença de posição entre
        // o vale mais forte da primeira metade e o vale mais forte da segunda.
        std::size_t p1 = std::distance(anom1.begin(), std::min_element(anom1.begin(), anom1.end()));
        std::size_t p2 = std::distance(anom2.begin(), std::min_element(anom2.begin(), anom2.end()));

        double dz = std::abs(static_cast<double>(p2) - static_cast<double>(p1)) * meta.depth_step_m;
        double dt = (n_times > 1) ? static_cast<double>(n_times) / meta.sampling_rate_hz : 0.0;
        double velocity = (dt > 0.0) ? dz / dt : 0.0;
        double conf = std::min(dz / 100.0, 1.0);
        double depth = detail::channel_to_depth((p1 + p2) / 2, meta.depth_step_m);

        double threshold = detail::adaptive_threshold(anom2, detail::AdaptiveMethod::Mad, 1.5);
        double min2 = *std::min_element(anom2.begin(), anom2.end());
        if (conf > 0.15 && std::abs(min2) > threshold) {
            auto res = make_result<CanonicalEvent::SlopeVelocity>(
                conf, depth, conf > 0.7 ? "High" : "Medium");
            res.recommendation += " Velocidade estimada: " + std::to_string(velocity) + " m/s.";
            co_yield std::move(res);
        }
        co_return;
    }
};

/**
 * @brief Regra 3: Warm-Back.
 *
 * Heurística: múltiplos picos térmicos negativos (resfriamento por injeção)
 * seguidos de tendência de recuperação na segunda metade.
 */
struct WarmBackRule {
    static ResultGenerator apply(std::span<const double> dts,
                                 std::span<const double>,
                                 std::size_t n_times,
                                 std::size_t n_channels,
                                 const InferenceMetadata& meta) {
        auto mean_profile = detail::temporal_mean(dts, n_times, n_channels);
        auto anomaly = detail::remove_polynomial_baseline(std::move(mean_profile), 2);
        double threshold = detail::adaptive_threshold(anomaly, detail::AdaptiveMethod::Mad, 1.5);
        // Warm-back: múltiplos vales de resfriamento.
        auto valleys = detail::find_valleys(anomaly, threshold, 20);

        if (valleys.size() >= 2) {
            double mean_depth = 0.0;
            for (std::size_t p : valleys) mean_depth += detail::channel_to_depth(p, meta.depth_step_m);
            mean_depth /= static_cast<double>(valleys.size());
            double conf = std::min(static_cast<double>(valleys.size()) / 5.0, 1.0);
            co_yield make_result<CanonicalEvent::WarmBack>(
                conf, mean_depth, conf > 0.7 ? "High" : "Medium");
        }
        co_return;
    }
};

/**
 * @brief Regra 4: Valve Chatter.
 *
 * Heurística: pico de energia DAS localizado e oscilatório. Como o DAS
 * sintético pode ter amplitude baixa, usamos também anomalia térmica
 * localizada (DTS) como evidência secundária.
 */
struct ValveChatterRule {
    static ResultGenerator apply(std::span<const double> dts,
                                 std::span<const double> das,
                                 std::size_t n_times,
                                 std::size_t n_channels,
                                 const InferenceMetadata& meta) {
        if (n_channels == 0 || n_times == 0) co_return;

        double best_conf = 0.0;
        std::size_t best_idx = 0;

        // Evidência DAS: energia localizada.
        if (!das.empty()) {
            auto energy = detail::das_energy_profile(das, n_times, n_channels);
            double max_e = *std::max_element(energy.begin(), energy.end());
            for (std::size_t i = 0; i < n_channels; ++i) {
                double conf = std::min(energy[i] / (max_e + 1e-12), 1.0);
                if (conf > best_conf) {
                    best_conf = conf;
                    best_idx = i;
                }
            }
        }

        // Evidência DTS: pico térmico localizado.
        auto mean_profile = detail::temporal_mean(dts, n_times, n_channels);
        auto anomaly = detail::remove_polynomial_baseline(std::move(mean_profile), 2);
        double threshold = detail::adaptive_threshold(anomaly, detail::AdaptiveMethod::Mad, 1.5);
        auto thermal_peaks = detail::find_peaks(anomaly, threshold, 5);
        for (std::size_t p : thermal_peaks) {
            double conf = std::min(std::abs(anomaly[p]) / std::max(threshold, 0.1), 1.0);
            if (conf > best_conf) {
                best_conf = conf;
                best_idx = p;
            }
        }

        if (best_conf > 0.25) {
            co_yield make_result<CanonicalEvent::ValveChatter>(
                best_conf, detail::channel_to_depth(best_idx, meta.depth_step_m),
                best_conf > 0.7 ? "High" : "Medium");
        }
        co_return;
    }
};

/**
 * @brief Regra 5: Slugging Cycle.
 *
 * Heurística: alta variância espacial de energia DAS em intervalo profundo.
 * Como o DAS sintético pode ser fraco, também usamos oscilação térmica (DTS)
 * como evidência secundária.
 */
struct SluggingCycleRule {
    static ResultGenerator apply(std::span<const double> dts,
                                 std::span<const double> das,
                                 std::size_t n_times,
                                 std::size_t n_channels,
                                 const InferenceMetadata& meta) {
        if (n_channels == 0 || n_times < 4) co_return;

        double best_conf = 0.0;
        std::size_t best_idx = 0;

        // Evidência DAS: coeficiente de variação da energia.
        if (!das.empty()) {
            auto energy = detail::das_energy_profile(das, n_times, n_channels);
            double mean_e = std::accumulate(energy.begin(), energy.end(), 0.0) / energy.size();
            double var = 0.0;
            for (double e : energy) var += (e - mean_e) * (e - mean_e);
            var /= static_cast<double>(energy.size());
            double coeff_var = (mean_e > 1e-12) ? std::sqrt(var) / mean_e : 0.0;
            if (coeff_var > best_conf) {
                best_conf = coeff_var;
                best_idx = std::distance(energy.begin(),
                                         std::max_element(energy.begin(), energy.end()));
            }
        }

        // Evidência DTS: desvio padrão temporal por canal (oscilação de temperatura).
        for (std::size_t c = 0; c < n_channels; ++c) {
            double sum = 0.0;
            double sum_sq = 0.0;
            for (std::size_t t = 0; t < n_times; ++t) {
                double v = dts[t * n_channels + c];
                sum += v;
                sum_sq += v * v;
            }
            double mean_c = sum / static_cast<double>(n_times);
            double var_c = sum_sq / static_cast<double>(n_times) - mean_c * mean_c;
            double std_c = std::sqrt(std::max(var_c, 0.0));
            if (std_c > best_conf) {
                best_conf = std_c;
                best_idx = c;
            }
        }

        // Normaliza pela escala de temperatura típica do poço (~10 °C).
        double conf = std::min(best_conf / 10.0, 1.0);
        if (conf > 0.3) {
            co_yield make_result<CanonicalEvent::SluggingCycle>(
                conf, detail::channel_to_depth(best_idx, meta.depth_step_m),
                conf > 0.7 ? "High" : "Medium");
        }
        co_return;
    }
};

/**
 * @brief Regra 6: Leak Path.
 *
 * Heurística: anomalia térmica positiva crescente e localizada.
 * Comparamos a segunda metade da aquisição com a primeira: regiões que
 * aqueceram consistentemente indicam vazamento.
 */
struct LeakPathRule {
    static ResultGenerator apply(std::span<const double> dts,
                                 std::span<const double>,
                                 std::size_t n_times,
                                 std::size_t n_channels,
                                 const InferenceMetadata& meta) {
        if (n_times < 10 || n_channels == 0) co_return;
        std::size_t mid_t = n_times / 2;
        auto first = detail::temporal_mean(dts.subspan(0, mid_t * n_channels), mid_t, n_channels);
        auto second = detail::temporal_mean(
            dts.subspan(mid_t * n_channels, (n_times - mid_t) * n_channels),
            n_times - mid_t, n_channels);
        auto second_anom = detail::remove_polynomial_baseline(std::move(second), 2);
        auto first_anom = detail::remove_polynomial_baseline(std::move(first), 2);
        for (std::size_t i = 0; i < n_channels; ++i) {
            second_anom[i] -= first_anom[i];
        }
        double threshold = detail::adaptive_threshold(second_anom, detail::AdaptiveMethod::Mad, 2.0);
        auto max_it = std::max_element(second_anom.begin(), second_anom.end());
        if (*max_it > threshold) {
            std::size_t p = std::distance(second_anom.begin(), max_it);
            double conf = std::min(*max_it / std::max(threshold, 0.1), 1.0);
            co_yield make_result<CanonicalEvent::LeakPath>(
                conf, detail::channel_to_depth(p, meta.depth_step_m),
                conf > 0.7 ? "High" : "Medium");
        }
        co_return;
    }
};

/**
 * @brief Regra 7: GLV Bellow Rupture.
 *
 * Heurística: múltiplos picos de energia DAS espaçados regularmente (válvulas),
 * com um deles apresentando queda relativa de energia.
 */
struct GlvBellowRuptureRule {
    static ResultGenerator apply(std::span<const double> dts,
                                 std::span<const double> das,
                                 std::size_t n_times,
                                 std::size_t n_channels,
                                 const InferenceMetadata& meta) {
        if (n_times == 0 || n_channels == 0) co_return;

        std::vector<std::size_t> peaks;

        // Evidência DAS: picos de energia espaçados regularmente.
        if (!das.empty()) {
            auto energy = detail::das_energy_profile(das, n_times, n_channels);
            double threshold = detail::percentile(energy, 75.0);
            peaks = detail::find_peaks(energy, threshold, 10);
        }

        // Fallback DTS: múltiplos picos térmicos espaçados regularmente.
        if (peaks.size() < 3) {
            auto mean_profile = detail::temporal_mean(dts, n_times, n_channels);
            auto anomaly = detail::remove_polynomial_baseline(std::move(mean_profile), 2);
            double threshold = detail::adaptive_threshold(anomaly, detail::AdaptiveMethod::Mad, 2.0);
            peaks = detail::find_peaks(anomaly, threshold, 10);
        }

        if (peaks.size() >= 3) {
            // Procura gap onde uma válvula deveria existir.
            std::vector<double> spacings;
            for (std::size_t i = 1; i < peaks.size(); ++i) {
                spacings.push_back(static_cast<double>(peaks[i] - peaks[i - 1]) * meta.depth_step_m);
            }
            double median_spacing = spacings[spacings.size() / 2];
            double rupture_depth = 0.0;
            for (std::size_t i = 1; i < peaks.size(); ++i) {
                if (spacings[i - 1] > 1.5 * median_spacing) {
                    rupture_depth = detail::channel_to_depth(peaks[i - 1], meta.depth_step_m) +
                                    median_spacing;
                    break;
                }
            }
            double conf = std::min(static_cast<double>(peaks.size()) / 8.0, 1.0);
            if (rupture_depth > 0.0) {
                co_yield make_result<CanonicalEvent::GlvBellowRupture>(
                    conf, rupture_depth, conf > 0.6 ? "High" : "Medium");
            }
        }
        co_return;
    }
};

/**
 * @brief Regra 8: Perforation Effectiveness.
 *
 * Heurística: regiões com anomalia térmica negativa acentuada e extensa.
 */
struct PerforationEffectivenessRule {
    static ResultGenerator apply(std::span<const double> dts,
                                 std::span<const double>,
                                 std::size_t n_times,
                                 std::size_t n_channels,
                                 const InferenceMetadata& meta) {
        auto mean_profile = detail::temporal_mean(dts, n_times, n_channels);
        auto anomaly = detail::remove_polynomial_baseline(std::move(mean_profile), 2);
        double threshold = detail::adaptive_threshold(anomaly, detail::AdaptiveMethod::Mad, 2.0);
        std::vector<std::size_t> negative_zones;
        for (std::size_t i = 0; i < anomaly.size(); ++i) {
            if (std::abs(anomaly[i]) > threshold) negative_zones.push_back(i);
        }
        if (negative_zones.size() > 20) {
            double mean_depth = std::accumulate(negative_zones.begin(), negative_zones.end(), 0.0) /
                                static_cast<double>(negative_zones.size()) * meta.depth_step_m;
            double conf = std::min(static_cast<double>(negative_zones.size()) / 200.0, 1.0);
            co_yield make_result<CanonicalEvent::PerforationEffectiveness>(
                conf, mean_depth, conf > 0.7 ? "High" : "Medium");
        }
        co_return;
    }
};

/**
 * @brief Regra 9: Frac Screenout.
 *
 * Heurística: transição de anomalia negativa (injeção) para positiva
 * (aquecimento pós-screenout) na segunda metade temporal.
 */
struct FracScreenoutRule {
    static ResultGenerator apply(std::span<const double> dts,
                                 std::span<const double>,
                                 std::size_t n_times,
                                 std::size_t n_channels,
                                 const InferenceMetadata& meta) {
        if (n_times < 10 || n_channels == 0) co_return;
        std::size_t mid_t = n_times / 2;
        auto first = detail::temporal_mean(dts.subspan(0, mid_t * n_channels), mid_t, n_channels);
        auto second = detail::temporal_mean(
            dts.subspan(mid_t * n_channels, (n_times - mid_t) * n_channels),
            n_times - mid_t, n_channels);
        auto anom1 = detail::remove_polynomial_baseline(std::move(first), 2);
        auto anom2 = detail::remove_polynomial_baseline(std::move(second), 2);

        double threshold = detail::adaptive_threshold(anom2, detail::AdaptiveMethod::Mad, 1.5);
        double min1 = *std::min_element(anom1.begin(), anom1.end());
        double max2 = *std::max_element(anom2.begin(), anom2.end());
        if (min1 < -threshold && max2 > threshold) {
            std::size_t p = std::distance(anom2.begin(), std::max_element(anom2.begin(), anom2.end()));
            double conf = std::min((std::abs(min1) + max2) / std::max(4.0 * threshold, 0.1), 1.0);
            co_yield make_result<CanonicalEvent::FracScreenout>(
                conf, detail::channel_to_depth(p, meta.depth_step_m),
                conf > 0.7 ? "High" : "Medium");
        }
        co_return;
    }
};

/**
 * @brief Regra 10: Frac Proppant Distribution.
 *
 * Heurística: múltiplos sub-intervalos com anomalias térmicas negativas
 * dentro de uma janela profunda.
 */
struct FracProppantDistributionRule {
    static ResultGenerator apply(std::span<const double> dts,
                                 std::span<const double>,
                                 std::size_t n_times,
                                 std::size_t n_channels,
                                 const InferenceMetadata& meta) {
        auto mean_profile = detail::temporal_mean(dts, n_times, n_channels);
        auto anomaly = detail::remove_polynomial_baseline(std::move(mean_profile), 2);
        double threshold = detail::adaptive_threshold(anomaly, detail::AdaptiveMethod::Mad, 1.5);
        auto peaks = detail::find_peaks(anomaly, threshold, 8);
        if (peaks.size() >= 2) {
            double mean_depth = 0.0;
            for (std::size_t p : peaks) mean_depth += detail::channel_to_depth(p, meta.depth_step_m);
            mean_depth /= static_cast<double>(peaks.size());
            double conf = std::min(static_cast<double>(peaks.size()) / 6.0, 1.0);
            co_yield make_result<CanonicalEvent::FracProppantDistribution>(
                conf, mean_depth, conf > 0.7 ? "High" : "Medium");
        }
        co_return;
    }
};

/**
 * @brief Regra 11: Frac Height Growth.
 *
 * Heurística: anomalia térmica vertical ampla (crescimento acima do target).
 */
struct FracHeightGrowthRule {
    static ResultGenerator apply(std::span<const double> dts,
                                 std::span<const double>,
                                 std::size_t n_times,
                                 std::size_t n_channels,
                                 const InferenceMetadata& meta) {
        auto mean_profile = detail::temporal_mean(dts, n_times, n_channels);
        auto anomaly = detail::remove_polynomial_baseline(std::move(mean_profile), 2);
        double threshold = detail::adaptive_threshold(anomaly, detail::AdaptiveMethod::Mad, 2.0);
        std::size_t first = n_channels, last = 0;
        for (std::size_t i = 0; i < anomaly.size(); ++i) {
            if (std::abs(anomaly[i]) > threshold) {
                first = std::min(first, i);
                last = std::max(last, i);
            }
        }
        if (first < last) {
            double height = static_cast<double>(last - first) * meta.depth_step_m;
            double conf = std::min(height / 100.0, 1.0);
            double mid = (static_cast<double>(first) + static_cast<double>(last)) * 0.5 * meta.depth_step_m;
            co_yield make_result<CanonicalEvent::FracHeightGrowth>(
                conf, mid, conf > 0.7 ? "High" : "Medium");
        }
        co_return;
    }
};

/**
 * @brief Regra 12: Cement Bond Evaluation.
 *
 * Heurística: alta variabilidade espacial do perfil médio de temperatura.
 */
struct CementBondEvaluationRule {
    static ResultGenerator apply(std::span<const double> dts,
                                 std::span<const double>,
                                 std::size_t n_times,
                                 std::size_t n_channels,
                                 const InferenceMetadata& meta) {
        auto mean_profile = detail::temporal_mean(dts, n_times, n_channels);
        // Mediana movel preserva melhor as anomalias localizadas do que
        // polinomio global para este evento.
        auto anomaly = detail::remove_median_baseline(mean_profile, 51);
        double dispersion = detail::std_dev(anomaly);
        double conf = std::min(dispersion / 3.0, 1.0);
        if (conf > 0.12) {
            co_yield make_result<CanonicalEvent::CementBondEvaluation>(
                conf, static_cast<double>(n_channels) * meta.depth_step_m * 0.5,
                conf > 0.7 ? "High" : "Medium");
        }
        co_return;
    }
};

/**
 * @brief Regra 13: Re-Cementing Assessment.
 *
 * Heurística: presença de anomalias negativas seguidas de estabilização.
 */
struct ReCementingAssessmentRule {
    static ResultGenerator apply(std::span<const double> dts,
                                 std::span<const double>,
                                 std::size_t n_times,
                                 std::size_t n_channels,
                                 const InferenceMetadata& meta) {
        if (n_times < 10 || n_channels == 0) co_return;
        std::size_t mid_t = n_times / 2;
        auto first = detail::temporal_mean(dts.subspan(0, mid_t * n_channels), mid_t, n_channels);
        auto second = detail::temporal_mean(
            dts.subspan(mid_t * n_channels, (n_times - mid_t) * n_channels),
            n_times - mid_t, n_channels);
        auto anom1 = detail::remove_polynomial_baseline(std::move(first), 2);
        auto anom2 = detail::remove_polynomial_baseline(std::move(second), 2);
        double threshold = detail::adaptive_threshold(anom2, detail::AdaptiveMethod::Mad, 1.5);
        double min1 = *std::min_element(anom1.begin(), anom1.end());
        double mean2 = std::accumulate(anom2.begin(), anom2.end(), 0.0) / anom2.size();
        if (min1 < -threshold && std::abs(mean2) < threshold) {
            std::size_t p = std::distance(anom1.begin(), std::min_element(anom1.begin(), anom1.end()));
            double conf = std::min(std::abs(min1) / std::max(4.0 * threshold, 0.1), 1.0);
            co_yield make_result<CanonicalEvent::ReCementingAssessment>(
                conf, detail::channel_to_depth(p, meta.depth_step_m),
                conf > 0.7 ? "High" : "Medium");
        }
        co_return;
    }
};

/**
 * @brief Regra 14: Crossflow Zonal.
 *
 * Heurística: múltiplos picos térmicos positivos e negativos alternados.
 */
struct CrossflowZonalRule {
    static ResultGenerator apply(std::span<const double> dts,
                                 std::span<const double>,
                                 std::size_t n_times,
                                 std::size_t n_channels,
                                 const InferenceMetadata& meta) {
        auto mean_profile = detail::temporal_mean(dts, n_times, n_channels);
        auto anomaly = detail::remove_polynomial_baseline(std::move(mean_profile), 2);
        double threshold = detail::adaptive_threshold(anomaly, detail::AdaptiveMethod::Mad, 1.5);
        auto pos_peaks = detail::find_peaks(anomaly, threshold, 15);
        auto neg_valleys = detail::find_valleys(anomaly, threshold, 15);
        if (pos_peaks.size() >= 2 && neg_valleys.size() >= 2) {
            double mean_depth = 0.0;
            for (std::size_t p : pos_peaks) mean_depth += detail::channel_to_depth(p, meta.depth_step_m);
            for (std::size_t p : neg_valleys) mean_depth += detail::channel_to_depth(p, meta.depth_step_m);
            mean_depth /= static_cast<double>(pos_peaks.size() + neg_valleys.size());
            double conf = std::min((pos_peaks.size() + neg_valleys.size()) / 8.0, 1.0);
            co_yield make_result<CanonicalEvent::CrossflowZonal>(
                conf, mean_depth, conf > 0.7 ? "High" : "Medium");
        }
        co_return;
    }
};

/**
 * @brief Regra 15: Cement Channeling.
 *
 * Heurística: canais estreitos e múltiplos no perfil de anomalia térmica.
 */
struct CementChannelingRule {
    static ResultGenerator apply(std::span<const double> dts,
                                 std::span<const double>,
                                 std::size_t n_times,
                                 std::size_t n_channels,
                                 const InferenceMetadata& meta) {
        auto mean_profile = detail::temporal_mean(dts, n_times, n_channels);
        auto anomaly = detail::remove_polynomial_baseline(std::move(mean_profile), 2);
        double threshold = detail::adaptive_threshold(anomaly, detail::AdaptiveMethod::Mad, 1.5);
        // Canalização aparece como múltiplos vales (resfriamento) estreitos.
        auto valleys = detail::find_valleys(anomaly, threshold, 5);
        if (valleys.size() >= 3) {
            double mean_depth = 0.0;
            for (std::size_t p : valleys) mean_depth += detail::channel_to_depth(p, meta.depth_step_m);
            mean_depth /= static_cast<double>(valleys.size());
            double conf = std::min(static_cast<double>(valleys.size()) / 8.0, 1.0);
            co_yield make_result<CanonicalEvent::CementChanneling>(
                conf, mean_depth, conf > 0.7 ? "High" : "Medium");
        }
        co_return;
    }
};

// =============================================================================
// Executor com metaprogramação variádica
// =============================================================================

/**
 * @brief Consome um ResultGenerator e acumula os resultados em um vector.
 *
 * Esta é a ponte entre a API corrotinada interna e a API síncrona exposta.
 */
inline std::vector<InferenceResult> collect_results(ResultGenerator gen) {
    std::vector<InferenceResult> results;
    results.reserve(4); // estimativa inicial; evita realocações para regras típicas
    while (!gen.done()) {
        gen.resume();
        if (!gen.done()) {
            results.push_back(std::move(gen.value()));
        }
    }
    return results;
}

/**
 * @brief Engine de inferência parametrizada por uma lista de eventos.
 *
 * Usa if constexpr para mapear cada evento para sua regra correspondente
 * e fold expressions para executar todas as regras.
 */
template <CanonicalEvent... Events>
class InferenceEngine {
public:
    static_assert(sizeof...(Events) > 0, "InferenceEngine precisa de pelo menos um evento.");

    /**
     * @brief Executa todas as regras registradas e retorna resultados agregados.
     */
    std::vector<InferenceResult> infer(std::span<const double> dts,
                                       std::span<const double> das,
                                       std::size_t n_times,
                                       std::size_t n_channels,
                                       const InferenceMetadata& meta) const {
        std::vector<InferenceResult> all;
        all.reserve(sizeof...(Events));
        // Fold expression sobre uma lambda que executa uma regra por evento.
        (execute_rule<Events>(dts, das, n_times, n_channels, meta, all), ...);
        return all;
    }

private:
    template <CanonicalEvent E>
    void execute_rule(std::span<const double> dts,
                      std::span<const double> das,
                      std::size_t n_times,
                      std::size_t n_channels,
                      const InferenceMetadata& meta,
                      std::vector<InferenceResult>& out) const {
        ResultGenerator gen = [&]() {
            if constexpr (E == CanonicalEvent::JouleThomson) {
                return JouleThomsonRule::apply(dts, das, n_times, n_channels, meta);
            } else if constexpr (E == CanonicalEvent::SlopeVelocity) {
                return SlopeVelocityRule::apply(dts, das, n_times, n_channels, meta);
            } else if constexpr (E == CanonicalEvent::WarmBack) {
                return WarmBackRule::apply(dts, das, n_times, n_channels, meta);
            } else if constexpr (E == CanonicalEvent::ValveChatter) {
                return ValveChatterRule::apply(dts, das, n_times, n_channels, meta);
            } else if constexpr (E == CanonicalEvent::SluggingCycle) {
                return SluggingCycleRule::apply(dts, das, n_times, n_channels, meta);
            } else if constexpr (E == CanonicalEvent::LeakPath) {
                return LeakPathRule::apply(dts, das, n_times, n_channels, meta);
            } else if constexpr (E == CanonicalEvent::GlvBellowRupture) {
                return GlvBellowRuptureRule::apply(dts, das, n_times, n_channels, meta);
            } else if constexpr (E == CanonicalEvent::PerforationEffectiveness) {
                return PerforationEffectivenessRule::apply(dts, das, n_times, n_channels, meta);
            } else if constexpr (E == CanonicalEvent::FracScreenout) {
                return FracScreenoutRule::apply(dts, das, n_times, n_channels, meta);
            } else if constexpr (E == CanonicalEvent::FracProppantDistribution) {
                return FracProppantDistributionRule::apply(dts, das, n_times, n_channels, meta);
            } else if constexpr (E == CanonicalEvent::FracHeightGrowth) {
                return FracHeightGrowthRule::apply(dts, das, n_times, n_channels, meta);
            } else if constexpr (E == CanonicalEvent::CementBondEvaluation) {
                return CementBondEvaluationRule::apply(dts, das, n_times, n_channels, meta);
            } else if constexpr (E == CanonicalEvent::ReCementingAssessment) {
                return ReCementingAssessmentRule::apply(dts, das, n_times, n_channels, meta);
            } else if constexpr (E == CanonicalEvent::CrossflowZonal) {
                return CrossflowZonalRule::apply(dts, das, n_times, n_channels, meta);
            } else if constexpr (E == CanonicalEvent::CementChanneling) {
                return CementChannelingRule::apply(dts, das, n_times, n_channels, meta);
            } else {
                // Nunca deve ocorrer, mas mantém o código bem formado.
                return ResultGenerator{nullptr};
            }
        }();
        auto partial = collect_results(std::move(gen));
        out.insert(out.end(),
                   std::make_move_iterator(partial.begin()),
                   std::make_move_iterator(partial.end()));
    }
};

/**
 * @brief Alias conveniente para a engine com todos os 15 eventos.
 */
using CanonicalInferenceEngine = InferenceEngine<
    CanonicalEvent::JouleThomson,
    CanonicalEvent::SlopeVelocity,
    CanonicalEvent::WarmBack,
    CanonicalEvent::ValveChatter,
    CanonicalEvent::SluggingCycle,
    CanonicalEvent::LeakPath,
    CanonicalEvent::GlvBellowRupture,
    CanonicalEvent::PerforationEffectiveness,
    CanonicalEvent::FracScreenout,
    CanonicalEvent::FracProppantDistribution,
    CanonicalEvent::FracHeightGrowth,
    CanonicalEvent::CementBondEvaluation,
    CanonicalEvent::ReCementingAssessment,
    CanonicalEvent::CrossflowZonal,
    CanonicalEvent::CementChanneling
>;

} // namespace inference
} // namespace alakoro
