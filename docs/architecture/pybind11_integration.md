# Integração C++20 com Python via pybind11

Este documento descreve a camada C++20 do Alakoro FiberSense, entregue na **Fase 1** do cronograma.

## Objetivo

Fornecer estruturas de dados de alta performance e processadores de sinal que possam ser usados diretamente a partir de Python, com:

- **Zero-copy** entre C++ e NumPy (buffer protocol)
- **Metaprogramação moderna** com C++20
- **Código especializado** em tempo de compilação para cada modalidade (DAS/DTS/DSS) e precisão (float/double)

## Estrutura de Diretórios

```text
src/cpp/
├── CMakeLists.txt              # Build C++20 com pybind11
├── include/alakoro/
│   ├── concepts.hpp            # Concepts C++20
│   ├── core.hpp                # SensingData, DASData, DTSData, DSSData
│   ├── processors.hpp          # detrend, demean, taper, decimate
│   ├── filters.hpp             # Butterworth lowpass/highpass/bandpass
│   ├── fft.hpp                 # FFT, magnitude spectrum, PSD
│   ├── wavelet.hpp             # CWT (Morlet, Ricker)
│   └── serialization.hpp       # JSON-LD, Avro/Protobuf stubs
├── src/
│   └── bindings.cpp            # Bindings pybind11
└── tests/
    └── test_core.cpp           # Testes C++ (opcional)

alakoro_core/
├── __init__.py                 # Pacote Python que carrega _alakoro_core
└── _alakoro_core*.so           # Extensão nativa compilada
```

## Recursos de C++20 Utilizados

### 1. Concepts (`concepts.hpp`)

Restringimos templates a tipos que fazem sentido físico:

```cpp
template <typename T>
concept NumericScalar = std::is_arithmetic_v<T> &&
                        !std::is_same_v<T, bool> &&
                        !std::is_same_v<T, char>;
```

Isso evita mensagens de erro confusas quando alguém tenta usar, por exemplo, `DASData<std::string>`.

### 2. `if constexpr` para Especialização

No lugar de herança polimórfica, usamos `if constexpr` para especializar comportamentos em tempo de compilação:

```cpp
constexpr std::string_view modality_str() const noexcept {
    if constexpr (M == SensingModality::DAS) return "DAS";
    else if constexpr (M == SensingModality::DTS) return "DTS";
    else return "DSS";
}
```

O compilador elimina os branches não utilizados, gerando código tão eficiente quanto uma implementação manual por modalidade.

### 3. `std::span` para Views Zero-Copy

As classes expõem seus dados internos como `std::span<T>`:

```cpp
std::span<T> data() { return std::span<T>(data_); }
std::span<T> row(std::size_t t) { ... }
```

Isso permite que pybind11 implemente o buffer protocol sem cópia de memória.

### 4. Type Traits para Unidades

Usamos traits para definir unidades padrão por modalidade:

```cpp
template <>
struct ModalityTraits<SensingModality::DAS> {
    static constexpr std::string_view default_units = "strain_rate";
};
```

## Uso em Python

```python
import numpy as np
from alakoro_core import DASData, detrend, decimate

# Criar dados
das = DASData(n_times=1000, n_channels=64)
das.metadata.sampling_rate_hz = 1000.0
das.metadata.units = "strain_rate"

# View NumPy zero-copy
arr = np.array(das, copy=False)
arr[:, :] = np.random.randn(1000, 64)

# Processadores C++20
detrend(das)
reduced = decimate(das, factor=10)

# Serializar
jsonld = das.to_jsonld()
```

## Build

### Requisitos

- C++20 compiler (g++ 11+, clang++ 13+, MSVC 2019+)
- CMake >= 3.16
- pybind11

### Instalação em modo desenvolvimento

```bash
pip install -e .
```

### Build manual com CMake

```bash
cd src/cpp
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --parallel
```

## Testes

```bash
pytest tests/test_cpp_core.py tests/test_advanced_processors.py -v
```

## Próximos Passos

- [ ] Implementar serialização Avro e Protobuf (`-DALAKORO_WITH_AVRO=ON`)
- [x] Adicionar processadores avançados: pass_filter Butterworth, FFT, wavelets (concluído na v2.7.0)
- [ ] Integrar `alakoro_core` com `src.io.dascore` para conversão zero-copy Alakoro ↔ DASCore Patch
