#include <gtest/gtest.h>
#include <alakoro/das_decoder.hpp>
#include <filesystem>
#include <fstream>

using namespace alakoro;
namespace fs = std::filesystem;

class DASDecoderTest : public ::testing::Test {
protected:
    void SetUp() override {
        test_file = "test_das.raw";
        std::ofstream file(test_file, std::ios::binary);
        
        int num_samples = 100;
        int num_channels = 10;
        file.write(reinterpret_cast<const char*>(&num_samples), sizeof(int));
        file.write(reinterpret_cast<const char*>(&num_channels), sizeof(int));
        
        for (int i = 0; i < num_samples; ++i) {
            for (int j = 0; j < num_channels; ++j) {
                double val = static_cast<double>(i * num_channels + j);
                file.write(reinterpret_cast<const char*>(&val), sizeof(double));
            }
        }
        file.close();
        
        decoder = std::make_unique<DASDecoder>(DASFormat::ALAKORO_RAW);
    }
    
    void TearDown() override {
        if (fs::exists(test_file)) {
            fs::remove(test_file);
        }
    }
    
    std::string test_file;
    std::unique_ptr<DASDecoder> decoder;
};

TEST_F(DASDecoderTest, DecodeFile) {
    auto frames = decoder->decode_file(test_file);
    
    EXPECT_EQ(frames.size(), 1);
    EXPECT_EQ(frames[0].data.rows(), 100);
    EXPECT_EQ(frames[0].data.cols(), 10);
}

TEST_F(DASDecoderTest, ComputeSNR) {
    auto frames = decoder->decode_file(test_file);
    double snr = decoder->compute_snr(frames[0].data);
    
    EXPECT_GT(snr, 0.0);
}

TEST_F(DASDecoderTest, DetectDeadChannels) {
    auto frames = decoder->decode_file(test_file);
    auto dead = decoder->detect_dead_channels(frames[0].data, 1e-6);
    
    EXPECT_EQ(dead.size(), 0);
}

TEST_F(DASDecoderTest, Streaming) {
    EXPECT_FALSE(decoder->is_streaming());
    
    decoder->start_stream(test_file);
    EXPECT_TRUE(decoder->is_streaming());
    
    decoder->stop_stream();
    EXPECT_FALSE(decoder->is_streaming());
}

TEST_F(DASDecoderTest, FormatConfiguration) {
    decoder->set_format(DASFormat::SILIXA_HDF5);
    EXPECT_NO_THROW(decoder->set_format(DASFormat::ALAKORO_RAW));
}
