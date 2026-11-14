"""
Alakoro FiberSense — Gerador de Assinaturas MSE
MSE Signature Generator

Autor/Author: Luiz Paulo Colombiano
Licença/License: MIT

Assinaturas físicas DFOS (DTS/DSS/DAS) para o Monitoramento da Saúde
Estrutural (MSE) de edifícios antigos: difusão térmica 1D em alvenaria,
pontes térmicas de fissuras, abertura de fissuras em Brillouin (DSS),
recalque diferencial, emissão acústica de fissuras (DAS), vibração modal
de torres de alvenaria e ruído ambiental.

DFOS physical signatures (DTS/DSS/DAS) for Structural Health Monitoring
(SHM) of heritage buildings: 1D thermal diffusion in masonry, crack
thermal bridges, Brillouin crack opening (DSS), differential settlement,
crack acoustic emission (DAS), masonry-tower modal vibration and
ambient noise.

Referências / References
------------------------
- Owczarek (2021): difusividade térmica da alvenaria α ≈ 5e-7 m²/s
  (faixa 3.5e-7–1e-6 m²/s); penetração diária δ ≈ 0.117 m.
- Glisic & Inaudi (2012): fissura ativa = pico localizado de 3500–5000 µε
  (0.35–0.5 mm de abertura sobre comprimento de transferência ~10 cm).
- Hubbard (2021), Di Gennaro (2025): cross-sensibilidade Brillouin
  ≈ 20 µε/°C (equivalência térmica crítica do DSS).
"""

from typing import Dict, Optional, Tuple

import numpy as np

from .structures import ConfigAquisicaoMSE, GeometriaEstrutura, TipoAssinaturaMSE

try:  # Extensão C++20 opcional (funções mse_*) / optional C++20 extension (mse_* fns)
    import alakoro_core as _nucleo
except ImportError:  # pragma: no cover - depende do ambiente
    _nucleo = None

#: True quando o núcleo C++ está instalado com todas as funções `mse_*` usadas
#: aqui (útil para testes e logging) / True when the C++ core is installed with
#: every `mse_*` function used here (useful for tests and logging).
NUCLEO_CPP_ATIVO: bool = _nucleo is not None and all(
    callable(getattr(_nucleo, nome, None))
    for nome in (
        "mse_thermal_wave_d",
        "mse_crack_strain_profile_d",
        "mse_ae_impulse_d",
        "mse_modal_decay_d",
        "mse_material_traits_d",
    )
)

# Constantes físicas / Physical constants
OMEGA_DIURNO_RAD_S: float = 7.272e-5  # ciclo diário / daily cycle T = 86400 s (rad/s)
PERIODO_DIURNO_S: float = 86400.0  # período canônico do ciclo diário [s] (cache do núcleo C++)
RAZAO_OMEGA_ANUAL: float = 1.0 / 365.25  # ω_anual = ω_diurno / 365.25
CTE_TIJOLO_PADRAO: float = 5.6e-6  # coef. dilatação térmica do tijolo (1/°C), faixa 4–8e-6
CROSS_BRILLOUIN_PADRAO: float = 20e-6  # cross-sensibilidade Brillouin (strain/°C)
AMPLITUDE_ANUAL_PADRAO_K: float = 20.0  # amplitude superficial do ciclo anual (K), faixa 15–25
AMPLITUDE_TERMICA_FISSURA_PADRAO_K: float = 15.0  # ciclo térmico local na fissura (K)

#: Materiais do núcleo C++ (nomes em minúsculas, vide mse_material_traits_d) /
#: C++ core materials (lowercase names, see mse_material_traits_d).
MATERIAIS_NUCLEO: Tuple[str, ...] = ("tijolo", "pedra", "argamassa", "concreto")
MATERIAL_NUCLEO_PADRAO: str = "tijolo"  # material default para α = 5e-7 m²/s (Owczarek 2021)

_DIFUSIVIDADE_MATERIAL: Dict[str, float] = {}


def funcao_nucleo_mse(nome: str):
    """Retorna uma função `mse_*` do alakoro_core, ou None se indisponível /
    Returns an `mse_*` function from alakoro_core, or None if unavailable.

    O módulo funciona com ou sem a extensão C++: quando a função não existe,
    cada chamada cai no fallback NumPy puro correspondente.
    """
    if _nucleo is None:
        return None
    return getattr(_nucleo, nome, None)


def material_para_alpha(alpha: float) -> Optional[str]:
    """Material do núcleo C++ cuja difusividade coincide com `alpha` /
    C++ core material whose diffusivity matches `alpha`.

    O solver térmico C++ (`mse_thermal_wave_d`) trabalha com α fixo por
    material (traits em tempo de compilação); esta função resolve o nome do
    material a partir do α pedido. Retorna None quando nenhum material casa
    (o chamador então mantém o fallback NumPy, que aceita qualquer α).
    """
    if not _DIFUSIVIDADE_MATERIAL:
        fn = funcao_nucleo_mse("mse_material_traits_d")
        if fn is None:
            return None
        for nome in MATERIAIS_NUCLEO:
            try:
                difusividade, _, _, _ = fn(nome)
                _DIFUSIVIDADE_MATERIAL[nome] = float(difusividade)
            except (TypeError, ValueError):
                continue
    for nome, difusividade in _DIFUSIVIDADE_MATERIAL.items():
        if abs(difusividade - alpha) <= 1e-6 * abs(difusividade):
            return nome
    return None


def delta_penetracao_m(alpha: float, omega: float = OMEGA_DIURNO_RAD_S) -> float:
    """Profundidade de penetração térmica δ = √(2α/ω) / Thermal penetration depth δ = √(2α/ω)."""
    return float(np.sqrt(2.0 * alpha / omega))


def amplitude_analitica_k(x_m: np.ndarray, alpha: float, a0_k: float,
                          omega: float = OMEGA_DIURNO_RAD_S) -> np.ndarray:
    """Amplitude da onda térmica harmônica A(x) = A₀·e^(−x/δ) / Harmonic thermal wave amplitude."""
    return a0_k * np.exp(-np.asarray(x_m, dtype=float) / delta_penetracao_m(alpha, omega))


def defasagem_s(x_m: np.ndarray, alpha: float, omega: float = OMEGA_DIURNO_RAD_S) -> np.ndarray:
    """Defasagem temporal da onda térmica Δt(x) = x/(δ·ω) / Temporal lag of the thermal wave."""
    delta = delta_penetracao_m(alpha, omega)
    return np.asarray(x_m, dtype=float) / (delta * omega)


class GeradorAssinaturasMSE:
    """Gerador de assinaturas físicas DFOS para MSE de edifícios antigos /
    Generator of DFOS physical signatures for SHM of heritage buildings.

    Replica o padrão do simulador de poços (`alakoro.simulation.SignatureGenerator`):
    RNG local `np.random.default_rng(seed)`, constantes de classe e retorno
    canônico em dicionário::

        {'dts': np.ndarray | None, 'dss': np.ndarray | None, 'das': np.ndarray | None,
         'signature_type': TipoAssinaturaMSE, 'parameters': dict}

    As chaves 'dts', 'dss' e 'das' estão sempre presentes; vale None quando a
    modalidade não se aplica ao método. Unidades: DTS em °C, DSS em µε,
    DAS em µε (acústico/quase-estático).

    Parameters
    ----------
    geometria : GeometriaEstrutura, opcional
        Geometria do percurso da fibra na estrutura.
    acq : ConfigAquisicaoMSE, opcional
        Configuração de aquisição (taxas, duração, posições).
    seed : int, opcional
        Semente do gerador local (determinismo dos testes).

    Notes
    -----
    Como a taxa DAS típica (1000 Hz) sobre uma campanha completa produziria
    volumes inviáveis (100 GB+), os métodos DAS geram uma *janela curta*
    (default 60 s, ajustável via `duracao_janela_s`), coerente com a
    aquisição acústica de eventos.
    """

    # Constantes físicas de classe / Class-level physical constants
    OMEGA_DIURNO: float = OMEGA_DIURNO_RAD_S
    RAZAO_OMEGA_ANUAL: float = RAZAO_OMEGA_ANUAL
    CTE_TIJOLO: float = CTE_TIJOLO_PADRAO
    CROSS_BRILLOUIN: float = CROSS_BRILLOUIN_PADRAO
    A0_ANUAL_K: float = AMPLITUDE_ANUAL_PADRAO_K
    L_SR_PADRAO_M: float = 1.0
    JANELA_PONTE_TERMICA_PADRAO_M: float = 2.0
    DURACAO_PADRAO_JANELA_DAS_S: float = 60.0

    def __init__(self, geometria: Optional[GeometriaEstrutura] = None,
                 acq: Optional[ConfigAquisicaoMSE] = None, seed: Optional[int] = 42):
        self.geometria = geometria or GeometriaEstrutura()
        self.acq = acq or ConfigAquisicaoMSE()
        self.n_z = int(self.acq.n_posicoes)
        self.posicoes = self.geometria.eixo_posicoes(self.n_z)
        self._fator_exposicao = self.geometria.fator_exposicao(self.posicoes)
        self._profundidades = self.geometria.profundidades(self.posicoes)
        # Gerador local: testes determinísticos e imunes a consumo de estado
        # global por outros módulos (ex.: GUI, NumPy).
        self._rng = np.random.default_rng(seed)

    # ─────────────────────────────────────────────────────────
    # MÉTODOS UTILITÁRIOS / UTILITY METHODS
    # ─────────────────────────────────────────────────────────

    def _eixo_tempo(self, fs_hz: float, n_t: int) -> np.ndarray:
        """Eixo temporal (n_t,) em segundos / Time axis (n_t,) in seconds."""
        return np.arange(n_t, dtype=float) / fs_hz

    def _eixo_das(self, duracao_janela_s: Optional[float] = None) -> Tuple[int, np.ndarray, float]:
        """Eixo temporal DAS de janela curta / Short-window DAS time axis.

        Parameters
        ----------
        duracao_janela_s : float, opcional
            Duração da janela DAS (s). Default: `min(duracao_s, 60 s)`.

        Returns
        -------
        n_t : int
            Número de amostras temporais.
        t : np.ndarray
            Eixo temporal (n_t,).
        fs : float
            Taxa de amostragem (Hz).
        """
        duracao = min(self.acq.duracao_s, duracao_janela_s or self.DURACAO_PADRAO_JANELA_DAS_S)
        fs = float(self.acq.fs_das_hz)
        n_t = max(2, int(round(duracao * fs)))
        return n_t, self._eixo_tempo(fs, n_t), fs

    def _media_movel_gauge(self, perfil: np.ndarray, gauge_m: float) -> np.ndarray:
        """Média móvel espacial que emula o gauge físico / Spatial moving average emulating the gauge."""
        n_amostras = max(1, int(round(gauge_m / self.acq.passo_espacial_m)))
        if n_amostras <= 1:
            return perfil
        kernel = np.ones(n_amostras) / n_amostras
        return np.convolve(perfil, kernel, mode="same")

    def _perfil_espacial_fissura(self, posicao_fissura_m: float, abertura_mm: float,
                                 comprimento_transferencia_m: float, l_sr_m: float,
                                 gauge_m: float, usar_nucleo: bool = True) -> np.ndarray:
        """Perfil espacial do pico de fissura (µε) em `self.posicoes` /
        Spatial crack-peak profile (µε) at `self.posicoes`.

        Núcleo C++: `mse_crack_strain_profile_d` produz o triângulo
        ε(x) = (w/L_t)·triângulo(x; centro, 2·SR) com média-móvel de gauge
        embutida (janela L_t/SR). Como o triângulo só atinge o pico exato
        w/L_t sobre o centro, exige-se amostragem espacial fina
        (passo ≤ L_SR/4); em grids coarse mantém-se o gaussiano NumPy
        (σ = L_SR, média-móvel de gauge por `gauge_m`), que é o modelo do
        fallback e dos testes analíticos existentes.
        """
        if usar_nucleo and self.acq.passo_espacial_m * 4.0 <= l_sr_m:
            fn = funcao_nucleo_mse("mse_crack_strain_profile_d")
            if fn is not None:
                try:
                    perfil = np.asarray(
                        fn(self.posicoes,
                           np.array([posicao_fissura_m], dtype=float),
                           np.array([abertura_mm], dtype=float),
                           float(comprimento_transferencia_m), float(l_sr_m)),
                        dtype=float,
                    )
                    # O núcleo retorna strain absoluto (pico = w/L_t); o gerador
                    # trabalha com forma normalizada (pico = 1) multiplicada por
                    # pico_ue, igual ao gaussiano NumPy abaixo.
                    pico = float(perfil.max())
                    if pico > 0.0:
                        return perfil / pico
                    return perfil
                except (TypeError, ValueError):
                    pass  # fallback NumPy
        forma = np.exp(-0.5 * ((self.posicoes - posicao_fissura_m) / l_sr_m) ** 2)
        return self._media_movel_gauge(forma, gauge_m)

    def _campo_termico(self, n_t: int, fs_hz: float, alpha: float, a0_k: float,
                       incluir_anual: bool, rugosidade_k: float,
                       usar_nucleo: bool = True) -> np.ndarray:
        """Campo térmico harmônico (n_t, n_z) da solução analítica 1D + ruído /
        Harmonic thermal field (n_t, n_z) from the 1D analytical solution + noise.

        Implementa A(x) = A₀·e^(−x/δ) e defasagem Δt(x) = x/(δ·ω), modulados
        pelo fator de exposição solar do percurso da fibra.

        Núcleo C++: o harmônico diário usa `mse_thermal_wave_d` quando o α
        coincide com a difusividade de um material do núcleo (default
        "tijolo" para α = 5e-7 m²/s). Os tempos são deslocados de T/4 porque
        o solver C++ trabalha em convenção cosseno e o gerador em seno
        (equivalentes a um atraso de um quarto de período). O harmônico
        anual permanece em NumPy para manter a fase exata de ambos os
        componentes. O fator de exposição e o ruído branco são sempre
        aplicados em NumPy, sobre o núcleo harmônico.
        """
        omega = OMEGA_DIURNO_RAD_S
        t = self._eixo_tempo(fs_hz, n_t)
        campo = None
        if usar_nucleo:
            fn = funcao_nucleo_mse("mse_thermal_wave_d")
            material = material_para_alpha(alpha) if fn is not None else None
            if material is not None:
                tempos_cpp = t - 0.25 * PERIODO_DIURNO_S  # cos(θ−π/2) ≡ sen(θ)
                amplitudes = np.full(n_t, a0_k)
                try:
                    campo = np.asarray(
                        fn(material, self._profundidades, tempos_cpp, amplitudes,
                           PERIODO_DIURNO_S, False),
                        dtype=float,
                    )
                except (TypeError, ValueError):
                    campo = None  # fallback NumPy
        if campo is None:
            delta_d = delta_penetracao_m(alpha, omega)
            amplitude = a0_k * np.exp(-self._profundidades / delta_d)
            fase = self._profundidades / delta_d
            campo = amplitude[None, :] * np.sin(omega * t[:, None] - fase[None, :])
        if incluir_anual:
            omega_a = omega * RAZAO_OMEGA_ANUAL
            delta_a = delta_penetracao_m(alpha, omega_a)
            amp_a = self.A0_ANUAL_K * np.exp(-self._profundidades / delta_a)
            campo = campo + amp_a[None, :] * np.sin(omega_a * t[:, None] - (self._profundidades / delta_a)[None, :])
        campo = campo * self._fator_exposicao[None, :]
        if rugosidade_k > 0.0:
            campo = campo + self._rng.normal(0.0, rugosidade_k, (n_t, self.n_z))
        return campo

    def _finalizar(self, dts: Optional[np.ndarray], dss: Optional[np.ndarray],
                   das: Optional[np.ndarray], signature_type: TipoAssinaturaMSE,
                   parameters: Dict) -> Dict:
        """Monta o dicionário canônico de retorno / Builds the canonical return dict."""
        return {
            "dts": dts,
            "dss": dss,
            "das": das,
            "signature_type": signature_type,
            "parameters": parameters,
        }

    # ─────────────────────────────────────────────────────────
    # ASSINATURAS TÉRMICAS (DTS) / THERMAL SIGNATURES (DTS)
    # ─────────────────────────────────────────────────────────

    def difusao_termica_parede(self, alpha: float = 5e-7, amplitude_superficial_k: float = 20.0,
                               incluir_anual: bool = False, temperatura_base_c: float = 20.0,
                               rugosidade_termica_k: float = 0.05, usar_nucleo: bool = True) -> Dict:
        """Difusão térmica 1D em parede de alvenaria / 1D thermal diffusion in a masonry wall.

        Superposição harmônica do ciclo diário (T = 86400 s; opcionalmente o
        anual, T = 1 ano) com envelope espacial dado pela exposição solar ao
        longo do percurso da fibra e amortecimento/defasagem por profundidade
        de instalação (solução analítica de Owczarek 2021).

        Parameters
        ----------
        alpha : float
            Difusividade térmica da alvenaria (m²/s). Default: 5e-7 (faixa 3.5e-7–1e-6).
        amplitude_superficial_k : float
            Amplitude térmica superficial diária A₀ (K). Default: 20 (faixa 15–35).
        incluir_anual : bool
            Inclui o componente anual (A₀ = 20 K, δ ≈ 2.24 m para α = 5e-7).
        temperatura_base_c : float
            Temperatura média da parede (°C).
        rugosidade_termica_k : float
            Desvio-padrão do ruído térmico branco (K). Default: 0.05.
        usar_nucleo : bool
            Usa o solver térmico C++ (`mse_thermal_wave_d`) quando o α casa
            com a difusividade de um material do núcleo (default "tijolo"
            para α = 5e-7 m²/s); False força o fallback NumPy puro.

        Returns
        -------
        dict
            Dicionário canônico com 'dts' (n_t, n_z) em °C.
        """
        n_t = self.acq.n_amostras_dts
        campo = self._campo_termico(n_t, self.acq.fs_dts_hz, alpha, amplitude_superficial_k,
                                    incluir_anual, rugosidade_termica_k, usar_nucleo=usar_nucleo)
        dts = temperatura_base_c + campo
        return self._finalizar(
            dts=dts, dss=None, das=None,
            signature_type=TipoAssinaturaMSE.DIFUSAO_TERMICA_PAREDE,
            parameters={
                "alpha_m2_s": alpha,
                "amplitude_superficial_k": amplitude_superficial_k,
                "incluir_anual": incluir_anual,
                "temperatura_base_c": temperatura_base_c,
                "delta_penetracao_diario_m": delta_penetracao_m(alpha),
            },
        )

    def ponte_termica_fissura(self, posicao_fissura_m: float, offset_k: float = 3.0,
                              alpha: float = 5e-7, amplitude_superficial_k: float = 20.0,
                              incluir_anual: bool = False, janela_m: float = JANELA_PONTE_TERMICA_PADRAO_M,
                              amplificacao_local: float = 2.0, reducao_defasagem: float = 0.5,
                              temperatura_base_c: float = 20.0,
                              rugosidade_termica_k: float = 0.05,
                              usar_nucleo: bool = True) -> Dict:
        """Ponte térmica associada a fissura aberta / Thermal bridge of an open crack.

        Campo térmico de parede (vide `difusao_termica_parede`) acrescido de:
        (i) offset localizado e persistente de 1–5 K na posição da fissura
        (fluxo de ar/umidade pela fissura) e (ii) resposta local de menor
        inércia — amplitude amplificada e defasagem reduzida numa janela
        espacial de ~2 m.

        Parameters
        ----------
        posicao_fissura_m : float
            Posição da fissura ao longo da fibra (m).
        offset_k : float
            Offset térmico persistente na fissura (K). Default: 3 (faixa 1–5).
        janela_m : float
            Largura espacial da perturbação local (m). Default: 2.
        amplificacao_local : float
            Ganho de amplitude da resposta local (menor inércia térmica).
        reducao_defasagem : float
            Fração de defasagem removida localmente (0 = igual à parede, 1 = sem defasagem).

        Returns
        -------
        dict
            Dicionário canônico com 'dts' (n_t, n_z) em °C.
        """
        n_t = self.acq.n_amostras_dts
        fs = self.acq.fs_dts_hz
        t = self._eixo_tempo(fs, n_t)
        campo = self._campo_termico(n_t, fs, alpha, amplitude_superficial_k,
                                    incluir_anual, rugosidade_termica_k, usar_nucleo=usar_nucleo)
        omega = OMEGA_DIURNO_RAD_S
        delta_d = delta_penetracao_m(alpha, omega)
        perfil = np.exp(-0.5 * ((self.posicoes - posicao_fissura_m) / (janela_m / 2.0)) ** 2)
        amp_local = amplificacao_local * amplitude_superficial_k * self._fator_exposicao * perfil
        fase_local = -reducao_defasagem * self._profundidades / delta_d
        campo = campo + amp_local[None, :] * np.sin(omega * t[:, None] + fase_local[None, :])
        campo = campo + offset_k * perfil[None, :]
        dts = temperatura_base_c + campo
        return self._finalizar(
            dts=dts, dss=None, das=None,
            signature_type=TipoAssinaturaMSE.PONTE_TERMICA_FISSURA,
            parameters={
                "posicao_fissura_m": posicao_fissura_m,
                "offset_k": offset_k,
                "janela_m": janela_m,
                "amplificacao_local": amplificacao_local,
                "reducao_defasagem": reducao_defasagem,
                "alpha_m2_s": alpha,
            },
        )

    # ─────────────────────────────────────────────────────────
    # ASSINATURAS DE DEFORMAÇÃO (DSS/Brillouin) / STRAIN SIGNATURES (DSS)
    # ─────────────────────────────────────────────────────────

    def fissura_dss(self, posicao_fissura_m: float, abertura_mm: float = 0.4,
                    taxa_creep_ue_dia: float = 10.0, comprimento_transferencia_m: float = 0.1,
                    l_sr_m: float = L_SR_PADRAO_M, gauge_m: float = 0.5,
                    incluir_termico: bool = True, temperatura_ref_c: float = 20.0,
                    coef_expansao_termica: float = CTE_TIJOLO_PADRAO,
                    ciclo_sazonal: bool = False,
                    amplitude_termica_fissura_k: float = AMPLITUDE_TERMICA_FISSURA_PADRAO_K,
                    amplitude_termica_cabo_k: float = 20.0,
                    alpha: float = 5e-7, rugosidade_dss_ue: float = 5.0,
                    usar_nucleo: bool = True) -> Dict:
        """Abertura de fissura ativa medida por DSS (Brillouin) / Active crack opening measured by DSS.

        Fissura ativa = pico localizado ε ≈ w/L_t (3500–5000 µε para
        0.35–0.5 mm sobre L_t ≈ 10 cm; Glisic & Inaudi 2012), com largura
        espacial ~2×L_SR e média no gauge. Inclui: creep (taxa µε/dia),
        abertura/fecho térmico cíclico via CTE do tijolo (4–8e-6/°C) e a
        cross-sensibilidade Brillouin de 20 µε/°C aplicada a *todo* o traço
        (Hubbard 2021; Di Gennaro 2025).

        Parameters
        ----------
        posicao_fissura_m : float
            Posição da fissura ao longo da fibra (m).
        abertura_mm : float
            Abertura da fissura (mm). Default: 0.4.
        taxa_creep_ue_dia : float
            Taxa de creep da abertura (µε/dia). Default: 10 (faixa 1–50).
        comprimento_transferencia_m : float
            Comprimento de transferência de deformação L_t (m). Default: 0.1.
        l_sr_m : float
            Resolução espacial L_SR (m); largura do pico ~2×L_SR. Default: 1.
        gauge_m : float
            Comprimento de gauge (m) para a média móvel espacial.
        incluir_termico : bool
            Adiciona a cross-sensibilidade Brillouin (20 µε/°C) em todo o
            traço, gerando o campo térmico do cabo como referência.
        coef_expansao_termica : float
            CTE do tijolo (1/°C). Default: 5.6e-6.
        ciclo_sazonal : bool
            Inclui o componente anual no ciclo térmico local e no cabo.
        rugosidade_dss_ue : float
            Ruído do sistema Brillouin (µε). Default: 5 (faixa ±2–20).
        usar_nucleo : bool
            Usa o perfil espacial C++ (`mse_crack_strain_profile_d`, pico
            triangular com média-móvel de gauge do próprio núcleo) quando a
            amostragem espacial é adequada (≥ 4 posições por L_SR — abaixo
            disso o triângulo subestima o pico no grid coarse e mantém-se o
            gaussiano NumPy). A evolução temporal (creep, térmico, ruído)
            segue sempre em NumPy vetorizado. Default: True.

        Returns
        -------
        dict
            Dicionário canônico com 'dss' (n_t, n_z) em µε.
        """
        n_t = self.acq.n_amostras_dss
        fs = self.acq.fs_dss_hz
        t = self._eixo_tempo(fs, n_t)
        pico_ue = abertura_mm * 1e-3 / comprimento_transferencia_m * 1e6
        forma = self._perfil_espacial_fissura(posicao_fissura_m, abertura_mm,
                                              comprimento_transferencia_m, l_sr_m,
                                              gauge_m, usar_nucleo=usar_nucleo)
        dias = t / 86400.0
        dss = pico_ue * forma[None, :]
        dss = dss + (taxa_creep_ue_dia * dias)[:, None] * forma[None, :]
        delta_t_local = amplitude_termica_fissura_k * np.sin(OMEGA_DIURNO_RAD_S * t)
        if ciclo_sazonal:
            delta_t_local = delta_t_local + self.A0_ANUAL_K * np.sin(OMEGA_DIURNO_RAD_S * RAZAO_OMEGA_ANUAL * t)
        dss = dss + (coef_expansao_termica * delta_t_local * 1e6)[:, None] * forma[None, :]
        if incluir_termico:
            campo_t = self._campo_termico(n_t, fs, alpha, amplitude_termica_cabo_k,
                                          ciclo_sazonal, rugosidade_k=0.05)
            dss = dss + self.CROSS_BRILLOUIN * campo_t * 1e6
        if rugosidade_dss_ue > 0.0:
            dss = dss + self._rng.normal(0.0, rugosidade_dss_ue, (n_t, self.n_z))
        return self._finalizar(
            dts=None, dss=dss, das=None,
            signature_type=TipoAssinaturaMSE.FISSURA_DSS,
            parameters={
                "posicao_fissura_m": posicao_fissura_m,
                "abertura_mm": abertura_mm,
                "pico_ue": pico_ue,
                "comprimento_transferencia_m": comprimento_transferencia_m,
                "taxa_creep_ue_dia": taxa_creep_ue_dia,
                "l_sr_m": l_sr_m,
                "gauge_m": gauge_m,
                "incluir_termico": incluir_termico,
                "coef_expansao_termica": coef_expansao_termica,
            },
        )

    def recalque_diferencial(self, taxa_ue_dia: float = 5.0, n_episodios: int = 3,
                             taxa_episodio_ue_dia: float = 25.0,
                             posicao_episodio_m: Optional[float] = None,
                             largura_episodio_m: Optional[float] = None,
                             extremidade: str = "fim", rugosidade_dss_ue: float = 5.0) -> Dict:
        """Recalque diferencial de fundação / Differential foundation settlement.

        Deriva lenta de deformação espacialmente gradiente (maior numa
        extremidade, ex.: sob a torre) acrescida de eventos episódicos
        localizados (abrandamento repentino do solo).

        Parameters
        ----------
        taxa_ue_dia : float
            Taxa de deriva na extremidade mais carregada (µε/dia).
        n_episodios : int
            Número de eventos episódicos ao longo da campanha.
        taxa_episodio_ue_dia : float
            Taxa adicional durante um episódio (µε/dia).
        posicao_episodio_m : float, opcional
            Centro espacial dos episódios. Default: aleatório na metade ativa.
        largura_episodio_m : float, opcional
            Largura espacial dos episódios. Default: L/4.
        extremidade : str
            "fim" (maior deformação no final do percurso) ou "inicio".

        Returns
        -------
        dict
            Dicionário canônico com 'dss' (n_t, n_z) em µε.
        """
        n_t = self.acq.n_amostras_dss
        t = self._eixo_tempo(self.acq.fs_dss_hz, n_t)
        dias = t / 86400.0
        comprimento = self.geometria.comprimento_fibra_m
        if extremidade == "inicio":
            peso = ((comprimento - self.posicoes) / comprimento) ** 2
        else:
            peso = (self.posicoes / comprimento) ** 2
        dss = (taxa_ue_dia * dias)[:, None] * peso[None, :]
        largura = largura_episodio_m or comprimento / 4.0
        for _ in range(int(n_episodios)):
            t_k = float(self._rng.uniform(0.05, 0.95)) * self.acq.duracao_s
            if posicao_episodio_m is not None:
                centro = float(posicao_episodio_m)
            elif extremidade == "inicio":
                centro = float(self._rng.uniform(0.0, 0.5 * comprimento))
            else:
                centro = float(self._rng.uniform(0.5 * comprimento, comprimento))
            forma = np.exp(-0.5 * ((self.posicoes - centro) / largura) ** 2)
            acumulo = np.maximum(dias - t_k / 86400.0, 0.0) * taxa_episodio_ue_dia
            dss = dss + acumulo[:, None] * forma[None, :]
        if rugosidade_dss_ue > 0.0:
            dss = dss + self._rng.normal(0.0, rugosidade_dss_ue, (n_t, self.n_z))
        return self._finalizar(
            dts=None, dss=dss, das=None,
            signature_type=TipoAssinaturaMSE.RECALQUE_DIFERENCIAL,
            parameters={
                "taxa_ue_dia": taxa_ue_dia,
                "n_episodios": int(n_episodios),
                "taxa_episodio_ue_dia": taxa_episodio_ue_dia,
                "extremidade": extremidade,
            },
        )

    # ─────────────────────────────────────────────────────────
    # ASSINATURAS ACÚSTICAS (DAS) / ACOUSTIC SIGNATURES (DAS)
    # ─────────────────────────────────────────────────────────

    def _vento(self, t: np.ndarray, amplitude_ue: float = 0.5) -> np.ndarray:
        """Vento: conteúdo contínuo < 1–5 Hz / Wind: continuous content below 1–5 Hz."""
        fases = self._rng.uniform(0.0, 2.0 * np.pi, 3)
        sinal = (np.sin(2.0 * np.pi * 0.7 * t + fases[0])
                 + 0.6 * np.sin(2.0 * np.pi * 1.7 * t + fases[1])
                 + 0.4 * np.sin(2.0 * np.pi * 3.1 * t + fases[2]))
        return amplitude_ue * sinal[:, None]

    def _trafego(self, t: np.ndarray, fs: float, amplitude_ue: float = 1.0) -> np.ndarray:
        """Tráfego: 10–40 Hz com energia 50–500 Hz móvel ao longo da fibra /
        Traffic: 10–40 Hz with 50–500 Hz energy moving along the fiber."""
        f_k = float(self._rng.uniform(10.0, 40.0))
        comprimento = self.geometria.comprimento_fibra_m
        z0 = float(self._rng.uniform(0.0, comprimento))
        velocidade = float(self._rng.uniform(1.0, 5.0))
        largura = max(2.0, 0.05 * comprimento)
        centro = (z0 + velocidade * t) % comprimento
        envelope = np.exp(-0.5 * ((self.posicoes[None, :] - centro[:, None]) / largura) ** 2)
        f2 = float(self._rng.uniform(50.0, min(500.0, 0.45 * fs)))
        return amplitude_ue * (np.sin(2.0 * np.pi * f_k * t)
                               + 0.3 * np.sin(2.0 * np.pi * f2 * t))[:, None] * envelope

    def _pedestres(self, t: np.ndarray, fs: float, amplitude_ue: float = 0.8) -> np.ndarray:
        """Pedestres: rajadas periódicas 50–300 Hz / Pedestrians: periodic 50–300 Hz bursts."""
        n_t = t.shape[0]
        sinal = np.zeros((n_t, self.n_z))
        periodo = float(self._rng.uniform(5.0, 15.0))
        z_caminho = float(self._rng.uniform(0.0, self.geometria.comprimento_fibra_m))
        forma = np.exp(-0.5 * ((self.posicoes - z_caminho) / 1.0) ** 2)
        for t_k in np.arange(periodo * 0.5, t[-1], periodo):
            dur = float(self._rng.uniform(0.3, 0.8))
            amp = amplitude_ue * float(self._rng.uniform(0.5, 1.0))
            i0 = int(np.searchsorted(t, t_k))
            i1 = min(n_t, i0 + int(dur * fs) + 1)
            tt = t[i0:i1] - t_k
            if tt.size == 0:
                continue
            env = np.sin(np.pi * np.clip(tt / dur, 0.0, 1.0)) ** 2
            f_a = float(self._rng.uniform(50.0, 300.0))
            f_b = f_a + float(self._rng.uniform(20.0, 80.0))
            rajada = amp * env * (np.sin(2.0 * np.pi * f_a * tt) + 0.5 * np.sin(2.0 * np.pi * f_b * tt))
            sinal[i0:i1, :] += rajada[:, None] * forma[None, :]
        return sinal

    def _sinos(self, t: np.ndarray, fs: float, amplitude_ue: float = 5.0) -> np.ndarray:
        """Sinos: impulsos ~0.5–2 Hz fortemente filtrados / Bells: heavily filtered 0.5–2 Hz impulses."""
        n_t = t.shape[0]
        sinal = np.zeros((n_t, self.n_z))
        periodo = float(self._rng.uniform(8.0, 20.0))
        f_sino = float(self._rng.uniform(0.5, 2.0))
        amortecimento = 0.01  # filtrado: banda estreita, decaimento lento
        omega = 2.0 * np.pi * f_sino
        for t_k in np.arange(periodo * 0.3, t[-1], periodo):
            i0 = int(np.searchsorted(t, t_k))
            n_decay = min(n_t - i0, int(3.0 / (amortecimento * omega) * fs) + 1)
            if n_decay <= 0:
                continue
            tt = t[i0:i0 + n_decay] - t_k
            sinal[i0:i0 + n_decay, :] += (amplitude_ue * np.sin(omega * tt)
                                          * np.exp(-amortecimento * omega * tt))[:, None]
        return sinal

    def _adicionar_impulso_ae(self, das: np.ndarray, forma: np.ndarray, i0: int, n_t: int,
                              fs: float, f_k: float, dur_k: float, amp_k: float, fn) -> bool:
        """Sobrepõe o transiente AE via núcleo C++; True se aplicado /
        Overlays the AE transient via the C++ core; True when applied.

        Usa `mse_ae_impulse_d` (tons ortogonais em faixa estreita centrada
        em f_k, subida 5%, decaimento e^−4 e degrau residual de 10% da
        amplitude). Retorna False quando o núcleo está indisponível ou
        rejeita os parâmetros, caso em que o chamador usa o burst NumPy.
        """
        if fn is None:
            return False
        n_rem = n_t - i0
        f0 = max(0.8 * f_k, 1.0)
        f1 = min(1.25 * f_k, 0.45 * fs)
        if not (0.0 < f0 < f1 < 0.5 * fs):
            return False
        try:
            seed_ev = int(self._rng.integers(0, 2**62))
            evento = np.asarray(fn(n_rem, fs, f0, f1, dur_k, amp_k, seed_ev), dtype=float)
        except (TypeError, ValueError):
            return False
        das[i0:, :] += evento[:, None] * forma[None, :]
        return True

    def _adicionar_ringing_modal(self, das: np.ndarray, forma: np.ndarray, i0: int, n_t: int,
                                 fs: float, f_r: float, amortecimento: float,
                                 amp_k: float, fn) -> bool:
        """Sobrepõe o ringing modal via núcleo C++; True se aplicado /
        Overlays the modal ringing via the C++ core; True when applied.

        Usa `mse_modal_decay_d` (A = 2·amp_k, mesma amplitude do fallback
        NumPy). Retorna False para o ringing NumPy quando indisponível.
        """
        if fn is None:
            return False
        n_ring = min(n_t - i0, int(5.0 / (amortecimento * 2.0 * np.pi * f_r) * fs) + 1)
        if n_ring <= 0 or not (0.0 < f_r < 0.5 * fs) or not (0.0 <= amortecimento < 1.0):
            return False
        try:
            anel = np.asarray(fn(n_ring, fs, f_r, amortecimento, 2.0 * amp_k), dtype=float)
        except (TypeError, ValueError):
            return False
        das[i0:i0 + n_ring, :] += anel[:, None] * forma[None, :]
        return True

    def emissao_acustica_fissura(self, posicao_fissura_m: float, n_eventos: int = 8,
                                 faixa_hz: Tuple[float, float] = (50.0, 500.0),
                                 duracao_s: Tuple[float, float] = (0.01, 0.2),
                                 degrau_ue=100.0,
                                 amplitude_burst_ue: Tuple[float, float] = (0.5, 2.0),
                                 faixa_modal_hz: Tuple[float, float] = (1.0, 5.0),
                                 amortecimento_modal: float = 0.03,
                                 duracao_janela_s: Optional[float] = None,
                                 l_sr_m: float = L_SR_PADRAO_M, gauge_m: float = 0.5,
                                 rugosidade_das_ue: float = 0.5,
                                 incluir_ruido_ambiental: bool = False,
                                 usar_nucleo: bool = True) -> Dict:
        """Emissão acústica de fissura ativa (DAS) / Active crack acoustic emission (DAS).

        Eventos impulsivos na banda 50–500 Hz (conteúdo até 1–2 kHz), com
        subida rápida e decaimento exponencial (10–200 ms), centrados na
        posição da fissura. Cada evento deixa um degrau permanente
        quase-estático de 5–250 µε (média no gauge, largura = gauge) e
        excita o ringing modal da estrutura (torres de alvenaria: flexão
        1–5 Hz, torção ~2–2.5×f1, amortecimento 1–5%).

        Parameters
        ----------
        posicao_fissura_m : float
            Posição da fissura ao longo da fibra (m).
        n_eventos : int
            Número de eventos impulsivos na janela (taxa ativa: 1–30/h).
        faixa_hz : tuple
            Banda dominante dos eventos (Hz). Default: (50, 500).
        duracao_s : tuple
            Faixa de duração dos eventos (s). Default: (0.01, 0.2).
        degrau_ue : float ou tuple
            Degrau permanente por evento (µε). Aceita escalar ou faixa
            (5–250). Default: 100.
        faixa_modal_hz : tuple
            Faixa do ringing modal (Hz). Default: (1, 5).
        amortecimento_modal : float
            Razão de amortecimento modal (1–5%). Default: 0.03.
        duracao_janela_s : float, opcional
            Janela DAS (s). Default: `min(duracao_s, 60 s)`.
        l_sr_m, gauge_m : float
            Resolução espacial e gauge (m) do perfil do evento.
        rugosidade_das_ue : float
            Ruído de fundo DAS (µε). Default: 0.5.
        incluir_ruido_ambiental : bool
            Sobrepõe o ruído ambiental de fundo.
        usar_nucleo : bool
            Usa as formas de onda C++ quando disponíveis: `mse_ae_impulse_d`
            para o transiente banda-limitado de cada evento (faixa estreita
            centrada em f_k, degrau residual 10% da amplitude embutido) e
            `mse_modal_decay_d` para o ringing modal. Default: True; o
            fallback NumPy (senoide única + exponencial) permanece testado.

        Returns
        -------
        dict
            Dicionário canônico com 'das' (n_t, n_z) em µε.
        """
        n_t, t, fs = self._eixo_das(duracao_janela_s)
        forma = np.exp(-0.5 * ((self.posicoes - posicao_fissura_m) / l_sr_m) ** 2)
        forma = self._media_movel_gauge(forma, gauge_m)
        das = np.zeros((n_t, self.n_z))
        if incluir_ruido_ambiental:
            das = das + self.ruido_ambiental(duracao_janela_s=duracao_janela_s)["das"]
        f_min, f_max = faixa_hz
        f_max = max(f_min + 1.0, min(f_max, 0.45 * fs))
        instantes = np.sort(self._rng.uniform(0.05 * t[-1], 0.95 * t[-1], size=int(n_eventos)))
        fn_impulso = funcao_nucleo_mse("mse_ae_impulse_d") if usar_nucleo else None
        fn_modal = funcao_nucleo_mse("mse_modal_decay_d") if usar_nucleo else None
        passos = np.zeros(n_t)
        for t_k in instantes:
            f_k = float(self._rng.uniform(f_min, f_max))
            dur_k = float(self._rng.uniform(*duracao_s))
            amp_k = float(self._rng.uniform(*amplitude_burst_ue))
            i0 = int(np.searchsorted(t, t_k))
            if not self._adicionar_impulso_ae(das, forma, i0, n_t, fs, f_k, dur_k, amp_k, fn_impulso):
                i1 = min(n_t, i0 + int(3.0 * dur_k * fs) + 1)
                tt = t[i0:i1] - t_k
                tau = max(dur_k / 3.0, 1.0 / fs)
                t_rise = max(1.0 / (4.0 * f_k), 1.0 / fs)
                burst = amp_k * np.sin(2.0 * np.pi * f_k * tt) * np.exp(-tt / tau) * (1.0 - np.exp(-tt / t_rise))
                das[i0:i1, :] += burst[:, None] * forma[None, :]
            f_r = float(self._rng.uniform(*faixa_modal_hz))
            if not self._adicionar_ringing_modal(das, forma, i0, n_t, fs, f_r, amortecimento_modal, amp_k, fn_modal):
                omega_r = 2.0 * np.pi * f_r
                n_ring = min(n_t - i0, int(5.0 / (amortecimento_modal * omega_r) * fs) + 1)
                if n_ring > 0:
                    tr = t[i0:i0 + n_ring] - t_k
                    anel = (2.0 * amp_k) * np.sin(omega_r * tr) * np.exp(-amortecimento_modal * omega_r * tr)
                    das[i0:i0 + n_ring, :] += anel[:, None] * forma[None, :]
            degrau_k = float(degrau_ue) if np.isscalar(degrau_ue) else float(self._rng.uniform(*degrau_ue))
            i_degrau = min(n_t - 1, i0 + int(dur_k * fs))
            passos[i_degrau] += degrau_k
        das = das + np.cumsum(passos)[:, None] * forma[None, :]
        if rugosidade_das_ue > 0.0:
            das = das + self._rng.normal(0.0, rugosidade_das_ue, (n_t, self.n_z))
        return self._finalizar(
            dts=None, dss=None, das=das,
            signature_type=TipoAssinaturaMSE.EMISSAO_ACUSTICA_FISSURA,
            parameters={
                "posicao_fissura_m": posicao_fissura_m,
                "n_eventos": int(n_eventos),
                "faixa_hz": tuple(faixa_hz),
                "duracao_s": tuple(duracao_s),
                "degrau_ue": degrau_ue if np.isscalar(degrau_ue) else tuple(degrau_ue),
                "amortecimento_modal": amortecimento_modal,
                "l_sr_m": l_sr_m,
                "gauge_m": gauge_m,
            },
        )

    def vibracao_modal(self, f1: float = 1.5, razao_torcao: float = 2.2,
                       amortecimento: float = 0.03, amplitude_modal_ue: float = 2.0,
                       duracao_janela_s: Optional[float] = None,
                       vento: bool = True, trafego_fraco: bool = True) -> Dict:
        """Vibração modal de torre de alvenaria / Masonry-tower modal vibration.

        Fundo modal contínuo: flexão fundamental f1 (1–5 Hz) e modo de
        torção ~2–2.5×f1 com batimento lento de amplitude, mais vento
        (< 1–5 Hz contínuo) e tráfego fraco (10–40 Hz).

        Parameters
        ----------
        f1 : float
            Frequência fundamental de flexão (Hz). Default: 1.5.
        razao_torcao : float
            Razão do modo de torção sobre f1. Default: 2.2.
        amortecimento : float
            Razão de amortecimento (1–5%). Default: 0.03.
        amplitude_modal_ue : float
            Amplitude do fundo modal (µε). Default: 2.0.
        vento, trafego_fraco : bool
            Inclui os respectivos ruídos de fundo.

        Returns
        -------
        dict
            Dicionário canônico com 'das' (n_t, n_z) em µε.
        """
        n_t, t, fs = self._eixo_das(duracao_janela_s)
        das = np.zeros((n_t, self.n_z))
        fase1 = float(self._rng.uniform(0.0, 2.0 * np.pi))
        fase2 = float(self._rng.uniform(0.0, 2.0 * np.pi))
        env1 = 0.6 + 0.4 * np.sin(2.0 * np.pi * 0.07 * t + fase1)
        env2 = 0.6 + 0.4 * np.sin(2.0 * np.pi * 0.05 * t + fase2)
        resposta = amplitude_modal_ue * (env1 * np.sin(2.0 * np.pi * f1 * t)
                                         + 0.7 * env2 * np.sin(2.0 * np.pi * f1 * razao_torcao * t))
        das = das + resposta[:, None]
        if vento:
            das = das + self._vento(t)
        if trafego_fraco:
            das = das + self._trafego(t, fs, amplitude_ue=0.2)
        das = das + self._rng.normal(0.0, 0.1, (n_t, self.n_z))
        return self._finalizar(
            dts=None, dss=None, das=das,
            signature_type=TipoAssinaturaMSE.VIBRACAO_MODAL,
            parameters={
                "f1_hz": f1,
                "f_torcao_hz": f1 * razao_torcao,
                "razao_torcao": razao_torcao,
                "amortecimento": amortecimento,
                "amplitude_modal_ue": amplitude_modal_ue,
            },
        )

    def ruido_ambiental(self, trafego: bool = True, pedestres: bool = False,
                        vento: bool = True, sinos: bool = False,
                        duracao_janela_s: Optional[float] = None,
                        rugosidade_base_ue: float = 0.3) -> Dict:
        """Ruído ambiente urbano / Urban ambient noise.

        Combina os fundos característicos: tráfego (10–40 Hz + energia
        50–500 Hz móvel ao longo da fibra), pedestres (rajadas periódicas
        50–300 Hz), vento (< 1–5 Hz contínuo) e sinos (impulsos ~0.5–2 Hz
        fortemente filtrados, típicos de torres sineiras).

        Parameters
        ----------
        trafego, pedestres, vento, sinos : bool
            Componentes a incluir. Default: tráfego e vento.
        duracao_janela_s : float, opcional
            Janela DAS (s). Default: `min(duracao_s, 60 s)`.
        rugosidade_base_ue : float
            Ruído branco de fundo (µε). Default: 0.3.

        Returns
        -------
        dict
            Dicionário canônico com 'das' (n_t, n_z) em µε.
        """
        n_t, t, fs = self._eixo_das(duracao_janela_s)
        das = np.zeros((n_t, self.n_z))
        if vento:
            das = das + self._vento(t)
        if trafego:
            das = das + self._trafego(t, fs)
        if pedestres:
            das = das + self._pedestres(t, fs)
        if sinos:
            das = das + self._sinos(t, fs)
        if rugosidade_base_ue > 0.0:
            das = das + self._rng.normal(0.0, rugosidade_base_ue, (n_t, self.n_z))
        return self._finalizar(
            dts=None, dss=None, das=das,
            signature_type=TipoAssinaturaMSE.RUIDO_AMBIENTAL,
            parameters={
                "trafego": bool(trafego),
                "pedestres": bool(pedestres),
                "vento": bool(vento),
                "sinos": bool(sinos),
                "rugosidade_base_ue": rugosidade_base_ue,
            },
        )

    # ─────────────────────────────────────────────────────────
    # CENÁRIO MULTIMODAL / MULTIMODAL SCENARIO
    # ─────────────────────────────────────────────────────────

    _CHAVES_DTS = ("alpha", "amplitude_superficial_k", "incluir_anual", "janela_m",
                   "amplificacao_local", "reducao_defasagem", "rugosidade_termica_k")
    _CHAVES_DSS = ("comprimento_transferencia_m", "temperatura_ref_c", "ciclo_sazonal",
                   "amplitude_termica_fissura_k", "amplitude_termica_cabo_k",
                   "taxa_creep_ue_dia", "rugosidade_dss_ue")
    _CHAVES_DAS = ("faixa_hz", "duracao_s", "degrau_ue", "amplitude_burst_ue",
                   "faixa_modal_hz", "amortecimento_modal", "rugosidade_das_ue",
                   "incluir_ruido_ambiental")

    def cenario_fissura_multimodal(self, posicao_fissura_m: float = 50.0,
                                   abertura_mm: float = 0.4, taxa_creep_ue_dia: float = 10.0,
                                   offset_ponte_k: float = 3.0, n_eventos_das: int = 8,
                                   incluir_termico: bool = True,
                                   coef_expansao_termica: float = CTE_TIJOLO_PADRAO,
                                   duracao_janela_das_s: Optional[float] = None,
                                   **kwargs) -> Dict:
        """Cenário fissura multimodal na mesma posição / Multimodal crack scenario at the same position.

        Combina, de forma coerente e na mesma posição, as três assinaturas
        de uma fissura ativa: ponte térmica (DTS), abertura em Brillouin
        (DSS) e emissão acústica com degraus permanentes (DAS). Caso
        *showcase* do motor de inferência MSE.

        Parameters
        ----------
        posicao_fissura_m : float
            Posição comum da fissura nas três modalidades (m). Default: 50.
        abertura_mm : float
            Abertura da fissura (mm). Default: 0.4.
        taxa_creep_ue_dia : float
            Taxa de creep (µε/dia). Default: 10.
        offset_ponte_k : float
            Offset térmico persistente (K). Default: 3.
        n_eventos_das : int
            Número de eventos acústicos na janela DAS. Default: 8.
        incluir_termico : bool
            Inclui a cross-sensibilidade Brillouin em todo o traço DSS.
        coef_expansao_termica : float
            CTE do material (1/°C). Default: 5.6e-6 (tijolo).
        duracao_janela_das_s : float, opcional
            Janela DAS (s). Default: `min(duracao_s, 60 s)`.
        **kwargs
            Parâmetros extras repassados às assinaturas componentes:
            ver `_CHAVES_DTS`, `_CHAVES_DSS` e `_CHAVES_DAS`.

        Returns
        -------
        dict
            Dicionário canônico com 'dts', 'dss' e 'das' preenchidos.
        """
        params = dict(kwargs)
        comuns_z = {k: params.pop(k) for k in ("l_sr_m", "gauge_m") if k in params}
        p_dts = {k: params.pop(k) for k in list(params) if k in self._CHAVES_DTS}
        p_dss = {k: params.pop(k) for k in list(params) if k in self._CHAVES_DSS}
        p_das = {k: params.pop(k) for k in list(params) if k in self._CHAVES_DAS}
        if params:
            raise TypeError(f"parâmetros desconhecidos: {sorted(params)}")
        p_dss.update(comuns_z)
        p_das.update(comuns_z)
        res_dts = self.ponte_termica_fissura(posicao_fissura_m, offset_k=offset_ponte_k, **p_dts)
        res_dss = self.fissura_dss(posicao_fissura_m, abertura_mm=abertura_mm,
                                   taxa_creep_ue_dia=taxa_creep_ue_dia,
                                   incluir_termico=incluir_termico,
                                   coef_expansao_termica=coef_expansao_termica, **p_dss)
        res_das = self.emissao_acustica_fissura(posicao_fissura_m, n_eventos=n_eventos_das,
                                                duracao_janela_s=duracao_janela_das_s, **p_das)
        return self._finalizar(
            dts=res_dts["dts"], dss=res_dss["dss"], das=res_das["das"],
            signature_type=TipoAssinaturaMSE.CENARIO_FISSURA_MULTIMODAL,
            parameters={
                "posicao_fissura_m": posicao_fissura_m,
                "abertura_mm": abertura_mm,
                "taxa_creep_ue_dia": taxa_creep_ue_dia,
                "offset_ponte_k": offset_ponte_k,
                "n_eventos_das": int(n_eventos_das),
                "incluir_termico": incluir_termico,
                "coef_expansao_termica": coef_expansao_termica,
                "componentes": {
                    "dts": res_dts["parameters"],
                    "dss": res_dss["parameters"],
                    "das": res_das["parameters"],
                },
            },
        )
