#pragma once

#include "alakoro/signal_processor.hpp"
#include "alakoro/das_decoder.hpp"
#include <vector>
#include <functional>
#include <chrono>

namespace alakoro {

enum class EventType {
    VIBRATION,
    FRACTURE,
    FLOW,
    LEAK,
    CUSTOM
};

struct Event {
    EventType type;
    double timestamp;
    int channel_start;
    int channel_end;
    double frequency_center;
    double bandwidth;
    double amplitude;
    double confidence;
    double snr;
    Signal waveform;
    std::map<std::string, double> features;
};

struct DetectorConfig {
    double threshold_snr;
    double min_duration_ms;
    double max_duration_ms;
    double min_frequency;
    double max_frequency;
    int min_channels;
    int merge_gap_ms;
    bool use_ml_classifier;
    std::string model_path;
};

class EventDetector {
public:
    EventDetector();
    explicit EventDetector(const DetectorConfig& config);
    ~EventDetector() = default;

    // Configuration
    void set_config(const DetectorConfig& config);
    DetectorConfig get_config() const;
    
    // Detection methods
    std::vector<Event> detect_events(const SignalMatrix& das_data, double sample_rate);
    std::vector<Event> detect_on_single_channel(const Signal& signal, double sample_rate, int channel_index);
    std::vector<Event> detect_in_region(const SignalMatrix& das_data, int ch_start, int ch_end, double sample_rate);
    
    // Real-time processing
    void process_frame(const DASFrame& frame);
    void flush();
    
    // Callbacks
    std::function<void(const Event&)> on_event_detected;
    std::function<void(const std::vector<Event>&)> on_batch_processed;
    
    // State
    void reset();
    int get_event_count() const;
    std::vector<Event> get_event_history() const;
    void clear_history();
    
    // Classification
    void load_classifier_model(const std::string& model_path);
    EventType classify_event(const Event& event);
    
    // Feature extraction
    std::map<std::string, double> extract_features(const Signal& waveform, double sample_rate);
    SignalMatrix compute_features_matrix(const SignalMatrix& data, double sample_rate);

private:
    DetectorConfig config_;
    std::vector<Event> event_history_;
    std::vector<DASFrame> frame_buffer_;
    bool model_loaded_;
    
    std::vector<Event> threshold_based_detection(const SignalMatrix& data, double sample_rate);
    std::vector<Event> spectral_detection(const SignalMatrix& data, double sample_rate);
    std::vector<Event> merge_events(const std::vector<Event>& events);
    bool meets_criteria(const Event& event) const;
    double compute_event_snr(const Signal& waveform) const;
};

} // namespace alakoro
