# Testes C++

include(FetchContent)
FetchContent_Declare(
    googletest
    URL https://github.com/google/googletest/archive/refs/tags/release-1.12.1.zip
)
FetchContent_MakeAvailable(googletest)

enable_testing()

add_executable(alakoro_tests
    test_signal_processor.cpp
    test_das_decoder.cpp
    test_event_detector.cpp
)

target_link_libraries(alakoro_tests
    alakoro_core
    GTest::gtest_main
    GTest::gtest
)

include(GoogleTest)
gtest_discover_tests(alakoro_tests)
