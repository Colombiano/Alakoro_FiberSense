#include "alakoro/signal_processor.hpp"
#include <cmath>
#include <algorithm>
#include <numeric>

namespace alakoro {

// ==================== FFT / IFFT ====================

ComplexSignal SignalProcessor::fft(const Signal& signal) {
    int n = signal.size();
    std::vector<std::complex<double>> data(n);
    for (int i = 0; i < n; ++i) {
        data[i] = std::complex<double>(signal(i), 0.0);
    }
    fft_radix2(data);
    ComplexSignal result(n);
    for (int i = 0; i < n; ++i) {
        result(i) = data[i];
    }
    return result;
}

Signal SignalProcessor::ifft(const ComplexSignal& spectrum) {
    int n = spectrum.size();
    std::vector<std::complex<double>> data(n);
    for (int i = 0; i < n; ++i) {
        data[i] = spectrum(i);
    }
    fft_radix2(data);
    Signal result(n);
    for (int i = 0; i < n; ++i) {
        result(i) = data[i].real() / n;
    }
    return result;
}

std::vector<std::complex<double>> SignalProcessor::fft_radix2(std::vector<std::complex<double>>& data) {
    int n = data.size();
    if (n <= 1) return data;
    
    std::vector<std::complex<double>> even(n / 2), odd(n / 2);
    for (int i = 0; i < n / 2; ++i) {
        even[i] = data[i * 2];
        odd[i] = data[i * 2 + 1];
    }
    
    fft_radix2(even);
    fft_radix2(odd);
    
    for (int k = 0; k < n / 2; ++k) {
        std::complex<double> t = std::polar(1.0, -2.0 * M_PI * k / n) * odd[k];
        data[k] = even[k] + t;
        data[k + n / 2] = even[k] - t;
    }
    return data;
}

SignalMatrix SignalProcessor::stft(const Signal& signal, int window_size, int hop_size, WindowType window) {
    int num_frames = (signal.size() - window_size) / hop_size + 1;
    Signal window_vec = create_window(window_size, window);
    SignalMatrix spectrogram(window_size / 2 + 1, num_frames);
    
    for (int i = 0; i < num_frames; ++i) {
        int start = i * hop_size;
        Signal frame(window_size);
        for (int j = 0; j < window_size; ++j) {
            frame(j) = signal(start + j) * window_vec(j);
        }
        auto spec = fft(frame);
        for (int k = 0; k <= window_size / 2; ++k) {
            spectrogram(k, i) = std::abs(spec(k));
        }
    }
    return spectrogram;
}

Signal SignalProcessor::istft(const SignalMatrix& spectrogram, int hop_size, WindowType window) {
    int window_size = (spectrogram.rows() - 1) * 2;
    int num_frames = spectrogram.cols();
    int signal_length = (num_frames - 1) * hop_size + window_size;
    Signal window_vec = create_window(window_size, window);
    Signal signal = Signal::Zero(signal_length);
    Signal window_sum = Signal::Zero(signal_length);
    
    for (int i = 0; i < num_frames; ++i) {
        int start = i * hop_size;
        ComplexSignal full_spec(window_size);
        for (int k = 0; k <= window_size / 2; ++k) {
            full_spec(k) = std::complex<double>(spectrogram(k, i), 0.0);
        }
        for (int k = window_size / 2 + 1; k < window_size; ++k) {
            full_spec(k) = std::conj(full_spec(window_size - k));
        }
        Signal frame = ifft(full_spec);
        for (int j = 0; j < window_size; ++j) {
            signal(start + j) += frame(j) * window_vec(j);
            window_sum(start + j) += window_vec(j) * window_vec(j);
        }
    }
    
    for (int i = 0; i < signal_length; ++i) {
        if (window_sum(i) > 1e-10) {
            signal(i) /= window_sum(i);
        }
    }
    return signal;
}

// ==================== Filtering ====================

Signal SignalProcessor::fir_filter(const Signal& signal, const Signal& coefficients) {
    int n = signal.size();
    int m = coefficients.size();
    Signal result = Signal::Zero(n);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m && i - j >= 0; ++j) {
            result(i) += signal(i - j) * coefficients(j);
        }
    }
    return result;
}

Signal SignalProcessor::butterworth_filter(const Signal& signal, double cutoff, int order, FilterType type, double sample_rate) {
    double nyquist = sample_rate / 2.0;
    double wc = cutoff / nyquist;
    
    Signal b(order + 1), a(order + 1);
    b(0) = wc;
    a(0) = 1.0;
    for (int i = 1; i <= order; ++i) {
        b(i) = b(i - 1) * wc;
        a(i) = a(i - 1) * (1.0 + wc);
    }
    
    if (type == FilterType::HIGHPASS) {
        for (int i = 1; i <= order; i += 2) {
            b(i) = -b(i);
        }
    }
    
    return iir_filter(signal, b, a);
}

Signal SignalProcessor::iir_filter(const Signal& signal, const Signal& b, const Signal& a) {
    int n = signal.size();
    int nb = b.size();
    int na = a.size();
    Signal result(n);
    
    for (int i = 0; i < n; ++i) {
        result(i) = 0;
        for (int j = 0; j < nb && i - j >= 0; ++j) {
            result(i) += b(j) * signal(i - j);
        }
        for (int j = 1; j < na && i - j >= 0; ++j) {
            result(i) -= a(j) * result(i - j);
        }
        result(i) /= a(0);
    }
    return result;
}

// ==================== Window Functions ====================

Signal SignalProcessor::create_window(int size, WindowType type, double parameter) {
    Signal window(size);
    for (int i = 0; i < size; ++i) {
        switch (type) {
            case WindowType::HANN:
                window(i) = 0.5 * (1.0 - std::cos(2.0 * M_PI * i / (size - 1)));
                break;
            case WindowType::HAMMING:
                window(i) = 0.54 - 0.46 * std::cos(2.0 * M_PI * i / (size - 1));
                break;
            case WindowType::BLACKMAN:
                window(i) = 0.42 - 0.5 * std::cos(2.0 * M_PI * i / (size - 1)) 
                          + 0.08 * std::cos(4.0 * M_PI * i / (size - 1));
                break;
            case WindowType::KAISER:
                window(i) = 1.0;
                break;
        }
    }
    return window;
}

// ==================== Spectral Analysis ====================

Signal SignalProcessor::power_spectrum(const Signal& signal) {
    auto spec = fft(signal);
    int n = spec.size();
    Signal power(n / 2 + 1);
    for (int i = 0; i <= n / 2; ++i) {
        power(i) = std::norm(spec(i));
    }
    return power;
}

Signal SignalProcessor::power_spectral_density(const Signal& signal, double sample_rate) {
    Signal psd = power_spectrum(signal);
    double scale = sample_rate / signal.size();
    return psd * scale;
}

std::vector<std::pair<double, double>> SignalProcessor::detect_peaks(const Signal& spectrum, double threshold, int min_distance) {
    std::vector<std::pair<double, double>> peaks;
    int n = spectrum.size();
    
    for (int i = 1; i < n - 1; ++i) {
        if (spectrum(i) > threshold && spectrum(i) > spectrum(i - 1) && spectrum(i) > spectrum(i + 1)) {
            if (peaks.empty() || i - peaks.back().first >= min_distance) {
                peaks.push_back({static_cast<double>(i), spectrum(i)});
            }
        }
    }
    return peaks;
}

// ==================== Time-Domain Analysis ====================

Signal SignalProcessor::envelope(const Signal& signal) {
    Signal analytic = analytic_signal(signal);
    return analytic.cwiseAbs();
}

Signal SignalProcessor::analytic_signal(const Signal& signal) {
    auto spec = fft(signal);
    int n = signal.size();
    for (int i = 1; i < n / 2; ++i) {
        spec(i) *= 2.0;
    }
    if (n % 2 == 0) {
        spec(n / 2) *= 2.0;
    }
    for (int i = n / 2 + 1; i < n; ++i) {
        spec(i) = std::complex<double>(0.0, 0.0);
    }
    auto result = ifft(spec);
    Signal envelope(n);
    for (int i = 0; i < n; ++i) {
        envelope(i) = std::abs(result(i));
    }
    return envelope;
}

double SignalProcessor::rms(const Signal& signal) {
    return std::sqrt(signal.array().square().mean());
}

double SignalProcessor::crest_factor(const Signal& signal) {
    return signal.maxCoeff() / rms(signal);
}

Signal SignalProcessor::moving_average(const Signal& signal, int window_size) {
    int n = signal.size();
    Signal result(n);
    double sum = 0.0;
    for (int i = 0; i < n; ++i) {
        sum += signal(i);
        if (i >= window_size) {
            sum -= signal(i - window_size);
        }
        result(i) = sum / std::min(i + 1, window_size);
    }
    return result;
}

// ==================== Phase Analysis ====================

Signal SignalProcessor::instantaneous_frequency(const Signal& signal, double sample_rate) {
    auto spec = fft(signal);
    Signal phase(signal.size());
    for (int i = 0; i < signal.size(); ++i) {
        phase(i) = std::arg(spec(i));
    }
    Signal inst_freq(signal.size());
    for (int i = 1; i < signal.size(); ++i) {
        double dp = phase(i) - phase(i - 1);
        if (dp > M_PI) dp -= 2 * M_PI;
        if (dp < -M_PI) dp += 2 * M_PI;
        inst_freq(i) = dp * sample_rate / (2.0 * M_PI);
    }
    inst_freq(0) = inst_freq(1);
    return inst_freq;
}

Signal SignalProcessor::phase_unwrap(const Signal& phase) {
    int n = phase.size();
    Signal unwrapped(n);
    unwrapped(0) = phase(0);
    double cumsum = 0;
    for (int i = 1; i < n; ++i) {
        double diff = phase(i) - phase(i - 1);
        if (diff > M_PI) cumsum -= 2 * M_PI;
        if (diff < -M_PI) cumsum += 2 * M_PI;
        unwrapped(i) = phase(i) + cumsum;
    }
    return unwrapped;
}

// ==================== Decimation / Interpolation ====================

Signal SignalProcessor::decimate(const Signal& signal, int factor) {
    int n = signal.size() / factor;
    Signal result(n);
    for (int i = 0; i < n; ++i) {
        result(i) = signal(i * factor);
    }
    return result;
}

Signal SignalProcessor::interpolate(const Signal& signal, int factor) {
    int n = signal.size() * factor;
    Signal result = Signal::Zero(n);
    for (int i = 0; i < signal.size(); ++i) {
        result(i * factor) = signal(i);
    }
    for (int i = 0; i < n - factor; i += factor) {
        for (int j = 1; j < factor; ++j) {
            result(i + j) = result(i) + (result(i + factor) - result(i)) * j / factor;
        }
    }
    return result;
}

} // namespace alakoro
