"""
Alakoro FiberSense — Testes das Assinaturas MSE
MSE Signature Tests
"""

import numpy as np
import pytest

from alakoro.mse import (
    ConfigAquisicaoMSE,
    GeometriaEstrutura,
    GeradorAssinaturasMSE,
    MotorInferenciaMSE,
    TipoAssinaturaMSE,
    TrechoExposicao,
    amplitude_analitica_k,
    defasagem_s,
    delta_penetracao_m,
)
from alakoro.mse.signatures import OMEGA_DIURNO_RAD_S


@pytest.fixture
def geometria():
    return GeometriaEstrutura(
        comprimento_fibra_m=100.0,
        trechos=[TrechoExposicao(0.0, 50.0, 1.0), TrechoExposicao(50.0, 100.0, 0.3)],
    )


@pytest.fixture
def acq():
    return ConfigAquisicaoMSE(n_posicoes=200, passo_espacial_m=0.5, duracao_s=86400.0, fs_das_hz=1000.0)


@pytest.fixture
def gerador(geometria, acq):
    return GeradorAssinaturasMSE(geometria, acq, seed=42)


class TestShapes:
    def test_difusao_termica_shape(self, gerador, acq):
        res = gerador.difusao_termica_parede()
        assert res["dts"].shape == (acq.n_amostras_dts, acq.n_posicoes)
        assert res["dss"] is None and res["das"] is None
        assert res["signature_type"] is TipoAssinaturaMSE.DIFUSAO_TERMICA_PAREDE
        assert isinstance(res["parameters"], dict) and res["parameters"]["alpha_m2_s"] == 5e-7

    def test_ponte_termica_shape(self, gerador, acq):
        res = gerador.ponte_termica_fissura(50.0)
        assert res["dts"].shape == (acq.n_amostras_dts, acq.n_posicoes)
        assert res["signature_type"] is TipoAssinaturaMSE.PONTE_TERMICA_FISSURA

    def test_fissura_dss_shape(self, gerador, acq):
        res = gerador.fissura_dss(25.0)
        assert res["dss"].shape == (acq.n_amostras_dss, acq.n_posicoes)
        assert res["dts"] is None and res["das"] is None
        assert res["signature_type"] is TipoAssinaturaMSE.FISSURA_DSS

    def test_recalque_shape(self, gerador, acq):
        res = gerador.recalque_diferencial()
        assert res["dss"].shape == (acq.n_amostras_dss, acq.n_posicoes)
        assert res["signature_type"] is TipoAssinaturaMSE.RECALQUE_DIFERENCIAL

    def test_emissao_acustica_shape(self, gerador, acq):
        res = gerador.emissao_acustica_fissura(40.0, duracao_janela_s=5.0)
        assert res["das"].shape == (int(5.0 * acq.fs_das_hz), acq.n_posicoes)
        assert res["dts"] is None and res["dss"] is None
        assert res["signature_type"] is TipoAssinaturaMSE.EMISSAO_ACUSTICA_FISSURA

    def test_vibracao_modal_shape(self, gerador, acq):
        res = gerador.vibracao_modal(duracao_janela_s=2.0)
        assert res["das"].shape == (int(2.0 * acq.fs_das_hz), acq.n_posicoes)
        assert res["signature_type"] is TipoAssinaturaMSE.VIBRACAO_MODAL

    def test_ruido_ambiental_shape(self, gerador, acq):
        res = gerador.ruido_ambiental(pedestres=True, sinos=True, duracao_janela_s=2.0)
        assert res["das"].shape == (int(2.0 * acq.fs_das_hz), acq.n_posicoes)
        assert res["signature_type"] is TipoAssinaturaMSE.RUIDO_AMBIENTAL

    def test_cenario_multimodal_shape(self, gerador, acq):
        res = gerador.cenario_fissura_multimodal(50.0, duracao_janela_das_s=2.0)
        assert res["dts"].shape == (acq.n_amostras_dts, acq.n_posicoes)
        assert res["dss"].shape == (acq.n_amostras_dss, acq.n_posicoes)
        assert res["das"].shape == (int(2.0 * acq.fs_das_hz), acq.n_posicoes)
        assert res["signature_type"] is TipoAssinaturaMSE.CENARIO_FISSURA_MULTIMODAL


class TestDeterminismo:
    def test_mesma_seed_arrays_iguais(self, geometria, acq):
        g1 = GeradorAssinaturasMSE(geometria, acq, seed=42)
        g2 = GeradorAssinaturasMSE(geometria, acq, seed=42)
        assert np.allclose(g1.difusao_termica_parede()["dts"], g2.difusao_termica_parede()["dts"])
        assert np.allclose(g1.fissura_dss(25.0)["dss"], g2.fissura_dss(25.0)["dss"])
        assert np.allclose(
            g1.emissao_acustica_fissura(40.0, duracao_janela_s=5.0)["das"],
            g2.emissao_acustica_fissura(40.0, duracao_janela_s=5.0)["das"],
        )

    def test_seed_diferente_arrays_diferentes(self, geometria, acq):
        g1 = GeradorAssinaturasMSE(geometria, acq, seed=1)
        g2 = GeradorAssinaturasMSE(geometria, acq, seed=2)
        assert not np.allclose(g1.fissura_dss(25.0)["dss"], g2.fissura_dss(25.0)["dss"])


class TestPonteTermica:
    def test_offset_persistent_localizado(self, gerador):
        res = gerador.ponte_termica_fissura(50.0, offset_k=3.0)
        dts = res["dts"]
        media = dts.mean(axis=0)
        idx_fissura = int(np.argmin(np.abs(gerador.posicoes - 50.0)))
        idx_longe = int(np.argmin(np.abs(gerador.posicoes - 20.0)))
        assert abs(media[idx_fissura] - 23.0) < 0.3
        assert abs(media[idx_longe] - 20.0) < 0.3

    def test_resposta_local_maior_amplitude(self, gerador):
        res = gerador.ponte_termica_fissura(40.0, offset_k=0.0, amplificacao_local=3.0)
        amplitude_local = np.ptp(res["dts"][:, np.argmin(np.abs(gerador.posicoes - 40.0))])
        amplitude_longe = np.ptp(res["dts"][:, np.argmin(np.abs(gerador.posicoes - 20.0))])
        assert amplitude_local > 1.5 * amplitude_longe


class TestFissuraDSS:
    def test_pico_na_posicao_da_fissura(self, gerador):
        res = gerador.fissura_dss(25.0, abertura_mm=0.4, incluir_termico=False, rugosidade_dss_ue=2.0)
        dss = res["dss"]
        assert float(dss.max()) > 3500.0
        proeminencia = np.max(np.abs(dss - np.median(dss, axis=0)), axis=0)
        idx_pico = int(np.argmax(proeminencia))
        assert abs(gerador.posicoes[idx_pico] - 25.0) < 2.0

    def test_pico_escala_com_abertura(self, gerador):
        # ε ≈ w/L_t: 0.4 mm / 0.1 m = 4000 µε (isolando creep e ciclo térmico)
        res = gerador.fissura_dss(25.0, abertura_mm=0.4, incluir_termico=False, rugosidade_dss_ue=0.0,
                                  taxa_creep_ue_dia=0.0, amplitude_termica_fissura_k=0.0)
        assert res["parameters"]["pico_ue"] == pytest.approx(4000.0)
        assert float(res["dss"].max()) == pytest.approx(4000.0, rel=1e-2)

    def test_creep_crescente(self, gerador):
        res = gerador.fissura_dss(25.0, incluir_termico=False, rugosidade_dss_ue=0.0)
        dss = res["dss"]
        idx = int(np.argmin(np.abs(gerador.posicoes - 25.0)))
        assert dss[-1, idx] > dss[0, idx]  # creep acumula ao longo do dia


class TestDifusaoTermicaAnalitica:
    """Teste da solução analítica: A(x) = A₀·e^(−x/δ), Δt(x) = x/(δ·ω)."""

    @pytest.fixture
    def gerador_profundidade(self):
        n_z = 200
        geometria = GeometriaEstrutura(
            comprimento_fibra_m=100.0,
            profundidade_posicoes=np.linspace(0.0, 0.25, n_z),
        )
        acq = ConfigAquisicaoMSE(n_posicoes=n_z, passo_espacial_m=0.5, duracao_s=86400.0)
        return GeradorAssinaturasMSE(geometria, acq, seed=42)

    def test_amplitude_decai_com_profundidade(self, gerador_profundidade):
        alpha, a0 = 5e-7, 20.0
        dts = gerador_profundidade.difusao_termica_parede(alpha=alpha, amplitude_superficial_k=a0,
                                                          rugosidade_termica_k=0.05)["dts"]
        n_t = dts.shape[0]
        t = np.arange(n_t) * 60.0
        proj_sin = 2.0 / n_t * (dts * np.sin(OMEGA_DIURNO_RAD_S * t)[:, None]).sum(axis=0)
        proj_cos = 2.0 / n_t * (dts * np.cos(OMEGA_DIURNO_RAD_S * t)[:, None]).sum(axis=0)
        amp_estimada = np.hypot(proj_sin, proj_cos)
        profundidades = gerador_profundidade.geometria.profundidade_posicoes
        amp_esperada = amplitude_analitica_k(profundidades, alpha, a0)
        assert np.allclose(amp_estimada, amp_esperada, rtol=0.05)

    def test_defasagem_cresce_com_profundidade(self, gerador_profundidade):
        alpha = 5e-7
        dts = gerador_profundidade.difusao_termica_parede(alpha=alpha, rugosidade_termica_k=0.05)["dts"]
        n_t = dts.shape[0]
        t = np.arange(n_t) * 60.0
        proj_sin = 2.0 / n_t * (dts * np.sin(OMEGA_DIURNO_RAD_S * t)[:, None]).sum(axis=0)
        proj_cos = 2.0 / n_t * (dts * np.cos(OMEGA_DIURNO_RAD_S * t)[:, None]).sum(axis=0)
        fase = np.arctan2(proj_cos, proj_sin)  # campo = A·sin(ωt − x/δ) → φ = −x/δ
        defasagem_estimada_s = -fase / OMEGA_DIURNO_RAD_S
        profundidades = gerador_profundidade.geometria.profundidade_posicoes
        # atol absorve o erro de fase do ruído térmico onde a defasagem é ~0
        assert np.allclose(defasagem_estimada_s, defasagem_s(profundidades, alpha), rtol=0.05, atol=90.0)
        assert defasagem_estimada_s[-1] > defasagem_estimada_s[0] > 0.0

    def test_delta_penetracao_literatura(self):
        assert delta_penetracao_m(5e-7) == pytest.approx(0.117, abs=0.001)
        omega_anual = OMEGA_DIURNO_RAD_S / 365.25
        assert delta_penetracao_m(5e-7, omega_anual) == pytest.approx(2.24, abs=0.01)


class TestEmissaoAcustica:
    def test_degrau_permanente_cumulativo(self, gerador):
        n_eventos, degrau = 6, 50.0
        res = gerador.emissao_acustica_fissura(40.0, n_eventos=n_eventos, degrau_ue=degrau,
                                               duracao_s=(0.01, 0.05), duracao_janela_s=10.0,
                                               rugosidade_das_ue=0.1)
        das = res["das"]
        idx = int(np.argmin(np.abs(gerador.posicoes - 40.0)))
        assert abs(das[0, idx]) < 5.0
        degrau_total = das[-1, idx] - das[0, idx]
        assert degrau_total > n_eventos * degrau * 0.8  # ~300 µε acumulados

    def test_eventos_impulsivos_banda(self, gerador):
        res = gerador.emissao_acustica_fissura(40.0, n_eventos=4, duracao_janela_s=5.0,
                                               faixa_hz=(100.0, 200.0))
        idx = int(np.argmin(np.abs(gerador.posicoes - 40.0)))
        traco = res["das"][:, idx]
        assert np.max(np.abs(traco)) > 1.0  # bursts acima do ruído


class TestCenarioMultimodal:
    def test_coerencia_de_posicao_entre_modalidades(self, gerador):
        pos = 50.0
        res = gerador.cenario_fissura_multimodal(pos, n_eventos_das=4, degrau_ue=80.0, duracao_janela_das_s=5.0)
        idx_dts = int(np.argmax(res["dts"].mean(axis=0) - np.median(res["dts"].mean(axis=0))))
        residuo_dss = res["dss"] - np.median(res["dss"], axis=0)
        idx_dss = int(np.argmax(np.max(np.abs(residuo_dss), axis=0)))
        idx_das = int(np.argmax(res["das"][-1]))
        for idx in (idx_dts, idx_dss, idx_das):
            assert abs(gerador.posicoes[idx] - pos) < 2.0

    def test_parametros_componentes(self, gerador):
        res = gerador.cenario_fissura_multimodal(50.0, duracao_janela_das_s=2.0)
        assert res["parameters"]["posicao_fissura_m"] == 50.0
        assert "componentes" in res["parameters"]
        assert res["parameters"]["componentes"]["dts"]["offset_k"] == 3.0

    def test_parametro_desconhecido_rejeitado(self, gerador):
        with pytest.raises(TypeError):
            gerador.cenario_fissura_multimodal(50.0, parametro_fantasia=1.0)


# ─────────────────────────────────────────────────────────
# INTEGRAÇÃO COM O NÚCLEO C++ / C++ CORE INTEGRATION
# ─────────────────────────────────────────────────────────

from alakoro.mse.signatures import NUCLEO_CPP_ATIVO, material_para_alpha  # noqa: E402


@pytest.fixture
def gerador_fino():
    """Grade espacial fina (passo 0.1 m ≤ L_SR/4) — núcleo C++ do perfil de fissura ativo."""
    n_z = 1001
    geometria = GeometriaEstrutura(comprimento_fibra_m=100.0)
    acq = ConfigAquisicaoMSE(n_posicoes=n_z, passo_espacial_m=0.1, duracao_s=86400.0)
    return GeradorAssinaturasMSE(geometria, acq, seed=1)


@pytest.mark.skipif(not NUCLEO_CPP_ATIVO, reason="alakoro_core sem funções mse_*")
class TestNucleoCpp:
    """Concordância física NumPy↔C++ e invariantes analíticos com o núcleo ativo."""

    @pytest.fixture
    def gerador_profundidade(self):
        n_z = 200
        geometria = GeometriaEstrutura(
            comprimento_fibra_m=100.0,
            profundidade_posicoes=np.linspace(0.0, 0.25, n_z),
        )
        acq = ConfigAquisicaoMSE(n_posicoes=n_z, passo_espacial_m=0.5, duracao_s=86400.0)
        return GeradorAssinaturasMSE(geometria, acq, seed=42)

    # ── Disponibilidade / seleção de material ──

    def test_nucleo_ativo_e_selecao_de_material(self):
        assert NUCLEO_CPP_ATIVO
        assert material_para_alpha(5.0e-7) == "tijolo"    # α default (Owczarek 2021)
        assert material_para_alpha(1.2e-6) == "pedra"
        assert material_para_alpha(3.0e-7) == "argamassa"
        assert material_para_alpha(4.0e-7) is None        # fora da tabela → fallback NumPy

    # ── Térmico (DTS): invariantes analíticas + concordância NumPy↔C++ ──

    @staticmethod
    def _projecao_harmonica(dts):
        n_t = dts.shape[0]
        t = np.arange(n_t) * 60.0
        proj_sin = 2.0 / n_t * (dts * np.sin(OMEGA_DIURNO_RAD_S * t)[:, None]).sum(axis=0)
        proj_cos = 2.0 / n_t * (dts * np.cos(OMEGA_DIURNO_RAD_S * t)[:, None]).sum(axis=0)
        return np.hypot(proj_sin, proj_cos)

    def test_difusao_cpp_mantem_amplitude_analitica(self, gerador_profundidade):
        alpha, a0 = 5e-7, 20.0
        dts = gerador_profundidade.difusao_termica_parede(
            alpha=alpha, amplitude_superficial_k=a0, rugosidade_termica_k=0.05)["dts"]
        amp_estimada = self._projecao_harmonica(dts)
        profundidades = gerador_profundidade.geometria.profundidade_posicoes
        amp_esperada = amplitude_analitica_k(profundidades, alpha, a0)
        assert np.allclose(amp_estimada, amp_esperada, rtol=0.05)

    def test_difusao_cpp_mantem_defasagem_analitica(self, gerador_profundidade):
        alpha = 5e-7
        dts = gerador_profundidade.difusao_termica_parede(alpha=alpha, rugosidade_termica_k=0.05)["dts"]
        n_t = dts.shape[0]
        t = np.arange(n_t) * 60.0
        proj_sin = 2.0 / n_t * (dts * np.sin(OMEGA_DIURNO_RAD_S * t)[:, None]).sum(axis=0)
        proj_cos = 2.0 / n_t * (dts * np.cos(OMEGA_DIURNO_RAD_S * t)[:, None]).sum(axis=0)
        fase = np.arctan2(proj_cos, proj_sin)
        defasagem_estimada_s = -fase / OMEGA_DIURNO_RAD_S
        profundidades = gerador_profundidade.geometria.profundidade_posicoes
        assert np.allclose(defasagem_estimada_s, defasagem_s(profundidades, alpha), rtol=0.05, atol=90.0)
        assert defasagem_estimada_s[-1] > defasagem_estimada_s[0] > 0.0

    @pytest.mark.parametrize("incluir_anual", [False, True])
    def test_comparacao_termica_numpy_vs_cpp(self, gerador_profundidade, incluir_anual):
        """Mesma frequência dominante ±5% e mesma amplitude por posição ±10%."""
        kwargs = dict(alpha=5e-7, amplitude_superficial_k=20.0, incluir_anual=incluir_anual,
                      rugosidade_termica_k=0.0)
        d_cpp = gerador_profundidade.difusao_termica_parede(**kwargs)["dts"]
        d_np = gerador_profundidade.difusao_termica_parede(usar_nucleo=False, **kwargs)["dts"]
        fs = 1.0 / 60.0

        def freq_dominante(traco):
            j = int(np.argmax(np.abs(np.fft.rfft(traco - traco.mean()))[1:]) + 1)
            return np.fft.rfftfreq(traco.size, d=1.0 / fs)[j]

        f_cpp, f_np = freq_dominante(d_cpp.mean(axis=1)), freq_dominante(d_np.mean(axis=1))
        assert abs(f_cpp - f_np) <= 0.05 * f_np
        amp_cpp = 0.5 * np.ptp(d_cpp, axis=0)
        amp_np = 0.5 * np.ptp(d_np, axis=0)
        np.testing.assert_allclose(amp_cpp, amp_np, rtol=0.1)
        assert int(np.argmax(amp_cpp)) == int(np.argmax(amp_np))  # mesmo pico espacial

    def test_alpha_fora_da_tabela_cai_no_numpy(self, gerador_profundidade):
        """α sem material correspondente: caminho NumPy (resultado idêntico ao forçado)."""
        kwargs = dict(alpha=4.0e-7, amplitude_superficial_k=20.0, rugosidade_termica_k=0.0)
        d_auto = gerador_profundidade.difusao_termica_parede(**kwargs)["dts"]
        d_np = gerador_profundidade.difusao_termica_parede(usar_nucleo=False, **kwargs)["dts"]
        np.testing.assert_allclose(d_auto, d_np, rtol=1e-9)

    # ── Fissura (DSS): perfil espacial C++ em grade fina ──

    def test_fissura_dss_cpp_vs_numpy(self, gerador_fino):
        kwargs = dict(posicao_fissura_m=50.0, abertura_mm=0.4, taxa_creep_ue_dia=0.0,
                      incluir_termico=False, rugosidade_dss_ue=0.0,
                      amplitude_termica_fissura_k=0.0, gauge_m=0.0)
        res_cpp = gerador_fino.fissura_dss(**kwargs)               # mse_crack_strain_profile_d
        res_np = gerador_fino.fissura_dss(usar_nucleo=False, **kwargs)
        for res in (res_cpp, res_np):
            linha0 = res["dss"][0]                                # perfil espacial puro (t = 0)
            assert float(linha0.max()) == pytest.approx(4000.0, rel=0.1)  # pico w/L_t (Glisic & Inaudi)
            idx = int(np.argmax(linha0))
            assert abs(gerador_fino.posicoes[idx] - 50.0) < 0.2
        idx_cpp = int(np.argmax(res_cpp["dss"][0]))
        idx_np = int(np.argmax(res_np["dss"][0]))
        assert abs(idx_cpp - idx_np) <= 1                          # mesma posição de pico (±1 amostra)
        np.testing.assert_allclose(res_cpp["dss"][0, idx_cpp], res_np["dss"][0, idx_np], rtol=0.1)

    def test_fissura_dss_grade_coarse_mantem_gaussiano(self, gerador):
        """Passo > L_SR/4: triângulo C++ subestimaria o pico → fallback NumPy (testes analíticos)."""
        res = gerador.fissura_dss(25.0, abertura_mm=0.4, taxa_creep_ue_dia=0.0,
                                  incluir_termico=False, rugosidade_dss_ue=0.0,
                                  amplitude_termica_fissura_k=0.0)
        assert float(res["dss"].max()) == pytest.approx(4000.0, rel=1e-2)

    # ── Emissão acústica (DAS): determinismo e concordância física ──

    def test_emissao_cpp_deterministica(self, geometria, acq):
        g1 = GeradorAssinaturasMSE(geometria, acq, seed=42)
        g2 = GeradorAssinaturasMSE(geometria, acq, seed=42)
        das1 = g1.emissao_acustica_fissura(40.0, n_eventos=5, duracao_janela_s=5.0,
                                           faixa_hz=(100.0, 300.0))["das"]
        das2 = g2.emissao_acustica_fissura(40.0, n_eventos=5, duracao_janela_s=5.0,
                                           faixa_hz=(100.0, 300.0))["das"]
        np.testing.assert_array_equal(das1, das2)

    def test_emissao_cpp_concordancia_fisica_com_numpy(self, geometria, acq):
        """Mesma seed/parâmetros: C++ e NumPy satisfazem os mesmos invariantes
        físicos — bursts acima do ruído, degrau cumulativo e detecção pelo
        motor de inferência na posição da fissura."""
        detectados = {}
        for nucleo in (True, False):
            gerador = GeradorAssinaturasMSE(geometria, acq, seed=42)
            das = gerador.emissao_acustica_fissura(
                40.0, n_eventos=8, duracao_janela_s=20.0, faixa_hz=(100.0, 300.0),
                rugosidade_das_ue=0.1, usar_nucleo=nucleo)["das"]
            idx = int(np.argmin(np.abs(gerador.posicoes - 40.0)))
            traco = das[:, idx]
            assert np.all(np.isfinite(das))
            assert float(np.abs(traco).max()) > 1.0                      # bursts acima do ruído
            assert das[-1, idx] - das[0, idx] > 0.5 * 8 * 100.0          # degraus acumulados
            motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
            eventos = [e for e in motor.inferir(das=das, fs_das_hz=acq.fs_das_hz)
                       if type(e).__name__ == "EventoAcusticoFissura"]
            assert len(eventos) >= 1
            assert abs(eventos[0].posicao_m - 40.0) < 3.0                # mesma posição de pico
            detectados[nucleo] = eventos[0]
        assert abs(detectados[True].posicao_m - detectados[False].posicao_m) < 3.0

    # ── Cenário multimodal: invariantes com o núcleo ativo ──

    def test_cenario_multimodal_cpp_mantem_invariantes(self, gerador):
        pos = 50.0
        res = gerador.cenario_fissura_multimodal(pos, n_eventos_das=4, degrau_ue=80.0,
                                                 duracao_janela_das_s=5.0)
        idx_dts = int(np.argmax(res["dts"].mean(axis=0) - np.median(res["dts"].mean(axis=0))))
        residuo_dss = res["dss"] - np.median(res["dss"], axis=0)
        idx_dss = int(np.argmax(np.max(np.abs(residuo_dss), axis=0)))
        idx_das = int(np.argmax(res["das"][-1]))
        for idx in (idx_dts, idx_dss, idx_das):
            assert abs(gerador.posicoes[idx] - pos) < 2.0
        assert float(res["dss"].max()) > 3500.0        # pico Brillouin 3500–5000 µε

    def test_cenario_multimodal_cpp_amplitude_termica_analitica(self):
        n_z = 200
        geometria = GeometriaEstrutura(
            comprimento_fibra_m=100.0,
            trechos=[TrechoExposicao(0.0, 100.0, 1.0)],
            profundidade_posicoes=np.linspace(0.0, 0.25, n_z),
        )
        acq = ConfigAquisicaoMSE(n_posicoes=n_z, passo_espacial_m=0.5, duracao_s=86400.0)
        gerador = GeradorAssinaturasMSE(geometria, acq, seed=42)
        res = gerador.cenario_fissura_multimodal(50.0, n_eventos_das=3, duracao_janela_das_s=2.0)
        amp = self._projecao_harmonica(res["dts"])
        esperada = amplitude_analitica_k(np.linspace(0.0, 0.25, n_z), 5e-7, 20.0)
        fora_da_fissura = np.abs(gerador.posicoes - 50.0) > 5.0
        assert np.allclose(amp[fora_da_fissura], esperada[fora_da_fissura], rtol=0.1)
