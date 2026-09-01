# Move Semantics (Semântica de Movimento) em C++20 — Alakoro FiberSense / Move Semantics in C++20 — Alakoro FiberSense

---

## 🇧🇷 Introdução

**Objetivo:** entender como a semântica de movimento do C++20 evita cópias caras de arrays DAS/DTS/DSS no motor de inferência do Alakoro FiberSense.

**Público-alvo:** engenheiros que conhecem Python e querem entender por que o C++20 do Alakoro é *move-only* em pontos críticos.

**Arquivos-fonte consultados:**
- `src/cpp/include/alakoro/inference_engine.hpp` — `InferenceResult`, `ResultGenerator`, `collect_results`, `execute_rule`, regras canônicas.
- `src/cpp/src/bindings.cpp` — bindings pybind11, `vector_to_numpy`.
- `tests/test_cpp_core.py` — testes da camada nativa.

## 🇺🇸 Introduction

**Goal:** understand how C++20 move semantics avoid expensive copies of DAS/DTS/DSS arrays in the Alakoro FiberSense inference engine.

**Target audience:** engineers familiar with Python who want to understand why Alakoro's C++20 core is *move-only* at critical points.

**Source files consulted:**
- `src/cpp/include/alakoro/inference_engine.hpp` — `InferenceResult`, `ResultGenerator`, `collect_results`, `execute_rule`, canonical rules.
- `src/cpp/src/bindings.cpp` — pybind11 bindings, `vector_to_numpy`.
- `tests/test_cpp_core.py` — native layer tests.

---

## 1. O problema: cópias caras de objetos grandes / The Problem: Expensive Copies of Large Objects

### 🇧🇷 PT

No processamento de dados de fibra óptica (DAS/DTS/DSS) do Alakoro, trabalhamos com volumes significativos: trilhas de amplitude/strain ao longo de milhares de amostras temporais e centenas ou milhares de canais de profundidade. Um único `std::vector<double>` que represente uma aquisição pode facilmente ocupar dezenas de megabytes.

Quando C++ copia esses objetos — seja um vetor de dados brutos, uma matriz de resultados ou uma corrotina que encapsula estado de processamento — o custo é proporcional ao tamanho do buffer. Para o motor de inferência (`InferenceEngine`), isso significa cópias indesejáveis entre:

- a extração de perfis médios (`temporal_mean`);
- a remoção de baseline (`remove_polynomial_baseline`, `remove_median_baseline`);
- a acumulação de `InferenceResult`;
- o retorno de resultados para Python via pybind11.

A **semântica de movimento** (*move semantics*), introduzida no C++11 e aperfeiçoada no C++14/C++17/C++20, resolve exatamente esse problema: em vez de duplicar recursos, transferimos a posse (*ownership*) dos dados de um objeto para outro. O buffer de memória não é copiado; apenas os ponteiros internos são trocados.

### 🇺🇸 EN

In Alakoro's fiber-optic data processing (DAS/DTS/DSS), we deal with significant volumes: amplitude/strain traces over thousands of time samples and hundreds or thousands of depth channels. A single `std::vector<double>` representing an acquisition can easily occupy tens of megabytes.

When C++ copies these objects — whether raw data vectors, result matrices, or coroutines encapsulating processing state — the cost is proportional to the buffer size. For the inference engine (`InferenceEngine`), this means undesirable copies between:

- mean profile extraction (`temporal_mean`);
- baseline removal (`remove_polynomial_baseline`, `remove_median_baseline`);
- accumulation of `InferenceResult`;
- returning results to Python via pybind11.

**Move semantics**, introduced in C++11 and refined in C++14/C++17/C++20, solves exactly this problem: instead of duplicating resources, we transfer *ownership* of data from one object to another. The memory buffer is not copied; only the internal pointers are swapped.

---

## 2. Conceitos fundamentais / Fundamental Concepts

### 2.1 lvalue vs rvalue

#### 🇧🇷 PT

- **lvalue** (*left value*): expressão que tem identidade e endereço. Pode aparecer à esquerda de uma atribuição.
  - Exemplos: uma variável nomeada, um elemento de vetor, um retorno por referência.
- **rvalue** (*right value*): expressão temporária, sem identidade própria. Geralmente aparece à direita de uma atribuição.
  - Exemplos: o resultado de uma função que retorna por valor, um literal, `std::move(x)`.

#### 🇺🇸 EN

- **lvalue** (*left value*): an expression that has identity and address. It can appear on the left side of an assignment.
  - Examples: a named variable, a vector element, a return by reference.
- **rvalue** (*right value*): a temporary expression without its own identity. It usually appears on the right side of an assignment.
  - Examples: the result of a function returning by value, a literal, `std::move(x)`.

```cpp
std::vector<double> make_data();          // retorna um rvalue / returns an rvalue
std::vector<double> v = make_data();      // v é um lvalue / v is an lvalue
v[0] = 1.0;                               // v[0] é um lvalue / v[0] is an lvalue
std::vector<double> w = std::move(v);     // std::move(v) é um rvalue / std::move(v) is an rvalue
```

### 2.2 Referências / References

#### 🇧🇷 PT

| Sintaxe | Significado | Quando usar |
|---------|-------------|-------------|
| `T&` | Referência não-constante para lvalue | Modificar o objeto original sem copiá-lo |
| `const T&` | Referência constante para lvalue/rvalue | Ler o objeto sem copiá-lo; liga-se a temporários |
| `T&&` | Referência para rvalue | Implementar move semantics; "roubar" recursos de um temporário |

> A regra prática: use `const T&` para leitura, `T&&` para mover, e `T&` quando precisar modificar o objeto original.

#### 🇺🇸 EN

| Syntax | Meaning | When to use |
|--------|---------|-------------|
| `T&` | Non-const reference to lvalue | Modify the original object without copying it |
| `const T&` | Const reference to lvalue/rvalue | Read the object without copying; binds to temporaries |
| `T&&` | Rvalue reference | Implement move semantics; "steal" resources from a temporary |

> Practical rule: use `const T&` for reading, `T&&` for moving, and `T&` when you need to modify the original object.

### 2.3 Move constructor e move assignment operator / Move Constructor and Move Assignment Operator

#### 🇧🇷 PT

Todo tipo pode ter, além do construtor de cópia e do operador de atribuição por cópia, versões de **movimento**:

#### 🇺🇸 EN

Every type can have, in addition to the copy constructor and copy assignment operator, **move** versions:

```cpp
class Buffer {
public:
    // Construtor padrão / Default constructor
    Buffer() = default;

    // Construtor de cópia (deep copy) / Copy constructor (deep copy)
    Buffer(const Buffer& other) : data_(other.data_) { /* copia elementos / copy elements */ }

    // Operador de atribuição por cópia / Copy assignment operator
    Buffer& operator=(const Buffer& other) {
        if (this != &other) {
            data_ = other.data_;  // copia / copy
        }
        return *this;
    }

    // Move constructor: rouba os recursos de other
    // Move constructor: steals other's resources
    Buffer(Buffer&& other) noexcept : data_(std::move(other.data_)) {
        // other é deixado em estado válido, mas vazio
        // other is left in a valid, but empty state
    }

    // Move assignment operator
    Buffer& operator=(Buffer&& other) noexcept {
        if (this != &other) {
            data_ = std::move(other.data_);  // move o vetor interno / move the internal vector
        }
        return *this;
    }

private:
    std::vector<double> data_;
};
```

#### 🇧🇷 PT

A palavra-chave `noexcept` é importante: se um move constructor lançar exceção, algumas operações da biblioteca padrão (como realocação de vetores) recuam para cópias, perdendo o ganho de performance.

#### 🇺🇸 EN

The `noexcept` keyword is important: if a move constructor throws an exception, some standard-library operations (such as vector reallocation) fall back to copies, losing the performance gain.

### 2.4 `std::move`: um cast, não uma operação de movimento / `std::move`: a Cast, Not a Move Operation

#### 🇧🇷 PT

`std::move(x)` **não move** `x`. Ele apenas converte `x` em um rvalue, permitindo que o compilador escolha a sobrecarga de movimento.

#### 🇺🇸 EN

`std::move(x)` does **not move** `x`. It merely converts `x` into an rvalue, allowing the compiler to select the move overload.

```cpp
std::vector<double> a = {1.0, 2.0, 3.0};
std::vector<double> b = std::move(a);  // agora b tem os dados; a está vazio
                                       // now b owns the data; a is empty
```

#### 🇧🇷 PT

Após `std::move(a)`, o estado de `a` é válido mas indefinido em termos de conteúdo. A única operação segura garantida é destruí-lo ou reassinar.

#### 🇺🇸 EN

After `std::move(a)`, the state of `a` is valid but undefined in terms of content. The only guaranteed safe operation is to destroy it or reassign it.

### 2.5 Rule of Zero / Rule of Five

#### 🇧🇷 PT

- **Rule of Zero**: se seus membros gerenciam recursos corretamente (como `std::vector`, `std::string`, `std::unique_ptr`), você **não precisa** escrever destrutor, cópia ou movimento. O compilador gera tudo corretamente.
- **Rule of Five**: se você precisa implementar **qualquer um** de (destrutor, copy constructor, copy assignment, move constructor, move assignment), provavelmente precisa implementar os cinco — ou declarar explicitamente o que não deve existir (`= delete`).

No Alakoro, `ResultGenerator` segue a **Rule of Five** de propósito: ele possui um `std::coroutine_handle`, que é um recurso único. Por isso, a cópia é deletada e o movimento é implementado manualmente.

#### 🇺🇸 EN

- **Rule of Zero**: if your members manage resources correctly (such as `std::vector`, `std::string`, `std::unique_ptr`), you **do not need** to write a destructor, copy, or move operations. The compiler generates everything correctly.
- **Rule of Five**: if you need to implement **any one** of (destructor, copy constructor, copy assignment, move constructor, move assignment), you probably need to implement all five — or explicitly declare what should not exist (`= delete`).

In Alakoro, `ResultGenerator` deliberately follows the **Rule of Five**: it owns a `std::coroutine_handle`, which is a unique resource. Therefore, copying is deleted and moving is implemented manually.

---

## 3. Exemplos mínimos: antes e depois do move / Minimal Examples: Before and After Move

### 3.1 Antes: cópia explícita de vetores / Before: Explicit Vector Copy

#### 🇧🇷 PT

```cpp
std::vector<double> temporal_mean(const std::vector<double>& data) {
    std::vector<double> mean(data.size());
    // ... preenche mean ...
    return mean;  // NRVO/Move já ajudam, mas vamos supor o pior caso
}

auto profile = temporal_mean(raw);
auto anomaly = remove_polynomial_baseline(profile, 2);  // copia profile!
```

Se `profile` tiver 100 mil elementos, a chamada acima pode copiar 800 KB desnecessariamente.

#### 🇺🇸 EN

```cpp
std::vector<double> temporal_mean(const std::vector<double>& data) {
    std::vector<double> mean(data.size());
    // ... fills mean ...
    return mean;  // NRVO/Move already help, but let's assume the worst case
}

auto profile = temporal_mean(raw);
auto anomaly = remove_polynomial_baseline(profile, 2);  // copies profile!
```

If `profile` has 100,000 elements, the call above may unnecessarily copy 800 KB.

### 3.2 Depois: move em vez de copiar / After: Move Instead of Copy

#### 🇧🇷 PT

```cpp
inline std::vector<double> remove_polynomial_baseline(std::vector<double> profile,
                                                       std::size_t degree = 2) {
    // recebemos por valor para poder trabalhar no próprio buffer
    if (profile.size() < degree + 2) return profile;
    const std::size_t n = profile.size();
    // ... usa profile diretamente para calcular baseline e subtrai ...
    return profile;  // move out (NRVO ou move)
}

auto mean_profile = detail::temporal_mean(dts, n_times, n_channels);
auto anomaly = detail::remove_polynomial_baseline(std::move(mean_profile), 2);
```

Aqui, `mean_profile` é **movido** para dentro de `remove_polynomial_baseline`. Nenhuma alocação extra ocorre para o vetor de anomalia: o mesmo buffer é reutilizado.

Esse padrão aparece repetidamente no `inference_engine.hpp`, por exemplo em `SlopeVelocityRule`:

#### 🇺🇸 EN

```cpp
inline std::vector<double> remove_polynomial_baseline(std::vector<double> profile,
                                                       std::size_t degree = 2) {
    // we take by value so we can work in the buffer itself
    if (profile.size() < degree + 2) return profile;
    const std::size_t n = profile.size();
    // ... uses profile directly to compute baseline and subtracts ...
    return profile;  // move out (NRVO or move)
}

auto mean_profile = detail::temporal_mean(dts, n_times, n_channels);
auto anomaly = detail::remove_polynomial_baseline(std::move(mean_profile), 2);
```

Here, `mean_profile` is **moved** into `remove_polynomial_baseline`. No extra allocation occurs for the anomaly vector: the same buffer is reused.

This pattern appears repeatedly in `inference_engine.hpp`, for example in `SlopeVelocityRule`:

```cpp
auto first_half = detail::temporal_mean(dts.subspan(0, mid_t * n_channels),
                                         mid_t, n_channels);
auto second_half = detail::temporal_mean(
    dts.subspan(mid_t * n_channels, (n_times - mid_t) * n_channels),
    n_times - mid_t, n_channels);

auto anom1 = detail::remove_polynomial_baseline(std::move(first_half), 2);
auto anom2 = detail::remove_polynomial_baseline(std::move(second_half), 2);
```

---

## 4. Aplicação no Alakoro / Application in Alakoro

### 4.1 `ResultGenerator`: recurso único, delete copy, implement move / `ResultGenerator`: Unique Resource, Delete Copy, Implement Move

#### 🇧🇷 PT

A `ResultGenerator` é a corrotina que produz `InferenceResult` via `co_yield`. Por baixo, ela guarda um `std::coroutine_handle<promise_type>`, um identificador de frame de corrotina — um recurso que não pode ser compartilhado.

No arquivo `src/cpp/include/alakoro/inference_engine.hpp` (linhas 228–281):

#### 🇺🇸 EN

`ResultGenerator` is the coroutine that produces `InferenceResult` via `co_yield`. Under the hood, it holds a `std::coroutine_handle<promise_type>`, a coroutine frame identifier — a resource that cannot be shared.

In the file `src/cpp/include/alakoro/inference_engine.hpp` (lines 228–281):

```cpp
struct ResultGenerator {
    struct promise_type {
        InferenceResult current_value;

        ResultGenerator get_return_object() {
            return ResultGenerator{std::coroutine_handle<promise_type>::from_promise(*this)};
        }

        std::suspend_always initial_suspend() noexcept { return {}; }
        std::suspend_always final_suspend() noexcept { return {}; }
        void unhandled_exception() { std::terminate(); }
        void return_void() noexcept {}

        std::suspend_always yield_value(InferenceResult value) noexcept {
            current_value = std::move(value);  // move o resultado do co_yield
                                               // move the co_yield result
            return {};
        }
    };

    using handle_type = std::coroutine_handle<promise_type>;

    explicit ResultGenerator(handle_type h) : handle_(h) {}

    // Não copiável: coroutine_handle é um recurso único.
    // Not copyable: coroutine_handle is a unique resource.
    ResultGenerator(const ResultGenerator&) = delete;
    ResultGenerator& operator=(const ResultGenerator&) = delete;

    // Move constructor: transfere posse do handle
    // Move constructor: transfers ownership of the handle
    ResultGenerator(ResultGenerator&& other) noexcept : handle_(other.handle_) {
        other.handle_ = nullptr;
    }

    // Move assignment: destrói handle antigo, rouba o novo
    // Move assignment: destroys old handle, steals the new one
    ResultGenerator& operator=(ResultGenerator&& other) noexcept {
        if (this != &other) {
            if (handle_) handle_.destroy();
            handle_ = other.handle_;
            other.handle_ = nullptr;
        }
        return *this;
    }

    ~ResultGenerator() {
        if (handle_) handle_.destroy();
    }

    bool done() const noexcept { return handle_.done(); }
    void resume() { if (handle_) handle_.resume(); }

    const InferenceResult& value() const noexcept {
        return handle_.promise().current_value;
    }

private:
    handle_type handle_;
};
```

#### 🇧🇷 PT

Observe:

1. **Cópia deletada**: `ResultGenerator(const ResultGenerator&) = delete;`. Tentar copiar uma corrotina é um erro de compilação, garantindo que nunca haverá dois handles para o mesmo frame.
2. **Move constructor `noexcept`**: rouba o `handle_` e zera o objeto fonte.
3. **Move assignment com self-check**: destrói o recurso antigo antes de assumir o novo, evitando vazamento.
4. **yield com move**: `current_value = std::move(value);` evita copiar `std::string`s dentro de `InferenceResult`.

#### 🇺🇸 EN

Note:

1. **Deleted copy**: `ResultGenerator(const ResultGenerator&) = delete;`. Trying to copy a coroutine is a compile error, ensuring there are never two handles to the same frame.
2. **`noexcept` move constructor**: steals `handle_` and zeroes the source object.
3. **Move assignment with self-check**: destroys the old resource before taking the new one, preventing leaks.
4. **Yield with move**: `current_value = std::move(value);` avoids copying `std::string`s inside `InferenceResult`.

### 4.2 `collect_results` e consumo da corrotina / `collect_results` and Coroutine Consumption

#### 🇧🇷 PT

A função `collect_results` é a ponte entre a API corrotinada interna e a API síncrona exposta. No código atual, ela recebe `ResultGenerator` por valor (linha 1230):

#### 🇺🇸 EN

The `collect_results` function is the bridge between the internal coroutine API and the exposed synchronous API. In the current code, it takes `ResultGenerator` by value (line 1230):

```cpp
inline std::vector<InferenceResult> collect_results(ResultGenerator gen) {
    std::vector<InferenceResult> results;
    results.reserve(4);
    while (!gen.done()) {
        gen.resume();
        if (!gen.done()) {
            results.push_back(std::move(gen.value()));  // move do generator para o vetor
                                                        // move from generator to vector
        }
    }
    return results;
}
```

#### 🇧🇷 PT

Receber por valor ainda permite que o caller mova a corrotina no momento da chamada:

```cpp
auto partial = collect_results(std::move(gen));
```

Uma alternativa ainda mais explícita, que deixa claro que a função **consome** o gerador, seria usar uma rvalue reference:

#### 🇺🇸 EN

Taking by value still allows the caller to move the coroutine at the call site:

```cpp
auto partial = collect_results(std::move(gen));
```

An even more explicit alternative, making it clear that the function **consumes** the generator, would be to use an rvalue reference:

```cpp
inline std::vector<InferenceResult> collect_results(ResultGenerator&& gen) {
    std::vector<InferenceResult> results;
    results.reserve(4);
    while (!gen.done()) {
        gen.resume();
        if (!gen.done()) {
            results.push_back(std::move(gen.value()));
        }
    }
    return results;
}
```

#### 🇧🇷 PT

Com essa assinatura, `collect_results(std::move(gen))` continua válido, mas `collect_results(gen)` se torna um erro de compilação, aumentando a segurança: ninguém pode esquecer de mover acidentalmente e depois tentar reusar `gen`.

#### 🇺🇸 EN

With this signature, `collect_results(std::move(gen))` remains valid, but `collect_results(gen)` becomes a compile error, increasing safety: no one can accidentally forget to move and later try to reuse `gen`.

### 4.3 `execute_rule`: movendo o generator e os resultados parciais / `execute_rule`: Moving the Generator and Partial Results

#### 🇧🇷 PT

No `InferenceEngine`, cada regra é executada dentro de `execute_rule`, e seus resultados são fundidos no vetor final via `std::make_move_iterator` (linhas 1276–1316):

#### 🇺🇸 EN

In `InferenceEngine`, each rule is executed inside `execute_rule`, and its results are merged into the final vector via `std::make_move_iterator` (lines 1276–1316):

```cpp
template <CanonicalEvent E>
void execute_rule(std::span<const double> dts,
                  std::span<const double> das,
                  std::size_t n_times,
                  std::size_t n_channels,
                  const InferenceMetadata& meta,
                  std::vector<InferenceResult>& out) const {
    ResultGenerator gen = [&]() {
        if constexpr (E == CanonicalEvent::JouleThomson) {
            return JouleThomsonRule::apply(dts, das, n_times, n_channels, meta);
        }
        // ... outras regras ...
        // ... other rules ...
    }();

    auto partial = collect_results(std::move(gen));  // move a corrotina / move the coroutine

    out.insert(out.end(),
               std::make_move_iterator(partial.begin()),
               std::make_move_iterator(partial.end()));  // move cada InferenceResult
                                                         // move each InferenceResult
}
```

#### 🇧🇷 PT

Sem `std::move(gen)`, `collect_results` tentaria copiar a corrotina — o que falharia em compilação, graças ao `= delete` na cópia. Sem `std::make_move_iterator`, os `InferenceResult` (que contêm várias `std::string`) seriam copiados um a um para `out`.

#### 🇺🇸 EN

Without `std::move(gen)`, `collect_results` would try to copy the coroutine — which would fail to compile, thanks to the `= delete` on copying. Without `std::make_move_iterator`, the `InferenceResult` objects (which contain several `std::string`s) would be copied one by one into `out`.

### 4.4 pybind11: `py::return_value_policy::move`

#### 🇧🇷 PT

No `src/cpp/src/bindings.cpp`, a camada Python recebe os vetores de resultados por valor e os converte para listas/tuplas de NumPy. A função `vector_to_numpy` (linhas 43–50) já aproveita a semântica de movimento internamente:

#### 🇺🇸 EN

In `src/cpp/src/bindings.cpp`, the Python layer receives result vectors by value and converts them into NumPy lists/tuples. The `vector_to_numpy` function (lines 43–50) already takes advantage of move semantics internally:

```cpp
template <typename T>
py::array_t<T> vector_to_numpy(std::vector<T> vec) {
    const std::size_t size = vec.size();
    T* data = vec.data();
    auto* owned = new std::vector<T>(std::move(vec));  // move o vetor para a cápsula
                                                       // move the vector into the capsule
    py::capsule capsule(owned, [](void* p) { delete static_cast<std::vector<T>*>(p); });
    return py::array_t<T>({size}, {sizeof(T)}, data, capsule);
}
```

#### 🇧🇷 PT

Aqui, o `std::vector<T>` é movido para dentro de um `std::vector<T>` alocado no heap, que vive dentro de uma `py::capsule`. O array NumPy aponta para os mesmos dados sem cópia.

Quando registramos funções que retornam objetos C++ diretamente (não vetores convertidos manualmente), podemos instruir o pybind11 a mover o retorno em vez de copiar:

#### 🇺🇸 EN

Here, the `std::vector<T>` is moved into a heap-allocated `std::vector<T>` that lives inside a `py::capsule`. The NumPy array points to the same data without copying.

When registering functions that return C++ objects directly (not manually converted vectors), we can instruct pybind11 to move the return value instead of copying:

```cpp
m.def("make_inference_result",
      []() { return InferenceResult{...}; },
      py::return_value_policy::move,
      "Retorna um InferenceResult movido para Python / Returns an InferenceResult moved to Python");
```

#### 🇧🇷 PT

No binding atual do `infer_events_d`, o retorno é `std::vector<InferenceResult>`. Como `pybind11/stl.h` está incluído, o pybind11 converte automaticamente o vetor para uma `list` Python. Internamente, cada `InferenceResult` é **copiado** durante essa conversão, porque o padrão para tipos registrados é `copy` quando expostos dentro de containers STL.

Se quisermos garantir movimento também no retorno para Python, a alternativa é:

1. Retornar por valor e confiar na otimização de cópia (RVO/NRVO) do C++ no lado nativo.
2. Para objetos pesados, expor explicitamente o move constructor no binding:

#### 🇺🇸 EN

In the current `infer_events_d` binding, the return type is `std::vector<InferenceResult>`. Since `pybind11/stl.h` is included, pybind11 automatically converts the vector into a Python `list`. Internally, each `InferenceResult` is **copied** during this conversion, because the default for registered types is `copy` when exposed inside STL containers.

If we want to guarantee movement also on the return to Python, the alternatives are:

1. Return by value and rely on C++ copy elision (RVO/NRVO) on the native side.
2. For heavy objects, explicitly expose the move constructor in the binding:

```cpp
py::class_<InferenceResult>(m, "InferenceResult")
    .def(py::init<>())
    .def(py::init<const InferenceResult&>())  // copy / cópia
    .def(py::init<InferenceResult&&>())       // move (geralmente implícito)
                                              // move (usually implicit)
    // ... membros / members ...
```

#### 🇧🇷 PT

Para o caso do Alakoro, a cópia de `InferenceResult` é aceitável: cada resultado contém apenas strings pequenas (nome do evento, severidade, recomendação) e poucos `double`. O ganho de performance vem principalmente de **não copiar os arrays DAS/DTS** durante o processamento interno.

#### 🇺🇸 EN

For Alakoro's case, copying `InferenceResult` is acceptable: each result contains only small strings (event name, severity, recommendation) and a few `double`s. The performance gain comes mainly from **not copying the DAS/DTS arrays** during internal processing.

---

## 5. Ganho de performance e segurança para o Alakoro / Performance and Safety Gains for Alakoro

### 5.1 Evita copiar arrays entre regras / Avoid Copying Arrays Between Rules

#### 🇧🇷 PT

As regras de inferência operam sobre perfis temporários:

```cpp
auto mean_profile = detail::temporal_mean(dts, n_times, n_channels);
auto anomaly = detail::remove_polynomial_baseline(std::move(mean_profile), 2);
```

Sem `std::move`, `remove_polynomial_baseline` receberia uma referência constante e teria que alocar um novo vetor para o resultado. Com `std::move`, a função recebe o vetor por valor e pode reutilizar seu buffer para armazenar o resultado, economizando uma alocação e uma cópia.

#### 🇺🇸 EN

The inference rules operate on temporary profiles:

```cpp
auto mean_profile = detail::temporal_mean(dts, n_times, n_channels);
auto anomaly = detail::remove_polynomial_baseline(std::move(mean_profile), 2);
```

Without `std::move`, `remove_polynomial_baseline` would receive a const reference and would have to allocate a new vector for the result. With `std::move`, the function receives the vector by value and can reuse its buffer to store the result, saving one allocation and one copy.

### 5.2 Corrotinas sem cópia / Coroutines Without Copy

#### 🇧🇷 PT

`ResultGenerator` é **move-only**. Isso garante que:

- cada frame de corrotina tenha exatamente um dono;
- não haja double-free ou uso após destruição;
- o `std::coroutine_handle` seja destruído exatamente uma vez no destrutor.

#### 🇺🇸 EN

`ResultGenerator` is **move-only**. This guarantees that:

- each coroutine frame has exactly one owner;
- there is no double-free or use-after-destruction;
- the `std::coroutine_handle` is destroyed exactly once in the destructor.

### 5.3 Composição segura de resultados / Safe Composition of Results

#### 🇧🇷 PT

`std::make_move_iterator` permite fundir resultados parciais de várias regras no vetor final sem copiar strings:

```cpp
out.insert(out.end(),
           std::make_move_iterator(partial.begin()),
           std::make_move_iterator(partial.end()));
```

#### 🇺🇸 EN

`std::make_move_iterator` allows merging partial results from several rules into the final vector without copying strings:

```cpp
out.insert(out.end(),
           std::make_move_iterator(partial.begin()),
           std::make_move_iterator(partial.end()));
```

### 5.4 Estimativa de impacto / Impact Estimate

#### 🇧🇷 PT

Para uma aquisição típica de DAS/DTS com $N_t \\times N_c$ amostras:

- `temporal_mean` produz um vetor de $N_c$ doubles.
- `remove_polynomial_baseline` produz outro vetor de $N_c$ doubles.

Sem move: cada etapa aloca um novo buffer e copia $N_c$ elementos.  
Com move: a segunda etapa reusa o buffer da primeira. Em $N_c = 10.000$, isso evita copiar ~80 KB por etapa, por regra, por execução. Multiplicado pelas 15 regras canônicas e por muitas iterações de processamento, o ganho se torna mensurável em tempo e pressão sobre o garbage collector / allocator.

#### 🇺🇸 EN

For a typical DAS/DTS acquisition with $N_t \\times N_c$ samples:

- `temporal_mean` produces a vector of $N_c$ doubles.
- `remove_polynomial_baseline` produces another vector of $N_c$ doubles.

Without move: each step allocates a new buffer and copies $N_c$ elements.  
With move: the second step reuses the first step's buffer. At $N_c = 10{,}000$, this avoids copying ~80 KB per step, per rule, per execution. Multiplied by the 15 canonical rules and many processing iterations, the gain becomes measurable in time and pressure on the garbage collector / allocator.

---

## 6. Armadilhas / Pitfalls

### 6.1 Usar um objeto depois de `std::move` / Using an Object After `std::move`

#### 🇧🇷 PT

```cpp
std::vector<double> a = {1.0, 2.0, 3.0};
std::vector<double> b = std::move(a);
std::cout << a.size();  // válido? tecnicamente sim, mas o valor é indefinido
a.push_back(4.0);       // válido — a está em estado válido, mas vazio
```

A única garantia após `std::move(a)` é que `a` está em um estado válido para destruição ou reassinalação. Ler seu tamanho ou conteúdo sem reassinalar é um bug silencioso.

No Alakoro, evite:

```cpp
auto gen = SomeRule::apply(...);
auto results = collect_results(std::move(gen));
gen.resume();  // ERRO: gen não possui mais o handle
```

#### 🇺🇸 EN

```cpp
std::vector<double> a = {1.0, 2.0, 3.0};
std::vector<double> b = std::move(a);
std::cout << a.size();  // valid? technically yes, but the value is undefined
a.push_back(4.0);       // valid — a is in a valid, but empty state
```

The only guarantee after `std::move(a)` is that `a` is in a state valid for destruction or reassignment. Reading its size or content without reassigning is a silent bug.

In Alakoro, avoid:

```cpp
auto gen = SomeRule::apply(...);
auto results = collect_results(std::move(gen));
gen.resume();  // ERROR: gen no longer owns the handle
```

### 6.2 Self-assignment no move assignment / Self-Assignment in Move Assignment

#### 🇧🇷 PT

```cpp
Buffer& Buffer::operator=(Buffer&& other) noexcept {
    if (this != &other) {  // guarda essencial
        data_ = std::move(other.data_);
    }
    return *this;
}
```

Sem a verificação `this != &other`, `b = std::move(b)` poderia destruir o próprio recurso antes de movê-lo. O `ResultGenerator` do Alakoro implementa essa guarda corretamente:

#### 🇺🇸 EN

```cpp
Buffer& Buffer::operator=(Buffer&& other) noexcept {
    if (this != &other) {  // essential guard
        data_ = std::move(other.data_);
    }
    return *this;
}
```

Without the `this != &other` check, `b = std::move(b)` could destroy its own resource before moving it. Alakoro's `ResultGenerator` correctly implements this guard:

```cpp
ResultGenerator& operator=(ResultGenerator&& other) noexcept {
    if (this != &other) {
        if (handle_) handle_.destroy();
        handle_ = other.handle_;
        other.handle_ = nullptr;
    }
    return *this;
}
```

### 6.3 Exceções em move constructors / Exceptions in Move Constructors

#### 🇧🇷 PT

Se um move constructor não for `noexcept`, a biblioteca padrão pode recuar para cópias em operações como `std::vector::resize` ou `std::vector::push_back`. Por isso, recursos gerenciados manualmente devem ter move constructors marcados `noexcept`.

No Alakoro:

#### 🇺🇸 EN

If a move constructor is not `noexcept`, the standard library may fall back to copies in operations such as `std::vector::resize` or `std::vector::push_back`. Therefore, manually managed resources should have move constructors marked `noexcept`.

In Alakoro:

```cpp
ResultGenerator(ResultGenerator&& other) noexcept : handle_(other.handle_) {
    other.handle_ = nullptr;
}
```

#### 🇧🇷 PT

A operação é apenas trocar dois ponteiros; não há alocação, portanto `noexcept` é apropriado.

#### 🇺🇸 EN

The operation is just swapping two pointers; there is no allocation, so `noexcept` is appropriate.

### 6.4 `std::move` em objetos que já são rvalues / `std::move` on Objects That Are Already Rvalues

#### 🇧🇷 PT

```cpp
return std::move(local);  // geralmente piora: impede RVO/NRVO
```

O compilador pode otimizar o retorno por valor sem construir o objeto local. `std::move` nesse caso força uma chamada ao move constructor e pode eliminar a otimização. Prefira:

#### 🇺🇸 EN

```cpp
return std::move(local);  // usually worse: prevents RVO/NRVO
```

The compiler can optimize return-by-value without constructing the local object. `std::move` in this case forces a move constructor call and may disable the optimization. Prefer:

```cpp
return local;
```

#### 🇧🇷 PT

No Alakoro, `make_result` retorna por valor sem `std::move`, permitindo RVO:

#### 🇺🇸 EN

In Alakoro, `make_result` returns by value without `std::move`, allowing RVO:

```cpp
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

---

## 7. Comparação com Python / Comparison with Python

### 🇧🇷 PT

Python não tem uma noção explícita de "mover" um objeto. Variáveis Python são **referências** (ponteiros) para objetos alocados no heap.

```python
a = [1.0, 2.0, 3.0]
b = a          # b aponta para o mesmo objeto; nenhuma cópia ocorre
a.append(4.0)  # b também vê o 4.0
```

Se você quer criar uma cópia independente, deve fazê-lo explicitamente:

```python
import copy
b = copy.deepcopy(a)
```

Para dados NumPy, a distinção é semelhante:

```python
import numpy as np
x = np.array([1.0, 2.0, 3.0])
y = x              # view/referência, zero-copy
z = x.copy()       # cópia explícita
```

Em C++:

```cpp
std::vector<double> a = {1.0, 2.0, 3.0};
std::vector<double> b = a;            // cópia explícita (como deepcopy)
std::vector<double> c = std::move(a); // transferência de posse
```

A semântica de movimento em C++ é, portanto, uma ferramenta de **controle de lifetime e performance** que não tem equivalente direto em Python. No binding pybind11, o `vector_to_numpy` aproxima-se do ideal Python: move o `std::vector` para uma cápsula e entrega uma view NumPy zero-copy.

### 🇺🇸 EN

Python has no explicit notion of "moving" an object. Python variables are **references** (pointers) to heap-allocated objects.

```python
a = [1.0, 2.0, 3.0]
b = a          # b points to the same object; no copy occurs
a.append(4.0)  # b also sees 4.0
```

If you want to create an independent copy, you must do so explicitly:

```python
import copy
b = copy.deepcopy(a)
```

For NumPy data, the distinction is similar:

```python
import numpy as np
x = np.array([1.0, 2.0, 3.0])
y = x              # view/reference, zero-copy
z = x.copy()       # explicit copy
```

In C++:

```cpp
std::vector<double> a = {1.0, 2.0, 3.0};
std::vector<double> b = a;            // explicit copy (like deepcopy)
std::vector<double> c = std::move(a); // ownership transfer
```

C++ move semantics is therefore a tool of **lifetime and performance control** with no direct equivalent in Python. In the pybind11 binding, `vector_to_numpy` approaches the Python ideal: it moves the `std::vector` into a capsule and delivers a zero-copy NumPy view.

---

## 8. Resumo / Summary

### 🇧🇷 PT

| Conceito | O que faz | Exemplo no Alakoro |
|----------|-----------|-------------------|
| `T&&` | Referência para rvalue; permite roubar recursos | `ResultGenerator(ResultGenerator&&)` |
| `std::move` | Converte lvalue em rvalue | `collect_results(std::move(gen))` |
| Move constructor | Transfere posse sem copiar | `ResultGenerator` move-only |
| Move assignment | Substitui o objeto atual roubando recursos | `ResultGenerator::operator=(ResultGenerator&&)` |
| `= delete` | Impede cópia de recursos únicos | `ResultGenerator(const ResultGenerator&) = delete` |
| `std::make_move_iterator` | Move elementos entre containers | `out.insert(..., make_move_iterator(...))` |
| `noexcept` | Garante que move não lance exceções | Todos os moves de `ResultGenerator` |

A semântica de movimento é um dos pilares de performance do motor de inferência C++20 do Alakoro. Ela permite processar arrays DAS/DTS de grande volume sem cópias desnecessárias, mantendo ao mesmo tempo segurança de lifetime através de tipos move-only como `ResultGenerator`.

### 🇺🇸 EN

| Concept | What it does | Alakoro example |
|---------|--------------|-----------------|
| `T&&` | Rvalue reference; allows stealing resources | `ResultGenerator(ResultGenerator&&)` |
| `std::move` | Converts lvalue to rvalue | `collect_results(std::move(gen))` |
| Move constructor | Transfers ownership without copying | `ResultGenerator` move-only |
| Move assignment | Replaces the current object by stealing resources | `ResultGenerator::operator=(ResultGenerator&&)` |
| `= delete` | Prevents copying of unique resources | `ResultGenerator(const ResultGenerator&) = delete` |
| `std::make_move_iterator` | Moves elements between containers | `out.insert(..., make_move_iterator(...))` |
| `noexcept` | Guarantees the move won't throw | All `ResultGenerator` moves |

Move semantics is one of the performance pillars of Alakoro's C++20 inference engine. It enables processing large DAS/DTS arrays without unnecessary copies, while maintaining lifetime safety through move-only types such as `ResultGenerator`.

---

## Referências / References

### 🇧🇷 PT

- `src/cpp/include/alakoro/inference_engine.hpp` — definição de `ResultGenerator`, `InferenceEngine`, `collect_results` e regras canônicas.
- `src/cpp/src/bindings.cpp` — bindings pybind11, `vector_to_numpy` e exposição de `CanonicalInferenceEngine`.
- C++ Standard: `[class.copy]`, `[class.copy.assign]`, `[expr.prim.lambda.capture]`, `[coroutine.handle]`.

### 🇺🇸 EN

- `src/cpp/include/alakoro/inference_engine.hpp` — definition of `ResultGenerator`, `InferenceEngine`, `collect_results`, and canonical rules.
- `src/cpp/src/bindings.cpp` — pybind11 bindings, `vector_to_numpy`, and exposure of `CanonicalInferenceEngine`.
- C++ Standard: `[class.copy]`, `[class.copy.assign]`, `[expr.prim.lambda.capture]`, `[coroutine.handle]`.
