"""
Alakoro FiberSense — Estruturas de Dados do Módulo MSE
MSE Module Data Structures

Geometria da estrutura monitorada, configuração de aquisição DFOS
e tipos de assinatura (sinais) do domínio de Monitoramento da Saúde
Estrutural (MSE) de edifícios antigos via fibra óptica distribuída (DFOS).

Monitored-structure geometry, DFOS acquisition setup and signature types
for Structural Health Monitoring (SHM) of heritage buildings via
distributed fiber optic sensing.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

import numpy as np


class TipoAssinaturaMSE(Enum):
    """Tipos de assinatura MSE / MSE signature types (código, português, inglês)."""

    DIFUSAO_TERMICA_PAREDE = ("difusao_termica_parede", "Difusão Térmica em Parede", "Wall Thermal Diffusion")
    PONTE_TERMICA_FISSURA = ("ponte_termica_fissura", "Ponte Térmica em Fissura", "Crack Thermal Bridge")
    FISSURA_DSS = ("fissura_dss", "Abertura de Fissura (DSS)", "Crack Opening (DSS)")
    RECALQUE_DIFERENCIAL = ("recalque_diferencial", "Recalque Diferencial", "Differential Settlement")
    EMISSAO_ACUSTICA_FISSURA = ("emissao_acustica_fissura", "Emissão Acústica de Fissura", "Crack Acoustic Emission")
    VIBRACAO_MODAL = ("vibracao_modal", "Vibração Modal", "Modal Vibration")
    CENARIO_FISSURA_MULTIMODAL = (
        "cenario_fissura_multimodal",
        "Cenário Fissura Multimodal",
        "Multimodal Crack Scenario",
    )
    RUIDO_AMBIENTAL = ("ruido_ambiental", "Ruído Ambiental", "Ambient Noise")

    def __init__(self, code: str, pt: str, en: str):
        self.code = code
        self.pt = pt
        self.en = en


@dataclass
class TrechoExposicao:
    """Trecho do percurso da fibra com exposição solar característica /
    Fiber stretch with characteristic sun exposure.

    Parameters
    ----------
    inicio_m, fim_m : float
        Limites do trecho ao longo do percurso da fibra (m).
    exposicao : float
        Fator de exposição solar entre 0.0 (sombra/permanente) e 1.0 (sol pleno).
        Ex.: fachada sul ≈ 1.0, fachada norte ≈ 0.3–0.5, interior ≈ 0.1.
    """

    inicio_m: float
    fim_m: float
    exposicao: float = 1.0


@dataclass
class GeometriaEstrutura:
    """Geometria da estrutura monitorada / Monitored structure geometry.

    Parameters
    ----------
    comprimento_fibra_m : float
        Comprimento total da fibra instalada ao longo da estrutura (m).
    trechos : list[TrechoExposicao]
        Trechos do percurso com exposição solar distinta (fachadas, zonas
        internas). Posições fora de qualquer trecho recebem fator 0 (sombra).
    profundidade_posicoes : np.ndarray, opcional
        Profundidade de instalação da fibra em cada posição (m), medida a
        partir da superfície da parede. Alimenta a solução analítica de
        difusão térmica 1D: A(x) = A₀·e^(−x/δ), Δt(x) = x/(δ·ω).
    """

    comprimento_fibra_m: float = 100.0
    trechos: List[TrechoExposicao] = field(default_factory=lambda: [TrechoExposicao(0.0, 100.0, 1.0)])
    profundidade_posicoes: Optional[np.ndarray] = None

    def eixo_posicoes(self, n_posicoes: int) -> np.ndarray:
        """Retorna o eixo espacial uniforme (m) / Returns the uniform spatial axis (m)."""
        return np.linspace(0.0, self.comprimento_fibra_m, int(n_posicoes))

    def fator_exposicao(self, posicoes: np.ndarray) -> np.ndarray:
        """Fator de exposição solar por posição (0 = sombra) / Sun-exposure factor per position."""
        fator = np.zeros_like(posicoes, dtype=float)
        for trecho in self.trechos:
            mascara = (posicoes >= trecho.inicio_m) & (posicoes <= trecho.fim_m)
            fator[mascara] = float(np.clip(trecho.exposicao, 0.0, 1.0))
        return fator

    def profundidades(self, posicoes: np.ndarray) -> np.ndarray:
        """Profundidade por posição, interpolada se necessário / Depth per position, interpolated if needed."""
        if self.profundidade_posicoes is None:
            return np.zeros_like(posicoes, dtype=float)
        prof = np.asarray(self.profundidade_posicoes, dtype=float)
        if prof.shape[0] == posicoes.shape[0]:
            return prof
        eixo = np.linspace(0.0, self.comprimento_fibra_m, prof.shape[0])
        return np.interp(posicoes, eixo, prof)


@dataclass
class ConfigAquisicaoMSE:
    """Configuração de aquisição DFOS para MSE / DFOS acquisition setup for SHM.

    Parameters
    ----------
    n_posicoes : int
        Número de posições (canais) espaciais ao longo da fibra.
    passo_espacial_m : float
        Espaçamento nominal entre posições (m), usado na conversão do
        comprimento de gauge para amostras.
    fs_dts_hz, fs_dss_hz : float
        Taxas de amostragem temporais de DTS (temperatura) e DSS (deformação
        Brillouin) em Hz. Default: 1/60 Hz (1 traço/minuto).
    fs_das_hz : float
        Taxa de amostragem do DAS (acústico) em Hz. Default: 1000 Hz.
    duracao_s : float
        Duração total da campanha de monitoramento (s). Default: 86400 s (1 dia).
    """

    n_posicoes: int = 500
    passo_espacial_m: float = 0.25
    fs_dts_hz: float = 1.0 / 60.0
    fs_dss_hz: float = 1.0 / 60.0
    fs_das_hz: float = 1000.0
    duracao_s: float = 86400.0

    @property
    def n_amostras_dts(self) -> int:
        """Número de amostras temporais DTS / Number of DTS time samples."""
        return max(1, int(round(self.duracao_s * self.fs_dts_hz)))

    @property
    def n_amostras_dss(self) -> int:
        """Número de amostras temporais DSS / Number of DSS time samples."""
        return max(1, int(round(self.duracao_s * self.fs_dss_hz)))
