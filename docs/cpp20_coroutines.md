# Coroutines (Corrotinas) em C++20

## Foco no Alakoro FiberSense

Este documento explica, de forma profunda e didática, como as **corrotinas do C++20** são usadas no núcleo C++ do Alakoro FiberSense para implementar o motor de inferência de eventos em fibras ópticas de sensoreamento (DTS/DAS).

Todas as amostras de código são extraídas do arquivo real do projeto:

```text
src/cpp/include/alakoro/inference_engine.hpp
```

---

## 1. O que são corrotinas?

Uma **corrotina** é uma função capaz de **suspender** sua execução em um ponto qualquer, **preservar seu estado local** (variáveis, registradores, ponto de execução) e **retomar** mais tarde exatamente de onde parou.

Imagine uma função normal como um telefonema: quando você desliga, tudo se perde. Uma corrotina é como uma conversa por mensagens de texto: você pode parar no meio da frase e continuar depois, sem perder o contexto.

Em C++20, uma função se torna corrotina automaticamente se usa qualquer uma destas palavras-chave:

- `co_await` — suspende a execução esperando uma operação.
- `co_yield` — suspende e devolve um valor ao chamador.
- `co_return` — termina a corrotina e devolve um valor final.

> **Importante:** quando uma corrotina é suspensa, o compilador aloca (tipicamente no heap) uma estrutura chamada **frame de corrotina**, que guarda as variáveis locais, temporários e o ponto de retorno. O chamador recebe um *handle* que permite retomar a corrotina.

---

## 2. Comparação com iteradores/generators em Python

Se você conhece Python, a ideia é muito parecida com `yield`:

```python
# Python: generator simples
def contador(maximo):
    n = 0
    while n < maximo:
        yield n          # suspende e devolve n
        n += 1           # retoma daqui na próxima iteração

for x in contador(3):
    print(x)             # 0, 1, 2
```

Em C++20, o equivalente manual seria algo como:

```cpp
// C++20: corrotina com co_yield
ResultGenerator minha_regra(...) {
    for (std::size_t c = 0; c < n_channels; ++c) {
        auto res = processar_canal(c);
        co_yield res;          // suspende e devolve InferenceResult
    }
    co_return;                 // fim da corrotina
}
```

### Diferenças principais

| Aspecto | Python `yield` | C++20 coroutines |
|---|---|---|
| Tipo retornado | objeto `generator` | tipo definido pelo usuário (RAII) |
| Controle do estado | interpretador gerencia | compilador + `promise_type` |
| Alocação | automática | heap, mas configurável |
| Segurança de lifetime | gerenciada pelo GC | programador controla via `coroutine_handle` |
| Personalização | limitada | total: promessa, suspensão, exceções |

A maior vantagem do C++20 é o **controle total**: você decide quando suspender, como armazenar o valor produzido, como destruir o frame e como expor a API ao chamador.

---

## 3. Componentes de uma corrotina em C++20

### 3.1 `co_yield`, `co_return` e `co_await`

- `co_yield valor` — suspende a corrotina e torna `valor` disponível para o chamador.
- `co_return` — finaliza a corrotina. Pode vir com ou sem valor, dependendo da `promise_type`.
- `co_await` — suspende até que uma *awaitable* esteja pronta. No Alakoro não usamos `co_await` diretamente nas regras, mas a infraestrutura de corrotinas o utiliza internamente para implementar `co_yield`.

### 3.2 `promise_type`

A `promise_type` é uma estrutura aninhada obrigatória que define o *comportamento* da corrotina. O compilador acessa seus métodos para:

- criar o objeto retornado (`get_return_object`);
- decidir se suspende no início (`initial_suspend`);
- decidir se suspende no fim (`final_suspend`);
- receber valores produzidos por `co_yield` (`yield_value`);
- tratar exceções (`unhandled_exception`);
- tratar `co_return` (`return_void` ou `return_value`).

### 3.3 `std::coroutine_handle`

É um ponteiro opaco (e barato de copiar) para o frame da corrotina. Através dele podemos:

- `resume()` — retomar a execução.
- `done()` — verificar se a corrotina terminou.
- `destroy()` — destruir o frame e liberar memória.
- `promise()` — acessar a `promise_type` associada.

### 3.4 Políticas de suspensão

O C++20 oferece duas políticas prontas:

- `std::suspend_always` — sempre suspende.
- `std::suspend_never` — nunca suspende.

No Alakoro usamos `std::suspend_always` tanto no início quanto no fim, o que permite ao chamador consumir o generator no seu próprio ritmo.

---

## 4. Implementação real: `ResultGenerator`

A classe `ResultGenerator` está definida em `src/cpp/include/alakoro/inference_engine.hpp`, por volta da linha 228.

### 4.1 Visão geral

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
            current_value = std::move(value);
            return {};
        }
    };

    using handle_type = std::coroutine_handle<promise_type>;

    explicit ResultGenerator(handle_type h) : handle_(h) {}

    ResultGenerator(const ResultGenerator&) = delete;
    ResultGenerator& operator=(const ResultGenerator&) = delete;

    ResultGenerator(ResultGenerator&& other) noexcept : handle_(other.handle_) {
        other.handle_ = nullptr;
    }

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

### 4.2 Explicação método a método

#### `promise_type`

- **`InferenceResult current_value;`**
  
  Armazena o último valor produzido por `co_yield`. O chamador acessa esse campo via `handle.promise().current_value`.

- **`ResultGenerator get_return_object()`**
  
  Chamado pelo compilador assim que o frame da corrotina é criado. Ele constrói o `ResultGenerator` que será visto pelo chamador, usando `std::coroutine_handle<promise_type>::from_promise(*this)` para obter o handle a partir da promessa.

- **`std::suspend_always initial_suspend() noexcept`**
  
  A corrotina suspende imediatamente após entrar no corpo da função. Isso é típico de generators: o primeiro `resume()` executa o código até o primeiro `co_yield`.

- **`std::suspend_always final_suspend() noexcept`**
  
  A corrotina também suspende ao atingir `co_return` ou o fim do corpo. O chamador detecta o término via `done()`.

- **`void unhandled_exception()`**
  
  Se uma exceção escapar do corpo da corrotina, este método é chamado. Aqui optamos por `std::terminate()` — simples, mas rigoroso.

- **`void return_void() noexcept`**
  
  Nossas regras usam `co_return;` sem valor. Portanto a promessa implementa `return_void()`.

- **`std::suspend_always yield_value(InferenceResult value) noexcept`**
  
  Chamado para cada `co_yield`. Movemos o valor para `current_value` e retornamos `std::suspend_always`, fazendo a corrotina parar imediatamente após produzir o resultado.

#### Classe `ResultGenerator`

- **`explicit ResultGenerator(handle_type h)`**
  
  Construtor que recebe o handle criado pela promessa.

- **Construtor de cópia deletado**
  
  `coroutine_handle` é um recurso único; copiar geraria dois donos do mesmo frame.

- **Construtor/operador de move**
  
  Transferem a propriedade do handle, anulando o objeto de origem. No move assignment, destruímos o frame atual antes de assumir o novo.

- **`~ResultGenerator()`**
  
  Se ainda houver um handle ativo, chamamos `destroy()` para liberar o frame da corrotina. Sem isso haveria vazamento de memória.

- **`done()`, `resume()`, `value()`**
  
  API mínima para consumir o generator: verifica se terminou, retoma a execução e lê o valor atual.

---

## 5. Como as regras de inferência usam `co_yield`

Cada regra é uma função estática que retorna `ResultGenerator`. Veja um exemplo real, extraído de `JouleThomsonRule::apply`:

```cpp
static ResultGenerator apply(std::span<const double> dts,
                             std::span<const double>,
                             std::size_t n_times,
                             std::size_t n_channels,
                             const InferenceMetadata& meta) {
    // ... cálculos de perfil médio, baseline, anomalia, score ...

    if (best_score > threshold) {
        double depth = detail::channel_to_depth(best_idx, meta.depth_step_m);
        double conf = std::min(best_score / (5.0 * threshold), 1.0);
        co_yield make_result<CanonicalEvent::JouleThomson>(
            conf, depth, conf > 0.7 ? "High" : (conf > 0.4 ? "Medium" : "Low"));
    }
    co_return;
}
```

### Por que isso é vantajoso?

Sem corrotinas, cada regra precisaria:

1. Alocar um `std::vector<InferenceResult>`;
2. Preencher todos os resultados;
3. Retornar o vetor completo para quem a chamou.

Com corrotinas:

1. A regra produz **um resultado por vez** via `co_yield`;
2. O consumidor decide quando continuar;
3. **Não há vetor intermediário grande** — só o resultado atual fica na `promise_type`;
4. A memória do frame da corrotina é fixa e previsível.

Outro exemplo, de `SlopeVelocityRule`, mostra que podemos mover o resultado já construído:

```cpp
auto res = make_result<CanonicalEvent::SlopeVelocity>(
    conf, depth, conf > 0.7 ? "High" : "Medium");
res.recommendation += " Velocidade estimada: " + std::to_string(velocity) + " m/s.";
co_yield std::move(res);
```

Aqui `co_yield std::move(res)` evita uma cópia do `std::string recommendation`.

---

## 6. Consumindo o generator: `collect_results`

A função `collect_results` é a ponte entre a API corrotinada interna e a API síncrona exposta ao Python.

```cpp
inline std::vector<InferenceResult> collect_results(ResultGenerator gen) {
    std::vector<InferenceResult> results;
    results.reserve(4); // estimativa inicial; evita realocações para regras típicas
    while (!gen.done()) {
        gen.resume();
        if (!gen.done()) {
            results.push_back(std::move(gen.value()));
        }
    }
    return results;
}
```

### Fluxo de execução

1. A `InferenceEngine` cria um `ResultGenerator` chamando `Rule::apply(...)`.
2. Passa o generator por move para `collect_results`.
3. Enquanto a corrotina não terminar, `resume()` executa o código até o próximo `co_yield`.
4. Após cada suspensão, o valor em `gen.value()` é movido para o vetor final.
5. Quando `co_return` é atingido, `done()` passa a ser `true` e o loop termina.

A `InferenceEngine` usa `if constexpr` para selecionar a regra correta em tempo de compilação e fold expressions para executar todas as regras registradas:

```cpp
template <CanonicalEvent... Events>
class InferenceEngine {
public:
    std::vector<InferenceResult> infer(...) const {
        std::vector<InferenceResult> all;
        all.reserve(sizeof...(Events));
        (execute_rule<Events>(dts, das, n_times, n_channels, meta, all), ...);
        return all;
    }

private:
    template <CanonicalEvent E>
    void execute_rule(..., std::vector<InferenceResult>& out) const {
        ResultGenerator gen = [&]() {
            if constexpr (E == CanonicalEvent::JouleThomson) {
                return JouleThomsonRule::apply(...);
            }
            // ... outras regras ...
        }();
        auto partial = collect_results(std::move(gen));
        out.insert(out.end(),
                   std::make_move_iterator(partial.begin()),
                   std::make_move_iterator(partial.end()));
    }
};
```

---

## 7. Exposição ao Python via pybind11

O arquivo `src/cpp/src/bindings.cpp` expõe uma API **síncrona** ao Python, escondendo completamente as corrotinas C++.

### Estrutura do resultado

```cpp
py::class_<InferenceResult>(m, "InferenceResult")
    .def_readonly("event_type", &InferenceResult::event_type)
    .def_readonly("event_label_pt", &InferenceResult::event_label_pt)
    .def_readonly("event_label_en", &InferenceResult::event_label_en)
    .def_readonly("confidence", &InferenceResult::confidence)
    .def_readonly("depth_md", &InferenceResult::depth_md)
    .def_readonly("severity", &InferenceResult::severity)
    .def_readonly("recommendation", &InferenceResult::recommendation)
    .def("__repr__", [](const InferenceResult& r) {
        std::ostringstream oss;
        oss << "InferenceResult(" << r.event_type
            << ", confidence=" << r.confidence
            << ", depth_md=" << r.depth_md
            << ", severity=" << r.severity << ")";
        return oss.str();
    });
```

### Engine exposta como objeto Python

```cpp
py::class_<CanonicalInferenceEngine>(m, "CanonicalInferenceEngine")
    .def(py::init<>())
    .def("infer",
         [](const CanonicalInferenceEngine& engine,
            py::array_t<double> dts_array,
            std::optional<py::array_t<double>> das_array,
            const InferenceMetadata& meta) {
             auto dts_buf = dts_array.request();
             if (dts_buf.ndim != 2) {
                 throw std::invalid_argument("dts must be a 2D array (time, channel)");
             }
             const std::size_t n_times = static_cast<std::size_t>(dts_buf.shape[0]);
             const std::size_t n_channels = static_cast<std::size_t>(dts_buf.shape[1]);
             auto dts_span = std::span<const double>(static_cast<const double*>(dts_buf.ptr),
                                                     n_times * n_channels);
             // ... tratamento opcional de DAS ...
             return engine.infer(dts_span, das_span, n_times, n_channels, meta);
         },
         py::arg("dts"), py::arg("das") = py::none(), py::arg("metadata"),
         "Run all canonical inference rules on DTS (and optional DAS) data.");
```

### Função helper síncrona

```cpp
m.def("infer_events_d",
      [](py::array_t<double> dts_array,
         std::optional<py::array_t<double>> das_array,
         const InferenceMetadata& meta) {
          CanonicalInferenceEngine engine;
          // ... converte arrays para span ...
          return engine.infer(dts_span, das_span, n_times, n_channels, meta);
      },
      py::arg("dts"), py::arg("das") = py::none(), py::arg("metadata"),
      "Convenience function: run CanonicalInferenceEngine.infer()");
```

Para o usuário Python, a chamada é trivial:

```python
import numpy as np
from alakoro_core import infer_events_d, InferenceMetadata

meta = InferenceMetadata()
meta.sampling_rate_hz = 10.0
meta.depth_step_m = 1.0
meta.surface_temp_c = 25.0
meta.geo_gradient_cpm = 0.03

results = infer_events_d(dts_array, None, meta)
for r in results:
    print(r.event_type, r.confidence, r.depth_md, r.severity)
```

O generator existe apenas dentro do C++; o Python recebe uma simples `list` de `InferenceResult`.

---

## 8. Diagrama de fluxo: suspender e retomar

```text
Python
  │
  ▼
infer_events_d(dts, metadata)
  │
  ▼
CanonicalInferenceEngine::infer()
  │
  ├──► JouleThomsonRule::apply(...) ──► co_yield res ──► suspende
  │                                      │
  │                                      ▼
  │                              frame guarda estado
  │                                      │
  ▼                                      ▼
collect_results(gen) ◄──────────── resume()
  │                                      │
  ▼                                      ▼
results.push_back(res) ◄──────── value() da promise
  │
  ├──► resume() ──► continua regra até co_return
  │
  ▼
gen.done() == true
  │
  ▼
retorna vector<InferenceResult>
  │
  ▼
pybind11 converte para list[InferenceResult]
  │
  ▼
Python consome a lista
```

### Passo a passo visual

```text
Estado da corrotina ao longo do tempo:

  ┌─────────────────────────────────────┐
  │  1. apply() é chamada               │
  │     → frame criado no heap          │
  │     → initial_suspend() → PAUSA     │
  └─────────────────┬───────────────────┘
                    │ gen.resume()
  ┌─────────────────▼───────────────────┐
  │  2. Código executa até co_yield      │
  │     → yield_value(res) armazena     │
  │       res em current_value          │
  │     → PAUSA                         │
  └─────────────────┬───────────────────┘
                    │ gen.value()
  ┌─────────────────▼───────────────────┐
  │  3. Chamador lê current_value       │
  │     → move para vector              │
  │     → gen.resume() novamente        │
  └─────────────────┬───────────────────┘
                    │
  ┌─────────────────▼───────────────────┐
  │  4. Repete até co_return             │
  │     → final_suspend() → PAUSA       │
  │     → gen.done() == true            │
  └─────────────────┬───────────────────┘
                    │
  ┌─────────────────▼───────────────────┐
  │  5. collect_results termina          │
  │     → destrutor libera o frame      │
  └─────────────────────────────────────┘
```

---

## 9. Pegadinhas comuns

### 9.1 Lifetime do handle

O `std::coroutine_handle` é um ponteiro leve. Se você copiá-lo sem cuidado, pode ter dois objetros apontando para o mesmo frame. Por isso `ResultGenerator` **deleta o construtor de cópia**.

```cpp
ResultGenerator(const ResultGenerator&) = delete;
ResultGenerator& operator=(const ResultGenerator&) = delete;
```

Se o `ResultGenerator` for destruído prematuramente — por exemplo, se uma exceção for lançada antes que `collect_results` termine — o destrutor chama `handle_.destroy()`, evitando vazamento.

### 9.2 Esquecer de chamar `destroy()`

Se você implementar sua própria classe envelope e esquecer o destrutor, o frame da corrotina ficará alocado para sempre. No Alakoro isso está coberto:

```cpp
~ResultGenerator() {
    if (handle_) handle_.destroy();
}
```

### 9.3 Move semantics

Sempre que possível, passe o generator por **move**:

```cpp
auto partial = collect_results(std::move(gen));
```

Isso transfere a propriedade do handle para a função consumidora, mantendo a invariante de propriedade única.

### 9.4 `co_yield` com objetos pesados

Objetos como `InferenceResult` contêm várias `std::string`. Use `std::move` para evitar cópias:

```cpp
co_yield std::move(res);  // preferível
// vs
co_yield res;             // copia — aceitável se res for pequeno
```

### 9.5 Exceções em corrotinas

Se uma exceção não for capturada dentro da corrotina, `unhandled_exception()` é chamado. No Alakoro usamos `std::terminate()`, o que encerra o processo. Em produção, você pode querer armazenar a exceção e relançá-la no chamador:

```cpp
void unhandled_exception() {
    exception_ = std::current_exception();
}
```

### 9.6 `std::suspend_never` vs `std::suspend_always`

Se `initial_suspend()` retornar `std::suspend_never`, a corrotina executa até o primeiro ponto de suspensão antes mesmo do chamador ter uma chance de interagir. Para generators isso geralmente não é desejado, pois perde-se o controle fino sobre o primeiro valor.

---

## 10. Resumo

As corrotinas C++20 permitem ao Alakoro FiberSense:

- Implementar regras de inferência que produzem `InferenceResult` de forma incremental.
- Evitar alocação de grandes vetores intermediários.
- Manter o código sequencial e legível, mesmo com lógica de pausa/resume.
- Esconder toda a complexidade assíncrona atrás de uma API síncrona e amigável ao Python via pybind11.

O `ResultGenerator` é uma implementação mínima mas completa: define `promise_type`, gerencia o `coroutine_handle`, proíbe cópia, implementa move semantics e garante destruição correta do frame.

Para ver o código completo, consulte:

- `src/cpp/include/alakoro/inference_engine.hpp` — definição do generator, regras e engine.
- `src/cpp/src/bindings.cpp` — bindings pybind11 para `CanonicalInferenceEngine` e `infer_events_d`.

---

*Documento gerado para o projeto Alakoro FiberSense.*
