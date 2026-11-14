"""
Alakoro FiberSense — Cenários Lua para o Módulo MSE
Lua Scenarios for the MSE Module

Carrega cenários de monitoramento escritos em Lua (via `lupa`) e os
converte em estruturas Python do módulo MSE. O script Lua deve retornar
uma tabela com as chaves `geometria`, `aquisicao`, `material`,
`fissuras` e `gerador`.

Loads monitoring scenarios written in Lua (via `lupa`) and converts them
into MSE module Python structures. The Lua script must return a table
with the keys `geometria`, `aquisicao`, `material`, `fissuras` and
`gerador`.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from .signatures import GeradorAssinaturasMSE
from .structures import ConfigAquisicaoMSE, GeometriaEstrutura, TrechoExposicao

_MENSAGEM_LUPA = (
    "O pacote 'lupa' é necessário para carregar cenários Lua. Instale-o com: "
    "pip install alakoro-fibersense[mse]   (ou: pip install 'lupa>=2.0')"
)


def _runtime_lua():
    """Cria o runtime Lua, com mensagem amigável se `lupa` não estiver instalado /
    Creates the Lua runtime, with a friendly message if `lupa` is missing."""
    try:
        from lupa import LuaRuntime
    except ImportError as exc:
        raise ImportError(_MENSAGEM_LUPA) from exc
    return LuaRuntime(unpack_returned_tuples=True)


def tabela_para_dict(obj: Any) -> Any:
    """Converte recursivamente uma tabela Lua em dict/list Python /
    Recursively converts a Lua table into a Python dict/list.

    Tabelas com chaves inteiras 1..n viram listas; as demais viram dicts.
    Escalares (números, strings, booleanos) passam direto.
    """
    from lupa import lua_type

    if lua_type(obj) is None:
        return obj
    chaves = list(obj.keys())
    if all(isinstance(chave, int) for chave in chaves):
        return [tabela_para_dict(obj[i + 1]) for i in range(len(chaves))]
    return {str(chave): tabela_para_dict(obj[chave]) for chave in chaves}


def carrega_cenario_lua(caminho: Optional[str] = None, lua: Optional[str] = None) -> Dict[str, Any]:
    """Carrega um cenário MSE a partir de um script Lua / Loads an MSE scenario from a Lua script.

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
        Cenário convertido (dict Python aninhado).

    Raises
    ------
    ImportError
        Se `lupa` não estiver instalado.
    ValueError
        Se nenhuma fonte for fornecida ou o script não retornar tabela.
    """
    if caminho is None and lua is None:
        raise ValueError("forneça 'caminho' (arquivo .lua) ou 'lua' (código inline)")
    runtime = _runtime_lua()
    codigo = Path(caminho).read_text(encoding="utf-8") if caminho is not None else lua
    tabela = runtime.execute(codigo)
    if tabela is None:
        raise ValueError("o script Lua não retornou uma tabela de cenário")
    return tabela_para_dict(tabela)


def constroi_geometria(dados: Dict[str, Any]) -> GeometriaEstrutura:
    """Monta uma `GeometriaEstrutura` a partir do dict do cenário /
    Builds a `GeometriaEstrutura` from the scenario dict."""
    trechos = [
        TrechoExposicao(float(t["inicio_m"]), float(t["fim_m"]), float(t.get("exposicao", 1.0)))
        for t in dados.get("trechos", [])
    ]
    kwargs: Dict[str, Any] = {"comprimento_fibra_m": float(dados.get("comprimento_fibra_m", 100.0))}
    if trechos:
        kwargs["trechos"] = trechos
    profundidade = dados.get("profundidade_posicoes")
    if profundidade is not None:
        kwargs["profundidade_posicoes"] = np.asarray(profundidade, dtype=float)
    return GeometriaEstrutura(**kwargs)


def constroi_aquisicao(dados: Dict[str, Any]) -> ConfigAquisicaoMSE:
    """Monta uma `ConfigAquisicaoMSE` a partir do dict do cenário /
    Builds a `ConfigAquisicaoMSE` from the scenario dict."""
    campos = {}
    for nome in ("n_posicoes", "passo_espacial_m", "fs_dts_hz", "fs_dss_hz", "fs_das_hz", "duracao_s"):
        if nome in dados:
            campos[nome] = dados[nome]
    if "n_posicoes" in campos:
        campos["n_posicoes"] = int(campos["n_posicoes"])
    return ConfigAquisicaoMSE(**campos)


def aplica_cenario(gerador: GeradorAssinaturasMSE, cenario: Dict[str, Any]) -> Dict[str, Any]:
    """Aplica o dict de cenário ao gerador de assinaturas / Applies the scenario dict to the generator.

    Lê `cenario['gerador']['tipo']` (default 'cenario_fissura_multimodal') e
    repassa os demais campos como argumentos do método correspondente. O
    `material.coef_expansao_termica`, quando presente, alimenta as
    assinaturas de fissura (DSS).

    Parameters
    ----------
    gerador : GeradorAssinaturasMSE
        Gerador já construído (geometria + aquisição do cenário).
    cenario : dict
        Dict convertido do script Lua.

    Returns
    -------
    dict
        Dicionário canônico da assinatura gerada.
    """
    material = cenario.get("material") or {}
    gerador_cfg = dict(cenario.get("gerador") or {})
    tipo = gerador_cfg.pop("tipo", "cenario_fissura_multimodal")
    if "coef_expansao_termica" in material and "coef_expansao_termica" not in gerador_cfg \
            and tipo in ("fissura_dss", "cenario_fissura_multimodal"):
        gerador_cfg["coef_expansao_termica"] = float(material["coef_expansao_termica"])
    metodos = {
        "difusao_termica_parede": gerador.difusao_termica_parede,
        "ponte_termica_fissura": gerador.ponte_termica_fissura,
        "fissura_dss": gerador.fissura_dss,
        "recalque_diferencial": gerador.recalque_diferencial,
        "emissao_acustica_fissura": gerador.emissao_acustica_fissura,
        "vibracao_modal": gerador.vibracao_modal,
        "ruido_ambiental": gerador.ruido_ambiental,
        "cenario_fissura_multimodal": gerador.cenario_fissura_multimodal,
    }
    if tipo not in metodos:
        raise ValueError(f"tipo de cenário desconhecido: {tipo!r}; opções: {sorted(metodos)}")
    return metodos[tipo](**gerador_cfg)
