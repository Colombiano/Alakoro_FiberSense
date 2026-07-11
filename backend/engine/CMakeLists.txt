cmake_minimum_required(VERSION 3.20)
project(alakoro_engine VERSION 2.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find pybind11
find_package(pybind11 REQUIRED)

# Find Python
find_package(Python3 REQUIRED COMPONENTS Development)

# Source files
set(SOURCES
    src/signal_processor.cpp
    py_bindings.cpp
)

# Create Python module
pybind11_add_module(alakoro_engine ${SOURCES})

target_include_directories(alakoro_engine PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${Python3_INCLUDE_DIRS}
)

target_link_libraries(alakoro_engine PRIVATE
    Python3::Python
)

# Set properties
set_target_properties(alakoro_engine PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/build
)

# Enable optimizations
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(alakoro_engine PRIVATE -O3 -march=native -ffast-math)
elseif(MSVC)
    target_compile_options(alakoro_engine PRIVATE /O2)
endif()

# Install
install(TARGETS alakoro_engine DESTINATION .)
