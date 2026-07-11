#pragma once

#include <vector>
#include <complex>
#include <memory>
#include <Eigen/Dense>

namespace alakoro {

using Signal = Eigen::VectorXd;
using ComplexSignal = Eigen::VectorXcd;
using SignalMatrix = Eigen::MatrixXd;

enum class FilterType {
    LOWPASS,
    HIGHPASS,
    BANDPASS,
    NOTCH
};

enum class WindowType {
    HANN,
    HAMMING,
    BLACKMAN,
    KAISER
};

class SignalProcessor {
public:
    SignalProcessor() = default;
    ~SignalProcessor() = default;

    // FFT / IFFT
    static ComplexSignal fft(const Signal& signal);
    static Signal ifft(const ComplexSignal& spectrum);
    static SignalMatrix stft(const Signal& signal, int window_size, int hop_size, WindowType window = WindowType::HANN);
    static Signal istft(const SignalMatrix& spectrogram, int hop_size, WindowType window = WindowType::HANN);

    // Filtering
    static Signal fir_filter(const Signal& signal, const Signal& coefficients);
    static Signal iir_filter(const Signal& signal, const Signal& b, const Signal& a);
    static Signal butterworth_filter(const Signal& signal, double cutoff, int order, FilterType type, double sample_rate);
    
    // Window functions
    static Signal create_window(int size, WindowType type, double parameter = 0.0);
    
    // Spectral analysis
    static Signal power_spectrum(const Signal& signal);
    static Signal power_spectral_density(const Signal& signal, double sample_rate);
    static std::vector<std::pair<double, double>> detect_peaks(const Signal& spectrum, double threshold, int min_distance);
    
    // Time-domain analysis
    static Signal envelope(const Signal& signal);
    static Signal analytic_signal(const Signal& signal);
    static double rms(const Signal& signal);
    static double crest_factor(const Signal& signal);
    static Signal moving_average(const Signal& signal, int window_size);
    
    // Phase analysis
    static Signal instantaneous_frequency(const Signal& signal, double sample_rate);
    static Signal phase_unwrap(const Signal& phase);
    
    // Decimation and interpolation
    static Signal decimate(const Signal& signal, int factor);
    static Signal interpolate(const Signal& signal, int factor);

private:
    static std::vector<std::complex<double>> fft_radix2(std::vector<std::complex<double>>& data);
};

} // namespace alakoro
