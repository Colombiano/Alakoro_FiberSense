"""
Alakoro FiberSense — Testes do Motor de Inferência MSE
MSE Inference Engine Tests
"""

import numpy as np
import pytest

from alakoro.mse import (
    ConfigAquisicaoMSE,
    GeometriaEstrutura,
    GeradorAssinaturasMSE,
    MotorInferenciaMSE,
)
from alakoro.mse.signatures import OMEGA_DIURNO_RAD_S
from alakoro.ontology import (
    AberturaFissuraTermicaEvento,
    AnomaliaTermicaEvento,
    DanoModalEvento,
    EventoAcusticoFissura,
    PropagacaoFissuraEvento,
    RecalqueEvento,
)


@pytest.fixture
def geometria():
    return GeometriaEstrutura(comprimento_fibra_m=100.0)


@pytest.fixture
def acq():
    return ConfigAquisicaoMSE(n_posicoes=200, passo_espacial_m=0.5, duracao_s=86400.0, fs_das_hz=1000.0)


class TestInferenciaMultimodal:
    def test_eventos_esperados_nas_posicoes_da_fissura(self, geometria, acq):
        gerador = GeradorAssinaturasMSE(geometria, acq, seed=7)
        pos_fissura = 25.0
        res = gerador.cenario_fissura_multimodal(
            posicao_fissura_m=pos_fissura,
            abertura_mm=0.8,
            taxa_creep_ue_dia=50.0,
            offset_ponte_k=4.0,
            n_eventos_das=6,
            degrau_ue=200.0,
            duracao_janela_das_s=20.0,
            rugosidade_dss_ue=3.0,
            amplitude_termica_fissura_k=20.0,
        )
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        eventos = motor.inferir(dts=res["dts"], dss=res["dss"], das=res["das"], fs_das_hz=1000.0)

        propagacoes = [e for e in eventos if isinstance(e, PropagacaoFissuraEvento)]
        acusticos = [e for e in eventos if isinstance(e, EventoAcusticoFissura)]
        anomalias = [e for e in eventos if isinstance(e, AnomaliaTermicaEvento)]

        assert propagacoes, "esperado ao menos um PropagacaoFissuraEvento"
        assert acusticos, "esperado ao menos um EventoAcusticoFissura"
        assert anomalias, "esperado ao menos um AnomaliaTermicaEvento"

        assert abs(propagacoes[0].posicao_fissura_m - pos_fissura) < 2.0
        assert propagacoes[0].abertura_ue > 100.0
        assert abs(acusticos[0].posicao_m - pos_fissura) < 3.0
        assert acusticos[0].taxa_eventos_h > 0.0
        assert abs(anomalias[0].posicao_m - pos_fissura) < 3.0

    def test_sem_das_retorna_apenas_dss_e_dts(self, geometria, acq):
        gerador = GeradorAssinaturasMSE(geometria, acq, seed=3)
        res = gerador.cenario_fissura_multimodal(25.0, duracao_janela_das_s=2.0)
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        eventos = motor.inferir(dts=res["dts"], dss=res["dss"])
        assert not [e for e in eventos if isinstance(e, EventoAcusticoFissura)]
        assert [e for e in eventos if isinstance(e, PropagacaoFissuraEvento)]
        assert [e for e in eventos if isinstance(e, AnomaliaTermicaEvento)]


class TestCorrecaoTermicaDSS:
    def test_remove_strain_aparente(self):
        n_t, n_z = 1440, 100
        sinal = np.zeros((n_t, n_z))
        sinal[:, 40:45] = 150.0  # µε localizados (fissura)
        t = np.arange(n_t) * 60.0
        delta_t = 12.0 * np.sin(OMEGA_DIURNO_RAD_S * t)  # ±12 K diurno
        dts = 20.0 + delta_t[:, None] * np.ones((1, n_z))
        dss = sinal + 20e-6 * delta_t[:, None] * 1e6  # cross-sensibilidade Brillouin

        motor = MotorInferenciaMSE()
        corrigido, residual = motor.corrige_temperatura_dss(dss, dts)

        assert corrigido.shape == dss.shape
        assert np.allclose(corrigido, sinal, atol=1.0)
        assert residual < 1.0

    def test_interpola_eixo_temporal(self):
        n_t, n_z = 1440, 50
        sinal = np.zeros((n_t, n_z))
        sinal[:, 10:15] = 200.0
        t_dts = np.arange(720) * 120.0
        delta_t = 8.0 * np.sin(OMEGA_DIURNO_RAD_S * t_dts)
        dts = 20.0 + delta_t[:, None] * np.ones((1, n_z))
        t_dss = np.arange(n_t) * 60.0
        dss = sinal + 20e-6 * 8.0 * np.sin(OMEGA_DIURNO_RAD_S * t_dss)[:, None] * 1e6

        motor = MotorInferenciaMSE()
        corrigido, residual = motor.corrige_temperatura_dss(dss, dts)

        assert np.allclose(corrigido, sinal, atol=1.0)
        assert residual < 1.0

    def test_coef_customizado(self):
        n_t, n_z = 1440, 20
        sinal = np.zeros((n_t, n_z))
        t = np.arange(n_t) * 60.0
        delta_t = 5.0 * np.sin(OMEGA_DIURNO_RAD_S * t)
        dts = 20.0 + delta_t[:, None] * np.ones((1, n_z))
        dss = sinal + 15e-6 * delta_t[:, None] * 1e6

        motor = MotorInferenciaMSE()
        corrigido, _ = motor.corrige_temperatura_dss(dss, dts, coef=15e-6)
        assert np.allclose(corrigido, sinal, atol=1.0)


class TestRegrasIndividuais:
    def test_dss_sem_correcao_termica_nao_detecta_fissura_mascarada(self, geometria, acq):
        # Fissura SUB-LIMIAR (degrau DC < piso de 100 µε) com cross-sensibilidade
        # uniforme de 20 µε/°C × 20 K = ±400 µε em todo o traço: a proeminência
        # espacial da fissura some sem o DTS de referência.
        gerador = GeradorAssinaturasMSE(geometria, acq, seed=5)
        res = gerador.fissura_dss(25.0, abertura_mm=0.005, taxa_creep_ue_dia=0.0,
                                  rugosidade_dss_ue=3.0, amplitude_termica_fissura_k=2.0)
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        eventos = motor.inferir(dss=res["dss"])  # sem dts -> sem correção
        assert not [e for e in eventos if isinstance(e, PropagacaoFissuraEvento)]

    def test_fissura_estatica_detectada_sem_dts(self, geometria, acq):
        # Degrau permanente de 4000 µε (0.4 mm) é proeminente no nível DC
        # espacial mesmo sob ruído térmico uniforme — a máscara DC torna a
        # fissura estática detectável sem correção térmica.
        gerador = GeradorAssinaturasMSE(geometria, acq, seed=5)
        res = gerador.fissura_dss(25.0, rugosidade_dss_ue=3.0, incluir_termico=True,
                                  amplitude_termica_cabo_k=20.0)
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        eventos = motor.inferir(dss=res["dss"])
        propagacoes = [e for e in eventos if isinstance(e, PropagacaoFissuraEvento)]
        assert propagacoes
        assert abs(propagacoes[0].posicao_fissura_m - 25.0) < 2.0
        assert propagacoes[0].abertura_ue > 1000.0

    def test_dss_com_correcao_detecta_fissura(self, geometria, acq):
        gerador = GeradorAssinaturasMSE(geometria, acq, seed=5)
        pos = 25.0
        res = gerador.cenario_fissura_multimodal(
            pos, abertura_mm=0.6, taxa_creep_ue_dia=40.0, offset_ponte_k=4.0,
            n_eventos_das=2, duracao_janela_das_s=2.0, rugosidade_dss_ue=3.0,
            amplitude_termica_fissura_k=20.0,
        )
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        eventos = motor.inferir(dts=res["dts"], dss=res["dss"])
        propagacoes = [e for e in eventos if isinstance(e, PropagacaoFissuraEvento)]
        assert propagacoes
        assert abs(propagacoes[0].posicao_fissura_m - pos) < 2.0

    def test_dts_sem_anomalia_nao_emite_evento(self, geometria, acq):
        gerador = GeradorAssinaturasMSE(geometria, acq, seed=5)
        res = gerador.difusao_termica_parede()
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        eventos = motor.inferir(dts=res["dts"])
        assert not [e for e in eventos if isinstance(e, AnomaliaTermicaEvento)]

    def test_das_ruido_puro_nao_dispara_sta_lta(self, geometria, acq):
        gerador = GeradorAssinaturasMSE(geometria, acq, seed=5)
        res = gerador.ruido_ambiental(trafego=False, vento=False, pedestres=False,
                                      sinos=False, duracao_janela_s=10.0,
                                      rugosidade_base_ue=0.3)
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        eventos = motor.inferir(das=res["das"], fs_das_hz=1000.0)
        assert not [e for e in eventos if isinstance(e, EventoAcusticoFissura)]


class TestRegraRecalque:
    def test_recalque_detectado_na_extremidade_carregada(self, geometria, acq):
        gerador = GeradorAssinaturasMSE(geometria, acq, seed=5)
        res = gerador.recalque_diferencial(taxa_ue_dia=5.0, n_episodios=0,
                                           extremidade="fim", rugosidade_dss_ue=2.0)
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        eventos = motor.inferir(dss=res["dss"])
        recalques = [e for e in eventos if isinstance(e, RecalqueEvento)]
        assert recalques, "esperado ao menos um RecalqueEvento"
        assert max(e.posicao_m for e in recalques) > 80.0
        assert max(e.taxa_ue_dia for e in recalques) > 2.0

    def test_recalque_na_extremidade_inicial(self, geometria, acq):
        gerador = GeradorAssinaturasMSE(geometria, acq, seed=5)
        res = gerador.recalque_diferencial(taxa_ue_dia=8.0, n_episodios=0,
                                           extremidade="inicio", rugosidade_dss_ue=2.0)
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        eventos = motor.inferir(dss=res["dss"])
        recalques = [e for e in eventos if isinstance(e, RecalqueEvento)]
        assert recalques
        assert min(e.posicao_m for e in recalques) < 20.0

    def test_sem_recalque_sem_evento(self, geometria, acq):
        rng = np.random.default_rng(11)
        dss = rng.normal(0.0, 2.0, (1440, 200))
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        eventos = motor.inferir(dss=dss)
        assert not [e for e in eventos if isinstance(e, RecalqueEvento)]


class TestAberturaTermicaFissura:
    def test_abertura_termica_detectada_na_fissura(self, geometria, acq):
        pos = 25.0
        gerador = GeradorAssinaturasMSE(geometria, acq, seed=7)
        res = gerador.cenario_fissura_multimodal(
            pos, abertura_mm=0.8, taxa_creep_ue_dia=50.0, offset_ponte_k=4.0,
            n_eventos_das=0, duracao_janela_das_s=2.0, rugosidade_dss_ue=3.0,
            amplitude_termica_fissura_k=20.0,
        )
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        eventos = motor.inferir(dts=res["dts"], dss=res["dss"])
        termicos = [e for e in eventos if isinstance(e, AberturaFissuraTermicaEvento)]
        assert termicos, "esperado AberturaFissuraTermicaEvento (fissura termicamente ativa)"
        assert abs(termicos[0].posicao_m - pos) < 2.0
        assert termicos[0].variacao_termica_c > 1.0

    def test_fissura_estatica_sem_variacao_termica(self, geometria, acq):
        n_t, n_z = 1440, 200
        dss = np.zeros((n_t, n_z))
        dss[:, 95:100] = 3000.0  # pico estático, sem creep nem ciclo térmico
        dts = np.full((n_t, n_z), 20.0)  # temperatura constante: ΔT sem variância
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        eventos = motor.inferir(dts=dts, dss=dss)
        assert not [e for e in eventos if isinstance(e, AberturaFissuraTermicaEvento)]


class TestTaxaCreep:
    def test_taxa_creep_preenchida_no_evento(self, geometria, acq):
        gerador = GeradorAssinaturasMSE(geometria, acq, seed=7)
        res = gerador.cenario_fissura_multimodal(
            25.0, abertura_mm=0.8, taxa_creep_ue_dia=40.0, n_eventos_das=0,
            duracao_janela_das_s=2.0, rugosidade_dss_ue=3.0,
            amplitude_termica_fissura_k=20.0,
        )
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        eventos = motor.inferir(dts=res["dts"], dss=res["dss"])
        propagacoes = [e for e in eventos if isinstance(e, PropagacaoFissuraEvento)]
        assert propagacoes
        assert propagacoes[0].taxa_ue_dia is not None
        assert 5.0 < propagacoes[0].taxa_ue_dia < 100.0


class TestDanoModal:
    @staticmethod
    def _das_com_migracao_modal(fs_hz=200.0, duracao_s=60.0, f1=2.0, f2=1.9,
                                n_z=8, seed=3):
        n_t = int(duracao_s * fs_hz)
        t = np.arange(n_t) / fs_hz
        serie = np.where(t < duracao_s / 2.0,
                         np.sin(2.0 * np.pi * f1 * t),
                         np.sin(2.0 * np.pi * f2 * t))
        rng = np.random.default_rng(seed)
        ruido = rng.normal(0.0, 0.05, (n_t, n_z))
        return serie[:, None] + ruido

    def test_queda_de_f1_emite_dano_modal(self, geometria, acq):
        das = self._das_com_migracao_modal(f1=2.0, f2=1.9)  # −5%: dano sintético
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        motor.JANELA_WELCH_MODAL_S = 8.0  # janela curta p/ teste rápido
        eventos = motor.inferir(das=das, fs_das_hz=200.0)
        danos = [e for e in eventos if isinstance(e, DanoModalEvento)]
        assert danos, "esperado DanoModalEvento para migração de −5% em f1"
        assert danos[0].variacao_relativa_pct < -1.0
        assert 1.0 < danos[0].frequencia_hz < 2.5

    def test_modal_estavel_sem_evento(self, geometria, acq):
        das = self._das_com_migracao_modal(f1=2.0, f2=2.0)  # sem migração
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        motor.JANELA_WELCH_MODAL_S = 8.0
        eventos = motor.inferir(das=das, fs_das_hz=200.0)
        assert not [e for e in eventos if isinstance(e, DanoModalEvento)]

    def test_serie_curta_sem_evento_sem_erro(self, geometria, acq):
        das = self._das_com_migracao_modal(duracao_s=1.0)
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        eventos = motor.inferir(das=das, fs_das_hz=200.0)
        assert not [e for e in eventos if isinstance(e, DanoModalEvento)]


class TestFusaoMultimodal:
    def test_eventos_corroborados_compartilham_correlation_id(self, geometria, acq):
        pos = 25.0
        gerador = GeradorAssinaturasMSE(geometria, acq, seed=7)
        res = gerador.cenario_fissura_multimodal(
            pos, abertura_mm=0.8, taxa_creep_ue_dia=50.0, offset_ponte_k=4.0,
            n_eventos_das=6, degrau_ue=200.0, duracao_janela_das_s=20.0,
            rugosidade_dss_ue=3.0, amplitude_termica_fissura_k=20.0,
        )
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        eventos = motor.inferir(dts=res["dts"], dss=res["dss"], das=res["das"],
                                fs_das_hz=1000.0)
        ids = {e.correlation_id for e in eventos if e.correlation_id}
        assert ids, "eventos corroborados devem compartilhar correlation_id"
        assert len(ids) == 1
        prop = [e for e in eventos if isinstance(e, PropagacaoFissuraEvento)][0]
        assert prop.confidence >= 0.9
        assert prop.severity == "High"

    def test_evento_isolado_sem_correlation_id(self, geometria, acq):
        gerador = GeradorAssinaturasMSE(geometria, acq, seed=5)
        res = gerador.ponte_termica_fissura(70.0, offset_k=4.0)
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        eventos = motor.inferir(dts=res["dts"])
        anomalias = [e for e in eventos if isinstance(e, AnomaliaTermicaEvento)]
        assert anomalias
        assert all(e.correlation_id is None for e in anomalias)


class TestRobustezNaN:
    def test_canal_nan_ignorado_sem_crash(self, geometria, acq):
        gerador = GeradorAssinaturasMSE(geometria, acq, seed=7)
        res = gerador.cenario_fissura_multimodal(
            25.0, abertura_mm=0.8, taxa_creep_ue_dia=50.0, offset_ponte_k=4.0,
            n_eventos_das=4, duracao_janela_das_s=10.0, rugosidade_dss_ue=3.0,
            amplitude_termica_fissura_k=20.0,
        )
        col_nan = 120  # ~60 m: canal inteiramente inválido
        for campo in ("dts", "dss", "das"):
            arr = res[campo].copy()
            arr[:, col_nan] = np.nan
            res[campo] = arr
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        eventos = motor.inferir(dts=res["dts"], dss=res["dss"], das=res["das"],
                                fs_das_hz=1000.0)
        prop = [e for e in eventos if isinstance(e, PropagacaoFissuraEvento)]
        assert prop and abs(prop[0].posicao_fissura_m - 25.0) < 2.0
        for e in eventos:
            pos = getattr(e, "posicao_m", getattr(e, "posicao_fissura_m", None))
            assert pos is None or not (55.0 < pos < 65.0)

    def test_inf_convertido_para_nan_sem_erro(self, geometria, acq):
        gerador = GeradorAssinaturasMSE(geometria, acq, seed=5)
        res = gerador.fissura_dss(25.0, rugosidade_dss_ue=3.0, incluir_termico=False)
        dss = np.asarray(res["dss"], dtype=float).copy()
        dss[:, 7] = np.inf
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        eventos = motor.inferir(dss=dss)
        prop = [e for e in eventos if isinstance(e, PropagacaoFissuraEvento)]
        assert prop and abs(prop[0].posicao_fissura_m - 25.0) < 2.0
