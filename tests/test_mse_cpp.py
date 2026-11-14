"""
Testes do núcleo C++20 do módulo MSE — Monitoramento da Saúde Estrutural.

Cobrem:
  - Importação das funções mse_* do alakoro_core
  - Tabela de materiais (MaterialTraits) e penetração térmica δ = sqrt(2α/ω)
  - Onda térmica harmônica (Ångström): amplitude exp(−x/δ) e fase x/(δω)
  - Perfil de deformação por fissura com média-móvel de gauge
  - Impulso AE banda-limitado com degrau permanente (determinismo por seed)
  - Decaimento modal amortecido (ringing 1–5 Hz de torres de alvenaria)
"""

import numpy as np
import pytest

try:
    import alakoro_core
    from alakoro_core import (
        mse_ae_impulse_d,
        mse_crack_strain_profile_d,
        mse_material_traits_d,
        mse_modal_decay_d,
        mse_thermal_wave_d,
    )

    _MSE_AVAILABLE = True
except Exception:
    _MSE_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _MSE_AVAILABLE,
    reason="alakoro_core extension without MSE bindings not available",
)


def test_mse_functions_exist():
    """As cinco funções mse_* e o enum MaterialAlvenaria devem existir."""
    assert hasattr(alakoro_core, "MaterialAlvenaria")
    for nome in (
        "mse_thermal_wave_d",
        "mse_crack_strain_profile_d",
        "mse_ae_impulse_d",
        "mse_modal_decay_d",
        "mse_material_traits_d",
    ):
        assert callable(getattr(alakoro_core, nome)), nome


def test_material_traits_tijolo():
    """Tijolo: difusividade 5e-7, dilatação 5.6e-6, δ diário ≈ 0.117 m."""
    difusividade, dilatacao, pen_diaria, pen_anual = mse_material_traits_d("tijolo")

    assert difusividade == pytest.approx(5.0e-7, rel=1e-12)
    assert dilatacao == pytest.approx(5.6e-6, rel=1e-12)
    assert pen_diaria == pytest.approx(0.117, rel=0.01)
    assert pen_anual == pytest.approx(2.24, rel=0.01)


def test_material_traits_all_materials():
    """Todos os materiais válidos retornam traits coerentes; inválido lança."""
    esperados = {
        "tijolo": (5.0e-7, 5.6e-6),
        "pedra": (1.2e-6, 6.5e-6),
        "argamassa": (3.0e-7, 4.5e-6),
        "concreto": (5.0e-6, 1.0e-5),
    }
    for nome, (dif_esperada, dil_esperada) in esperados.items():
        difusividade, dilatacao, pen_diaria, pen_anual = mse_material_traits_d(nome)
        assert difusividade == pytest.approx(dif_esperada, rel=1e-12)
        assert dilatacao == pytest.approx(dil_esperada, rel=1e-12)
        assert pen_diaria > 0.0
        assert pen_anual > pen_diaria  # ciclo anual penetra mais

    with pytest.raises(ValueError):
        mse_material_traits_d("cobre")


def test_thermal_wave_matches_analytic_solution():
    """Amplitude exp(−x/δ) e defasagem temporal 1/ω da solução analítica."""
    periodo = 86400.0  # ciclo diário [s]
    omega = 2.0 * np.pi / periodo
    delta = 0.11726  # penetração diária do tijolo [m]

    profundidades = np.array([0.0, delta, 2.0 * delta])
    n_por_periodo = 1440  # dt = 60 s
    n_t = 2 * n_por_periodo
    dt = periodo / n_por_periodo
    tempos = np.arange(n_t) * dt
    a0 = 5.0
    amplitudes = np.full(n_t, a0)

    saida = mse_thermal_wave_d(
        "tijolo", profundidades, tempos, amplitudes, periodo, False
    )
    assert saida.shape == (n_t, 3)
    assert np.all(np.isfinite(saida))

    # Amplitude: A(x) = A0 * exp(-x/delta)
    fatores = [1.0, np.exp(-1.0), np.exp(-2.0)]
    for z, fator in enumerate(fatores):
        sinal = saida[:, z]
        amplitude_medida = (sinal.max() - sinal.min()) / 2.0
        assert amplitude_medida == pytest.approx(a0 * fator, rel=0.02)

    # Fase: primeiro máximo em x=0 ocorre em t=0 (cos com fase zero)
    assert int(np.argmax(saida[:, 0])) == 0

    # Defasagem temporal entre x=0 e x=δ: máximo em t = 1/omega
    s1 = saida[:, 1]
    t_max = tempos[int(np.argmax(s1[:n_por_periodo]))]
    assert abs(t_max - 1.0 / omega) <= 2.0 * dt


def test_thermal_wave_incluir_anual():
    """O harmônico anual deve alterar o sinal e permanecer finito."""
    periodo = 86400.0
    profundidades = np.array([0.0, 0.11726])
    n_t = 1440
    tempos = np.arange(n_t) * 60.0
    amplitudes = np.full(n_t, 5.0)

    so_diario = mse_thermal_wave_d(
        "tijolo", profundidades, tempos, amplitudes, periodo, False
    )
    com_anual = mse_thermal_wave_d(
        "tijolo", profundidades, tempos, amplitudes, periodo, True
    )

    assert com_anual.shape == so_diario.shape
    assert np.all(np.isfinite(com_anual))
    assert not np.allclose(com_anual, so_diario)


def test_crack_strain_profile_peak_and_width():
    """Pico ε ≈ w/L_t no centro da fissura e suporte ≈ 2×SR (gauge L_t = SR)."""
    sr = 0.05  # resolução espacial [m]
    lt = 0.05  # comprimento de transferência [m] → janela de 1 amostra
    posicoes = np.linspace(0.0, 2.0, 201)  # dx = 0.01 m
    w_mm = 0.2

    perfil = mse_crack_strain_profile_d(
        posicoes, np.array([1.0]), np.array([w_mm]), lt, sr
    )

    i_max = int(np.argmax(perfil))
    assert posicoes[i_max] == pytest.approx(1.0)
    assert perfil[i_max] == pytest.approx((w_mm * 1e-3) / lt, rel=1e-9)

    # Suporte da triangular: |x - centro| < SR → largura ≈ 2*SR
    suporte = posicoes[perfil != 0.0]
    largura = suporte.max() - suporte.min()
    assert largura <= 2.0 * sr + 2.0 * (posicoes[1] - posicoes[0])


def test_crack_strain_profile_gauge_averaging():
    """Gauge maior (L_t = 4×SR) suaviza o pico e alarga o suporte."""
    sr = 0.05
    posicoes = np.linspace(0.0, 2.0, 201)
    args = (posicoes, np.array([1.0]), np.array([0.2]))

    fino = mse_crack_strain_profile_d(*args, sr, sr)  # janela = 1 amostra
    largo = mse_crack_strain_profile_d(*args, 4.0 * sr, sr)  # janela = 4 amostras

    assert abs(largo).max() < abs(fino).max()

    suporte_fino = posicoes[fino != 0.0]
    suporte_largo = posicoes[largo != 0.0]
    assert (suporte_largo.max() - suporte_largo.min()) > (
        suporte_fino.max() - suporte_fino.min()
    )


def test_ae_impulse_determinism():
    """Mesma seed deve gerar sinais idênticos."""
    params = (8192, 10000.0, 50.0, 500.0, 0.05, 1000.0, 42)
    sig1 = mse_ae_impulse_d(*params)
    sig2 = mse_ae_impulse_d(*params)
    assert np.array_equal(sig1, sig2)


def test_ae_impulse_energy_in_band_and_permanent_step():
    """Energia do evento concentrada em 50–500 Hz + degrau residual positivo."""
    n, fs = 8192, 10000.0
    f0, f1 = 50.0, 500.0
    duracao = 0.05
    amplitude = 1000.0
    sig = mse_ae_impulse_d(n, fs, f0, f1, duracao, amplitude, seed=42)

    assert sig.shape == (n,)

    # Espectro do trecho do evento: energia na faixa vs. banda larga (sem DC)
    n_evento = int(round(duracao * fs))
    espectro = np.abs(np.fft.rfft(sig[:n_evento]))
    freqs = np.fft.rfftfreq(n_evento, d=1.0 / fs)
    energia_faixa = espectro[(freqs >= f0) & (freqs <= f1)].sum()
    energia_total = espectro[(freqs >= 20.0) & (freqs <= 0.5 * fs)].sum()
    assert energia_faixa / energia_total > 0.8

    # Degrau permanente após o evento: 0.1 * amplitude_ue, positivo
    cauda = sig[int(0.06 * fs):]
    assert np.allclose(cauda, 0.1 * amplitude, rtol=1e-12)
    assert np.all(cauda > 0.0)


def test_modal_decay_envelope_and_frequency():
    """Envelope exp(−ζω_n t), amplitude inicial A e frequência ~2 Hz."""
    n, fs = 5000, 100.0
    f_n, zeta, amp = 2.0, 0.05, 1.0
    x = mse_modal_decay_d(n, fs, f_n, zeta, amp)

    assert x.shape == (n,)
    assert x[0] == pytest.approx(amp)

    t = np.arange(n) / fs
    envelope = amp * np.exp(-zeta * 2.0 * np.pi * f_n * t)
    assert np.all(np.abs(x) <= envelope * 1.001 + 1e-12)

    # Cruzamentos por zero ≈ 2 * f * T (frequência amortecida ~f_n)
    cruzamentos = int(np.count_nonzero(np.diff(np.sign(x)) != 0))
    esperado = 2.0 * f_n * (n / fs)
    assert abs(cruzamentos - esperado) <= 10
