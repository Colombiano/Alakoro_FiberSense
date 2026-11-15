"""
Alakoro FiberSense — Calibração por Script Lua
Lua-script calibration for domain parameters

Autor/Author: Luiz Paulo Colombiano
Licença/License: MIT

Carrega arquivos de calibração de poço escritos em Lua (extra `calibration`,
depende de `lupa`) e aplica os parâmetros nos componentes da plataforma:
LFDASProcessor (coeficiente térmico fase→°C), FlowRegressor (limiares das
regras ternárias, ML:F-04) e qualquer motor Python cujos limiares sejam
atributos de classe (ex.: o InferenceEngine da ontologia, quando expuser
limiares nomeados — o alvo é tratado genericamente por introspecção).

Loads well-calibration scripts written in Lua (`calibration` extra, requires
`lupa`) and applies the parameters to platform components: LFDASProcessor
(phase→°C thermal coefficient), FlowRegressor (ternary-rule thresholds) and
any Python engine exposing class-level threshold attributes (handled
generically by introspection).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

_MENSAGEM_LUPA = (
    "O pacote 'lupa' é necessário para carregar calibrações Lua. Instale-o com: "
    "pip install alakoro-fibersense[calibration]   (ou: pip install 'lupa>=2.0')"
)

# Nomes de priors reconhecidos para o coeficiente térmico (SP:I-03)
_CHAVES_COEFICIENTE_TERMICO = (
    "coeficiente_acoplamento_c_por_rad",
    "thermal_coefficient_c_per_rad",
)

# Atributos conhecidos por tipo de alvo / Known attributes per target type
_ATRIBUTO_COEF_LFDAS = "thermal_coefficient_c_per_rad"


def _runtime_lua():
    """Cria o runtime Lua, com mensagem amigável se `lupa` não estiver instalado /
    Creates the Lua runtime, with a friendly message if `lupa` is missing."""
    try:
        from lupa import LuaRuntime
    except ImportError as exc:
        raise ImportError(_MENSAGEM_LUPA) from exc
    return LuaRuntime(unpack_returned_tuples=True)


def _tabela_para_dict(obj: Any) -> Any:
    """Converte recursivamente uma tabela Lua em dict/list Python /
    Recursively converts a Lua table into a Python dict/list."""
    from lupa import lua_type

    if lua_type(obj) is None:
        return obj
    chaves = list(obj.keys())
    if all(isinstance(chave, int) for chave in chaves):
        return [_tabela_para_dict(obj[i + 1]) for i in range(len(chaves))]
    return {str(chave): _tabela_para_dict(obj[chave]) for chave in chaves}


def carrega_calibracao_lua(caminho: Optional[str] = None,
                           lua: Optional[str] = None) -> Dict[str, Any]:
    """Carrega uma calibração de poço a partir de um script Lua.

    Parameters
    ----------
    caminho : str, opcional
        Caminho do arquivo `.lua`. O script deve terminar com
        `return { ... }` (uma tabela).
    lua : str, opcional
        Código Lua inline (alternativa a `caminho`).

    Returns
    -------
    dict
        Calibração convertida com as chaves canônicas:
        - "zonas_calibracao": lista de faixas de profundidade não fraturadas
          usadas na calibração (cada item com "inicio_m"/"fim_m");
        - "priors": priors físicos (ex.: "coeficiente_acoplamento_c_por_rad");
        - "thresholds": limiares das regras de inferência.

    Raises
    ------
    ImportError
        Se `lupa` não estiver instalado (extra `calibration`).
    ValueError
        Se nenhuma fonte for fornecida ou o script não retornar tabela.
    """
    if caminho is None and lua is None:
        raise ValueError("forneça 'caminho' (arquivo .lua) ou 'lua' (código inline)")
    runtime = _runtime_lua()
    codigo = Path(caminho).read_text(encoding="utf-8") if caminho is not None else lua
    tabela = runtime.execute(codigo)
    if tabela is None:
        raise ValueError("o script Lua não retornou uma tabela de calibração")
    calibracao = _tabela_para_dict(tabela)

    # Normalização mínima da estrutura / minimal structure normalization
    calibracao.setdefault("zonas_calibracao", [])
    calibracao.setdefault("priors", {})
    calibracao.setdefault("thresholds", {})
    return calibracao


def _aplica_em_lfdas(alvo: Any, calibracao: Dict[str, Any], aplicados: Dict[str, Any]) -> None:
    """Aplica o prior do coeficiente térmico quando o alvo o expõe (SP:I-03).

    Só é aplicado se o atributo já existir no alvo (ex.: LFDASProcessor);
    nenhum atributo espúrio é criado em outros componentes.
    """
    if not hasattr(alvo, _ATRIBUTO_COEF_LFDAS):
        return
    priors = calibracao.get("priors") or {}
    for chave in _CHAVES_COEFICIENTE_TERMICO:
        valor = priors.get(chave)
        if valor is not None:
            coeficiente = float(valor)
            if coeficiente <= 0:
                raise ValueError(f"prior do coeficiente térmico deve ser > 0, got {coeficiente}")
            setattr(alvo, _ATRIBUTO_COEF_LFDAS, coeficiente)
            aplicados["thermal_coefficient_c_per_rad"] = coeficiente
            return


def _aplica_thresholds(alvo: Any, calibracao: Dict[str, Any], aplicados: Dict[str, Any]) -> None:
    """Aplica limiares em atributos de classe do alvo, quando existirem.

    Somente chaves que correspondam a atributos de classe declarados no tipo
    do alvo são aplicadas (ex.: FlowRegressor.velocidade_minima_m_s); as demais
    são ignoradas silenciosamente para não criar atributos espúrios.
    """
    thresholds = calibracao.get("thresholds") or {}
    for nome, valor in thresholds.items():
        if hasattr(type(alvo), nome):
            setattr(alvo, nome, valor)
            aplicados[nome] = valor


def aplica_calibracao(alvo: Any, calibracao: Dict[str, Any]) -> Dict[str, Any]:
    """Aplica um dict de calibração (de `carrega_calibracao_lua`) em um alvo.

    Alvos suportados / Supported targets:
      - LFDASProcessor: aplica o prior do coeficiente térmico
        (thermal_coefficient_c_per_rad);
      - FlowRegressor (ou qualquer classe com os mesmos atributos de classe):
        aplica os limiares das regras ternárias definidos como atributos de
        classe (velocidade_minima_m_s, razao_energia_banda_minima,
        anomalia_sigma, banda_discriminacao_hz);
      - InferenceEngine Python da ontologia: os limiares são aplicados da
        mesma forma quando expostos como atributos de classe — caso
        contrário nenhum atributo é criado espuriamente.

    Parameters
    ----------
    alvo : object
        Instância do processador/motor a calibrar.
    calibracao : dict
        Dict retornado por `carrega_calibracao_lua`.

    Returns
    -------
    dict
        Parâmetros efetivamente aplicados (nome -> valor).
    """
    if not isinstance(calibracao, dict):
        raise TypeError("calibracao deve ser o dict retornado por carrega_calibracao_lua")

    aplicados: Dict[str, Any] = {}
    _aplica_em_lfdas(alvo, calibracao, aplicados)
    _aplica_thresholds(alvo, calibracao, aplicados)
    return aplicados


__all__ = ["carrega_calibracao_lua", "aplica_calibracao"]
