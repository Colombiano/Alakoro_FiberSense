#pragma once

#include "alakoro/signal_processor.hpp"
#include <vector>
#include <memory>

namespace alakoro {

struct FilterBankConfig {
    int num_bands;
    double low_freq;
    double high_freq;
    int filter_order;
    double sample_rate;
    bool uniform_bands;
    std::vector<std::pair<double, double>> custom_bands;
};

class FilterBank {
public:
    explicit FilterBank(const FilterBankConfig& config);
    ~FilterBank() = default;

    // Analysis and synthesis
    std::vector<Signal> analyze(const Signal& signal);
    Signal synthesize(const std::vector<Signal>& subbands);
    
    // Individual band processing
    Signal get_band(const Signal& signal, int band_index);
    SignalMatrix get_all_bands(const SignalMatrix& signals);
    
    // Configuration
    std::vector<std::pair<double, double>> get_band_edges() const;
    int get_num_bands() const;
    double get_center_frequency(int band_index) const;
    
    // Reconfiguration
    void set_band_edges(const std::vector<std::pair<double, double>>& edges);
    void set_band_gain(int band_index, double gain);

private:
    FilterBankConfig config_;
    std::vector<std::pair<double, double>> band_edges_;
    std::vector<double> band_gains_;
    std::vector<Signal> filter_coefficients_;
    
    void design_filters();
    void compute_band_edges();
};

} // namespace alakoro
