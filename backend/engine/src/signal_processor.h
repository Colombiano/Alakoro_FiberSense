#pragma once

#include "fiber_types.h"
#include <vector>

class SignalProcessor {
public:
    SignalProcessor(FiberParams params, SignalType type);
    
    // FFT
    std::vector<double> fft_magnitude(const std::vector<double>& signal);
    std::vector<double> fft_frequencies(size_t n);
    
    // Bandpass filter
    std::vector<double> bandpass_filter(const std::vector<double>& signal, 
                                        double lowcut, double highcut);
    
    // Spectrogram
    std::vector<std::vector<double>> spectrogram(const std::vector<double>& signal, int nperseg);
    std::vector<double> get_spectrogram_freqs(int nperseg);
    std::vector<double> get_spectrogram_times(size_t signal_len, int nperseg);
    
    // Moving average
    std::vector<double> moving_average(const std::vector<double>& signal, int window);
    
    // Anomaly detection
    std::vector<double> detect_anomalies(const std::vector<double>& signal, double threshold);
    
    // Full processing pipeline
    ProcessedSignal process(const std::vector<double>& signal);

private:
    FiberParams params_;
    SignalType signal_type_;
    
    // Cooley-Tukey FFT implementation
    void cooley_tukey_fft(std::vector<double>& data);
};
