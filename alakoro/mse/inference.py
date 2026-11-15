"""
Alakoro FiberSense — Motor de Inferência MSE
MSE Inference Engine

Regras determinísticas sobre os arrays DTS/DSS/DAS que emitem eventos
semânticos da ontologia (alakoro.ontology.events):

- DSS: pico de deformação por proeminência sobre baseline robusto (MAD)
  em posição fixa -> PropagacaoFissuraEvento (com taxa de creep);
- DSS: gradiente espacial sustentado da taxa temporal de deformação
  (polyfit robusto sobre série median-filtrada) -> RecalqueEvento;
- DSS + DTS: correlação do residual na fissura com ΔT (inclinação na
  faixa do CTE da alvenaria, 2–12 µε/K) -> AberturaFissuraTermicaEvento;
- DAS: envoltória de Hilbert + STA/LTA na banda 50–500 Hz ->
  EventoAcusticoFissura (maior confiança com degrau residual);
- DAS: deriva da frequência fundamental (Welch no primeiro vs último
  terço da série) -> DanoModalEvento;
- DTS: mediana temporal + mediana móvel espacial -> offset local
  persistente -> AnomaliaTermicaEvento;
- Correção térmica do DSS pela cross-sensibilidade Brillouin
  (≈ 20 µε/°C) usando o DTS como referência.

Passo final de fusão multimodal: eventos de classes distintas e de
modalidades de sensor distintas convergindo para a mesma posição
(raio RAIO_FUSAO_M) recebem o mesmo `correlation_id` e elevam a
confiança do evento de fissura — corroboração por mecanismos físicos
independentes (abertura em strain DSS + emissão acústica mecânica DAS
+ ponte térmica DTS) reduz falsos positivos de qualquer regra isolada.

Robustez NaN/Inf (espírito do achado CL-01 da auditoria legada):
arrays são validados em 2D (ValueError claro), valores Inf são
convertidos para NaN na entrada de `inferir`, e todas as regras usam
estatísticas nan-safe (np.nanmedian/np.nanmax/np.nanmean). Canais
totalmente NaN são ignorados silenciosamente (sem crash e sem evento
fantasma); eventos das demais posições permanecem intactos.

Deterministic rules over DTS/DSS/DAS arrays that emit semantic ontology
events: DSS strain-peak prominence with creep rate, DSS sustained
settlement-gradient rates, DSS thermal crack-opening correlation,
DAS Hilbert envelope + STA/LTA, DAS modal-frequency drift (modal
damage), DTS persistent local offset, Brillouin thermal correction,
and a final multimodal fusion pass that shares `correlation_id` among
cross-modality events converging at the same position.
"""

import uuid
import warnings
from contextlib import contextmanager
from typing import List, Optional, Tuple

import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import hilbert, welch

_SEGUNDOS_POR_DIA: float = 86400.0


@contextmanager
def _sem_avisos_nan():
    """Suprime RuntimeWarnings de agregações nan-safe (fatias all-NaN) /
    Suppresses RuntimeWarnings from nan-safe aggregations (all-NaN slices).

    Canais totalmente inválidos são cenário de uso legítimo (CL-01): as
    regras os ignoram silenciosamente em vez de inundar o usuário com
    avisos de bibliotecas NumPy/SciPy.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        yield

from ..ontology.events import (
    AberturaFissuraTermicaEvento,
    AnomaliaTermicaEvento,
    DanoModalEvento,
    Event,
    EventoAcusticoFissura,
    PropagacaoFissuraEvento,
    RecalqueEvento,
)
from .signatures import OMEGA_DIURNO_RAD_S, RAZAO_OMEGA_ANUAL, funcao_nucleo_mse
from .structures import ConfigAquisicaoMSE, GeometriaEstrutura


class MotorInferenciaMSE:
    """Motor de inferência determinística para MSE / Deterministic SHM inference engine.

    Parameters
    ----------
    geometria : GeometriaEstrutura, opcional
        Geometria usada para converter índices de posição em metros.
    acq : ConfigAquisicaoMSE, opcional
        Configuração de aquisição (taxas, passo espacial).
    passo_espacial_m : float, opcional
        Passo espacial (m) usado quando não há geometria.

    Notes
    -----
    Quando `dts` e `dss` são fornecidos juntos a `inferir`, o DSS é
    primeiramente corrigido pela cross-sensibilidade térmica Brillouin
    (regra `corrige_temperatura_dss`), pois o strain aparente de 20 µε/°C
    mascararia a proeminência da fissura. A regressão térmica da abertura
    usa o residual *após* a correção: a inclinação remanescente na faixa
    do CTE (2–12 µε/K) isola a abertura real da fissura do strain
    aparente do cabo.

    A fusão multimodal final (`_fundir_multimodal`) eleva a confiança de
    eventos de fissura corroborados por modalidades independentes: o
    mesmo mecanismo físico (fissura ativa) deixa assinaturas coerentes no
    strain (DSS), na acústica (DAS) e na temperatura (DTS); a convergência
    espacial dentro de RAIO_FUSAO_M é evidência independente e por isso
    eleva `confidence` para ≥ 0.9, `severity` para "High" e compartilha
    um `correlation_id` entre os eventos do grupo.
    """

    LIMIAR_EXCESSO_PICO_UE: float = 100.0
    LIMIAR_OFFSET_TERMICO_K: float = 1.5
    FATOR_MAD: float = 8.0
    JANELA_STA_S: float = 0.2
    JANELA_LTA_S: float = 5.0
    LIMIAR_STA_LTA: float = 3.0
    LIMIAR_DEGRAU_UE: float = 20.0
    FAIXA_DAS_HZ: Tuple[float, float] = (50.0, 500.0)
    # Recalque diferencial: gradiente sustentado de taxa (µε/dia)
    LIMIAR_RECALQUE_UE_DIA: float = 2.0
    FATOR_MAD_REC: float = 3.0
    # Abertura térmica de fissura: inclinação na faixa do CTE da alvenaria
    # (1 µε/K de piso: ponte térmica local amplifica o swing do DTS e dilui
    # a inclinação; a discriminação vem da correlação + ordem de grandeza)
    CORRELACAO_TERMICA_MIN: float = 0.6
    CTE_MIN_UE_K: float = 1.0
    CTE_MAX_UE_K: float = 12.0
    # Dano modal: deriva da frequência fundamental (torres de alvenaria)
    FAIXA_MODAL_HZ: Tuple[float, float] = (0.5, 10.0)
    LIMIAR_DESVIO_MODAL_PCT: float = 1.0
    JANELA_WELCH_MODAL_S: float = 60.0
    # Fusão multimodal por corroboração espacial
    RAIO_FUSAO_M: float = 2.0

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
                das: Optional[np.ndarray] = None, fs_das_hz: Optional[float] = None,
                fs_dss_hz: Optional[float] = None) -> List[Event]:
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
        fs_dss_hz : float, opcional
            Taxa de amostragem do DSS (Hz) para a conversão das taxas de
            deformação em µε/dia. Default: da configuração ou 1/60 Hz.

        Returns
        -------
        list[Event]
            Instâncias das classes de evento da ontologia, com posições em
            metros quando a geometria (ou o passo espacial) é conhecida.
            Eventos corroborados por modalidades distintas na mesma posição
            compartilham `correlation_id` e têm confiança elevada.

        Notes
        -----
        Arrays devem ser 2D (n_t, n_z); caso contrário levanta ValueError.
        Valores Inf são convertidos para NaN e tratados como dados
        ausentes: canais totalmente inválidos são ignorados silenciosamente.
        """
        eventos: List[Event] = []
        if dss is not None:
            dss = self._sanitizar("dss", dss)
            dss_bruto = dss  # antes da correção térmica: usado na regressão de abertura
            fs_dss = float(fs_dss_hz or (self.acq.fs_dss_hz if self.acq is not None else 1.0 / 60.0))
            dts_dss: Optional[np.ndarray] = None
            if dts is not None:
                dss, _ = self.corrige_temperatura_dss(dss, dts)
                dts_dss = self._interpolar_para_eixo(self._sanitizar("dts", dts), dss.shape[0])
            eventos.extend(self._detectar_fissura_dss(dss, fs_dss, dts=dts_dss, dss_bruto=dss_bruto))
            eventos.extend(self._detectar_recalque(dss, fs_dss))
        if das is not None:
            das = self._sanitizar("das", das)
            fs = float(fs_das_hz or (self.acq.fs_das_hz if self.acq is not None else 1000.0))
            eventos.extend(self._detectar_emissao_acustica(das, fs))
            eventos.extend(self._detectar_dano_modal(das, fs))
        if dts is not None:
            dts = self._sanitizar("dts", dts)
            eventos.extend(self._detectar_anomalia_termica(dts))
        self._fundir_multimodal(eventos)
        return eventos

    def corrige_temperatura_dss(self, dss: np.ndarray, dts: np.ndarray,
                                coef: float = 20e-6) -> Tuple[np.ndarray, float]:
        """Remove o strain aparente térmico do DSS (cross-sensibilidade Brillouin) /
        Removes apparent thermal strain from DSS (Brillouin cross-sensitivity).

        Subtrai `coef · ΔT` (em µε) de todo o traço, usando o DTS como
        referência de temperatura: ΔT(t, z) = dts(t, z) − nanmediana_z(dts).
        Assume-se que o DTS cubra ciclos térmicos completos (ou que já
        esteja referenciado à linha de base), de modo que a mediana
        temporal aproxime a temperatura de referência por posição.

        Tolerante a NaN: posições com dados ausentes propagam NaN apenas
        localmente; o residual (MAD global) usa estatísticas nan-safe.
        """
        dss = np.asarray(dss, dtype=float)
        dts = np.asarray(dts, dtype=float)
        if dss.ndim != 2 or dts.ndim != 2:
            raise ValueError("dss e dts devem ser 2D (n_t, n_z)")
        if dts.shape[0] != dss.shape[0]:
            dts = self._interpolar_para_eixo(dts, dss.shape[0])
        with _sem_avisos_nan():
            delta_t = dts - np.nanmedian(dts, axis=0, keepdims=True)
            corrigido = dss - coef * delta_t * 1e6
            residual = float(1.4826 * np.nanmedian(np.abs(corrigido - np.nanmedian(corrigido))))
        return corrigido, residual

    # ─────────────────────────────────────────────────────────
    # REGRAS POR MODALIDADE / PER-MODALITY RULES
    # ─────────────────────────────────────────────────────────

    def _detectar_fissura_dss(self, dss: np.ndarray, fs_dss_hz: float,
                              dts: Optional[np.ndarray] = None,
                              dss_bruto: Optional[np.ndarray] = None) -> List[Event]:
        """Pico de deformação por proeminência espacial sobre baseline robusto /
        Strain peak by spatial prominence over a robust baseline.

        A proeminência de cada posição é medida contra a mediana espacial
        da energia residual (|dss − mediana temporal|), o que torna a regra
        imune a componentes térmicas uniformes ao longo da fibra. Em cada
        pico: (i) estima a taxa de creep (ajuste linear com o harmônico
        diário em conjunto, `_taxa_coluna_ue_dia`, µε/dia) para o
        `PropagacaoFissuraEvento`; (ii) se `dts` foi fornecido, regressão
        do residual vs ΔT local — correlação > 0.6 e inclinação no CTE da
        alvenaria (2–12 µε/K) caracterizam abertura térmica da fissura
        (`AberturaFissuraTermicaEvento`).

        A regressão térmica roda sobre o residual *espacialmente
        diferencial* do DSS bruto (mediana espacial por instante removida):
        o strain aparente do cabo é uniforme ao longo da fibra e se anula
        na diferenciação, restando apenas a abertura real da fissura —
        robusto mesmo quando o coeficiente de correção Brillouin é
        impreciso (é exatamente o papel da fibra de referência folgada).
        """
        n_t, n_z = dss.shape
        with _sem_avisos_nan():
            residuo = dss - np.nanmedian(dss, axis=0, keepdims=True)
            # Duas morfologias de fissura: (i) dinâmica — energia do residual
            # temporal (creep, abertura térmica, episódios); (ii) estática —
            # proeminência espacial do nível DC (degrau permanente de abertura,
            # a assinatura clássica de fissura em Brillouin). A máscara pega o
            # máximo das duas, para não perder degraus sem dinâmica temporal.
            energia_temporal = np.nanmax(np.abs(residuo), axis=0)
            nivel_dc = np.nanmedian(dss, axis=0)
            nivel_dc = nivel_dc - np.nanmedian(nivel_dc)
            energia = np.maximum(energia_temporal, np.abs(nivel_dc))
        fundo = float(np.nanmedian(energia))
        escala = float(1.4826 * np.nanmedian(np.abs(energia - fundo)))
        limiar = max(self.LIMIAR_EXCESSO_PICO_UE, self.FATOR_MAD * escala)
        posicoes = self._posicoes(n_z)
        base_termica = dss_bruto if dss_bruto is not None else dss
        with _sem_avisos_nan():
            residuo_espacial = base_termica - np.nanmedian(base_termica, axis=1, keepdims=True)
        eventos: List[Event] = []
        for grupo in self._grupos_contiguos(np.where(energia - fundo > limiar)[0]):
            i_pk = grupo[int(np.nanargmax(energia[grupo]))]
            excesso = float(energia[i_pk] - fundo)
            taxa = self._taxa_coluna_ue_dia(residuo[:, i_pk], fs_dss_hz)
            abertura = float(max(np.nanmax(np.abs(residuo[:, i_pk])), abs(float(nivel_dc[i_pk]))))
            eventos.append(PropagacaoFissuraEvento(
                posicao_fissura_m=float(posicoes[i_pk]),
                abertura_ue=abertura,
                taxa_ue_dia=taxa,
                confidence=float(min(0.99, 0.5 + excesso / (2.0 * limiar))),
                severity="High" if excesso > 2.0 * limiar else "Medium",
            ))
            if dts is not None:
                evento_termico = self._abertura_termica(residuo_espacial[:, i_pk], dts[:, i_pk],
                                                        float(posicoes[i_pk]))
                if evento_termico is not None:
                    eventos.append(evento_termico)
        return eventos

    def _detectar_recalque(self, dss: np.ndarray, fs_dss_hz: float) -> List[RecalqueEvento]:
        """Recalque diferencial: gradiente espacial sustentado da taxa de deformação /
        Differential settlement: sustained spatial gradient of strain rate.

        Para cada posição, a taxa temporal (µε/dia) é estimada por ajuste
        linear com o harmônico diário em conjunto (mediana temporal antes
        do ajuste, para robustez a impulsos). O padrão de recalque é um
        gradiente espacial sustentado — posições cuja taxa se afasta da
        mediana global por mais que max(2 µε/dia, 3·MAD) são sinalizadas.

        O MAD é computado sobre os desvios da mediana móvel espacial
        (janela ~n_z/5), não sobre as taxas brutas: um gradiente sustentado
        e suave — o próprio padrão físico de recalque — inflaria um MAD
        global e normalizaria a si mesmo; o MAD local só cresce com
        variações espaciais irregulares (ruído, episódios esparsos).
        """
        n_z = dss.shape[1]
        if n_z < 5:
            return []
        taxas = self._taxas_posicoes_ue_dia(dss, fs_dss_hz)
        validas = np.isfinite(taxas)
        if int(validas.sum()) < 5:
            return []
        with _sem_avisos_nan():
            mediana = float(np.nanmedian(taxas))
            # Eixo espacial completo (NaN interpolados) para a mediana móvel
            eixo = np.arange(n_z, dtype=float)
            preenchido = taxas.copy()
            preenchido[~validas] = np.interp(eixo[~validas], eixo[validas], taxas[validas])
            janela = max(5, ((n_z // 5) | 1))
            local = median_filter(preenchido, size=janela, mode="nearest")
            desvios = preenchido - local
            mad = float(1.4826 * np.nanmedian(np.abs(desvios - np.nanmedian(desvios))))
            # Suavização espacial leve das taxas antes do limiar: o gradiente
            # de recalque é uma região contínua; ruído de estimativa isolado
            # não deve fragmentar o padrão em eventos espúrios.
            suavizado = np.convolve(preenchido, np.ones(5) / 5.0, mode="same")
        limiar = max(self.LIMIAR_RECALQUE_UE_DIA, self.FATOR_MAD_REC * mad)
        with np.errstate(invalid="ignore"):
            excesso = np.where(validas, np.abs(suavizado - mediana), 0.0)
        posicoes = self._posicoes(n_z)
        eventos = []
        grupos = self._grupos_com_fenda(self._grupos_contiguos(np.where(excesso > limiar)[0]),
                                        fenda_max=3)
        for grupo in grupos:
            i_pk = grupo[int(np.argmax(excesso[grupo]))]
            eventos.append(RecalqueEvento(
                posicao_m=float(posicoes[i_pk]),
                taxa_ue_dia=float(suavizado[i_pk]),
                confidence=float(min(0.99, 0.5 + excesso[i_pk] / (2.0 * limiar))),
                severity="High" if excesso[i_pk] > 2.0 * limiar else "Medium",
            ))
        return eventos

    def _detectar_emissao_acustica(self, das: np.ndarray, fs_hz: float) -> List[EventoAcusticoFissura]:
        """Bursts impulsivos na banda 50–500 Hz via envoltória + STA/LTA /
        Impulsive bursts in the 50–500 Hz band via envelope + STA/LTA.

        A confiança é reforçada quando há degrau residual permanente na
        posição do evento (abertura quase-estática acumulada da fissura).
        Canais totalmente NaN são preenchidos com zero antes da envoltória
        de Hilbert para não contaminar a série espacialmente agregada.
        """
        n_t, n_z = das.shape
        colunas_nan = ~np.isfinite(das).any(axis=0)
        das_proc = das.copy()
        das_proc[:, colunas_nan] = 0.0
        envelope = np.abs(hilbert(das_proc, axis=0))
        with _sem_avisos_nan():
            energia_t = np.nanmean(envelope, axis=1)
        energia_t = np.nan_to_num(energia_t, nan=0.0)
        n_sta = max(2, int(round(self.JANELA_STA_S * fs_hz)))
        n_lta = max(n_sta + 1, int(round(self.JANELA_LTA_S * fs_hz)))
        razao = self._sta_lta(energia_t, n_sta, n_lta)
        disparos = self._grupos_contiguos(np.where(razao > self.LIMIAR_STA_LTA)[0])
        posicoes = self._posicoes(n_z)
        n_antes = max(2, n_t // 10)
        dur_total_s = n_t / fs_hz
        taxa_h = len(disparos) * 3600.0 / max(dur_total_s, 1e-9)
        eventos = []
        for disparo in disparos:
            i_trig = disparo[int(np.argmax(razao[disparo]))]
            i_ini = max(0, i_trig - n_sta)
            i_fim = min(n_t, i_trig + max(n_sta, int(0.5 * fs_hz)))
            with _sem_avisos_nan():
                z_janela = np.nanmean(envelope[i_ini:i_fim, :], axis=0)
            candidatos = np.where(~colunas_nan)[0]
            if candidatos.size == 0:
                continue
            i_z = int(candidatos[int(np.nanargmax(z_janela[candidatos]))])
            with _sem_avisos_nan():
                degrau = float(np.nanmean(das[-n_antes:, i_z]) - np.nanmean(das[:n_antes, i_z]))
            with np.errstate(invalid="ignore"):
                energia = float(np.nansum(das[i_ini:i_fim, i_z] ** 2))
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

    def _detectar_dano_modal(self, das: np.ndarray, fs_hz: float) -> List[DanoModalEvento]:
        """Dano modal: deriva da frequência fundamental da torre /
        Modal damage: drift of the tower fundamental frequency.

        Dano em torres de alvenaria reduz f1 em 0,5–3% e alarga o espectro
        (Hubbard 2021). Compara a PSD de Welch do primeiro terço da série
        espacialmente agregada com a do último terço; se o pico dominante
        na faixa FAIXA_MODAL_HZ migrar mais que LIMIAR_DESVIO_MODAL_PCT,
        emite `DanoModalEvento`. Requer duração ≥ 3× JANELA_WELCH_MODAL_S;
        séries curtas retornam [] (sem evento, sem erro).
        """
        n_t = das.shape[0]
        n_janela = int(round(self.JANELA_WELCH_MODAL_S * fs_hz))
        if n_janela < 16 or n_t < 3 * n_janela:
            return []
        serie = np.nanmean(das, axis=1)
        if not np.isfinite(serie).any():
            return []
        serie = np.nan_to_num(serie, nan=0.0)
        terço = n_t // 3
        f_inicial = self._pico_modal_welch(serie[:terço], fs_hz, n_janela)
        f_final = self._pico_modal_welch(serie[2 * terço:], fs_hz, n_janela)
        if f_inicial is None or f_final is None or f_inicial <= 0.0:
            return []
        variacao_pct = 100.0 * (f_final - f_inicial) / f_inicial
        if abs(variacao_pct) <= self.LIMIAR_DESVIO_MODAL_PCT:
            return []
        return [DanoModalEvento(
            frequencia_hz=float(f_final),
            variacao_relativa_pct=float(variacao_pct),
            confidence=float(min(0.99, 0.5 + abs(variacao_pct) / 5.0)),
            severity="High" if abs(variacao_pct) > 2.0 else "Medium",
        )]

    def _detectar_anomalia_termica(self, dts: np.ndarray) -> List[AnomaliaTermicaEvento]:
        """Offset local persistente no DTS / Persistent local offset in DTS.

        Mediana temporal por posição (persistência) comparada a uma mediana
        móvel espacial (referência da parede): |offset| > 1.5 K indica ponte
        térmica (fissura aberta, infiltração). Posições com NaN produzem
        offset NaN e são simplesmente não selecionadas.
        """
        n_t, n_z = dts.shape
        with _sem_avisos_nan():
            mediana_t = np.nanmedian(dts, axis=0)
        janela = 21 if n_z >= 21 else (n_z if n_z % 2 == 1 else n_z - 1)
        suave = mediana_t if janela < 3 else median_filter(mediana_t, size=janela, mode="nearest")
        with np.errstate(invalid="ignore"):
            offset = mediana_t - suave
        posicoes = self._posicoes(n_z)
        eventos = []
        for grupo in self._grupos_contiguos(np.where(np.abs(offset) > self.LIMIAR_OFFSET_TERMICO_K)[0]):
            i_pk = grupo[int(np.nanargmax(np.abs(offset[grupo])))]
            eventos.append(AnomaliaTermicaEvento(
                posicao_m=float(posicoes[i_pk]),
                offset_k=float(offset[i_pk]),
                confidence=float(min(0.99, abs(offset[i_pk]) / (2.0 * self.LIMIAR_OFFSET_TERMICO_K))),
                severity="Medium",
            ))
        return eventos

    # ─────────────────────────────────────────────────────────
    # FUSÃO MULTIMODAL / MULTIMODAL FUSION
    # ─────────────────────────────────────────────────────────

    def _fundir_multimodal(self, eventos: List[Event]) -> None:
        """Agrupa eventos por proximidade espacial e corrobora a fissura /
        Groups events by spatial proximity and corroborates the crack.

        Eventos de modalidades de sensor distintas (DTS/DSS/DAS) convergindo
        para a mesma posição (raio RAIO_FUSAO_M) são evidência física
        independente do mesmo mecanismo: o grupo recebe um `correlation_id`
        comum e a confiança dos eventos de fissura sobe para ≥ 0.9 com
        severidade "High". Executado in-place ao final de `inferir`.
        """
        posicionados = [(ev, pos) for ev in eventos
                        for pos in [self._posicao_evento(ev)] if pos is not None]
        n = len(posicionados)
        visitado = [False] * n
        for i in range(n):
            if visitado[i]:
                continue
            grupo = [i]
            visitado[i] = True
            for j in range(i + 1, n):
                if visitado[j]:
                    continue
                if any(abs(posicionados[j][1] - posicionados[k][1]) <= self.RAIO_FUSAO_M
                       for k in grupo):
                    grupo.append(j)
                    visitado[j] = True
            membros = [posicionados[k][0] for k in grupo]
            modalidades = {self._modalidade_evento(ev) for ev in membros}
            modalidades.discard(None)
            if len(membros) < 2 or len(modalidades) < 2:
                continue
            correlation_id = uuid.uuid4().hex
            for ev in membros:
                ev.correlation_id = correlation_id
            for ev in membros:
                if isinstance(ev, (PropagacaoFissuraEvento, AberturaFissuraTermicaEvento)):
                    ev.confidence = max(float(ev.confidence or 0.0), 0.9)
                    ev.severity = "High"

    # ─────────────────────────────────────────────────────────
    # UTILITÁRIOS / UTILITIES
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def _sanitizar(nome: str, arr: np.ndarray) -> np.ndarray:
        """Valida 2D e converte Inf -> NaN (tratados como dados ausentes) /
        Validates 2D and converts Inf to NaN (handled as missing data)."""
        arr = np.asarray(arr, dtype=float)
        if arr.ndim != 2:
            raise ValueError(f"{nome} deve ser um array 2D (n_t, n_z); recebido shape {arr.shape}")
        return np.where(np.isinf(arr), np.nan, arr)

    @staticmethod
    def _interpolar_para_eixo(arr: np.ndarray, n_alvo: int) -> np.ndarray:
        """Interpola um campo (n_t, n_z) para n_alvo amostras temporais /
        Interpolates a (n_t, n_z) field onto n_alvo time samples.

        Usa interpolação linear por posição (mesma origem e duração
        assumidas); sem custo quando o eixo já coincide.
        """
        if arr.shape[0] == n_alvo:
            return arr
        eixo_origem = np.linspace(0.0, 1.0, arr.shape[0])
        eixo_alvo = np.linspace(0.0, 1.0, n_alvo)
        return np.apply_along_axis(lambda col: np.interp(eixo_alvo, eixo_origem, col), 0, arr)

    def _taxa_tendencia_ue_dia(self, coluna: np.ndarray, t_s: np.ndarray,
                               filtrar: bool = True) -> float:
        """Taxa de tendência (µε/dia) com o harmônico diário ajustado em conjunto /
        Trend rate (µε/dia) with the daily harmonic jointly fitted.

        Base [sen ωt, cos ωt, t, 1] por mínimos quadrados (mediana temporal
        opcional antes do ajuste, para robustez a impulsos). Um seno de ~1
        período é fortemente correlacionado com uma reta: projetar o
        harmônico antes do ajuste linear (ou estimar a tendência sobre a
        série crua) transfere parte da tendência real ao seno e sufoca taxas
        de creep/recalque — o ajuste conjunto separa os dois sem viés. Para
        campanhas ≥ 10 dias o harmônico anual também entra na base.
        Retorna NaN para séries com poucas amostras válidas.
        """
        n = coluna.shape[0]
        valido = np.isfinite(coluna)
        if int(valido.sum()) < max(8, n // 4):
            return float("nan")
        y = coluna.copy()
        if int(valido.sum()) < n:
            y[~valido] = np.interp(t_s[~valido], t_s[valido], y[valido])
        if filtrar:
            janela = min(n, max(5, ((n // 100) | 1)))
            y = median_filter(y, size=janela, mode="nearest")
        omega = OMEGA_DIURNO_RAD_S
        base = [np.sin(omega * t_s), np.cos(omega * t_s)]
        indice_tendencia = 2
        if t_s[-1] >= 10.0 * _SEGUNDOS_POR_DIA:
            omega_a = omega * RAZAO_OMEGA_ANUAL
            base += [np.sin(omega_a * t_s), np.cos(omega_a * t_s)]
            indice_tendencia = 4
        base += [t_s / _SEGUNDOS_POR_DIA, np.ones_like(t_s)]
        A = np.column_stack(base)
        with _sem_avisos_nan():
            coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        return float(coef[indice_tendencia])

    def _taxas_posicoes_ue_dia(self, dss: np.ndarray, fs_dss_hz: float) -> np.ndarray:
        """Taxa de deformação (µε/dia) por posição / Strain rate (µε/dia) per position.

        Cada série temporal é median-filtrada (janela ~1/100 da campanha,
        robustez a impulsos) e ajustada conjuntamente com o harmônico diário
        (`_taxa_tendencia_ue_dia`); canais com menos de 25% de amostras
        válidas ficam com taxa NaN (ignorados pelas regras).
        """
        n_t, n_z = dss.shape
        t_s = np.arange(n_t, dtype=float) / float(fs_dss_hz)
        taxas = np.full(n_z, np.nan)
        for j in range(n_z):
            taxas[j] = self._taxa_tendencia_ue_dia(dss[:, j], t_s, filtrar=True)
        return taxas

    def _taxa_coluna_ue_dia(self, coluna: np.ndarray, fs_dss_hz: float) -> float:
        """Taxa de creep (µε/dia) de uma única série temporal /
        Creep rate (µε/dia) of a single time series (NaN se inválida)."""
        n = coluna.shape[0]
        t_s = np.arange(n, dtype=float) / float(fs_dss_hz)
        return self._taxa_tendencia_ue_dia(coluna, t_s, filtrar=True)

    @staticmethod
    def _ajuste_linear(x: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
        """Ajuste linear y = s·x + b suprimindo warnings numéricos /
        Linear fit y = s·x + b with numeric warnings suppressed."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            s, b = np.polyfit(x, y, 1)
        return float(s), float(b)

    def _abertura_termica(self, residual: np.ndarray, dts_coluna: np.ndarray,
                          posicao_m: float) -> Optional[AberturaFissuraTermicaEvento]:
        """Regressão do residual da fissura vs ΔT local / Crack residual vs local ΔT regression.

        Inclinação no CTE da alvenaria (CTE_MIN_UE_K..CTE_MAX_UE_K µε/K, com
        folga sobre a faixa 4–8 µε/K) e correlação de Pearson acima de
        CORRELACAO_TERMICA_MIN caracterizam abertura térmica real (não o
        strain aparente do cabo, removido pela correção Brillouin).
        """
        delta_t = dts_coluna - np.nanmedian(dts_coluna)
        valido = np.isfinite(residual) & np.isfinite(delta_t)
        if int(valido.sum()) < 8:
            return None
        x, y = delta_t[valido], residual[valido]
        if float(np.nanmax(x) - np.nanmin(x)) < 1e-9:
            return None  # ΔT sem variância: correlação térmica indefinida
        inclinacao, _ = self._ajuste_linear(x, y)
        with _sem_avisos_nan():
            pearson = float(np.corrcoef(x, y)[0, 1])
        if not np.isfinite(pearson):
            return None
        if pearson > self.CORRELACAO_TERMICA_MIN and self.CTE_MIN_UE_K <= inclinacao <= self.CTE_MAX_UE_K:
            amplitude_t = float((np.nanmax(delta_t) - np.nanmin(delta_t)) / 2.0)
            return AberturaFissuraTermicaEvento(
                posicao_m=posicao_m,
                variacao_termica_c=amplitude_t,
                confidence=float(min(0.99, 0.5 + 0.5 * pearson)),
                severity="Medium",
            )
        return None

    def _pico_modal_welch(self, segmento: np.ndarray, fs_hz: float,
                          n_janela: int) -> Optional[float]:
        """Frequência do pico dominante do PSD de Welch na faixa modal /
        Dominant PSD peak frequency from Welch's method in the modal band."""
        nperseg = min(int(n_janela), segmento.shape[0])
        if nperseg < 16:
            return None
        freqs, psd = welch(segmento, fs=fs_hz, nperseg=nperseg, noverlap=nperseg // 2)
        faixa = (freqs >= self.FAIXA_MODAL_HZ[0]) & (freqs <= self.FAIXA_MODAL_HZ[1])
        if not faixa.any():
            return None
        return float(freqs[faixa][int(np.argmax(psd[faixa]))])

    @staticmethod
    def _posicao_evento(ev: Event) -> Optional[float]:
        """Posição espacial de um evento (m), quando aplicável / Event spatial position (m), if any."""
        pos = getattr(ev, "posicao_m", None)
        if pos is None:
            pos = getattr(ev, "posicao_fissura_m", None)
        return None if pos is None else float(pos)

    @staticmethod
    def _modalidade_evento(ev: Event) -> Optional[str]:
        """Modalidade de sensor de origem do evento / Source sensor modality of the event."""
        if isinstance(ev, (EventoAcusticoFissura, DanoModalEvento)):
            return "das"
        if isinstance(ev, (PropagacaoFissuraEvento, AberturaFissuraTermicaEvento, RecalqueEvento)):
            return "dss"
        if isinstance(ev, AnomaliaTermicaEvento):
            return "dts"
        return None

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
        with np.errstate(invalid="ignore", divide="ignore"):
            razao[n_sta:n_sta + fim] = sta[:fim] / np.maximum(lta[:fim], 1e-12)
        return np.nan_to_num(razao, nan=0.0, posinf=0.0, neginf=0.0)

    @staticmethod
    def _grupos_contiguos(indices: np.ndarray) -> List[np.ndarray]:
        """Agrupa índices com diferença unitária / Groups indices with unit spacing."""
        if indices.size == 0:
            return []
        cortes = np.where(np.diff(indices) > 1)[0] + 1
        return [grupo for grupo in np.split(indices, cortes) if grupo.size > 0]

    @staticmethod
    def _grupos_com_fenda(grupos: List[np.ndarray], fenda_max: int) -> List[np.ndarray]:
        """Funde grupos separados por fendas curtas / Merges groups split by short gaps.

        O gradiente sustentado de recalque é uma região contínua; fendas de
        poucas posições (ruído de estimativa na fronteira do limiar) não
        devem fragmentar o padrão em eventos espúrios.
        """
        if not grupos:
            return []
        fundidos = [grupos[0]]
        for grupo in grupos[1:]:
            if grupo[0] - fundidos[-1][-1] <= fenda_max + 1:
                fundidos[-1] = np.concatenate([fundidos[-1], grupo])
            else:
                fundidos.append(grupo)
        return fundidos
