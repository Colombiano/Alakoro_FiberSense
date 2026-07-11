#pragma once

#include "alakoro/signal_processor.hpp"
#include <string>
#include <functional>
#include <map>

namespace alakoro {

enum class DASFormat {
    SILIXA_HDF5,
    OPTASENSE_TDMS,
    FEBUS_H5,
    ALAKORO_RAW,
    CUSTOM
};

struct DASMetadata {
    double gauge_length;
    double spatial_sampling;
    double temporal_sampling;
    double pulse_width;
    int num_channels;
    int num_samples;
    double start_distance;
    double fiber_length;
    std::string unit;
    std::string fiber_type;
    std::map<std::string, std::string> custom_fields;
};

struct DASFrame {
    SignalMatrix data;
    double timestamp;
    int frame_number;
    DASMetadata metadata;
};

class DASDecoder {
public:
    DASDecoder();
    explicit DASDecoder(DASFormat format);
    ~DASDecoder() = default;

    // Configuration
    void set_format(DASFormat format);
    void set_custom_parser(std::function<DASFrame(const std::string&)> parser);
    void set_metadata(const DASMetadata& metadata);
    
    // File I/O
    std::vector<DASFrame> decode_file(const std::string& filepath);
    DASFrame decode_buffer(const std::vector<uint8_t>& buffer);
    
    // Metadata handling
    DASMetadata read_metadata(const std::string& filepath);
    void write_metadata(const std::string& filepath, const DASMetadata& metadata);
    
    // Streaming
    void start_stream(const std::string& source);
    void stop_stream();
    bool is_streaming() const;
    std::function<void(const DASFrame&)> on_frame_received;
    
    // Calibration
    SignalMatrix apply_calibration(const SignalMatrix& raw_data, const Signal& calibration_vector);
    Signal compensate_attenuation(const Signal& channel_data, double alpha);
    
    // Quality metrics
    double compute_snr(const SignalMatrix& data);
    SignalMatrix compute_quality_map(const SignalMatrix& data);
    std::vector<int> detect_dead_channels(const SignalMatrix& data, double threshold);

private:
    DASFormat format_;
    DASMetadata metadata_;
    bool streaming_;
    std::function<DASFrame(const std::string&)> custom_parser_;
    
    std::vector<DASFrame> decode_silixa_hdf5(const std::string& filepath);
    std::vector<DASFrame> decode_optasense_tdms(const std::string& filepath);
    std::vector<DASFrame> decode_febus_h5(const std::string& filepath);
    std::vector<DASFrame> decode_alakoro_raw(const std::string& filepath);
};

} // namespace alakoro
