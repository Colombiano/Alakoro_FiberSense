# Metaprogramação em C++20 no Alakoro FiberSense / C++20 Metaprogramming in Alakoro FiberSense

> 🇧🇷 **PT** — Guia técnico e didático sobre como o núcleo C++20 do Alakoro usa
> metaprogramação para gerar código seguro, rápido e especializado para
> análise de dados de fibra óptica (DAS, DTS, DSS).
>
> 🇺🇸 **EN** — Technical, didactic guide on how the Alakoro C++20 core uses
> metaprogramming to generate safe, fast, and specialized code for
> distributed fiber optic sensing data analysis (DAS, DTS, DSS).

---

## 1. O que é metaprogramação em C++? / What is metaprogramming in C++?

🇧🇷 **PT**

**Metaprogramação** é a capacidade de um programa escrever ou inspecionar
outro programa — incluindo a si mesmo — **em tempo de compilação**.

Em C++, isso é feito principalmente com **templates**. Um template não é uma
função/classe concreta: é um *molde* a partir do qual o compilador gera
versões específicas quando encontra um uso. Combinados com os recursos do
C++20, os templates deixam de ser apenas "cópia e cola tipada" e se tornam
uma ferramenta poderosa de:

- **Restrição de tipos** (`concepts`);
- **Decisões em tempo de compilação** (`if constexpr`);
- **Geração de código para listas arbitrárias de tipos/valores** (templates
  variádicos e *fold expressions*);
- **Cálculo de valores em tempo de compilação** (`constexpr`,
  `std::string_view`).

No Alakoro, isso se traduz em: o mesmo algoritmo de processamento de sinal é
compilado de forma otimizada para `float` ou `double`, para DAS, DTS ou DSS,
e as 15 regras de eventos são conhecidas pelo compilador, que pode gerar
uma *engine* sob medida com apenas as regras selecionadas.

🇺🇸 **EN**

**Metaprogramming** is the ability of a program to write or inspect
another program — including itself — **at compile time**.

In C++, this is done mainly with **templates**. A template is not a concrete
function or class: it is a *mold* from which the compiler generates specific
versions whenever it finds a usage. Combined with C++20 features, templates
cease to be mere "typed copy-and-paste" and become a powerful tool for:

- **Type constraints** (`concepts`);
- **Compile-time decisions** (`if constexpr`);
- **Code generation for arbitrary lists of types/values** (variadic templates
  and *fold expressions*);
- **Compile-time value computation** (`constexpr`, `std::string_view`).

In Alakoro, this means: the same signal-processing algorithm is compiled in an
optimized way for `float` or `double`, for DAS, DTS, or DSS, and the 15 event
rules are known to the compiler, which can generate a tailor-made *engine*
with only the selected rules.

---

## 2. Recursos de C++20 usados no Alakoro / C++20 features used in Alakoro

### 2.1 `concepts` — restrições de tipo claras / `concepts` — clear type constraints

🇧🇷 **PT**

Antes do C++20, restringir um template a tipos numéricos exigia técnicas como
SFINAE (`std::enable_if`), que produzem mensagens de erro enormas e
confusas. Com `concepts`, escrevemos **requisitos nomeados** que o
compilador pode verificar e reportar de forma legível.

#### Exemplo mínimo

```cpp
#include <concepts>
#include <type_traits>

// Concept: aceita qualquer tipo aritmético, exceto bool e char.
template <typename T>
concept NumeroUtil = std::is_arithmetic_v<T> &&
                     !std::is_same_v<T, bool> &&
                     !std::is_same_v<T, char>;

// Só compila se T satisfizer NumeroUtil.
template <NumeroUtil T>
T dobro(T x) {
    return 2 * x;
}

// int compila...
auto a = dobro(21);

// std::string não compila: erro claro e curto.
// auto b = dobro(std::string{"x"});
```

#### No Alakoro: `src/cpp/include/alakoro/concepts.hpp`

```cpp
// src/cpp/include/alakoro/concepts.hpp:25-30
template <typename T>
concept NumericScalar = std::is_arithmetic_v<T> &&
                        !std::is_same_v<T, bool> &&
                        !std::is_same_v<T, char> &&
                        !std::is_same_v<T, signed char> &&
                        !std::is_same_v<T, unsigned char>;
```

Esse concept garante que os dados de sensing (`float`, `double`, `int` etc.)
representem grandezas físicas. Se um desenvolvedor tentar criar
`SensingData<std::string, ...>`, o erro será imediato e compreensível.

Outros concepts do projeto:

```cpp
// src/cpp/include/alakoro/concepts.hpp:38-39
template <typename T>
concept FloatingPoint = std::floating_point<T>;

// src/cpp/include/alakoro/concepts.hpp:44-45
template <typename T>
concept IndexType = std::integral<T> && !std::is_same_v<T, bool>;
```

E em `core.hpp` há o `AnySensingData`, que verifica a **interface** de uma
classe em vez de uma hierarquia de herança:

```cpp
// src/cpp/include/alakoro/core.hpp:216-222
template <typename U>
concept AnySensingData = requires(U u) {
    { U::modality } -> std::convertible_to<SensingModality>;
    { u.n_times() } -> std::convertible_to<std::size_t>;
    { u.n_channels() } -> std::convertible_to<std::size_t>;
    { u.data() } -> std::convertible_to<std::span<typename U::value_type>>;
};
```

Esse pattern é conhecido como **structural typing**: se o tipo se comporta
como um `SensingData`, ele *é* um `SensingData` para os algoritmos.

🇺🇸 **EN**

Before C++20, constraining a template to numeric types required techniques
like SFINAE (`std::enable_if`), which produce huge and confusing error
messages. With `concepts`, we write **named requirements** that the compiler
can check and report in a readable way.

#### Minimal example

```cpp
#include <concepts>
#include <type_traits>

// Concept: accepts any arithmetic type except bool and char.
template <typename T>
concept NumeroUtil = std::is_arithmetic_v<T> &&
                     !std::is_same_v<T, bool> &&
                     !std::is_same_v<T, char>;

// Only compiles if T satisfies NumeroUtil.
template <NumeroUtil T>
T dobro(T x) {
    return 2 * x;
}

// int compiles...
auto a = dobro(21);

// std::string does not compile: clear and short error.
// auto b = dobro(std::string{"x"});
```

#### In Alakoro: `src/cpp/include/alakoro/concepts.hpp`

```cpp
// src/cpp/include/alakoro/concepts.hpp:25-30
template <typename T>
concept NumericScalar = std::is_arithmetic_v<T> &&
                        !std::is_same_v<T, bool> &&
                        !std::is_same_v<T, char> &&
                        !std::is_same_v<T, signed char> &&
                        !std::is_same_v<T, unsigned char>;
```

This concept ensures that sensing data (`float`, `double`, `int`, etc.)
represent physical quantities. If a developer tries to create
`SensingData<std::string, ...>`, the error is immediate and understandable.

Other concepts in the project:

```cpp
// src/cpp/include/alakoro/concepts.hpp:38-39
template <typename T>
concept FloatingPoint = std::floating_point<T>;

// src/cpp/include/alakoro/concepts.hpp:44-45
template <typename T>
concept IndexType = std::integral<T> && !std::is_same_v<T, bool>;
```

And in `core.hpp` there is `AnySensingData`, which checks the **interface**
of a class rather than an inheritance hierarchy:

```cpp
// src/cpp/include/alakoro/core.hpp:216-222
template <typename U>
concept AnySensingData = requires(U u) {
    { U::modality } -> std::convertible_to<SensingModality>;
    { u.n_times() } -> std::convertible_to<std::size_t>;
    { u.n_channels() } -> std::convertible_to<std::size_t>;
    { u.data() } -> std::convertible_to<std::span<typename U::value_type>>;
};
```

This pattern is known as **structural typing**: if a type behaves like a
`SensingData`, it *is* a `SensingData` for the algorithms.

---

### 2.2 `if constexpr` — decisões em tempo de compilação / `if constexpr` — compile-time decisions

🇧🇷 **PT**

`if constexpr` executa **apenas um ramo** em tempo de compilação. O ramo
falso é *descartado* — não precisa nem compilar. Isso substitui
especializações excessivas de templates em muitos casos.

#### Exemplo mínimo

```cpp
#include <string>

template <typename T>
auto descricao() {
    if constexpr (std::is_integral_v<T>) {
        return "inteiro";
    } else if constexpr (std::is_floating_point_v<T>) {
        return "ponto flutuante";
    } else {
        return "outro";
    }
}

static_assert(descricao<int>() == "inteiro");
```

#### No Alakoro: `src/cpp/include/alakoro/core.hpp`

```cpp
// src/cpp/include/alakoro/core.hpp:180-184
constexpr std::string_view modality_str() const noexcept {
    if constexpr (M == SensingModality::DAS) return "DAS";
    else if constexpr (M == SensingModality::DTS) return "DTS";
    else return "DSS";
}
```

Como `M` é um valor de template conhecido na compilação, o compilador elimina
os ramos não utilizados. Para `SensingData<float, SensingModality::DTS>`, só
sobra `return "DTS";`. Não há custo de `switch` em tempo de execução nem
polimorfismo dinâmico.

Outro uso importante é em `filters.hpp`, onde a ordem do filtro é um
parâmetro de template:

```cpp
// src/cpp/include/alakoro/filters.hpp:124-136
void compute_coefficients(double w1, double w2) {
    if constexpr (Order == 1) {
        compute_first_order(w1, w2);
    } else if constexpr (Order == 2) {
        compute_second_order(w1, w2);
    } else {
        // Fallback: aproximação por seções de 2ª ordem.
        compute_second_order(w1, w2);
    }
}
```

O ramo inválido para a ordem escolhida é removido, permitindo que cada
instanciação do filtro tenha o caminho mais direto possível.

🇺🇸 **EN**

`if constexpr` executes **only one branch** at compile time. The false branch
is *discarded* — it does not even need to compile. This replaces excessive
template specializations in many cases.

#### Minimal example

```cpp
#include <string>

template <typename T>
auto descricao() {
    if constexpr (std::is_integral_v<T>) {
        return "inteiro";
    } else if constexpr (std::is_floating_point_v<T>) {
        return "ponto flutuante";
    } else {
        return "outro";
    }
}

static_assert(descricao<int>() == "inteiro");
```

#### In Alakoro: `src/cpp/include/alakoro/core.hpp`

```cpp
// src/cpp/include/alakoro/core.hpp:180-184
constexpr std::string_view modality_str() const noexcept {
    if constexpr (M == SensingModality::DAS) return "DAS";
    else if constexpr (M == SensingModality::DTS) return "DTS";
    else return "DSS";
}
```

Because `M` is a template value known at compile time, the compiler eliminates
the unused branches. For `SensingData<float, SensingModality::DTS>`, only
`return "DTS";` remains. There is no runtime `switch` cost and no dynamic
polymorphism.

Another important use is in `filters.hpp`, where the filter order is a
template parameter:

```cpp
// src/cpp/include/alakoro/filters.hpp:124-136
void compute_coefficients(double w1, double w2) {
    if constexpr (Order == 1) {
        compute_first_order(w1, w2);
    } else if constexpr (Order == 2) {
        compute_second_order(w1, w2);
    } else {
        // Fallback: approximation by 2nd-order sections.
        compute_second_order(w1, w2);
    }
}
```

The invalid branch for the chosen order is removed, allowing each filter
instantiation to take the most direct path possible.

---

### 2.3 Variadic templates — templates com número arbitrário de argumentos / Variadic templates — templates with an arbitrary number of arguments

🇧🇷 **PT**

`template <typename... Args>` (ou valores: `template <int... Values>`)
permitem que uma classe/função aceite uma **lista variável** de tipos ou
valores em tempo de compilação.

#### Exemplo mínimo

```cpp
#include <iostream>

template <typename... Args>
void imprimir(Args... args) {
    ((std::cout << args << ' '), ...);   // fold expression
}

imprimir(1, 2.5, "texto");  // gera: imprimir<int, double, const char*>
```

#### No Alakoro: `src/cpp/include/alakoro/inference_engine.hpp`

A `InferenceEngine` é parametrizada por uma lista de eventos canônicos:

```cpp
// src/cpp/include/alakoro/inference_engine.hpp:1248-1249
template <CanonicalEvent... Events>
class InferenceEngine {
public:
    static_assert(sizeof...(Events) > 0,
                  "InferenceEngine precisa de pelo menos um evento.");
    // ...
};
```

Isso permite criar engines especializadas, como:

```cpp
// Engine com todos os 15 eventos.
using CanonicalInferenceEngine = InferenceEngine<
    CanonicalEvent::JouleThomson,
    CanonicalEvent::SlopeVelocity,
    // ... etc
    CanonicalEvent::CementChanneling
>;

// Engine customizada: apenas termal.
using ThermalEngine = InferenceEngine<
    CanonicalEvent::JouleThomson,
    CanonicalEvent::WarmBack,
    CanonicalEvent::LeakPath
>;
```

Cada instância é um **tipo diferente** e o compilador gera código apenas
para as regras solicitadas.

🇺🇸 **EN**

`template <typename... Args>` (or values: `template <int... Values>`) allows a
class or function to accept a **variable-length list** of types or values at
compile time.

#### Minimal example

```cpp
#include <iostream>

template <typename... Args>
void imprimir(Args... args) {
    ((std::cout << args << ' '), ...);   // fold expression
}

imprimir(1, 2.5, "texto");  // generates: imprimir<int, double, const char*>
```

#### In Alakoro: `src/cpp/include/alakoro/inference_engine.hpp`

`InferenceEngine` is parameterized by a list of canonical events:

```cpp
// src/cpp/include/alakoro/inference_engine.hpp:1248-1249
template <CanonicalEvent... Events>
class InferenceEngine {
public:
    static_assert(sizeof...(Events) > 0,
                  "InferenceEngine precisa de pelo menos um evento.");
    // ...
};
```

This enables specialized engines such as:

```cpp
// Engine with all 15 events.
using CanonicalInferenceEngine = InferenceEngine<
    CanonicalEvent::JouleThomson,
    CanonicalEvent::SlopeVelocity,
    // ... etc
    CanonicalEvent::CementChanneling
>;

// Custom engine: thermal only.
using ThermalEngine = InferenceEngine<
    CanonicalEvent::JouleThomson,
    CanonicalEvent::WarmBack,
    CanonicalEvent::LeakPath
>;
```

Each instance is a **different type**, and the compiler generates code only
for the requested rules.

---

### 2.4 Fold expressions — dobrar listas de parâmetros / Fold expressions — folding parameter lists

🇧🇷 **PT**

Fold expressions permitem aplicar um operador a todos os elementos de um
*parameter pack* sem recursão explícita. A sintaxe `(f(args), ...)` executa
`f(arg1), f(arg2), f(arg3), ...`.

#### Exemplo mínimo

```cpp
template <typename... Ts>
void chamar_todos(Ts... ts) {
    (ts.processar(), ...);  // expande para t1.processar(), t2.processar(), ...
}
```

#### No Alakoro: `src/cpp/include/alakoro/inference_engine.hpp`

```cpp
// src/cpp/include/alakoro/inference_engine.hpp:1262-1266
std::vector<InferenceResult> infer(std::span<const double> dts,
                                   std::span<const double> das,
                                   std::size_t n_times,
                                   std::size_t n_channels,
                                   const InferenceMetadata& meta) const {
    std::vector<InferenceResult> all;
    all.reserve(sizeof...(Events));
    // Fold expression: executa execute_rule<E>() para cada E em Events...
    (execute_rule<Events>(dts, das, n_times, n_channels, meta, all), ...);
    return all;
}
```

A expressão `(execute_rule<Events>(...), ...)` é expandida pelo compilador
para uma sequência de chamadas, uma para cada evento na lista. Não há loop
em tempo de execução sobre a lista de eventos; a própria lista foi "dobrada"
no código gerado.

🇺🇸 **EN**

Fold expressions allow applying an operator to every element of a *parameter
pack* without explicit recursion. The syntax `(f(args), ...)` executes
`f(arg1), f(arg2), f(arg3), ...`.

#### Minimal example

```cpp
template <typename... Ts>
void chamar_todos(Ts... ts) {
    (ts.processar(), ...);  // expands to t1.processar(), t2.processar(), ...
}
```

#### In Alakoro: `src/cpp/include/alakoro/inference_engine.hpp`

```cpp
// src/cpp/include/alakoro/inference_engine.hpp:1262-1266
std::vector<InferenceResult> infer(std::span<const double> dts,
                                   std::span<const double> das,
                                   std::size_t n_times,
                                   std::size_t n_channels,
                                   const InferenceMetadata& meta) const {
    std::vector<InferenceResult> all;
    all.reserve(sizeof...(Events));
    // Fold expression: executes execute_rule<E>() for each E in Events...
    (execute_rule<Events>(dts, das, n_times, n_channels, meta, all), ...);
    return all;
}
```

The expression `(execute_rule<Events>(...), ...)` is expanded by the compiler
into a sequence of calls, one for each event in the list. There is no runtime
loop over the event list; the list itself has been "folded" into the
generated code.

---

### 2.5 `constexpr` e `std::string_view` — valores em tempo de compilação / `constexpr` and `std::string_view` — compile-time values

🇧🇷 **PT**

`constexpr` indica que uma função/variável pode ser avaliada em tempo de
compilação. `std::string_view` é uma visão não-proprietária sobre uma
sequência de caracteres, ideal para strings constantes: evita alocação e
cópia.

#### Exemplo mínimo

```cpp
#include <string_view>

constexpr std::string_view nome_do_evento(int id) {
    switch (id) {
        case 0:  return "joule_thomson";
        case 1:  return "slope_velocity";
        default: return "unknown";
    }
}

static_assert(nome_do_evento(0) == "joule_thomson");
```

#### No Alakoro: `src/cpp/include/alakoro/core.hpp`

```cpp
// src/cpp/include/alakoro/core.hpp:52-59
constexpr std::string_view modality_name(SensingModality m) noexcept {
    switch (m) {
        case SensingModality::DAS: return "DAS";
        case SensingModality::DTS: return "DTS";
        case SensingModality::DSS: return "DSS";
    }
    return "unknown";
}
```

Esse tipo de função pode ser usado em `static_assert`, em mensagens de
`concepts` ou para preencher metadados sem custo de heap.

No motor de inferência, `EventTraits<E>` armazena strings de evento como
`std::string_view`:

```cpp
// src/cpp/include/alakoro/inference_engine.hpp:106-112
template <CanonicalEvent E>
struct EventTraits {
    static constexpr std::string_view code = "unknown";
    static constexpr std::string_view label_pt = "Desconhecido";
    static constexpr std::string_view label_en = "Unknown";
    static constexpr std::string_view recommendation = "Investigar manualmente.";
};
```

E são especializadas para cada um dos 15 eventos:

```cpp
// src/cpp/include/alakoro/inference_engine.hpp:123-127
ALAKORO_EVENT_TRAITS(JouleThomson,
    "joule_thomson",
    "Dipolo Térmico Joule-Thomson",
    "Joule-Thomson Thermal Dipole",
    "Verificar passagem de gas/líquido na interface e validar PVT local.");
```

A macro expande para uma especialização de `EventTraits`. As strings vivem na
seção de constantes do executável e nunca são alocadas dinamicamente.

🇺🇸 **EN**

`constexpr` indicates that a function or variable can be evaluated at compile
time. `std::string_view` is a non-owning view over a character sequence, ideal
for constant strings: it avoids allocation and copying.

#### Minimal example

```cpp
#include <string_view>

constexpr std::string_view nome_do_evento(int id) {
    switch (id) {
        case 0:  return "joule_thomson";
        case 1:  return "slope_velocity";
        default: return "unknown";
    }
}

static_assert(nome_do_evento(0) == "joule_thomson");
```

#### In Alakoro: `src/cpp/include/alakoro/core.hpp`

```cpp
// src/cpp/include/alakoro/core.hpp:52-59
constexpr std::string_view modality_name(SensingModality m) noexcept {
    switch (m) {
        case SensingModality::DAS: return "DAS";
        case SensingModality::DTS: return "DTS";
        case SensingModality::DSS: return "DSS";
    }
    return "unknown";
}
```

This kind of function can be used in `static_assert`, in `concepts`
messages, or to fill metadata without heap cost.

In the inference engine, `EventTraits<E>` stores event strings as
`std::string_view`:

```cpp
// src/cpp/include/alakoro/inference_engine.hpp:106-112
template <CanonicalEvent E>
struct EventTraits {
    static constexpr std::string_view code = "unknown";
    static constexpr std::string_view label_pt = "Desconhecido";
    static constexpr std::string_view label_en = "Unknown";
    static constexpr std::string_view recommendation = "Investigar manualmente.";
};
```

And they are specialized for each of the 15 events:

```cpp
// src/cpp/include/alakoro/inference_engine.hpp:123-127
ALAKORO_EVENT_TRAITS(JouleThomson,
    "joule_thomson",
    "Dipolo Térmico Joule-Thomson",
    "Joule-Thomson Thermal Dipole",
    "Verificar passagem de gas/líquido na interface e validar PVT local.");
```

The macro expands into an `EventTraits` specialization. The strings live in
the executable's constant section and are never allocated dynamically.

---

### 2.6 Especialização de templates — `EventTraits` e `ModalityTraits` / Template specialization — `EventTraits` and `ModalityTraits`

🇧🇷 **PT**

A especialização de templates permite fornecer uma implementação específica
para um conjunto particular de argumentos de template, mantendo a interface
genérica.

#### Exemplo mínimo

```cpp
template <int N>
struct Fatorial {
    static constexpr int value = N * Fatorial<N - 1>::value;
};

template <>
struct Fatorial<0> {
    static constexpr int value = 1;
};

static_assert(Fatorial<5>::value == 120);
```

#### No Alakoro

Em `core.hpp`, `ModalityTraits` define unidades padrão por modalidade:

```cpp
// src/cpp/include/alakoro/core.hpp:67-85
template <SensingModality M>
struct ModalityTraits {
    static constexpr std::string_view default_units = "unknown";
};

template <>
struct ModalityTraits<SensingModality::DAS> {
    static constexpr std::string_view default_units = "strain_rate";
};

template <>
struct ModalityTraits<SensingModality::DTS> {
    static constexpr std::string_view default_units = "degC";
};

template <>
struct ModalityTraits<SensingModality::DSS> {
    static constexpr std::string_view default_units = "strain";
};
```

No construtor de `SensingData`, isso é usado para preencher as unidades
automaticamente:

```cpp
// src/cpp/include/alakoro/core.hpp:120-125
SensingData(std::size_t n_times, std::size_t n_channels)
    : n_times_(n_times),
      n_channels_(n_channels),
      data_(n_times * n_channels, T{}) {
    metadata_.units = std::string(ModalityTraits<M>::default_units);
}
```

No `inference_engine.hpp`, a especialização de `EventTraits` é a base para
`make_result<E>`, que cria um resultado preenchido com metadados do evento:

```cpp
// src/cpp/include/alakoro/inference_engine.hpp:630-642
template <CanonicalEvent E>
InferenceResult make_result(double confidence, double depth_md,
                            std::string_view severity) {
    return InferenceResult{
        std::string(EventTraits<E>::code),
        std::string(EventTraits<E>::label_pt),
        std::string(EventTraits<E>::label_en),
        confidence,
        depth_md,
        std::string(severity),
        std::string(EventTraits<E>::recommendation)
    };
}
```

A função `make_result` é genérica, mas os valores de `code`, `label_pt` etc.
são resolvidos em tempo de compilação através da especialização.

🇺🇸 **EN**

Template specialization allows providing a specific implementation for a
particular set of template arguments while keeping the generic interface.

#### Minimal example

```cpp
template <int N>
struct Fatorial {
    static constexpr int value = N * Fatorial<N - 1>::value;
};

template <>
struct Fatorial<0> {
    static constexpr int value = 1;
};

static_assert(Fatorial<5>::value == 120);
```

#### In Alakoro

In `core.hpp`, `ModalityTraits` defines default units per modality:

```cpp
// src/cpp/include/alakoro/core.hpp:67-85
template <SensingModality M>
struct ModalityTraits {
    static constexpr std::string_view default_units = "unknown";
};

template <>
struct ModalityTraits<SensingModality::DAS> {
    static constexpr std::string_view default_units = "strain_rate";
};

template <>
struct ModalityTraits<SensingModality::DTS> {
    static constexpr std::string_view default_units = "degC";
};

template <>
struct ModalityTraits<SensingModality::DSS> {
    static constexpr std::string_view default_units = "strain";
};
```

In the `SensingData` constructor, this is used to fill the units
automatically:

```cpp
// src/cpp/include/alakoro/core.hpp:120-125
SensingData(std::size_t n_times, std::size_t n_channels)
    : n_times_(n_times),
      n_channels_(n_channels),
      data_(n_times * n_channels, T{}) {
    metadata_.units = std::string(ModalityTraits<M>::default_units);
}
```

In `inference_engine.hpp`, the specialization of `EventTraits` is the basis
for `make_result<E>`, which creates a result filled with event metadata:

```cpp
// src/cpp/include/alakoro/inference_engine.hpp:630-642
template <CanonicalEvent E>
InferenceResult make_result(double confidence, double depth_md,
                            std::string_view severity) {
    return InferenceResult{
        std::string(EventTraits<E>::code),
        std::string(EventTraits<E>::label_pt),
        std::string(EventTraits<E>::label_en),
        confidence,
        depth_md,
        std::string(severity),
        std::string(EventTraits<E>::recommendation)
    };
}
```

The `make_result` function is generic, but the values of `code`, `label_pt`,
etc. are resolved at compile time through specialization.

---

## 3. Aplicação concreta no Alakoro / Concrete application in Alakoro

### 3.1 `concepts.hpp` — porteira dos tipos / `concepts.hpp` — gatekeeper of types

🇧🇷 **PT**

`concepts.hpp` é o primeiro arquivo de metaprogramação que um novo
componente C++ do Alakoro deve conhecer. Ele estabelece o vocabulário de
tipos válidos e permite que o restante do código seja escrito sem checagens
defensivas repetidas.

Se um algoritmo espera `FloatingPoint`, o desenvolvedor sabe que pode usar
`std::sin`, `std::sqrt` etc. sem medo de receber um `int` ou um tipo
complexo inesperado.

🇺🇸 **EN**

`concepts.hpp` is the first metaprogramming file a new Alakoro C++ component
should know. It establishes the vocabulary of valid types and allows the rest
of the code to be written without repeated defensive checks.

If an algorithm expects `FloatingPoint`, the developer knows they can use
`std::sin`, `std::sqrt`, etc. without fear of receiving an `int` or an
unexpected complex type.

---

### 3.2 `core.hpp` — dados tipados por modalidade / `core.hpp` — modality-typed data

🇧🇷 **PT**

`SensingData<T, M>` mostra a combinação de vários recursos:

- `NumericScalar T` restringe o tipo de dado.
- `SensingModality M` é um valor de template.
- `if constexpr` em `modality_str()` seleciona a string correta.
- `ModalityTraits<M>` fornece unidades via especialização.
- `using DASData<T> = SensingData<T, SensingModality::DAS>` cria aliases
  idiomáticos.

```cpp
// src/cpp/include/alakoro/core.hpp:202-209
template <NumericScalar T>
using DASData = SensingData<T, SensingModality::DAS>;

template <NumericScalar T>
using DTSData = SensingData<T, SensingModality::DTS>;

template <NumericScalar T>
using DSSData = SensingData<T, SensingModality::DSS>;
```

Isso permite ao Python, via pybind11, expor tipos concretos como
`DASDataFloat`, `DTSDataDouble` etc., cada um com memória e código
otimizados.

🇺🇸 **EN**

`SensingData<T, M>` shows the combination of several features:

- `NumericScalar T` restricts the data type.
- `SensingModality M` is a template value.
- `if constexpr` in `modality_str()` selects the correct string.
- `ModalityTraits<M>` provides units via specialization.
- `using DASData<T> = SensingData<T, SensingModality::DAS>` creates idiomatic
  aliases.

```cpp
// src/cpp/include/alakoro/core.hpp:202-209
template <NumericScalar T>
using DASData = SensingData<T, SensingModality::DAS>;

template <NumericScalar T>
using DTSData = SensingData<T, SensingModality::DTS>;

template <NumericScalar T>
using DSSData = SensingData<T, SensingModality::DSS>;
```

This allows Python, via pybind11, to expose concrete types such as
`DASDataFloat`, `DTSDataDouble`, etc., each with optimized memory and code.

---

### 3.3 `inference_engine.hpp` — geração da engine de regras / `inference_engine.hpp` — rule engine generation

🇧🇷 **PT**

O coração da metaprogramação no Alakoro está na `InferenceEngine`.

1. `CanonicalEvent` enumera 15 eventos canônicos.
2. `EventTraits<E>` fornece metadados por especialização.
3. Cada regra (`JouleThomsonRule`, `SlopeVelocityRule` etc.) é uma struct com
   `static ResultGenerator apply(...)`.
4. `InferenceRule` é um concept que verifica a assinatura de uma regra.
5. `InferenceEngine<Events...>` usa `if constexpr` dentro de
   `execute_rule<E>()` para escolher a regra correta.
6. A fold expression em `infer()` executa todas as regras registradas.

```cpp
// src/cpp/include/alakoro/inference_engine.hpp:1269-1311
template <CanonicalEvent E>
void execute_rule(...) const {
    ResultGenerator gen = [&]() {
        if constexpr (E == CanonicalEvent::JouleThomson) {
            return JouleThomsonRule::apply(...);
        } else if constexpr (E == CanonicalEvent::SlopeVelocity) {
            return SlopeVelocityRule::apply(...);
        }
        // ... todas as 15 regras ...
    }();
    auto partial = collect_results(std::move(gen));
    out.insert(out.end(), std::make_move_iterator(partial.begin()),
               std::make_move_iterator(partial.end()));
}
```

Esse design significa que adicionar um novo evento exige:

1. Adicionar o valor em `CanonicalEvent`;
2. Especializar `EventTraits`;
3. Implementar a `Rule`;
4. Adicionar um `else if constexpr` em `execute_rule`.

O compilador então gera automaticamente uma nova versão da engine.

🇺🇸 **EN**

The heart of metaprogramming in Alakoro lies in `InferenceEngine`.

1. `CanonicalEvent` enumerates 15 canonical events.
2. `EventTraits<E>` provides metadata via specialization.
3. Each rule (`JouleThomsonRule`, `SlopeVelocityRule`, etc.) is a struct with
   `static ResultGenerator apply(...)`.
4. `InferenceRule` is a concept that checks a rule's signature.
5. `InferenceEngine<Events...>` uses `if constexpr` inside
   `execute_rule<E>()` to choose the correct rule.
6. The fold expression in `infer()` executes all registered rules.

```cpp
// src/cpp/include/alakoro/inference_engine.hpp:1269-1311
template <CanonicalEvent E>
void execute_rule(...) const {
    ResultGenerator gen = [&]() {
        if constexpr (E == CanonicalEvent::JouleThomson) {
            return JouleThomsonRule::apply(...);
        } else if constexpr (E == CanonicalEvent::SlopeVelocity) {
            return SlopeVelocityRule::apply(...);
        }
        // ... all 15 rules ...
    }();
    auto partial = collect_results(std::move(gen));
    out.insert(out.end(), std::make_move_iterator(partial.begin()),
               std::make_move_iterator(partial.end()));
}
```

This design means that adding a new event requires:

1. Adding the value to `CanonicalEvent`;
2. Specializing `EventTraits`;
3. Implementing the `Rule`;
4. Adding an `else if constexpr` in `execute_rule`.

The compiler then automatically generates a new version of the engine.

---

### 3.4 `processors.hpp` e `filters.hpp` — processamento genérico / `processors.hpp` and `filters.hpp` — generic processing

🇧🇷 **PT**

`processors.hpp` demonstra como usar concepts para algoritmos que funcionam
sobre qualquer `SensingData`:

```cpp
// src/cpp/include/alakoro/processors.hpp:225-230
template <AnySensingData DataT>
void detrend(DataT& data) {
    using T = typename DataT::value_type;
    auto span = data.data();
    detrend<T>(span, data.n_times(), data.n_channels());
}
```

Aqui `AnySensingData` age como uma interface implícita. Não há herança, não
há `virtual`, mas qualquer tipo que satisfaça o concept pode ser passado.

`filters.hpp` usa `FloatingPoint T` e um `std::size_t Order` para criar
filtros Butterworth especializados em tempo de compilação:

```cpp
// src/cpp/include/alakoro/filters.hpp:51-52
template <FloatingPoint T, std::size_t Order>
class ButterworthFilter {
    // ...
};
```

🇺🇸 **EN**

`processors.hpp` demonstrates how to use concepts for algorithms that work on
any `SensingData`:

```cpp
// src/cpp/include/alakoro/processors.hpp:225-230
template <AnySensingData DataT>
void detrend(DataT& data) {
    using T = typename DataT::value_type;
    auto span = data.data();
    detrend<T>(span, data.n_times(), data.n_channels());
}
```

Here `AnySensingData` acts as an implicit interface. There is no inheritance,
no `virtual`, but any type satisfying the concept can be passed.

`filters.hpp` uses `FloatingPoint T` and a `std::size_t Order` to create
Butterworth filters specialized at compile time:

```cpp
// src/cpp/include/alakoro/filters.hpp:51-52
template <FloatingPoint T, std::size_t Order>
class ButterworthFilter {
    // ...
};
```

---

## 4. Benefícios para o Alakoro / Benefits for Alakoro

### 4.1 Tipagem forte / Strong typing

🇧🇷 **PT**

Cada modalidade é um tipo distinto em tempo de compilação. Não é possível
passar acidentalmente `DTSData` para uma função que espera `DASData`. Os
concepts garantem que operações matemáticas só sejam aplicadas a tipos
numéricos apropriados.

🇺🇸 **EN**

Each modality is a distinct type at compile time. It is impossible to
accidentally pass `DTSData` to a function expecting `DASData`. Concepts ensure
that mathematical operations are only applied to appropriate numeric types.

---

### 4.2 Desempenho / Performance

🇧🇷 **PT**

- `if constexpr` elimina branches e chamadas virtuais.
- Templates geram código especializado para `float` vs. `double`.
- `std::string_view` e `constexpr` evitam alocações desnecessárias.
- `std::span` propaga views zero-copy entre C++ e Python.

🇺🇸 **EN**

- `if constexpr` eliminates branches and virtual calls.
- Templates generate specialized code for `float` vs. `double`.
- `std::string_view` and `constexpr` avoid unnecessary allocations.
- `std::span` propagates zero-copy views between C++ and Python.

---

### 4.3 Erros de compilação claros / Clear compilation errors

🇧🇷 **PT**

Sem concepts, um erro em `SensingData<std::string, ...>` geraria uma
mensagem longa sobre `std::vector<std::string>` e operações aritméticas.
Com `NumericScalar`, o compilador responde diretamente:

```
error: constraint not satisfied: NumericScalar<std::string>
```

🇺🇸 **EN**

Without concepts, an error in `SensingData<std::string, ...>` would produce a
long message about `std::vector<std::string>` and arithmetic operations. With
`NumericScalar`, the compiler responds directly:

```
error: constraint not satisfied: NumericScalar<std::string>
```

---

### 4.4 Geração de código para as 15 regras de eventos / Code generation for the 15 event rules

🇧🇷 **PT**

A `InferenceEngine` não é uma máquina de estados interpretada. Cada
combinação de eventos é um tipo diferente, e o compilador gera código
específico que:

- Resolve os traits em tempo de compilação;
- Escolhe as regras via `if constexpr`;
- Expande a execução via fold expressions.

Isso permite versionar engines (por exemplo, uma engine leve para análise
em tempo real e uma engine completa para pós-processamento) sem alterar as
regras individuais.

🇺🇸 **EN**

`InferenceEngine` is not an interpreted state machine. Each combination of
events is a different type, and the compiler generates specific code that:

- Resolves traits at compile time;
- Chooses rules via `if constexpr`;
- Expands execution via fold expressions.

This allows versioning engines (for example, a lightweight engine for real-time
analysis and a full engine for post-processing) without changing the individual
rules.

---

## 5. Para desenvolvedores Python / For Python developers

🇧🇷 **PT**

A metaprogramação C++ pode parecer distante do Python, mas muitos dos seus
objetivos são semelhantes aos de recursos já conhecidos do ecossistema
Python.

### 5.1 `concepts` ↔ `Protocol` / `TypeVar` com `bound`

Em Python moderno, `typing.Protocol` define uma interface estrutural
(similar ao `AnySensingData`):

```python
from typing import Protocol, TypeVar
import numpy as np

class SensingDataLike(Protocol):
    @property
    def modality(self) -> str: ...
    @property
    def n_times(self) -> int: ...
    @property
    def n_channels(self) -> int: ...
    def data(self) -> np.ndarray: ...

T = TypeVar("T", bound=float)  # similar a NumericScalar/FloatingPoint

def detrend(data: SensingDataLike) -> None:
    ...
```

A diferença fundamental: em Python a verificação é feita pelo type checker
(mypy) em tempo de *desenvolvimento*, mas desaparece na execução. Em C++,
o concept é verificado pelo compilador e **gera ou rejeita código**.

### 5.2 `if constexpr` ↔ `if TYPE_CHECKING:` / dispatch manual

Python não tem `if constexpr`, mas pode simular o dispatch estático com
sobrecarga de funções ou com `functools.singledispatch`:

```python
from functools import singledispatch

@singledispatch
def process(data):
    raise NotImplementedError

@process.register
def _(data: DASData):
    return process_das(data)

@process.register
def _(data: DTSData):
    return process_dts(data)
```

No entanto, o dispatch ocorre em tempo de execução. Em C++, `if constexpr`
remove os ramos não escolhidos **antes** do programa rodar.

### 5.3 Variadic templates ↔ `*args, **kwargs` e generics

```python
# Python: aceita qualquer número de argumentos
def log_many(*args):
    for a in args:
        print(a)

# C++ variadic template equivalente (compila para cada chamada)
template <typename... Args>
void log_many(Args... args) {
    ((std::cout << args << '\n'), ...);
}
```

A vantagem do C++ é que cada uso gera código otimizado para os tipos
exatos; o Python mantém flexibilidade dinâmica.

### 5.4 Decoradores vs. traits

Em Python, um decorator pode adicionar metadados a uma função:

```python
def event_traits(code, label_pt, label_en, recommendation):
    def decorator(cls):
        cls.code = code
        cls.label_pt = label_pt
        cls.label_en = label_en
        cls.recommendation = recommendation
        return cls
    return decorator

@event_traits(
    code="joule_thomson",
    label_pt="Dipolo Térmico Joule-Thomson",
    label_en="Joule-Thomson Thermal Dipole",
    recommendation="Verificar passagem de gás/líquido..."
)
class JouleThomsonRule:
    def apply(self, dts, das, meta):
        ...
```

Em C++, o equivalente é a **especialização de `EventTraits<E>`**. A diferença
é que os metadados são resolvidos em tempo de compilação, sem dicionários
ou atributos em tempo de execução.

### 5.5 Tabela comparativa / Comparison table

| Recurso C++20 | Equivalente Python | Momento da verificação |
|---------------|--------------------|------------------------|
| `concepts` | `Protocol`, `TypeVar bound` | C++: compilação; Python: static analysis |
| `if constexpr` | `singledispatch`, `if TYPE_CHECKING` | C++: compilação; Python: execução |
| Variadic templates | `*args`, generics | C++: geração de código; Python: dinâmico |
| Fold expressions | `for a in args:` loop | C++: expansão em compilação |
| `constexpr` / `string_view` | strings literais, `__slots__` | C++: compilação; Python: execução |
| Especialização de templates | Decoradores, registro manual | C++: compilação; Python: execução |

🇺🇸 **EN**

C++ metaprogramming may seem far from Python, but many of its goals are
similar to features already known in the Python ecosystem.

### 5.1 `concepts` ↔ `Protocol` / `TypeVar` with `bound`

In modern Python, `typing.Protocol` defines a structural interface (similar to
`AnySensingData`):

```python
from typing import Protocol, TypeVar
import numpy as np

class SensingDataLike(Protocol):
    @property
    def modality(self) -> str: ...
    @property
    def n_times(self) -> int: ...
    @property
    def n_channels(self) -> int: ...
    def data(self) -> np.ndarray: ...

T = TypeVar("T", bound=float)  # similar to NumericScalar/FloatingPoint

def detrend(data: SensingDataLike) -> None:
    ...
```

The fundamental difference: in Python the check is performed by the type
checker (mypy) at *development* time, but disappears at runtime. In C++, the
concept is checked by the compiler and **generates or rejects code**.

### 5.2 `if constexpr` ↔ `if TYPE_CHECKING:` / manual dispatch

Python does not have `if constexpr`, but it can simulate static dispatch with
function overloading or `functools.singledispatch`:

```python
from functools import singledispatch

@singledispatch
def process(data):
    raise NotImplementedError

@process.register
def _(data: DASData):
    return process_das(data)

@process.register
def _(data: DTSData):
    return process_dts(data)
```

However, dispatch happens at runtime. In C++, `if constexpr` removes the
unchosen branches **before** the program runs.

### 5.3 Variadic templates ↔ `*args, **kwargs` and generics

```python
# Python: accepts any number of arguments
def log_many(*args):
    for a in args:
        print(a)

# Equivalent C++ variadic template (compiles for each call)
template <typename... Args>
void log_many(Args... args) {
    ((std::cout << args << '\n'), ...);
}
```

The advantage of C++ is that each use generates code optimized for the exact
types; Python keeps dynamic flexibility.

### 5.4 Decorators vs. traits

In Python, a decorator can add metadata to a function:

```python
def event_traits(code, label_pt, label_en, recommendation):
    def decorator(cls):
        cls.code = code
        cls.label_pt = label_pt
        cls.label_en = label_en
        cls.recommendation = recommendation
        return cls
    return decorator

@event_traits(
    code="joule_thomson",
    label_pt="Dipolo Térmico Joule-Thomson",
    label_en="Joule-Thomson Thermal Dipole",
    recommendation="Verificar passagem de gás/líquido..."
)
class JouleThomsonRule:
    def apply(self, dts, das, meta):
        ...
```

In C++, the equivalent is **`EventTraits<E>` specialization**. The difference
is that metadata is resolved at compile time, without dictionaries or
runtime attributes.

### 5.5 Comparison table

| C++20 feature | Python equivalent | When checked |
|---------------|-------------------|--------------|
| `concepts` | `Protocol`, `TypeVar bound` | C++: compile time; Python: static analysis |
| `if constexpr` | `singledispatch`, `if TYPE_CHECKING` | C++: compile time; Python: runtime |
| Variadic templates | `*args`, generics | C++: code generation; Python: dynamic |
| Fold expressions | `for a in args:` loop | C++: compile-time expansion |
| `constexpr` / `string_view` | literal strings, `__slots__` | C++: compile time; Python: runtime |
| Template specialization | Decorators, manual registry | C++: compile time; Python: runtime |

---

## 6. Conclusão / Conclusion

🇧🇷 **PT**

A metaprogramação em C++20 é uma ferramenta estratégica no Alakoro
FiberSense. Ela permite expressar regras de negócio complexas — como as 15
regras de eventos canônicos e as três modalidades de sensing — de forma
**tipada, rápida e mantível**.

Os recursos centrais:

- **`concepts`** tornam as restrições de tipo legíveis e os erros claros.
- **`if constexpr`** substitui polimorfismo e SFINAE por branches de
  compilação diretos.
- **Variadic templates** e **fold expressions** permitem construir engines
  parametrizadas por listas de eventos.
- **`constexpr` e `std::string_view`** movem metadados e strings para a
  compilação, eliminando alocações.
- **Especialização de templates** (`EventTraits`, `ModalityTraits`) associa
  metadados a valores de enum sem herança.

Para desenvolvedores Python, a analogia útil é: C++20 permite fazer grande
parte do que decorators, generics e `typing.Protocol` fazem, mas com
verificação e geração de código em tempo de compilação. O resultado é um
núcleo C++ que o Python consome via pybind11 como uma biblioteca síncrona,
rápida e fortemente tipada.

🇺🇸 **EN**

C++20 metaprogramming is a strategic tool in Alakoro FiberSense. It allows
complex business rules — such as the 15 canonical event rules and the three
sensing modalities — to be expressed in a **typed, fast, and maintainable**
way.

The core features:

- **`concepts`** make type constraints readable and errors clear.
- **`if constexpr`** replaces polymorphism and SFINAE with direct compile-time
  branches.
- **Variadic templates** and **fold expressions** enable engines parameterized
  by event lists.
- **`constexpr` and `std::string_view`** move metadata and strings to compile
  time, eliminating allocations.
- **Template specialization** (`EventTraits`, `ModalityTraits`) associates
  metadata with enum values without inheritance.

For Python developers, the useful analogy is: C++20 can do much of what
decorators, generics, and `typing.Protocol` do, but with compile-time
checking and code generation. The result is a C++ core that Python consumes
via pybind11 as a synchronous, fast, and strongly typed library.

---

## Referências de arquivos / File references

🇧🇷 **PT**

- `src/cpp/include/alakoro/concepts.hpp`
- `src/cpp/include/alakoro/core.hpp`
- `src/cpp/include/alakoro/inference_engine.hpp`
- `src/cpp/include/alakoro/processors.hpp`
- `src/cpp/include/alakoro/filters.hpp`

🇺🇸 **EN**

- `src/cpp/include/alakoro/concepts.hpp`
- `src/cpp/include/alakoro/core.hpp`
- `src/cpp/include/alakoro/inference_engine.hpp`
- `src/cpp/include/alakoro/processors.hpp`
- `src/cpp/include/alakoro/filters.hpp`
