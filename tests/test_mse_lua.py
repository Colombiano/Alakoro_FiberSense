"""
Alakoro FiberSense — Testes dos Cenários Lua do MSE
MSE Lua Scenario Tests
"""

from pathlib import Path

import numpy as np
import pytest

lupa = pytest.importorskip("lupa")

from alakoro.mse import GeradorAssinaturasMSE  # noqa: E402
from alakoro.mse.cenarios import (  # noqa: E402
    aplica_cenario,
    carrega_cenario_lua,
    constroi_aquisicao,
    constroi_geometria,
    tabela_para_dict,
)

CAMINHO_CENARIO = Path(__file__).resolve().parent.parent / "examples" / "mse_cenario.lua"


class TestCarregaCenarioLua:
    def test_carrega_arquivo_exemplo(self):
        cenario = carrega_cenario_lua(str(CAMINHO_CENARIO))
        assert cenario["nome"].startswith("Ruína de Igreja Colonial")
        assert len(cenario["fissuras"]) == 2
        assert cenario["fissuras"][0]["posicao_m"] == pytest.approx(32.0)
        assert cenario["fissuras"][0]["tipo"] == "transversal"
        assert cenario["material"]["coef_expansao_termica"] == pytest.approx(5.6e-6)
        assert len(cenario["geometria"]["trechos"]) == 3
        assert len(cenario["geometria"]["profundidade_posicoes"]) == 400
        assert cenario["aquisicao"]["n_posicoes"] == 400
        assert cenario["gerador"]["tipo"] == "cenario_fissura_multimodal"

    def test_lua_inline(self):
        cenario = carrega_cenario_lua(lua='return { nome = "Inline", valor = 2.5, lista = {1, 2, 3} }')
        assert cenario["nome"] == "Inline"
        assert cenario["valor"] == pytest.approx(2.5)
        assert cenario["lista"] == [1, 2, 3]

    def test_sem_fonte_levanta_valueerror(self):
        with pytest.raises(ValueError):
            carrega_cenario_lua()

    def test_tabela_para_dict_escalares(self):
        assert tabela_para_dict(1.5) == 1.5
        assert tabela_para_dict("texto") == "texto"


class TestAplicaCenario:
    def test_aplica_cenario_exemplo(self):
        cenario = carrega_cenario_lua(str(CAMINHO_CENARIO))
        geometria = constroi_geometria(cenario["geometria"])
        acq = constroi_aquisicao(cenario["aquisicao"])
        gerador = GeradorAssinaturasMSE(geometria, acq, seed=11)

        res = aplica_cenario(gerador, cenario)

        n_t_esperado = acq.n_amostras_dts
        assert res["dts"].shape == (n_t_esperado, acq.n_posicoes)
        assert res["dss"].shape == (n_t_esperado, acq.n_posicoes)
        assert res["das"].shape[1] == acq.n_posicoes
        assert res["das"].shape[0] == int(cenario["gerador"]["duracao_janela_das_s"] * acq.fs_das_hz)

        # Coerência: o pico de deformação fica na posição da fissura ativa.
        # O DSS bruto é mascarado pela cross-sensibilidade térmica espacialmente
        # variável; a correção com o DTS (como faz o MotorInferenciaMSE) revela
        # a fissura.
        from alakoro.mse import MotorInferenciaMSE

        motor = MotorInferenciaMSE(geometria=geometria, acq=acq)
        dss_corrigido, residual = motor.corrige_temperatura_dss(res["dss"], res["dts"])
        proeminencia = np.max(np.abs(dss_corrigido - np.median(dss_corrigido, axis=0)), axis=0)
        idx_pico = int(np.argmax(proeminencia))
        pos_fissura = cenario["gerador"]["posicao_fissura_m"]
        assert abs(gerador.posicoes[idx_pico] - pos_fissura) < 2.0
        assert residual < 50.0

        # Coerência térmica: offset persistente na posição da fissura.
        offset = np.median(res["dts"], axis=0)
        offset = offset - np.median(offset)
        idx_offset = int(np.argmax(np.abs(offset)))
        assert abs(gerador.posicoes[idx_offset] - pos_fissura) < 3.0

    def test_constroi_geometria_defaults(self):
        geometria = constroi_geometria({"comprimento_fibra_m": 50.0})
        assert geometria.comprimento_fibra_m == 50.0
        assert len(geometria.trechos) == 1  # trecho único exposto por default

    def test_tipo_desconhecido_levanta_valueerror(self):
        cenario = {"gerador": {"tipo": "tipo_inexistente"}}
        gerador = GeradorAssinaturasMSE(seed=1)
        with pytest.raises(ValueError):
            aplica_cenario(gerador, cenario)

    def test_aplica_difusao_termica(self):
        cenario = carrega_cenario_lua(lua="""
            return {
              gerador = { tipo = "difusao_termica_parede", alpha = 5e-7, amplitude_superficial_k = 25.0 },
            }
        """)
        gerador = GeradorAssinaturasMSE(
            constroi_geometria({"comprimento_fibra_m": 50.0}),
            constroi_aquisicao({"n_posicoes": 100, "duracao_s": 3600.0}),
            seed=1,
        )
        res = aplica_cenario(gerador, cenario)
        assert res["dts"].shape == (60, 100)
        assert res["dss"] is None and res["das"] is None
        assert res["parameters"]["amplitude_superficial_k"] == 25.0
