cmake_minimum_required(VERSION 3.14)
project(Alakoro_FiberSense VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Options
option(BUILD_TESTS "Build tests" ON)
option(BUILD_PYTHON_BINDINGS "Build Python bindings with pybind11" ON)

# Find packages
find_package(Eigen3 3.3 REQUIRED NO_MODULE)
find_package(Threads REQUIRED)

# Core C++ library
add_library(alakoro_core STATIC
    src/cpp/core/signal_processor.cpp
    src/cpp/core/das_decoder.cpp
    src/cpp/core/filter_bank.cpp
    src/cpp/core/event_detector.cpp
)

target_include_directories(alakoro_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/src/cpp/include
)

target_link_libraries(alakoro_core PUBLIC
    Eigen3::Eigen
    Threads::Threads
)

# Python bindings with pybind11
if(BUILD_PYTHON_BINDINGS)
    add_subdirectory(extern/pybind11)
    pybind11_add_module(alakoro_bindings
        src/cpp/bindings/bindings.cpp
        src/cpp/bindings/signal_processor_binding.cpp
        src/cpp/bindings/das_decoder_binding.cpp
        src/cpp/bindings/event_detector_binding.cpp
    )
    target_link_libraries(alakoro_bindings PRIVATE alakoro_core)
    set_target_properties(alakoro_bindings PROPERTIES OUTPUT_NAME "alakoro")
endif()

# Tests
if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests/cpp)
endif()
