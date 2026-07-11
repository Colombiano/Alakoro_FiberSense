#include "alakoro/filter_bank.hpp"
#include "alakoro/signal_processor.hpp"
#include <cmath>

namespace alakoro {

FilterBank::FilterBank(const FilterBankConfig& config) : config_(config) {
    band_gains_.resize(config.num_bands, 1.0);
    compute_band_edges();
    design_filters();
}

void FilterBank::compute_band_edges() {
    band_edges_.clear();
    
    if (!config_.custom_bands.empty()) {
        band_edges_ = config_.custom_bands;
        return;
    }
    
    double low = config_.low_freq;
    double high = config_.high_freq;
    int num = config_.num_bands;
    
    if (config_.uniform_bands) {
        double step = (high - low) / num;
        for (int i = 0; i < num; ++i) {
            band_edges_.push_back({low + i * step, low + (i + 1) * step});
        }
    } else {
        double log_low = std::log10(low > 0 ? low : 1.0);
        double log_high = std::log10(high);
        double step = (log_high - log_low) / num;
        
        for (int i = 0; i < num; ++i) {
            double f_low = std::pow(10.0, log_low + i * step);
            double f_high = std::pow(10.0, log_low + (i + 1) * step);
            band_edges_.push_back({f_low, f_high});
        }
    }
}

void FilterBank::design_filters() {
    filter_coefficients_.clear();
    int num_taps = config_.filter_order + 1;
    
    for (const auto& edge : band_edges_) {
        double center = (edge.first + edge.second) / 2.0;
        double bandwidth = edge.second - edge.first;
        
        Signal coeffs = Signal::Zero(num_taps);
        for (int n = 0; n < num_taps; ++n) {
            double h = (n == num_taps / 2) ? 2.0 * bandwidth / config_.sample_rate : 
                (std::sin(2.0 * M_PI * bandwidth * (n - num_taps / 2) / config_.sample_rate) / 
                 (M_PI * (n - num_taps / 2)));
            coeffs(n) = h * std::cos(2.0 * M_PI * center * (n - num_taps / 2) / config_.sample_rate);
        }
        filter_coefficients_.push_back(coeffs);
    }
}

std::vector<Signal> FilterBank::analyze(const Signal& signal) {
    std::vector<Signal> subbands;
    for (int i = 0; i < config_.num_bands; ++i) {
        Signal filtered = SignalProcessor::fir_filter(signal, filter_coefficients_[i]);
        subbands.push_back(filtered * band_gains_[i]);
    }
    return subbands;
}

Signal FilterBank::synthesize(const std::vector<Signal>& subbands) {
    if (subbands.empty()) return Signal();
    
    Signal result = Signal::Zero(subbands[0].size());
    for (const auto& subband : subbands) {
        result += subband;
    }
    return result;
}

Signal FilterBank::get_band(const Signal& signal, int band_index) {
    if (band_index < 0 || band_index >= config_.num_bands) {
        throw std::out_of_range("Band index out of range");
    }
    return SignalProcessor::fir_filter(signal, filter_coefficients_[band_index]);
}

SignalMatrix FilterBank::get_all_bands(const SignalMatrix& signals) {
    SignalMatrix all_bands(config_.num_bands, signals.cols());
    for (int j = 0; j < signals.cols(); ++j) {
        std::vector<Signal> bands = analyze(signals.col(j));
        for (int i = 0; i < config_.num_bands; ++i) {
            all_bands(i, j) = bands[i].mean();
        }
    }
    return all_bands;
}

std::vector<std::pair<double, double>> FilterBank::get_band_edges() const {
    return band_edges_;
}

int FilterBank::get_num_bands() const {
    return config_.num_bands;
}

double FilterBank::get_center_frequency(int band_index) const {
    if (band_index < 0 || band_index >= band_edges_.size()) {
        throw std::out_of_range("Band index out of range");
    }
    return (band_edges_[band_index].first + band_edges_[band_index].second) / 2.0;
}

void FilterBank::set_band_edges(const std::vector<std::pair<double, double>>& edges) {
    if (edges.size() != static_cast<size_t>(config_.num_bands)) {
        throw std::invalid_argument("Number of edges must match number of bands");
    }
    band_edges_ = edges;
    design_filters();
}

void FilterBank::set_band_gain(int band_index, double gain) {
    if (band_index < 0 || band_index >= config_.num_bands) {
        throw std::out_of_range("Band index out of range");
    }
    band_gains_[band_index] = gain;
}

} // namespace alakoro
