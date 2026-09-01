# Move Semantics (Semântica de Movimento) em C++20 — Alakoro FiberSense

## 1. O problema: cópias caras de objetos grandes

No processamento de dados de fibra óptica (DAS/DTS/DSS) do Alakoro, trabalhamos com volumes significativos: trilhas de amplitude/strain ao longo de milhares de amostras temporais e centenas ou milhares de canais de profundidade. Um único `std::vector<double>` que represente uma aquisição pode facilmente ocupar dezenas de megabytes.

Quando C++ copia esses objetos — seja um vetor de dados brutos, uma matriz de resultados ou uma corrotina que encapsula estado de processamento — o custo é proporcional ao tamanho do buffer. Para o motor de inferência (`InferenceEngine`), isso significa cópias indesejadas entre:

- a extração de perfis médios (`temporal_mean`);
- a remoção de baseline (`remove_polynomial_baseline`, `remove_median_baseline`);
- a acumulação de `InferenceResult`;
- o retorno de resultados para Python via pybind11.

A **semântica de movimento** (move semantics), introduzida no C++11 e aperfeiçoada no C++14/C++17/C++20, resolve exatamente esse problema: em vez de duplicar recursos, transferimos a posse (ownership) dos dados de um objeto para outro. O buffer de memória não é copiado; apenas os ponteiros internos são trocados.

## 2. Conceitos fundamentais

### 2.1 lvalue vs rvalue

- **lvalue** (left value): expressão que tem identidade e endereço. Pode aparecer à esquerda de uma atribuição.
  - Exemplos: uma variável nomeada, um elemento de vetor, um retorno por referência.
- **rvalue** (right value): expressão temporária, sem identidade própria. Geralmente aparece à direita de uma atribuição.
  - Exemplos: o resultado de uma função que retorna por valor, um literal, `std::move(x)`.

```cpp
std::vector<double> make_data();          // retorna um rvalue
std::vector<double> v = make_data();      // v é um lvalue
v[0] = 1.0;                               // v[0] é um lvalue
std::vector<double> w = std::move(v);     // std::move(v) é um rvalue
```

### 2.2 Referências

| Sintaxe | Significado | Quando usar |
|---------|-------------|-------------|
| `T&` | Referência não-constante para lvalue | Modificar o objeto original sem copiá-lo |
| `const T&` | Referência constante para lvalue/rvalue | Ler o objeto sem copiá-lo; liga-se a temporários |
| `T&&` | Referência para rvalue | Implementar move semantics; "roubar" recursos de um temporário |

> A regra prática: use `const T&` para leitura, `T&&` para mover, e `T&` quando precisar modificar o objeto original.

### 2.3 Move constructor e move assignment operator

Todo tipo pode ter, além do construtor de cópia e do operador de atribuição por cópia, versões de **movimento**:

```cpp
class Buffer {
public:
    // Construtor padrão
    Buffer() = default;

    // Construtor de cópia (deep copy)
    Buffer(const Buffer& other) : data_(other.data_) { /* copia elementos */ }

    // Operador de atribuição por cópia
    Buffer& operator=(const Buffer& other) {
        if (this != &other) {
            data_ = other.data_;  // copia
        }
        return *this;
    }

    // Move constructor: rouba os recursos de other
    Buffer(Buffer&& other) noexcept : data_(std::move(other.data_)) {
        // other é deixado em estado válido, mas vazio
    }

    // Move assignment operator
    Buffer& operator=(Buffer&& other) noexcept {
        if (this != &other) {
            data_ = std::move(other.data_);  // move o vetor interno
        }
        return *this;
    }

private:
    std::vector<double> data_;
};
```

A palavra-chave `noexcept` é importante: se um move constructor lançar exceção, algumas operações da biblioteca padrão (como realocação de vetores) recuam para cópias, perdendo o ganho de performance.

### 2.4 `std::move`: um cast, não uma operação de movimento

`std::move(x)` **não move** `x`. Ele apenas converte `x` em um rvalue, permitindo que o compilador escolha a sobrecarga de movimento.

```cpp
std::vector<double> a = {1.0, 2.0, 3.0};
std::vector<double> b = std::move(a);  // agora b tem os dados; a está vazio
```

Após `std::move(a)`, o estado de `a` é válido mas indefinido em termos de conteúdo. A única operação segura garantida é destruí-lo ou reassinar.

### 2.5 Rule of Zero / Rule of Five

- **Rule of Zero**: se seus membros gerenciam recursos corretamente (como `std::vector`, `std::string`, `std::unique_ptr`), você **não precisa** escrever destrutor, cópia ou movimento. O compilador gera tudo corretamente.
- **Rule of Five**: se você precisa implementar **qualquer um** de (destrutor, copy constructor, copy assignment, move constructor, move assignment), provavelmente precisa implementar os cinco — ou declarar explicitamente o que não deve existir (`= delete`).

No Alakoro, `ResultGenerator` segue a **Rule of Five** de propósito: ele possui um `std::coroutine_handle`, que é um recurso único. Por isso, a cópia é deletada e o movimento é implementado manualmente.

## 3. Exemplos mínimos: antes e depois do move

### 3.1 Antes: cópia explícita de vetores

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

### 3.2 Depois: move em vez de copiar

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

```cpp
auto first_half = detail::temporal_mean(dts.subspan(0, mid_t * n_channels),
                                         mid_t, n_channels);
auto second_half = detail::temporal_mean(
    dts.subspan(mid_t * n_channels, (n_times - mid_t) * n_channels),
    n_times - mid_t, n_channels);

auto anom1 = detail::remove_polynomial_baseline(std::move(first_half), 2);
auto anom2 = detail::remove_polynomial_baseline(std::move(second_half), 2);
```

## 4. Aplicação no Alakoro

### 4.1 `ResultGenerator`: recurso único, delete copy, implement move

A `ResultGenerator` é a corrotina que produz `InferenceResult` via `co_yield`. Por baixo, ela guarda um `std::coroutine_handle<promise_type>`, um identificador de frame de corrotina — um recurso que não pode ser compartilhado.

No arquivo `src/cpp/include/alakoro/inference_engine.hpp` (linhas 228–281):

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
            return {};
        }
    };

    using handle_type = std::coroutine_handle<promise_type>;

    explicit ResultGenerator(handle_type h) : handle_(h) {}

    // Não copiável: coroutine_handle é um recurso único.
    ResultGenerator(const ResultGenerator&) = delete;
    ResultGenerator& operator=(const ResultGenerator&) = delete;

    // Move constructor: transfere posse do handle
    ResultGenerator(ResultGenerator&& other) noexcept : handle_(other.handle_) {
        other.handle_ = nullptr;
    }

    // Move assignment: destrói handle antigo, rouba o novo
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

Observe:

1. **Cópia deletada**: `ResultGenerator(const ResultGenerator&) = delete;`. Tentar copiar uma corrotina é um erro de compilação, garantindo que nunca haverá dois handles para o mesmo frame.
2. **Move constructor `noexcept`**: rouba o `handle_` e zera o objeto fonte.
3. **Move assignment com self-check**: destrói o recurso antigo antes de assumir o novo, evitando vazamento.
4. **yield com move**: `current_value = std::move(value);` evita copiar `std::string`s dentro de `InferenceResult`.

### 4.2 `collect_results` e consumo da corrotina

A função `collect_results` é a ponte entre a API corrotinada interna e a API síncrona exposta. No código atual, ela recebe `ResultGenerator` por valor (linha 1230):

```cpp
inline std::vector<InferenceResult> collect_results(ResultGenerator gen) {
    std::vector<InferenceResult> results;
    results.reserve(4);
    while (!gen.done()) {
        gen.resume();
        if (!gen.done()) {
            results.push_back(std::move(gen.value()));  // move do generator para o vetor
        }
    }
    return results;
}
```

Receber por valor ainda permite que o caller mova a corrotina no momento da chamada:

```cpp
auto partial = collect_results(std::move(gen));
```

Uma alternativa ainda mais explícita, que deixa claro que a função **consome** o gerador, seria usar uma rvalue reference:

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

Com essa assinatura, `collect_results(std::move(gen))` continua válido, mas `collect_results(gen)` se torna um erro de compilação, aumentando a segurança: ninguém pode esquecer de mover acidentalmente e depois tentar reusar `gen`.

### 4.3 `execute_rule`: movendo o generator e os resultados parciais

No `InferenceEngine`, cada regra é executada dentro de `execute_rule`, e seus resultados são fundidos no vetor final via `std::make_move_iterator` (linhas 1276–1316):

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
    }();

    auto partial = collect_results(std::move(gen));  // move a corrotina

    out.insert(out.end(),
               std::make_move_iterator(partial.begin()),
               std::make_move_iterator(partial.end()));  // move cada InferenceResult
}
```

Sem `std::move(gen)`, `collect_results` tentaria copiar a corrotina — o que falharia em compilação, graças ao `= delete` na cópia. Sem `std::make_move_iterator`, os `InferenceResult` (que contêm várias `std::string`) seriam copiados um a um para `out`.

### 4.4 pybind11: `py::return_value_policy::move`

No `src/cpp/src/bindings.cpp`, a camada Python recebe os vetores de resultados por valor e os converte para listas/tuplas de NumPy. A função `vector_to_numpy` (linhas 43–50) já aproveita a semântica de movimento internamente:

```cpp
template <typename T>
py::array_t<T> vector_to_numpy(std::vector<T> vec) {
    const std::size_t size = vec.size();
    T* data = vec.data();
    auto* owned = new std::vector<T>(std::move(vec));  // move o vetor para a cápsula
    py::capsule capsule(owned, [](void* p) { delete static_cast<std::vector<T>*>(p); });
    return py::array_t<T>({size}, {sizeof(T)}, data, capsule);
}
```

Aqui, o `std::vector<T>` é movido para dentro de um `std::vector<T>` alocado no heap, que vive dentro de uma `py::capsule`. O array NumPy aponta para os mesmos dados sem cópia.

Quando registramos funções que retornam objetos C++ diretamente (não vetores convertidos manualmente), podemos instruir o pybind11 a mover o retorno em vez de copiar:

```cpp
m.def("make_inference_result",
      []() { return InferenceResult{...}; },
      py::return_value_policy::move,
      "Retorna um InferenceResult movido para Python");
```

No binding atual do `infer_events_d`, o retorno é `std::vector<InferenceResult>`. Como `pybind11/stl.h` está incluído, o pybind11 converte automaticamente o vetor para uma `list` Python. Internamente, cada `InferenceResult` é **copiado** durante essa conversão, porque o padrão para tipos registrados é `copy` quando expostos dentro de containers STL.

Se quisermos garantir movimento também no retorno para Python, a alternativa é:

1. Retornar por valor e confiar na otimização de cópia (RVO/NRVO) do C++ no lado nativo.
2. Para objetos pesados, expor explicitamente o move constructor no binding:

```cpp
py::class_<InferenceResult>(m, "InferenceResult")
    .def(py::init<>())
    .def(py::init<const InferenceResult&>())  // copy
    .def(py::init<InferenceResult&&>())       // move (geralmente implícito)
    // ... membros ...
```

Para o caso do Alakoro, a cópia de `InferenceResult` é aceitável: cada resultado contém apenas strings pequenas (nome do evento, severidade, recomendação) e poucos `double`. O ganho de performance vem principalmente de **não copiar os arrays DAS/DTS** durante o processamento interno.

## 5. Ganho de performance e segurança para o Alakoro

### 5.1 Evita copiar arrays entre regras

As regras de inferência operam sobre perfis temporários:

```cpp
auto mean_profile = detail::temporal_mean(dts, n_times, n_channels);
auto anomaly = detail::remove_polynomial_baseline(std::move(mean_profile), 2);
```

Sem `std::move`, `remove_polynomial_baseline` receberia uma referência constante e teria que alocar um novo vetor para o resultado. Com `std::move`, a função recebe o vetor por valor e pode reutilizar seu buffer para armazenar o resultado, economizando uma alocação e uma cópia.

### 5.2 Corrotinas sem cópia

`ResultGenerator` é **move-only**. Isso garante que:

- cada frame de corrotina tenha exatamente um dono;
- não haja double-free ou uso após destruição;
- o `std::coroutine_handle` seja destruído exatamente uma vez no destrutor.

### 5.3 Composição segura de resultados

`std::make_move_iterator` permite fundir resultados parciais de várias regras no vetor final sem copiar strings:

```cpp
out.insert(out.end(),
           std::make_move_iterator(partial.begin()),
           std::make_move_iterator(partial.end()));
```

### 5.4 Estimativa de impacto

Para uma aquisição típica de DAS/DTS com $N_t \times N_c$ amostras:

- `temporal_mean` produz um vetor de $N_c$ doubles.
- `remove_polynomial_baseline` produz outro vetor de $N_c$ doubles.

Sem move: cada etapa aloca um novo buffer e copia $N_c$ elementos.  
Com move: a segunda etapa reusa o buffer da primeira. Em $N_c = 10.000$, isso evita copiar ~80 KB por etapa, por regra, por execução. Multiplicado pelas 15 regras canônicas e por muitas iterações de processamento, o ganho se torna mensurável em tempo e pressão sobre o garbage collector / allocator.

## 6. Armadilhas

### 6.1 Usar um objeto depois de `std::move`

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

### 6.2 Self-assignment no move assignment

```cpp
Buffer& Buffer::operator=(Buffer&& other) noexcept {
    if (this != &other) {  // guarda essencial
        data_ = std::move(other.data_);
    }
    return *this;
}
```

Sem a verificação `this != &other`, `b = std::move(b)` poderia destruir o próprio recurso antes de movê-lo. O `ResultGenerator` do Alakoro implementa essa guarda corretamente:

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

### 6.3 Exceções em move constructors

Se um move constructor não for `noexcept`, a biblioteca padrão pode recuar para cópias em operações como `std::vector::resize` ou `std::vector::push_back`. Por isso, recursos gerenciados manualmente devem ter move constructors marcados `noexcept`.

No Alakoro:

```cpp
ResultGenerator(ResultGenerator&& other) noexcept : handle_(other.handle_) {
    other.handle_ = nullptr;
}
```

A operação é apenas trocar dois ponteiros; não há alocação, portanto `noexcept` é apropriado.

### 6.4 `std::move` em objetos que já são rvalues

```cpp
return std::move(local);  // geralmente piora: impede RVO/NRVO
```

O compilador pode otimizar o retorno por valor sem construir o objeto local. `std::move` nesse caso força uma chamada ao move constructor e pode eliminar a otimização. Prefira:

```cpp
return local;
```

No Alakoro, `make_result` retorna por valor sem `std::move`, permitindo RVO:

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

## 7. Comparação com Python

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

## 8. Resumo

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

## Referências

- `src/cpp/include/alakoro/inference_engine.hpp` — definição de `ResultGenerator`, `InferenceEngine`, `collect_results` e regras canônicas.
- `src/cpp/src/bindings.cpp` — bindings pybind11, `vector_to_numpy` e exposição de `CanonicalInferenceEngine`.
- C++ Standard: [class.copy], [class.copy.assign], [expr.prim.lambda.capture], [coroutine.handle].
