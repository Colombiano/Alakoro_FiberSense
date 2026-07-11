/** Wavelet Transforms Implementation
 *
 * CWT with Morlet wavelet for DAS acoustic transient analysis.
 * DWT with Daubechies-4 for multi-resolution denoising.
 */
#include "wavelet_transforms.h"
#include <cmath>
#include <algorithm>
#include <numeric>
#include <complex>

namespace alakoro {

// Daubechies-4 filter coefficients (normalized)
const std::vector<double> WaveletProcessor::db4_low_pass = {
    0.4829629131445341,
    0.8365163037378077,
    0.2241438680420134,
   -0.1294095225512603
};

const std::vector<double> WaveletProcessor::db4_high_pass = {
   -0.1294095225512603,
   -0.2241438680420134,
    0.8365163037378077,
   -0.4829629131445341
};

// ============================================================================
// Constructor / Destructor
// ============================================================================

WaveletProcessor::WaveletProcessor() = default;

WaveletProcessor::WaveletProcessor(const WaveletConfig& config)
    : config_(config) {}

WaveletProcessor::~WaveletProcessor() = default;

// ============================================================================
// Morlet Wavelet Functions
// ============================================================================

std::complex<double> WaveletProcessor::morlet_wavelet(double t, double omega0) {
    // Morlet wavelet: psi(t) = pi^(-1/4) * exp(i*omega0*t) * exp(-t^2/2)
    const double norm = 0.7511255444649425; // pi^(-1/4)
    const double envelope = std::exp(-t * t / 2.0);
    return std::complex<double>(
        norm * std::cos(omega0 * t) * envelope,
        norm * std::sin(omega0 * t) * envelope
    );
}

std::complex<double> WaveletProcessor::morlet_scaled(double t, double a, double b,
                                                      double omega0) {
    // Scaled and translated Morlet: psi_{a,b}(t) = (1/sqrt(a)) * psi((t-b)/a)
    double scaled_t = (t - b) / a;
    const double norm = 0.7511255444649425;
    const double envelope = std::exp(-scaled_t * scaled_t / 2.0);
    const double amplitude = 1.0 / std::sqrt(a);
    return std::complex<double>(
        amplitude * norm * std::cos(omega0 * scaled_t) * envelope,
        amplitude * norm * std::sin(omega0 * scaled_t) * envelope
    );
}

// ============================================================================
// Scale Generation
// ============================================================================

std::vector<double> WaveletProcessor::generate_scales(double s_min, double s_max, int n) {
    std::vector<double> scales(n);
    double log_min = std::log2(s_min);
    double log_max = std::log2(s_max);
    double delta = (log_max - log_min) / (n - 1);

    for (int i = 0; i < n; ++i) {
        scales[i] = std::pow(2.0, log_min + i * delta);
    }
    return scales;
}

double WaveletProcessor::scale_to_frequency(double scale, double omega0,
                                             double fs, int n) {
    // Equivalent Fourier frequency for Morlet at given scale
    // f = omega0 / (2*pi * scale * dt) where dt = 1/fs
    double dt = 1.0 / fs;
    return omega0 / (2.0 * M_PI * scale * dt * n) * n;  // simplified
}

// ============================================================================
// Continuous Wavelet Transform (CWT)
// ============================================================================

CWTResult WaveletProcessor::cwt(const std::vector<double>& signal, double fs) {
    CWTResult result;
    const int n = static_cast<int>(signal.size());
    const double dt = 1.0 / fs;

    if (n == 0) {
        last_error_ = "Empty signal";
        return result;
    }

    // Generate scales
    result.scales = generate_scales(config_.scale_min, config_.scale_max,
                                     config_.num_scales);
    const int n_scales = static_cast<int>(result.scales.size());

    // Time axis
    result.time.resize(n);
    for (int i = 0; i < n; ++i) {
        result.time[i] = i * dt;
    }

    // Frequency axis (equivalent Fourier frequency for each scale)
    result.frequencies.resize(n_scales);
    for (int j = 0; j < n_scales; ++j) {
        // f = omega0 / (2 * pi * scale)
        result.frequencies[j] = config_.central_freq /
            (2.0 * M_PI * result.scales[j] * dt);
    }

    // Initialize output matrices
    result.scalogram.resize(n_scales, std::vector<double>(n, 0.0));
    result.coeffs.resize(n_scales, std::vector<std::complex<double>>(n));

    // Pre-compute the mean for detrending
    double mean = std::accumulate(signal.begin(), signal.end(), 0.0) / n;

    // CWT computation
    // For efficiency, we use FFT-based convolution for each scale
    for (int j = 0; j < n_scales; ++j) {
        double scale = result.scales[j];

        // Wavelet width at this scale (in samples)
        // Effective support: ~4*sqrt(2)*scale in time units
        int wavelet_support = static_cast<int>(4.0 * std::sqrt(2.0) * scale / dt) + 1;
        wavelet_support = std::min(wavelet_support, 2 * n);
        if (wavelet_support % 2 == 0) wavelet_support++;
        int half_support = wavelet_support / 2;

        // Generate wavelet at this scale
        std::vector<std::complex<double>> wavelet(wavelet_support);
        for (int k = 0; k < wavelet_support; ++k) {
            double t = (k - half_support) * dt;
            wavelet[k] = std::conj(morlet_scaled(t, scale, 0.0, config_.central_freq));
        }

        // Convolve wavelet with signal for each time position
        for (int i = 0; i < n; ++i) {
            std::complex<double> sum(0.0, 0.0);
            for (int k = 0; k < wavelet_support; ++k) {
                int idx = i + k - half_support;
                // Symmetric boundary extension
                if (idx < 0) idx = -idx;
                if (idx >= n) idx = 2 * n - 2 - idx;
                sum += (signal[idx] - mean) * wavelet[k];
            }
            // Normalization by sqrt(scale)
            sum *= std::sqrt(dt / scale);
            result.coeffs[j][i] = sum;
            result.scalogram[j][i] = std::norm(sum);  // |W|^2
        }
    }

    return result;
}

std::vector<std::vector<double>> WaveletProcessor::scalogram(
    const std::vector<double>& signal, double fs) {
    CWTResult result = cwt(signal, fs);
    return result.scalogram;
}

// ============================================================================
// Transient Detection via Ridge Detection
// ============================================================================

std::vector<std::tuple<double, double, double>> WaveletProcessor::detect_transients(
    const std::vector<double>& signal, double fs, double threshold) {

    std::vector<std::tuple<double, double, double>> transients;

    // Compute CWT
    CWTResult cwt_result = cwt(signal, fs);
    if (cwt_result.scalogram.empty()) return transients;

    const int n_scales = static_cast<int>(cwt_result.scalogram.size());
    const int n_time = static_cast<int>(cwt_result.scalogram[0].size());

    // Find global mean and std for thresholding
    double total_mean = 0.0;
    int count = 0;
    for (int j = 0; j < n_scales; ++j) {
        for (int i = 0; i < n_time; ++i) {
            total_mean += cwt_result.scalogram[j][i];
            count++;
        }
    }
    total_mean /= count;

    double total_var = 0.0;
    for (int j = 0; j < n_scales; ++j) {
        for (int i = 0; i < n_time; ++i) {
            double diff = cwt_result.scalogram[j][i] - total_mean;
            total_var += diff * diff;
        }
    }
    double total_std = std::sqrt(total_var / count);
    double detection_threshold = total_mean + threshold * total_std;

    // Ridge detection: find local maxima along scales
    // A ridge is a connected path of local maxima in the scalogram
    std::vector<std::vector<bool>> visited(n_scales, std::vector<bool>(n_time, false));

    for (int j = 1; j < n_scales - 1; ++j) {
        for (int i = 1; i < n_time - 1; ++i) {
            if (visited[j][i]) continue;

            double val = cwt_result.scalogram[j][i];
            if (val < detection_threshold) continue;

            // Check if local maximum in neighborhood
            bool is_max = true;
            for (int dj = -1; dj <= 1 && is_max; ++dj) {
                for (int di = -1; di <= 1; ++di) {
                    if (dj == 0 && di == 0) continue;
                    int nj = j + dj;
                    int ni = i + di;
                    if (nj >= 0 && nj < n_scales && ni >= 0 && ni < n_time) {
                        if (cwt_result.scalogram[nj][ni] > val) {
                            is_max = false;
                            break;
                        }
                    }
                }
            }

            if (is_max) {
                // Follow ridge upward and downward in scale
                double max_power = val;
                int best_j = j;

                // Trace ridge
                int curr_j = j, curr_i = i;
                while (curr_j > 0) {
                    visited[curr_j][curr_i] = true;
                    // Find maximum in next finer scale
                    int next_i = curr_i;
                    double next_max = cwt_result.scalogram[curr_j - 1][curr_i];
                    for (int di = -2; di <= 2; ++di) {
                        int ni = curr_i + di;
                        if (ni >= 0 && ni < n_time &&
                            cwt_result.scalogram[curr_j - 1][ni] > next_max) {
                            next_max = cwt_result.scalogram[curr_j - 1][ni];
                            next_i = ni;
                        }
                    }
                    if (next_max > max_power) {
                        max_power = next_max;
                        best_j = curr_j - 1;
                    }
                    curr_j--;
                    curr_i = next_i;
                }

                double time = cwt_result.time[i];
                double freq = cwt_result.frequencies[j];
                double amplitude = std::sqrt(max_power);
                transients.emplace_back(time, freq, amplitude);
            }
        }
    }

    // Sort by time
    std::sort(transients.begin(), transients.end(),
              [](const auto& a, const auto& b) {
                  return std::get<0>(a) < std::get<0>(b);
              });

    return transients;
}

// ============================================================================
// Discrete Wavelet Transform (DWT) - Daubechies-4
// ============================================================================

std::vector<double> WaveletProcessor::convolve_symmetric(
    const std::vector<double>& signal, const std::vector<double>& filter) {

    int n = static_cast<int>(signal.size());
    int m = static_cast<int>(filter.size());
    int half_m = m / 2;
    std::vector<double> result(n, 0.0);

    for (int i = 0; i < n; ++i) {
        double sum = 0.0;
        for (int k = 0; k < m; ++k) {
            int idx = i + k - half_m;
            // Symmetric boundary extension
            if (idx < 0) idx = -idx - 1;
            if (idx >= n) idx = 2 * n - 1 - idx;
            // Clamp to valid range
            idx = std::max(0, std::min(n - 1, idx));
            sum += signal[idx] * filter[k];
        }
        result[i] = sum;
    }
    return result;
}

std::vector<double> WaveletProcessor::downsample(const std::vector<double>& signal) {
    int n = static_cast<int>(signal.size());
    int n_out = n / 2;
    std::vector<double> result(n_out);
    for (int i = 0; i < n_out; ++i) {
        result[i] = signal[2 * i];
    }
    return result;
}

std::vector<double> WaveletProcessor::upsample(const std::vector<double>& signal) {
    int n = static_cast<int>(signal.size());
    std::vector<double> result(2 * n, 0.0);
    for (int i = 0; i < n; ++i) {
        result[2 * i] = signal[i];
    }
    return result;
}

DWTResult WaveletProcessor::dwt(const std::vector<double>& signal, int levels) {
    DWTResult result;
    result.wavelet_name = "db4";

    if (levels < 0) levels = config_.dwt_levels;
    result.levels = levels;

    int n = static_cast<int>(signal.size());
    // Pad to power of 2 if needed
    int pow2 = 1;
    while (pow2 < n) pow2 *= 2;

    std::vector<double> working(pow2, 0.0);
    for (int i = 0; i < n; ++i) working[i] = signal[i];

    result.details.resize(levels);

    for (int level = 0; level < levels; ++level) {
        // Apply low-pass and high-pass filters
        std::vector<double> low = convolve_symmetric(working, db4_low_pass);
        std::vector<double> high = convolve_symmetric(working, db4_high_pass);

        // Downsample
        working = downsample(low);
        result.details[level] = downsample(high);
    }

    result.approximation = working;
    return result;
}

std::vector<double> WaveletProcessor::idwt(const DWTResult& dwt_result) {
    std::vector<double> working = dwt_result.approximation;

    for (int level = dwt_result.levels - 1; level >= 0; --level) {
        // Upsample
        std::vector<double> up_low = upsample(working);
        std::vector<double> up_high = upsample(dwt_result.details[level]);

        // Pad to match lengths
        while (up_high.size() < up_low.size()) up_high.push_back(0.0);
        while (up_low.size() < up_high.size()) up_low.push_back(0.0);

        // Apply reconstruction filters (reversed and swapped)
        std::vector<double> rec_low = {db4_low_pass[3], db4_low_pass[2],
                                        db4_low_pass[1], db4_low_pass[0]};
        std::vector<double> rec_high = {db4_high_pass[3], db4_high_pass[2],
                                         db4_high_pass[1], db4_high_pass[0]};

        std::vector<double> low_filtered = convolve_symmetric(up_low, rec_low);
        std::vector<double> high_filtered = convolve_symmetric(up_high, rec_high);

        // Reconstruct
        int n = static_cast<int>(low_filtered.size());
        working.resize(n);
        for (int i = 0; i < n; ++i) {
            working[i] = low_filtered[i] + high_filtered[i];
        }
    }

    return working;
}

// ============================================================================
// Denoising
// ============================================================================

double WaveletProcessor::soft_threshold(double x, double lambda) {
    if (x > lambda) return x - lambda;
    if (x < -lambda) return x + lambda;
    return 0.0;
}

double WaveletProcessor::hard_threshold(double x, double lambda) {
    return (std::abs(x) > lambda) ? x : 0.0;
}

double WaveletProcessor::mad_noise_estimate(const std::vector<double>& coeffs) {
    // Median Absolute Deviation: robust noise std dev estimate
    std::vector<double> abs_coeffs(coeffs.size());
    for (size_t i = 0; i < coeffs.size(); ++i) {
        abs_coeffs[i] = std::abs(coeffs[i]);
    }

    std::nth_element(abs_coeffs.begin(),
                      abs_coeffs.begin() + abs_coeffs.size() / 2,
                      abs_coeffs.end());
    double median = abs_coeffs[abs_coeffs.size() / 2];

    // MAD = median(|coeffs - median|) / 0.6745
    return median / 0.6745;
}

double WaveletProcessor::sure_threshold(const std::vector<double>& coeffs) {
    // Stein's Unbiased Risk Estimate threshold
    int n = static_cast<int>(coeffs.size());
    if (n == 0) return 0.0;

    // Sort |coeffs|
    std::vector<double> sorted(n);
    for (int i = 0; i < n; ++i) sorted[i] = std::abs(coeffs[i]);
    std::sort(sorted.begin(), sorted.end());

    // Find threshold that minimizes SURE
    double min_risk = 1e300;
    double best_threshold = sorted[n - 1];

    for (int k = 0; k < n; ++k) {
        double threshold = sorted[k];
        double risk = 0.0;
        int num_shrink = 0;

        for (int i = 0; i < n; ++i) {
            double c = sorted[i];
            if (c <= threshold) {
                risk += c * c;
                num_shrink++;
            } else {
                risk += threshold * threshold + 1.0;
            }
        }
        risk = (risk - n + 2.0 * num_shrink) / n;

        if (risk < min_risk) {
            min_risk = risk;
            best_threshold = threshold;
        }
    }

    return best_threshold;
}

std::vector<double> WaveletProcessor::denoise(const std::vector<double>& signal,
                                               int levels) {
    if (levels < 0) levels = config_.dwt_levels;

    // DWT
    DWTResult dwt_result = dwt(signal, levels);

    // Estimate noise from finest scale detail coefficients
    double sigma = mad_noise_estimate(dwt_result.details[0]);

    // Universal threshold (VisuShrink)
    for (int level = 0; level < levels; ++level) {
        int n_level = static_cast<int>(dwt_result.details[level].size());
        double lambda = config_.denoise_threshold * sigma * std::sqrt(2.0 * std::log(n_level));

        for (double& coeff : dwt_result.details[level]) {
            coeff = soft_threshold(coeff, lambda);
        }
    }

    // IDWT reconstruction
    return idwt(dwt_result);
}

std::vector<double> WaveletProcessor::denoise_sure(const std::vector<double>& signal,
                                                    int levels) {
    if (levels < 0) levels = config_.dwt_levels;

    // DWT
    DWTResult dwt_result = dwt(signal, levels);

    // Apply SURE threshold per level
    for (int level = 0; level < levels; ++level) {
        double lambda = sure_threshold(dwt_result.details[level]);

        for (double& coeff : dwt_result.details[level]) {
            coeff = soft_threshold(coeff, lambda);
        }
    }

    // IDWT reconstruction
    return idwt(dwt_result);
}

// ============================================================================
// Multi-scale Analysis
// ============================================================================

std::vector<double> WaveletProcessor::wavelet_power_spectrum(
    const std::vector<double>& signal, double fs) {

    CWTResult cwt_result = cwt(signal, fs);
    if (cwt_result.scalogram.empty()) return {};

    int n_scales = static_cast<int>(cwt_result.scalogram.size());
    int n_time = static_cast<int>(cwt_result.scalogram[0].size());

    std::vector<double> power(n_scales, 0.0);
    for (int j = 0; j < n_scales; ++j) {
        for (int i = 0; i < n_time; ++i) {
            power[j] += cwt_result.scalogram[j][i];
        }
        power[j] /= n_time;
    }

    return power;
}

std::vector<double> WaveletProcessor::scale_average_power(
    const CWTResult& cwt, double fmin, double fmax) {

    if (cwt.scalogram.empty()) return {};

    int n_scales = static_cast<int>(cwt.scalogram.size());
    int n_time = static_cast<int>(cwt.scalogram[0].size());

    // Find scale indices for frequency band
    int j_min = 0, j_max = n_scales - 1;
    for (int j = 0; j < n_scales; ++j) {
        if (cwt.frequencies[j] >= fmin && j_min == 0) j_min = j;
        if (cwt.frequencies[j] <= fmax) j_max = j;
    }

    std::vector<double> avg_power(n_time, 0.0);
    int count = 0;
    for (int j = j_min; j <= j_max && j < n_scales; ++j) {
        for (int i = 0; i < n_time; ++i) {
            avg_power[i] += cwt.scalogram[j][i];
        }
        count++;
    }

    if (count > 0) {
        for (int i = 0; i < n_time; ++i) {
            avg_power[i] /= count;
        }
    }

    return avg_power;
}

std::vector<std::vector<bool>> WaveletProcessor::cone_of_influence(
    int signal_length, const std::vector<double>& scales, double fs) {

    int n_scales = static_cast<int>(scales.size());
    std::vector<std::vector<bool>> coi(n_scales,
                                        std::vector<bool>(signal_length, true));

    double dt = 1.0 / fs;

    for (int j = 0; j < n_scales; ++j) {
        // COI: e-folding time = sqrt(2) * scale
        double coi_time = std::sqrt(2.0) * scales[j];
        int coi_samples = static_cast<int>(coi_time / dt);

        for (int i = 0; i < signal_length; ++i) {
            // Mark points outside COI as affected by edge effects
            if (i < coi_samples || i >= signal_length - coi_samples) {
                coi[j][i] = false;  // Edge-affected
            }
        }
    }

    return coi;
}

// ============================================================================
// Configuration
// ============================================================================

void WaveletProcessor::set_config(const WaveletConfig& config) {
    config_ = config;
}

const WaveletConfig& WaveletProcessor::get_config() const {
    return config_;
}

std::string WaveletProcessor::get_last_error() const {
    return last_error_;
}

} // namespace alakoro
