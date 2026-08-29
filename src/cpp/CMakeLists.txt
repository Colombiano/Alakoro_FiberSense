# Alakoro FiberSense — C++20 Extension Build
#
# Este CMake configura a extensão Python usando pybind11.
# Recursos C++20 usados:
#   - concepts, if constexpr, std::span, std::optional, constexpr std::string_view
#
# Uso manual:
#   mkdir build && cd build
#   cmake .. -DCMAKE_BUILD_TYPE=Release
#   cmake --build . --parallel

cmake_minimum_required(VERSION 3.16)
project(alakoro_core CXX)

# ─── C++20 é obrigatório ───
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ─── Opções de build ───
option(BUILD_TESTS "Build C++ unit tests" OFF)
option(ALAKORO_WITH_AVRO "Enable Apache Avro serialization" OFF)
option(ALAKORO_WITH_PROTOBUF "Enable Protobuf serialization" OFF)

# ─── Flags rigorosas para garantir qualidade ───
if(MSVC)
    add_compile_options(/W4 /permissive-)
else()
    add_compile_options(-Wall -Wextra -Wpedantic)
    if(CMAKE_BUILD_TYPE STREQUAL "Release")
        add_compile_options(-O3)
    endif()
endif()

# ─── pybind11 ───
# scikit-build-core injeta o pybind11 no CMAKE_PREFIX_PATH automaticamente.
# Para build manual, certifique-se de que pybind11 esteja instalado:
#   pip install pybind11
find_package(pybind11 CONFIG REQUIRED)

# ─── Extensão Python principal ───
pybind11_add_module(
    _alakoro_core
    src/bindings.cpp
)

target_include_directories(_alakoro_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# O módulo nativo será importado por alakoro_core/__init__.py
set_target_properties(_alakoro_core PROPERTIES
    OUTPUT_NAME "_alakoro_core"
)

# ─── Instalação no pacote Python ───
install(TARGETS _alakoro_core
    LIBRARY DESTINATION alakoro_core
    RUNTIME DESTINATION alakoro_core
)
