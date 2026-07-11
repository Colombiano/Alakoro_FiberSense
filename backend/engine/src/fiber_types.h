#pragma once

#include <string>
#include <vector>

namespace alakoro {

enum class SignalType {
    DAS,
    DTS,
    DSS
};

struct FiberParams {
    double fiber_length = 10000.0;
    double spatial_resolution = 1.0;
    double sampling_rate = 1000.0;
    double gauge_length = 10.0;
    double refractive_index = 1.468;
    std::string cable_type = "single_mode";
};

struct SignalData {
    SignalType signal_type;
    std::vector<double> raw_data;
    FiberParams params;
};

struct ProcessedSignal {
    std::vector<double> fft_magnitude;
    std::vector<double> fft_frequencies;
    std::vector<std::vector<double>> spectrogram;
    std::vector<double> spectrogram_freqs;
    std::vector<double> spectrogram_times;
    std::vector<double> event_positions;
    std::vector<double> event_amplitudes;
    std::vector<double> anomaly_scores;
};

struct SignalAlert {
    SignalType signal_type;
    std::string level;
    std::string message;
    double position = 0.0;
    double confidence = 0.0;
};

} // namespace alakoro

using namespace alakoro;
