#include "alakoro/das_decoder.hpp"
#include <fstream>
#include <iostream>
#include <cmath>

namespace alakoro {

DASDecoder::DASDecoder() : format_(DASFormat::ALAKORO_RAW), streaming_(false) {}

DASDecoder::DASDecoder(DASFormat format) : format_(format), streaming_(false) {}

void DASDecoder::set_format(DASFormat format) {
    format_ = format;
}

void DASDecoder::set_custom_parser(std::function<DASFrame(const std::string&)> parser) {
    custom_parser_ = parser;
}

void DASDecoder::set_metadata(const DASMetadata& metadata) {
    metadata_ = metadata;
}

std::vector<DASFrame> DASDecoder::decode_file(const std::string& filepath) {
    switch (format_) {
        case DASFormat::SILIXA_HDF5:
            return decode_silixa_hdf5(filepath);
        case DASFormat::OPTASENSE_TDMS:
            return decode_optasense_tdms(filepath);
        case DASFormat::FEBUS_H5:
            return decode_febus_h5(filepath);
        case DASFormat::ALAKORO_RAW:
            return decode_alakoro_raw(filepath);
        case DASFormat::CUSTOM:
            if (custom_parser_) {
                return {custom_parser_(filepath)};
            }
            throw std::runtime_error("Custom parser not set");
        default:
            throw std::runtime_error("Unknown DAS format");
    }
}

DASMetadata DASDecoder::read_metadata(const std::string& filepath) {
    DASMetadata meta;
    meta.gauge_length = 10.2;
    meta.spatial_sampling = 1.0;
    meta.temporal_sampling = 1000.0;
    meta.pulse_width = 100.0;
    meta.num_channels = 1000;
    meta.num_samples = 10000;
    meta.start_distance = 0.0;
    meta.fiber_length = 1000.0;
    meta.unit = "strain_rate";
    meta.fiber_type = "SMF-28";
    return meta;
}

void DASDecoder::write_metadata(const std::string& filepath, const DASMetadata& metadata) {
    // Placeholder
}

void DASDecoder::start_stream(const std::string& source) {
    streaming_ = true;
}

void DASDecoder::stop_stream() {
    streaming_ = false;
}

bool DASDecoder::is_streaming() const {
    return streaming_;
}

SignalMatrix DASDecoder::apply_calibration(const SignalMatrix& raw_data, const Signal& calibration_vector) {
    SignalMatrix calibrated(raw_data.rows(), raw_data.cols());
    for (int i = 0; i < raw_data.cols(); ++i) {
        if (i < calibration_vector.size()) {
            calibrated.col(i) = raw_data.col(i) * calibration_vector(i);
        } else {
            calibrated.col(i) = raw_data.col(i);
        }
    }
    return calibrated;
}

Signal DASDecoder::compensate_attenuation(const Signal& channel_data, double alpha) {
    Signal compensated(channel_data.size());
    for (int i = 0; i < channel_data.size(); ++i) {
        double distance = i;
        compensated(i) = channel_data(i) * std::exp(alpha * distance);
    }
    return compensated;
}

double DASDecoder::compute_snr(const SignalMatrix& data) {
    double signal_power = 0.0;
    double noise_power = 0.0;
    
    for (int i = 0; i < data.rows(); ++i) {
        for (int j = 0; j < data.cols(); ++j) {
            signal_power += data(i, j) * data(i, j);
        }
    }
    
    for (int i = data.rows() / 2; i < data.rows(); ++i) {
        for (int j = 0; j < data.cols(); ++j) {
            noise_power += data(i, j) * data(i, j);
        }
    }
    
    if (noise_power < 1e-10) return 100.0;
    return 10.0 * std::log10(signal_power / noise_power);
}

SignalMatrix DASDecoder::compute_quality_map(const SignalMatrix& data) {
    SignalMatrix quality(data.rows(), data.cols());
    for (int j = 0; j < data.cols(); ++j) {
        Signal channel = data.col(j);
        double mean = channel.mean();
        double std = std::sqrt((channel.array() - mean).square().mean());
        for (int i = 0; i < data.rows(); ++i) {
            quality(i, j) = std::abs(data(i, j) - mean) / (std + 1e-10);
        }
    }
    return quality;
}

std::vector<int> DASDecoder::detect_dead_channels(const SignalMatrix& data, double threshold) {
    std::vector<int> dead_channels;
    for (int j = 0; j < data.cols(); ++j) {
        Signal channel = data.col(j);
        double variance = (channel.array() - channel.mean()).square().mean();
        if (variance < threshold) {
            dead_channels.push_back(j);
        }
    }
    return dead_channels;
}

std::vector<DASFrame> DASDecoder::decode_silixa_hdf5(const std::string& filepath) {
    std::vector<DASFrame> frames;
    DASFrame frame;
    frame.data = SignalMatrix::Random(1000, 100);
    frame.timestamp = 0.0;
    frame.frame_number = 0;
    frame.metadata = metadata_;
    frames.push_back(frame);
    return frames;
}

std::vector<DASFrame> DASDecoder::decode_optasense_tdms(const std::string& filepath) {
    std::vector<DASFrame> frames;
    DASFrame frame;
    frame.data = SignalMatrix::Random(1000, 100);
    frame.timestamp = 0.0;
    frame.frame_number = 0;
    frame.metadata = metadata_;
    frames.push_back(frame);
    return frames;
}

std::vector<DASFrame> DASDecoder::decode_febus_h5(const std::string& filepath) {
    std::vector<DASFrame> frames;
    DASFrame frame;
    frame.data = SignalMatrix::Random(1000, 100);
    frame.timestamp = 0.0;
    frame.frame_number = 0;
    frame.metadata = metadata_;
    frames.push_back(frame);
    return frames;
}

std::vector<DASFrame> DASDecoder::decode_alakoro_raw(const std::string& filepath) {
    std::vector<DASFrame> frames;
    std::ifstream file(filepath, std::ios::binary);
    
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + filepath);
    }
    
    int num_samples, num_channels;
    file.read(reinterpret_cast<char*>(&num_samples), sizeof(int));
    file.read(reinterpret_cast<char*>(&num_channels), sizeof(int));
    
    DASFrame frame;
    frame.data.resize(num_samples, num_channels);
    frame.timestamp = 0.0;
    frame.frame_number = 0;
    frame.metadata = metadata_;
    
    for (int i = 0; i < num_samples; ++i) {
        for (int j = 0; j < num_channels; ++j) {
            double value;
            file.read(reinterpret_cast<char*>(&value), sizeof(double));
            frame.data(i, j) = value;
        }
    }
    
    frames.push_back(frame);
    return frames;
}

DASFrame DASDecoder::decode_buffer(const std::vector<uint8_t>& buffer) {
    DASFrame frame;
    frame.data = SignalMatrix::Random(1000, 100);
    frame.timestamp = 0.0;
    frame.frame_number = 0;
    frame.metadata = metadata_;
    return frame;
}

} // namespace alakoro
