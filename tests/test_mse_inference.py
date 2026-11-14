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
    AnomaliaTermicaEvento,
    EventoAcusticoFissura,
    PropagacaoFissuraEvento,
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
        # Cross-sensibilidade uniforme de 20 µε/°C × 20 K = ±400 µε em todo o
        # traço: a proeminência espacial da fissura some sem o DTS de referência.
        gerador = GeradorAssinaturasMSE(geometria, acq, seed=5)
        res = gerador.fissura_dss(25.0, abertura_mm=0.2, taxa_creep_ue_dia=2.0,
                                  rugosidade_dss_ue=3.0, amplitude_termica_fissura_k=2.0)
        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        eventos = motor.inferir(dss=res["dss"])  # sem dts -> sem correção
        assert not [e for e in eventos if isinstance(e, PropagacaoFissuraEvento)]

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
