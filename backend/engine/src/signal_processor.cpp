"""
Alakoro FiberSense - C++ Signal Processor
Implementacao do processamento de sinais de fibra otica.
"""
#include "signal_processor.h"
#include <algorithm>
#include <cmath>
#include <complex>
#include <numeric>

SignalProcessor::SignalProcessor(FiberParams params, SignalType type) 
    : params_(params), signal_type_(type) {}

std::vector<double> SignalProcessor::fft_magnitude(const std::vector<double>& signal) {
    size_t n = signal.size();
    size_t n_fft = n / 2 + 1;
    
    std::vector<std::complex<double>> fft_result(n);
    std::vector<double> input_complex(2 * n);
    
    for (size_t i = 0; i < n; ++i) {
        input_complex[2 * i] = signal[i];
        input_complex[2 * i + 1] = 0.0;
    }
    
    // Cooley-Tukey FFT
    cooley_tukey_fft(input_complex);
    
    std::vector<double> magnitude(n_fft);
    for (size_t i = 0; i < n_fft; ++i) {
        magnitude[i] = std::sqrt(input_complex[2 * i] * input_complex[2 * i] + 
                                 input_complex[2 * i + 1] * input_complex[2 * i + 1]);
    }
    
    return magnitude;
}

std::vector<double> SignalProcessor::fft_frequencies(size_t n) {
    size_t n_fft = n / 2 + 1;
    std::vector<double> freqs(n_fft);
    double df = params_.sampling_rate / n;
    for (size_t i = 0; i < n_fft; ++i) {
        freqs[i] = i * df;
    }
    return freqs;
}

void SignalProcessor::cooley_tukey_fft(std::vector<double>& data) {
    size_t n = data.size() / 2;
    if (n <= 1) return;
    
    // Bit reversal permutation
    size_t j = 0;
    for (size_t i = 0; i < n; ++i) {
        if (i < j) {
            std::swap(data[2 * i], data[2 * j]);
            std::swap(data[2 * i + 1], data[2 * j + 1]);
        }
        size_t m = n;
        while (m >= 2 && j >= m / 2) {
            j -= m / 2;
            m /= 2;
        }
        j += m / 2;
    }
    
    // Danielson-Lanczos section
    for (size_t step = 2; step <= n; step *= 2) {
        double theta = -2.0 * M_PI / step;
        double wtemp = std::sin(0.5 * theta);
        double wpr = -2.0 * wtemp * wtemp;
        double wpi = std::sin(theta);
        double wr = 1.0;
        double wi = 0.0;
        
        for (size_t m = 0; m < step / 2; ++m) {
            for (size_t k = m; k < n; k += step) {
                size_t j_idx = k + step / 2;
                double tempr = wr * data[2 * j_idx] - wi * data[2 * j_idx + 1];
                double tempi = wr * data[2 * j_idx + 1] + wi * data[2 * j_idx];
                data[2 * j_idx] = data[2 * k] - tempr;
                data[2 * j_idx + 1] = data[2 * k + 1] - tempi;
                data[2 * k] += tempr;
                data[2 * k + 1] += tempi;
            }
            double wtemp_next = wr;
            wr = wr * wpr - wi * wpi + wr;
            wi = wi * wpr + wtemp_next * wpi + wi;
        }
    }
}

std::vector<double> SignalProcessor::bandpass_filter(
    const std::vector<double>& signal, double lowcut, double highcut) {
    
    size_t n = signal.size();
    std::vector<double> filtered(n);
    
    // FFT
    std::vector<double> fft_data(2 * n);
    for (size_t i = 0; i < n; ++i) {
        fft_data[2 * i] = signal[i];
        fft_data[2 * i + 1] = 0.0;
    }
    
    cooley_tukey_fft(fft_data);
    
    // Apply filter in frequency domain
    size_t n_fft = n / 2 + 1;
    double df = params_.sampling_rate / n;
    
    for (size_t i = 0; i < n_fft; ++i) {
        double freq = i * df;
        if (freq < lowcut || freq > highcut) {
            fft_data[2 * i] = 0.0;
            fft_data[2 * i + 1] = 0.0;
            if (i > 0 && i < n - i) {
                fft_data[2 * (n - i)] = 0.0;
                fft_data[2 * (n - i) + 1] = 0.0;
            }
        }
    }
    
    // Inverse FFT
    for (size_t i = 0; i < 2 * n; ++i) {
        fft_data[i] /= n;
    }
    
    // Conjugate for inverse
    for (size_t i = 1; i < n; ++i) {
        fft_data[2 * (n - i) + 1] = -fft_data[2 * (n - i) + 1];
    }
    
    cooley_tukey_fft(fft_data);
    
    for (size_t i = 0; i < n; ++i) {
        filtered[i] = fft_data[2 * i] / n;
    }
    
    return filtered;
}

std::vector<std::vector<double>> SignalProcessor::spectrogram(
    const std::vector<double>& signal, int nperseg) {
    
    size_t n = signal.size();
    int noverlap = nperseg / 2;
    int stride = nperseg - noverlap;
    int n_frames = (n - noverlap) / stride;
    int n_freqs = nperseg / 2 + 1;
    
    std::vector<std::vector<double>> spec(n_frames, std::vector<double>(n_freqs));
    
    for (int i = 0; i < n_frames; ++i) {
        int start = i * stride;
        std::vector<double> segment(nperseg);
        
        for (int j = 0; j < nperseg && start + j < static_cast<int>(n); ++j) {
            // Hann window
            double window = 0.5 * (1.0 - std::cos(2.0 * M_PI * j / (nperseg - 1)));
            segment[j] = signal[start + j] * window;
        }
        
        auto mag = fft_magnitude(segment);
        for (int j = 0; j < n_freqs && j < static_cast<int>(mag.size()); ++j) {
            spec[i][j] = 10.0 * std::log10(mag[j] * mag[j] + 1e-10);
        }
    }
    
    return spec;
}

std::vector<double> SignalProcessor::moving_average(
    const std::vector<double>& signal, int window) {
    
    size_t n = signal.size();
    std::vector<double> result(n);
    
    for (size_t i = 0; i < n; ++i) {
        double sum = 0.0;
        int count = 0;
        for (int j = -window / 2; j <= window / 2; ++j) {
            int idx = static_cast<int>(i) + j;
            if (idx >= 0 && idx < static_cast<int>(n)) {
                sum += signal[idx];
                count++;
            }
        }
        result[i] = sum / count;
    }
    
    return result;
}

std::vector<double> SignalProcessor::detect_anomalies(
    const std::vector<double>& signal, double threshold) {
    
    size_t n = signal.size();
    std::vector<double> scores(n);
    
    // Calculate mean and std
    double mean = std::accumulate(signal.begin(), signal.end(), 0.0) / n;
    double sq_sum = 0.0;
    for (double x : signal) {
        sq_sum += (x - mean) * (x - mean);
    }
    double std = std::sqrt(sq_sum / n) + 1e-10;
    
    // Z-score
    for (size_t i = 0; i < n; ++i) {
        scores[i] = std::abs(signal[i] - mean) / std;
    }
    
    return scores;
}

ProcessedSignal SignalProcessor::process(const std::vector<double>& signal) {
    ProcessedSignal result;
    
    // FFT
    result.fft_magnitude = fft_magnitude(signal);
    result.fft_frequencies = fft_frequencies(signal.size());
    
    // Spectrogram
    result.spectrogram = spectrogram(signal, 256);
    
    // Anomaly detection
    auto scores = detect_anomalies(signal, 3.0);
    result.anomaly_scores = scores;
    
    // Find events (positions where score > threshold)
    double mean_score = std::accumulate(scores.begin(), scores.end(), 0.0) / scores.size();
    double threshold = mean_score + 3.0;
    
    for (size_t i = 0; i < scores.size(); ++i) {
        if (scores[i] > threshold) {
            result.event_positions.push_back(i * params_.spatial_resolution);
            result.event_amplitudes.push_back(signal[i]);
        }
    }
    
    return result;
}

std::vector<double> SignalProcessor::get_spectrogram_freqs(int nperseg) {
    int n_freqs = nperseg / 2 + 1;
    std::vector<double> freqs(n_freqs);
    double df = params_.sampling_rate / nperseg;
    for (int i = 0; i < n_freqs; ++i) {
        freqs[i] = i * df;
    }
    return freqs;
}

std::vector<double> SignalProcessor::get_spectrogram_times(size_t signal_len, int nperseg) {
    int noverlap = nperseg / 2;
    int stride = nperseg - noverlap;
    int n_frames = (signal_len - noverlap) / stride;
    std::vector<double> times(n_frames);
    double dt = static_cast<double>(stride) / params_.sampling_rate;
    for (int i = 0; i < n_frames; ++i) {
        times[i] = i * dt;
    }
    return times;
}
