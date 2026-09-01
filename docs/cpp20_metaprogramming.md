# Metaprogramação em C++20 no Alakoro FiberSense

> Guia técnico e didático sobre como o núcleo C++20 do Alakoro usa
> metaprogramação para gerar código seguro, rápido e especializado para
> análise de dados de fibra óptica (DAS, DTS, DSS).

---

## 1. O que é metaprogramação em C++?

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

---

## 2. Recursos de C++20 usados no Alakoro

### 2.1 `concepts` — restrições de tipo claras

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

---

### 2.2 `if constexpr` — decisões em tempo de compilação

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

---

### 2.3 Variadic templates — templates com número arbitrário de argumentos

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

---

### 2.4 Fold expressions — dobrar listas de parâmetros

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

---

### 2.5 `constexpr` e `std::string_view` — valores em tempo de compilação

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

---

### 2.6 Especialização de templates — `EventTraits` e `ModalityTraits`

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

---

## 3. Aplicação concreta no Alakoro

### 3.1 `concepts.hpp` — porteira dos tipos

`concepts.hpp` é o primeiro arquivo de metaprogramação que um novo
componente C++ do Alakoro deve conhecer. Ele estabelece o vocabulário de
tipos válidos e permite que o restante do código seja escrito sem checagens
defensivas repetidas.

Se um algoritmo espera `FloatingPoint`, o desenvolvedor sabe que pode usar
`std::sin`, `std::sqrt` etc. sem medo de receber um `int` ou um tipo
complexo inesperado.

### 3.2 `core.hpp` — dados tipados por modalidade

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

### 3.3 `inference_engine.hpp` — geração da engine de regras

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

### 3.4 `processors.hpp` e `filters.hpp` — processamento genérico

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

---

## 4. Benefícios para o Alakoro

### 4.1 Tipagem forte

Cada modalidade é um tipo distinto em tempo de compilação. Não é possível
passar acidentalmente `DTSData` para uma função que espera `DASData`. Os
concepts garantem que operações matemáticas só sejam aplicadas a tipos
numéricos apropriados.

### 4.2 Desempenho

- `if constexpr` elimina branches e chamadas virtuais.
- Templates geram código especializado para `float` vs. `double`.
- `std::string_view` e `constexpr` evitam alocações desnecessárias.
- `std::span` propaga views zero-copy entre C++ e Python.

### 4.3 Erros de compilação claros

Sem concepts, um erro em `SensingData<std::string, ...>` geraria uma
mensagem longa sobre `std::vector<std::string>` e operações aritméticas.
Com `NumericScalar`, o compilador responde diretamente:

```
error: constraint not satisfied: NumericScalar<std::string>
```

### 4.4 Geração de código para as 15 regras de eventos

A `InferenceEngine` não é uma máquina de estados interpretada. Cada
combinação de eventos é um tipo diferente, e o compilador gera código
específico que:

- Resolve os traits em tempo de compilação;
- Escolhe as regras via `if constexpr`;
- Expande a execução via fold expressions.

Isso permite versionar engines (por exemplo, uma engine leve para análise
em tempo real e uma engine completa para pós-processamento) sem alterar as
regras individuais.

---

## 5. Para desenvolvedores Python

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

### 5.5 Tabela comparativa

| Recurso C++20 | Equivalente Python | Momento da verificação |
|---------------|--------------------|------------------------|
| `concepts` | `Protocol`, `TypeVar bound` | C++: compilação; Python: static analysis |
| `if constexpr` | `singledispatch`, `if TYPE_CHECKING` | C++: compilação; Python: execução |
| Variadic templates | `*args`, generics | C++: geração de código; Python: dinâmico |
| Fold expressions | `for a in args:` loop | C++: expansão em compilação |
| `constexpr` / `string_view` | strings literais, `__slots__` | C++: compilação; Python: execução |
| Especialização de templates | Decoradores, registro manual | C++: compilação; Python: execução |

---

## 6. Conclusão

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

---

## Referências de arquivos

- `src/cpp/include/alakoro/concepts.hpp`
- `src/cpp/include/alakoro/core.hpp`
- `src/cpp/include/alakoro/inference_engine.hpp`
- `src/cpp/include/alakoro/processors.hpp`
- `src/cpp/include/alakoro/filters.hpp`
