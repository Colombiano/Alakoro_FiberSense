"""
Alakoro FiberSense — Motor de Inferência MSE
MSE Inference Engine

Regras determinísticas sobre os arrays DTS/DSS/DAS que emitem eventos
semânticos da ontologia (alakoro.ontology.events):

- DSS: pico de deformação por proeminência sobre baseline robusto (MAD)
  em posição fixa -> PropagacaoFissuraEvento;
- DAS: envoltória de Hilbert + STA/LTA na banda 50–500 Hz ->
  EventoAcusticoFissura (maior confiança com degrau residual);
- DTS: mediana temporal + mediana móvel espacial -> offset local
  persistente -> AnomaliaTermicaEvento;
- Correção térmica do DSS pela cross-sensibilidade Brillouin
  (≈ 20 µε/°C) usando o DTS como referência.

Deterministic rules over DTS/DSS/DAS arrays that emit semantic ontology
events: DSS strain-peak prominence, DAS Hilbert envelope + STA/LTA,
DTS persistent local offset, and Brillouin thermal cross-sensitivity
correction of DSS using DTS as reference.
"""

from typing import List, Optional, Tuple

import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import hilbert

from ..ontology.events import (
    AnomaliaTermicaEvento,
    Event,
    EventoAcusticoFissura,
    PropagacaoFissuraEvento,
)
from .signatures import funcao_nucleo_mse
from .structures import ConfigAquisicaoMSE, GeometriaEstrutura


class MotorInferenciaMSE:
    """Motor de inferência determinística para MSE / Deterministic SHM inference engine.

    Parameters
    ----------
    geometria : GeometriaEstrutura, opcional
        Geometria usada para converter índices de posição em metros.
    acq : ConfigAquisicaoMSE, opcional
        Configuração de aquisição (taxa DAS, passo espacial).
    passo_espacial_m : float, opcional
        Passo espacial (m) usado quando não há geometria.

    Notes
    -----
    Quando `dts` e `dss` são fornecidos juntos a `inferir`, o DSS é
    primeiramente corrigido pela cross-sensibilidade térmica Brillouin
    (regra `corrige_temperatura_dss`), pois o strain aparente de 20 µε/°C
    mascararia a proeminência da fissura.
    """

    LIMIAR_EXCESSO_PICO_UE: float = 100.0
    LIMIAR_OFFSET_TERMICO_K: float = 1.5
    FATOR_MAD: float = 8.0
    JANELA_STA_S: float = 0.2
    JANELA_LTA_S: float = 5.0
    LIMIAR_STA_LTA: float = 3.0
    LIMIAR_DEGRAU_UE: float = 20.0
    FAIXA_DAS_HZ: Tuple[float, float] = (50.0, 500.0)

    def __init__(self, geometria: Optional[GeometriaEstrutura] = None,
                 acq: Optional[ConfigAquisicaoMSE] = None,
                 passo_espacial_m: Optional[float] = None):
        self.geometria = geometria
        self.acq = acq
        if passo_espacial_m is None and acq is not None:
            passo_espacial_m = acq.passo_espacial_m
        self.passo_espacial_m = float(passo_espacial_m or 0.25)

    # ─────────────────────────────────────────────────────────
    # API PRINCIPAL / MAIN API
    # ─────────────────────────────────────────────────────────

    def inferir(self, dts: Optional[np.ndarray] = None, dss: Optional[np.ndarray] = None,
                das: Optional[np.ndarray] = None, fs_das_hz: Optional[float] = None) -> List[Event]:
        """Executa as regras de inferência sobre as modalidades disponíveis /
        Runs the inference rules over the available modalities.

        Parameters
        ----------
        dts : np.ndarray, opcional
            Campo DTS (n_t, n_z) em °C.
        dss : np.ndarray, opcional
            Campo DSS (n_t, n_z) em µε.
        das : np.ndarray, opcional
            Campo DAS (n_t, n_z) em µε.
        fs_das_hz : float, opcional
            Taxa de amostragem do DAS (Hz). Default: da configuração ou 1000 Hz.

        Returns
        -------
        list[Event]
            Instâncias das classes de evento da ontologia, com posições em
            metros quando a geometria (ou o passo espacial) é conhecida.
        """
        eventos: List[Event] = []
        if dss is not None:
            if dts is not None:
                dss, _ = self.corrige_temperatura_dss(dss, dts)
            eventos.extend(self._detectar_fissura_dss(np.asarray(dss, dtype=float)))
        if das is not None:
            fs = float(fs_das_hz or (self.acq.fs_das_hz if self.acq is not None else 1000.0))
            eventos.extend(self._detectar_emissao_acustica(np.asarray(das, dtype=float), fs))
        if dts is not None:
            eventos.extend(self._detectar_anomalia_termica(np.asarray(dts, dtype=float)))
        return eventos

    def corrige_temperatura_dss(self, dss: np.ndarray, dts: np.ndarray,
                                coef: float = 20e-6) -> Tuple[np.ndarray, float]:
        """Remove o strain aparente térmico do DSS (cross-sensibilidade Brillouin) /
        Removes apparent thermal strain from DSS (Brillouin cross-sensitivity).

        Subtrai `coef · ΔT` (em µε) de todo o traço, usando o DTS como
        referência de temperatura: ΔT(t, z) = dts(t, z) − mediana_z(dts).
        Assume-se que o DTS cubra ciclos térmicos completos (ou que já
        esteja referenciado à linha de base), de modo que a mediana
        temporal aproxime a temperatura de referência por posição.

        Parameters
        ----------
        dss : np.ndarray
            Campo DSS (n_t_dss, n_z) em µε.
        dts : np.ndarray
            Campo DTS (n_t_dts, n_z) em °C. Se n_t_dts ≠ n_t_dss, cada
            posição é interpolada linearmente para o eixo temporal do DSS.
        coef : float
            Equivalência térmica do Brillouin (strain/°C). Default: 20e-6.

        Returns
        -------
        dss_corrigido : np.ndarray
            Campo DSS corrigido (n_t_dss, n_z) em µε.
        residual_ue : float
            Residual estimado (MAD global do corrigido, em µε) — típico de
            2–20 µε com correção por fibra solta bem comportada.
        """
        dss = np.asarray(dss, dtype=float)
        dts = np.asarray(dts, dtype=float)
        if dts.shape[0] != dss.shape[0]:
            eixo_dts = np.linspace(0.0, 1.0, dts.shape[0])
            eixo_dss = np.linspace(0.0, 1.0, dss.shape[0])
            dts_interp = np.empty_like(dss)
            for j in range(dts.shape[1]):
                dts_interp[:, j] = np.interp(eixo_dss, eixo_dts, dts[:, j])
            dts = dts_interp
        delta_t = dts - np.median(dts, axis=0, keepdims=True)
        corrigido = dss - coef * delta_t * 1e6
        residual = float(1.4826 * np.median(np.abs(corrigido - np.median(corrigido))))
        return corrigido, residual

    # ─────────────────────────────────────────────────────────
    # REGRAS POR MODALIDADE / PER-MODALITY RULES
    # ─────────────────────────────────────────────────────────

    def _detectar_fissura_dss(self, dss: np.ndarray) -> List[PropagacaoFissuraEvento]:
        """Pico de deformação por proeminência espacial sobre baseline robusto /
        Strain peak by spatial prominence over a robust baseline.

        A proeminência de cada posição é medida contra a mediana espacial
        da energia residual (|dss − mediana temporal|), o que torna a regra
        imune a componentes térmicas uniformes ao longo da fibra.
        """
        n_t, n_z = dss.shape
        residuo = dss - np.median(dss, axis=0, keepdims=True)
        energia = np.max(np.abs(residuo), axis=0)
        fundo = float(np.median(energia))
        escala = float(1.4826 * np.median(np.abs(energia - fundo)))
        limiar = max(self.LIMIAR_EXCESSO_PICO_UE, self.FATOR_MAD * escala)
        posicoes = self._posicoes(n_z)
        eventos = []
        for grupo in self._grupos_contiguos(np.where(energia - fundo > limiar)[0]):
            i_pk = grupo[int(np.argmax(energia[grupo]))]
            excesso = float(energia[i_pk] - fundo)
            eventos.append(PropagacaoFissuraEvento(
                posicao_fissura_m=float(posicoes[i_pk]),
                abertura_ue=float(np.max(residuo[:, i_pk])),
                confidence=float(min(0.99, 0.5 + excesso / (2.0 * limiar))),
                severity="High" if excesso > 2.0 * limiar else "Medium",
            ))
        return eventos

    def _detectar_emissao_acustica(self, das: np.ndarray, fs_hz: float) -> List[EventoAcusticoFissura]:
        """Bursts impulsivos na banda 50–500 Hz via envoltória + STA/LTA /
        Impulsive bursts in the 50–500 Hz band via envelope + STA/LTA.

        A confiança é reforçada quando há degrau residual permanente na
        posição do evento (abertura quase-estática acumulada da fissura).
        """
        envelope = np.abs(hilbert(das, axis=0))
        energia_t = np.mean(envelope, axis=1)
        n_sta = max(2, int(round(self.JANELA_STA_S * fs_hz)))
        n_lta = max(n_sta + 1, int(round(self.JANELA_LTA_S * fs_hz)))
        razao = self._sta_lta(energia_t, n_sta, n_lta)
        disparos = self._grupos_contiguos(np.where(razao > self.LIMIAR_STA_LTA)[0])
        posicoes = self._posicoes(das.shape[1])
        n_antes = max(2, das.shape[0] // 10)
        dur_total_s = das.shape[0] / fs_hz
        taxa_h = len(disparos) * 3600.0 / max(dur_total_s, 1e-9)
        eventos = []
        for disparo in disparos:
            i_trig = disparo[int(np.argmax(razao[disparo]))]
            i_ini = max(0, i_trig - n_sta)
            i_fim = min(das.shape[0], i_trig + max(n_sta, int(0.5 * fs_hz)))
            z_janela = np.mean(envelope[i_ini:i_fim, :], axis=0)
            i_z = int(np.argmax(z_janela))
            degrau = float(np.mean(das[-n_antes:, i_z]) - np.mean(das[:n_antes, i_z]))
            energia = float(np.sum(das[i_ini:i_fim, i_z] ** 2))
            confianca = 0.6 + min(0.14, float(razao[i_trig]) * 0.01)
            tem_degrau = degrau > self.LIMIAR_DEGRAU_UE
            if tem_degrau:
                confianca += 0.25
            eventos.append(EventoAcusticoFissura(
                posicao_m=float(posicoes[i_z]),
                energia=energia,
                taxa_eventos_h=float(taxa_h),
                confidence=float(min(0.99, confianca)),
                severity="High" if tem_degrau else "Medium",
            ))
        return eventos

    def _detectar_anomalia_termica(self, dts: np.ndarray) -> List[AnomaliaTermicaEvento]:
        """Offset local persistente no DTS / Persistent local offset in DTS.

        Mediana temporal por posição (persistência) comparada a uma mediana
        móvel espacial (referência da parede): |offset| > 1.5 K indica ponte
        térmica (fissura aberta, infiltração).
        """
        n_t, n_z = dts.shape
        mediana_t = np.median(dts, axis=0)
        janela = 21 if n_z >= 21 else (n_z if n_z % 2 == 1 else n_z - 1)
        suave = mediana_t if janela < 3 else median_filter(mediana_t, size=janela, mode="nearest")
        offset = mediana_t - suave
        posicoes = self._posicoes(n_z)
        eventos = []
        for grupo in self._grupos_contiguos(np.where(np.abs(offset) > self.LIMIAR_OFFSET_TERMICO_K)[0]):
            i_pk = grupo[int(np.argmax(np.abs(offset[grupo])))]
            eventos.append(AnomaliaTermicaEvento(
                posicao_m=float(posicoes[i_pk]),
                offset_k=float(offset[i_pk]),
                confidence=float(min(0.99, abs(offset[i_pk]) / (2.0 * self.LIMIAR_OFFSET_TERMICO_K))),
                severity="Medium",
            ))
        return eventos

    # ─────────────────────────────────────────────────────────
    # UTILITÁRIOS / UTILITIES
    # ─────────────────────────────────────────────────────────

    def _posicoes(self, n_z: int) -> np.ndarray:
        """Eixo espacial em metros para n_z canais / Spatial axis in meters for n_z channels."""
        if self.geometria is not None:
            return self.geometria.eixo_posicoes(n_z)
        return np.arange(n_z, dtype=float) * self.passo_espacial_m

    def _sta_lta(self, traco: np.ndarray, n_sta: int, n_lta: int) -> np.ndarray:
        """Razão STA/LTA (1D) com fallback NumPy / STA/LTA ratio (1D) with NumPy fallback.

        Usa `alakoro_core.mse_sta_lta` quando disponível; caso contrário,
        versão vetorizada pura em NumPy (janelas STA e LTA com mesma origem).
        """
        fn = funcao_nucleo_mse("mse_sta_lta")
        if fn is not None:
            try:
                return np.asarray(fn(traco.tolist(), n_sta, n_lta), dtype=float)
            except (TypeError, ValueError):
                pass  # fallback NumPy
        n = traco.shape[0]
        acumulado = np.concatenate(([0.0], np.cumsum(traco)))
        sta = (acumulado[n_sta:] - acumulado[:n + 1 - n_sta]) / n_sta
        lta = (acumulado[n_lta:] - acumulado[:n + 1 - n_lta]) / n_lta
        razao = np.zeros(n)
        fim = n - n_lta + 1
        razao[n_sta:n_sta + fim] = sta[:fim] / np.maximum(lta[:fim], 1e-12)
        return razao

    @staticmethod
    def _grupos_contiguos(indices: np.ndarray) -> List[np.ndarray]:
        """Agrupa índices com diferença unitária / Groups indices with unit spacing."""
        if indices.size == 0:
            return []
        cortes = np.where(np.diff(indices) > 1)[0] + 1
        return [grupo for grupo in np.split(indices, cortes) if grupo.size > 0]
