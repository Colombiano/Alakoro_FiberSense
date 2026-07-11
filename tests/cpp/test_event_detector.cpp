#include <gtest/gtest.h>
#include <alakoro/event_detector.hpp>
#include <cmath>

using namespace alakoro;

class EventDetectorTest : public ::testing::Test {
protected:
    void SetUp() override {
        int num_samples = 1000;
        int num_channels = 100;
        test_data = SignalMatrix::Zero(num_samples, num_channels);
        
        for (int i = 0; i < num_samples; ++i) {
            for (int j = 0; j < num_channels; ++j) {
                test_data(i, j) = 0.01 * (static_cast<double>(rand()) / RAND_MAX - 0.5);
            }
        }
        
        for (int ch = 40; ch < 60; ++ch) {
            for (int i = 0; i < num_samples; ++i) {
                test_data(i, ch) += 0.5 * std::sin(2.0 * M_PI * 50.0 * i / 1000.0);
            }
        }
        
        detector = std::make_unique<EventDetector>();
    }
    
    SignalMatrix test_data;
    std::unique_ptr<EventDetector> detector;
};

TEST_F(EventDetectorTest, DetectEvents) {
    auto events = detector->detect_events(test_data, 1000.0);
    
    EXPECT_GT(events.size(), 0);
}

TEST_F(EventDetectorTest, EventConfig) {
    DetectorConfig config;
    config.threshold_snr = 5.0;
    config.min_duration_ms = 5.0;
    config.max_duration_ms = 10000.0;
    
    detector->set_config(config);
    auto retrieved = detector->get_config();
    
    EXPECT_EQ(retrieved.threshold_snr, 5.0);
    EXPECT_EQ(retrieved.min_duration_ms, 5.0);
}

TEST_F(EventDetectorTest, ResetAndCount) {
    detector->detect_events(test_data, 1000.0);
    
    int count = detector->get_event_count();
    EXPECT_GT(count, 0);
    
    detector->reset();
    EXPECT_EQ(detector->get_event_count(), 0);
}

TEST_F(EventDetectorTest, EventHistory) {
    detector->detect_events(test_data, 1000.0);
    
    auto history = detector->get_event_history();
    EXPECT_GT(history.size(), 0);
    
    detector->clear_history();
    EXPECT_EQ(detector->get_event_history().size(), 0);
}

TEST_F(EventDetectorTest, ExtractFeatures) {
    Signal waveform = Signal::LinSpaced(1000, 0, 1);
    auto features = detector->extract_features(waveform, 1000.0);
    
    EXPECT_GT(features.size(), 0);
    EXPECT_TRUE(features.count("rms") > 0);
    EXPECT_TRUE(features.count("peak_amplitude") > 0);
}

TEST_F(EventDetectorTest, ClassifyEvent) {
    detector->detect_events(test_data, 1000.0);
    auto history = detector->get_event_history();
    
    if (!history.empty()) {
        auto classification = detector->classify_event(history[0]);
        EXPECT_TRUE(
            classification == EventType::VIBRATION ||
            classification == EventType::FLOW ||
            classification == EventType::FRACTURE ||
            classification == EventType::CUSTOM
        );
    }
}
