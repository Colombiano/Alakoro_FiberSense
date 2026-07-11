#include "alakoro/event_detector.hpp"
#include "alakoro/signal_processor.hpp"
#include <cmath>
#include <algorithm>

namespace alakoro {

EventDetector::EventDetector() : model_loaded_(false) {
    config_.threshold_snr = 10.0;
    config_.min_duration_ms = 10.0;
    config_.max_duration_ms = 5000.0;
    config_.min_frequency = 1.0;
    config_.max_frequency = 500.0;
    config_.min_channels = 1;
    config_.merge_gap_ms = 50.0;
    config_.use_ml_classifier = false;
}

EventDetector::EventDetector(const DetectorConfig& config) : config_(config), model_loaded_(false) {}

void EventDetector::set_config(const DetectorConfig& config) {
    config_ = config;
}

DetectorConfig EventDetector::get_config() const {
    return config_;
}

std::vector<Event> EventDetector::detect_events(const SignalMatrix& das_data, double sample_rate) {
    auto events = threshold_based_detection(das_data, sample_rate);
    auto spectral = spectral_detection(das_data, sample_rate);
    
    events.insert(events.end(), spectral.begin(), spectral.end());
    events = merge_events(events);
    
    std::vector<Event> filtered;
    for (const auto& event : events) {
        if (meets_criteria(event)) {
            filtered.push_back(event);
        }
    }
    
    event_history_.insert(event_history_.end(), filtered.begin(), filtered.end());
    
    if (on_batch_processed) {
        on_batch_processed(filtered);
    }
    for (const auto& event : filtered) {
        if (on_event_detected) {
            on_event_detected(event);
        }
    }
    
    return filtered;
}

std::vector<Event> EventDetector::detect_on_single_channel(const Signal& signal, double sample_rate, int channel_index) {
    SignalMatrix data(signal.size(), 1);
    data.col(0) = signal;
    auto events = detect_events(data, sample_rate);
    for (auto& event : events) {
        event.channel_start = channel_index;
        event.channel_end = channel_index;
    }
    return events;
}

std::vector<Event> EventDetector::detect_in_region(const SignalMatrix& das_data, int ch_start, int ch_end, double sample_rate) {
    SignalMatrix region = das_data.block(0, ch_start, das_data.rows(), ch_end - ch_start + 1);
    auto events = detect_events(region, sample_rate);
    for (auto& event : events) {
        event.channel_start += ch_start;
        event.channel_end += ch_start;
    }
    return events;
}

void EventDetector::process_frame(const DASFrame& frame) {
    frame_buffer_.push_back(frame);
    auto events = detect_events(frame.data, frame.metadata.temporal_sampling);
    
    if (frame_buffer_.size() > 100) {
        frame_buffer_.erase(frame_buffer_.begin());
    }
}

void EventDetector::flush() {
    frame_buffer_.clear();
}

void EventDetector::reset() {
    frame_buffer_.clear();
    event_history_.clear();
}

int EventDetector::get_event_count() const {
    return static_cast<int>(event_history_.size());
}

std::vector<Event> EventDetector::get_event_history() const {
    return event_history_;
}

void EventDetector::clear_history() {
    event_history_.clear();
}

void EventDetector::load_classifier_model(const std::string& model_path) {
    config_.model_path = model_path;
    model_loaded_ = true;
}

EventType EventDetector::classify_event(const Event& event) {
    if (!model_loaded_ || !config_.use_ml_classifier) {
        if (event.frequency_center < 10.0) return EventType::FLOW;
        if (event.frequency_center < 50.0) return EventType::VIBRATION;
        if (event.bandwidth > 100.0) return EventType::FRACTURE;
        return EventType::CUSTOM;
    }
    return EventType::CUSTOM;
}

std::map<std::string, double> EventDetector::extract_features(const Signal& waveform, double sample_rate) {
    std::map<std::string, double> features;
    
    features["rms"] = SignalProcessor::rms(waveform);
    features["peak_amplitude"] = waveform.maxCoeff();
    features["crest_factor"] = SignalProcessor::crest_factor(waveform);
    
    auto spectrum = SignalProcessor::power_spectrum(waveform);
    features["spectral_centroid"] = 0.0;
    double total_power = spectrum.sum();
    for (int i = 0; i < spectrum.size(); ++i) {
        double freq = i * sample_rate / waveform.size();
        features["spectral_centroid"] += freq * spectrum(i);
    }
    if (total_power > 0) {
        features["spectral_centroid"] /= total_power;
    }
    
    features["duration"] = waveform.size() / sample_rate * 1000.0;
    features["zero_crossing_rate"] = 0.0;
    for (int i = 1; i < waveform.size(); ++i) {
        if (waveform(i) * waveform(i - 1) < 0) {
            features["zero_crossing_rate"] += 1.0;
        }
    }
    features["zero_crossing_rate"] /= waveform.size();
    
    return features;
}

SignalMatrix EventDetector::compute_features_matrix(const SignalMatrix& data, double sample_rate) {
    int num_features = 6;
    SignalMatrix features(data.cols(), num_features);
    
    for (int j = 0; j < data.cols(); ++j) {
        auto feats = extract_features(data.col(j), sample_rate);
        features(j, 0) = feats["rms"];
        features(j, 1) = feats["peak_amplitude"];
        features(j, 2) = feats["crest_factor"];
        features(j, 3) = feats["spectral_centroid"];
        features(j, 4) = feats["duration"];
        features(j, 5) = feats["zero_crossing_rate"];
    }
    
    return features;
}

std::vector<Event> EventDetector::threshold_based_detection(const SignalMatrix& data, double sample_rate) {
    std::vector<Event> events;
    
    for (int ch = 0; ch < data.cols(); ++ch) {
        Signal channel = data.col(ch);
        double snr = compute_event_snr(channel);
        
        if (snr < config_.threshold_snr) continue;
        
        bool in_event = false;
        int event_start = 0;
        double threshold = channel.mean() + 2.0 * std::sqrt((channel.array() - channel.mean()).square().mean());
        
        for (int i = 0; i < channel.size(); ++i) {
            if (std::abs(channel(i)) > threshold && !in_event) {
                in_event = true;
                event_start = i;
            } else if (std::abs(channel(i)) <= threshold && in_event) {
                in_event = false;
                int event_end = i;
                
                Event event;
                event.type = EventType::VIBRATION;
                event.timestamp = event_start / sample_rate;
                event.channel_start = ch;
                event.channel_end = ch;
                event.amplitude = channel.segment(event_start, event_end - event_start).maxCoeff();
                event.snr = snr;
                event.confidence = std::min(snr / config_.threshold_snr, 1.0);
                
                int len = event_end - event_start;
                event.waveform = Signal(len);
                for (int k = 0; k < len; ++k) {
                    event.waveform(k) = channel(event_start + k);
                }
                
                event.features = extract_features(event.waveform, sample_rate);
                
                events.push_back(event);
            }
        }
    }
    
    return events;
}

std::vector<Event> EventDetector::spectral_detection(const SignalMatrix& data, double sample_rate) {
    std::vector<Event> events;
    
    for (int ch = 0; ch < data.cols(); ++ch) {
        Signal channel = data.col(ch);
        auto psd = SignalProcessor::power_spectral_density(channel, sample_rate);
        
        auto peaks = SignalProcessor::detect_peaks(psd, config_.threshold_snr, 5);
        
        for (const auto& peak : peaks) {
            double freq = peak.first * sample_rate / channel.size();
            if (freq >= config_.min_frequency && freq <= config_.max_frequency) {
                Event event;
                event.type = EventType::VIBRATION;
                event.frequency_center = freq;
                event.amplitude = peak.second;
                event.channel_start = ch;
                event.channel_end = ch;
                event.snr = 10.0 * std::log10(peak.second / psd.mean());
                event.confidence = std::min(event.snr / config_.threshold_snr, 1.0);
                events.push_back(event);
            }
        }
    }
    
    return events;
}

std::vector<Event> EventDetector::merge_events(const std::vector<Event>& events) {
    if (events.size() <= 1) return events;
    
    std::vector<Event> sorted = events;
    std::sort(sorted.begin(), sorted.end(), [](const Event& a, const Event& b) {
        return a.timestamp < b.timestamp;
    });
    
    std::vector<Event> merged;
    merged.push_back(sorted[0]);
    
    for (size_t i = 1; i < sorted.size(); ++i) {
        Event& last = merged.back();
        if (sorted[i].timestamp - last.timestamp < config_.merge_gap_ms / 1000.0 &&
            std::abs(sorted[i].channel_start - last.channel_end) <= 2) {
            last.channel_end = std::max(last.channel_end, sorted[i].channel_end);
            last.amplitude = std::max(last.amplitude, sorted[i].amplitude);
            last.snr = std::max(last.snr, sorted[i].snr);
            last.confidence = std::max(last.confidence, sorted[i].confidence);
        } else {
            merged.push_back(sorted[i]);
        }
    }
    
    return merged;
}

bool EventDetector::meets_criteria(const Event& event) const {
    double duration = event.features.count("duration") ? event.features.at("duration") : 0.0;
    return event.snr >= config_.threshold_snr &&
           duration >= config_.min_duration_ms &&
           duration <= config_.max_duration_ms &&
           (event.channel_end - event.channel_start + 1) >= config_.min_channels;
}

double EventDetector::compute_event_snr(const Signal& waveform) const {
    double signal_power = waveform.array().square().mean();
    int noise_samples = waveform.size() / 10;
    if (noise_samples < 2) noise_samples = 2;
    
    Signal noise_region(noise_samples * 2);
    for (int i = 0; i < noise_samples; ++i) {
        noise_region(i) = waveform(i);
        noise_region(noise_samples + i) = waveform(waveform.size() - noise_samples + i);
    }
    double noise_power = noise_region.array().square().mean();
    
    if (noise_power < 1e-10) return 100.0;
    return 10.0 * std::log10(signal_power / noise_power);
}

} // namespace alakoro
