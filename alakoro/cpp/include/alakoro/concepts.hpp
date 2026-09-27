/**
 * @file concepts.hpp
 * @brief Concepts C++20 para tipos de dados suportados pelo Alakoro.
 *
 * Aqui usamos C++20 concepts para restringir templates a tipos numéricos
 * que fazem sentido para dados de sensing (float, double, int, etc.).
 * Concepts permitem erros de compilação claros em vez de mensagens de
 * template instantiation intermináveis.
 */

#pragma once

#include <concepts>
#include <type_traits>

namespace alakoro {

/**
 * @brief Concept para tipos numéricos escalares suportados.
 *
 * Requer que o tipo seja aritmético (inteiro ou ponto flutuante) mas
 * não bool nem char (que são aritméticos em C++ mas não representam
 * grandezas físicas para nossos dados).
 */
template <typename T>
concept NumericScalar = std::is_arithmetic_v<T> &&
                        !std::is_same_v<T, bool> &&
                        !std::is_same_v<T, char> &&
                        !std::is_same_v<T, signed char> &&
                        !std::is_same_v<T, unsigned char>;

/**
 * @brief Concept para tipos de ponto flutuante.
 *
 * Usado quando precisamos garantir precisão em cálculos científicos,
 * como filtros, derivadas e transformadas.
 */
template <typename T>
concept FloatingPoint = std::floating_point<T>;

/**
 * @brief Concept para tipos que podem ser usados como índice de canal/tempo.
 */
template <typename T>
concept IndexType = std::integral<T> && !std::is_same_v<T, bool>;

} // namespace alakoro
