cmake_minimum_required(VERSION 3.14)
project(alakoro_engine VERSION 2.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Options
option(BUILD_PYTHON_BINDINGS "Build Python bindings" ON)
option(BUILD_TESTS "Build tests" OFF)

# Core library
add_library(alakoro_core STATIC
    src/signal_processor.cpp
    src/wavelet_transforms.cpp
)

target_include_directories(alakoro_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

# Python bindings
if(BUILD_PYTHON_BINDINGS)
    # Find pybind11
    find_package(pybind11 QUIET)
    if(NOT pybind11_FOUND)
        include(FetchContent)
        FetchContent_Declare(
            pybind11
            GIT_REPOSITORY https://github.com/pybind/pybind11.git
            GIT_TAG v2.11.1
        )
        FetchContent_MakeAvailable(pybind11)
    endif()

    pybind11_add_module(alakoro_engine py_bindings.cpp)
    target_link_libraries(alakoro_engine PRIVATE alakoro_core)
    set_target_properties(alakoro_engine PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
endif()

# Tests
if(BUILD_TESTS)
    enable_testing()
    add_executable(test_engine tests/test_engine.cpp)
    target_link_libraries(test_engine PRIVATE alakoro_core)
    add_test(NAME engine_tests COMMAND test_engine)
endif()
