/** Wavelet Transforms for Alakoro FiberSense
 *
 * Continuous Wavelet Transform (CWT) with Morlet wavelet for transient
 * acoustic analysis in DAS signals. Discrete Wavelet Transform (DWT) for
 * multi-resolution denoising.
 *
 * References:
 *   - Morlet wavelet: Goupillaud, Grossmann & Morlet (1984)
 *   - CWT for DAS: SPE papers on acoustic transient detection
 */
#ifndef WAVELET_TRANSFORMS_H
#define WAVELET_TRANSFORMS_H

#include <vector>
#include <complex>
#include <string>

namespace alakoro {

// ============================================================================
// Wavelet Coefficients & Results
// ============================================================================

/** Result of a Continuous Wavelet Transform */
struct CWTResult {
    std::vector<std::vector<double>> scalogram;      ///< |W(a,b)|^2 [scales][time]
    std::vector<std::vector<std::complex<double>>> coeffs;  ///< Complex W(a,b)
    std::vector<double> scales;                       ///< Analysis scales
    std::vector<double> frequencies;                  ///< Equivalent frequencies (Hz)
    std::vector<double> time;                         ///< Time axis (s)
};

/** Result of a Discrete Wavelet Transform */
struct DWTResult {
    std::vector<double> approximation;                ///< A_J - coarsest approximation
    std::vector<std::vector<double>> details;         ///< D_j - detail coefficients per level
    int levels;                                       ///< Decomposition levels
    std::string wavelet_name;                         ///< Wavelet used
};

/** Configuration for wavelet processing */
struct WaveletConfig {
    double central_freq = 6.0;        ///< Morlet central frequency omega0
    int num_scales = 128;             ///< Number of scales for CWT
    double scale_min = 1.0;           ///< Minimum scale
    double scale_max = 512.0;         ///< Maximum scale
    std::string wavelet_type = "morlet";  ///< "morlet", "paul", "dog"
    int dwt_levels = 4;               ///< DWT decomposition levels
    double denoise_threshold = 3.0;   ///< Threshold multiplier for denoising
    std::string threshold_mode = "soft";  ///< "soft" or "hard" thresholding
};

// ============================================================================
// Wavelet Transform Engine
// ============================================================================

class WaveletProcessor {
public:
    WaveletProcessor();
    explicit WaveletProcessor(const WaveletConfig& config);
    ~WaveletProcessor();

    // ------------------------------------------------------------------------
    // Continuous Wavelet Transform (CWT)
    // ------------------------------------------------------------------------

    /** Compute CWT of a 1D signal using Morlet wavelet
     *
     * The Morlet wavelet is optimal for acoustic transient detection in DAS
     * because it provides the best time-frequency localization for
     * oscillatory signals.
     *
     * @param signal   Input signal vector
     * @param fs       Sampling frequency in Hz
     * @return         CWTResult with scalogram and complex coefficients
     */
    CWTResult cwt(const std::vector<double>& signal, double fs);

    /** Compute CWT scalogram (magnitude squared) only - faster
     *
     * @param signal   Input signal vector
     * @param fs       Sampling frequency in Hz
     * @return         Scalogram matrix [scales][time]
     */
    std::vector<std::vector<double>> scalogram(const std::vector<double>& signal, double fs);

    /** Detect transient events using CWT ridge detection
     *
     * Finds the "ridges" in the scalogram that correspond to transient
     * acoustic events. More sensitive than STFT for short-duration events.
     *
     * @param signal    Input signal
     * @param fs        Sampling frequency
     * @param threshold Ridge detection threshold (std dev multiples)
     * @return          Vector of (time, frequency, amplitude) tuples
     */
    std::vector<std::tuple<double, double, double>> detect_transients(
        const std::vector<double>& signal,
        double fs,
        double threshold = 4.0
    );

    // ------------------------------------------------------------------------
    // Discrete Wavelet Transform (DWT)
    // ------------------------------------------------------------------------

    /** Compute DWT using Daubechies-4 wavelet
     *
     * Multi-level decomposition for denoising and feature extraction.
     *
     * @param signal   Input signal
     * @param levels   Decomposition levels (default from config)
     * @return         DWTResult with approximations and details
     */
    DWTResult dwt(const std::vector<double>& signal, int levels = -1);

    /** Inverse DWT reconstruction */
    std::vector<double> idwt(const DWTResult& dwt_result);

    /** Wavelet denoising with universal threshold (VisuShrink)
     *
     * Applies DWT, thresholds detail coefficients, and reconstructs.
     * Particularly effective for DAS signals where noise is spread across
     * scales but transients concentrate at specific scales.
     *
     * @param signal   Noisy input signal
     * @param levels   Decomposition levels
     * @return         Denoised signal
     */
    std::vector<double> denoise(const std::vector<double>& signal, int levels = -1);

    /** Wavelet denoising with scale-dependent soft thresholding (SureShrink)
     *
     * Uses Stein's Unbiased Risk Estimate for adaptive threshold per level.
     * Better preserves transient features than VisuShrink.
     *
     * @param signal   Noisy input signal
     * @param levels   Decomposition levels
     * @return         Denoised signal
     */
    std::vector<double> denoise_sure(const std::vector<double>& signal, int levels = -1);

    // ------------------------------------------------------------------------
    // Multi-scale Analysis
    // ------------------------------------------------------------------------

    /** Compute wavelet power spectrum (global) */
    std::vector<double> wavelet_power_spectrum(
        const std::vector<double>& signal,
        double fs
    );

    /** Compute scale-averaged wavelet power over a frequency band */
    std::vector<double> scale_average_power(
        const CWTResult& cwt,
        double fmin,
        double fmax
    );

    /** Cone of influence mask - marks edge effects in CWT */
    std::vector<std::vector<bool>> cone_of_influence(
        int signal_length,
        const std::vector<double>& scales,
        double fs
    );

    // ------------------------------------------------------------------------
    // Configuration
    // ------------------------------------------------------------------------

    void set_config(const WaveletConfig& config);
    const WaveletConfig& get_config() const;

    /** Get the last error message */
    std::string get_last_error() const;

private:
    WaveletConfig config_;
    std::string last_error_;

    // Morlet wavelet mother function psi(t)
    std::complex<double> morlet_wavelet(double t, double omega0);

    // Morlet wavelet at scale a, translated by b
    std::complex<double> morlet_scaled(double t, double a, double b, double omega0);

    // Generate scales (logarithmic spacing)
    std::vector<double> generate_scales(double s_min, double s_max, int n);

    // Scale to equivalent frequency conversion
    double scale_to_frequency(double scale, double omega0, double fs, int n);

    // Daubechies-4 filter coefficients
    static const std::vector<double> db4_low_pass;
    static const std::vector<double> db4_high_pass;

    // Convolution with boundary handling (symmetric extension)
    std::vector<double> convolve_symmetric(
        const std::vector<double>& signal,
        const std::vector<double>& filter
    );

    // Downsample by 2
    std::vector<double> downsample(const std::vector<double>& signal);

    // Upsample by 2 (insert zeros)
    std::vector<double> upsample(const std::vector<double>& signal);

    // Soft thresholding function
    double soft_threshold(double x, double lambda);

    // Hard thresholding function
    double hard_threshold(double x, double lambda);

    // Median absolute deviation estimate of noise std dev
    double mad_noise_estimate(const std::vector<double>& coeffs);

    // Stein's Unbiased Risk Estimate threshold
    double sure_threshold(const std::vector<double>& coeffs);
};

} // namespace alakoro

#endif // WAVELET_TRANSFORMS_H
