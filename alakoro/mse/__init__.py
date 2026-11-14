"""
Módulo de Monitoramento da Saúde Estrutural (MSE)
Structural Health Monitoring Module

Fibra óptica distribuída (DFOS: DTS/DSS/DAS) aplicada ao monitoramento
da saúde estrutural de edifícios antigos: igrejas históricas, ruínas
coloniais e outros patrimônios de alvenaria.

Distributed fiber optic sensing (DFOS: DTS/DSS/DAS) applied to structural
health monitoring of heritage buildings: historic churches, colonial
ruins and other masonry heritage.

Autor/Author: Luiz Paulo Colombiano
Licença/License: MIT
"""

from .structures import (
    ConfigAquisicaoMSE,
    GeometriaEstrutura,
    TipoAssinaturaMSE,
    TrechoExposicao,
)
from .signatures import (
    GeradorAssinaturasMSE,
    NUCLEO_CPP_ATIVO,
    amplitude_analitica_k,
    defasagem_s,
    delta_penetracao_m,
)
from .inference import MotorInferenciaMSE
from .cenarios import (
    aplica_cenario,
    carrega_cenario_lua,
    constroi_aquisicao,
    constroi_geometria,
    tabela_para_dict,
)


def __getattr__(name: str):
    """Import lazy do visualizador Qt (não importa PySide6 no `import alakoro.mse`) /
    Lazy import of the Qt viewer (does not import PySide6 on `import alakoro.mse`)."""
    if name == "JanelaVisualizacaoMSE":
        from .viewer import JanelaVisualizacaoMSE

        return JanelaVisualizacaoMSE
    raise AttributeError(f"módulo {__name__!r} não tem atributo {name!r}")


__all__ = [
    "GeradorAssinaturasMSE",
    "ConfigAquisicaoMSE",
    "GeometriaEstrutura",
    "TipoAssinaturaMSE",
    "MotorInferenciaMSE",
    "TrechoExposicao",
    "JanelaVisualizacaoMSE",
    "NUCLEO_CPP_ATIVO",
    "carrega_cenario_lua",
    "aplica_cenario",
    "tabela_para_dict",
    "constroi_geometria",
    "constroi_aquisicao",
    "delta_penetracao_m",
    "amplitude_analitica_k",
    "defasagem_s",
]
