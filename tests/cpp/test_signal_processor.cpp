#include <gtest/gtest.h>
#include <alakoro/signal_processor.hpp>
#include <cmath>

using namespace alakoro;

class SignalProcessorTest : public ::testing::Test {
protected:
    void SetUp() override {
        int n = 1024;
        test_signal = Signal::Zero(n);
        for (int i = 0; i < n; ++i) {
            test_signal(i) = std::sin(2.0 * M_PI * 50.0 * i / 1000.0);
        }
    }
    
    Signal test_signal;
};

TEST_F(SignalProcessorTest, FFT_IFFT) {
    auto spectrum = SignalProcessor::fft(test_signal);
    auto recovered = SignalProcessor::ifft(spectrum);
    
    for (int i = 0; i < test_signal.size(); ++i) {
        EXPECT_NEAR(test_signal(i), recovered(i), 1e-10);
    }
}

TEST_F(SignalProcessorTest, RMS) {
    double rms = SignalProcessor::rms(test_signal);
    EXPECT_NEAR(rms, 1.0 / std::sqrt(2.0), 0.01);
}

TEST_F(SignalProcessorTest, PowerSpectrum) {
    auto ps = SignalProcessor::power_spectrum(test_signal);
    
    int expected_peak_idx = 50 * test_signal.size() / 1000;
    double max_val = 0;
    int max_idx = 0;
    for (int i = 0; i < ps.size(); ++i) {
        if (ps(i) > max_val) {
            max_val = ps(i);
            max_idx = i;
        }
    }
    EXPECT_NEAR(max_idx, expected_peak_idx, 2);
}

TEST_F(SignalProcessorTest, MovingAverage) {
    Signal ma = SignalProcessor::moving_average(test_signal, 10);
    
    EXPECT_EQ(ma.size(), test_signal.size());
    EXPECT_NEAR(ma.mean(), 0.0, 0.1);
}

TEST_F(SignalProcessorTest, WindowFunctions) {
    int size = 100;
    
    auto hann = SignalProcessor::create_window(size, WindowType::HANN);
    auto hamming = SignalProcessor::create_window(size, WindowType::HAMMING);
    auto blackman = SignalProcessor::create_window(size, WindowType::BLACKMAN);
    
    EXPECT_EQ(hann.size(), size);
    EXPECT_EQ(hamming.size(), size);
    EXPECT_EQ(blackman.size(), size);
    
    for (int i = 0; i < size; ++i) {
        EXPECT_GE(hann(i), 0.0);
        EXPECT_LE(hann(i), 1.0);
    }
}
