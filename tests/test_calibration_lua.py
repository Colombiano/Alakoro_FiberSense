"""
Testes da Onda 2 — Calibração Lua (extra `calibration`)

- carrega_calibracao_lua no exemplo examples/calibracao_decoupling.lua
- aplica_calibracao altera o coeficiente térmico de LFDASProcessor
- aplica_calibracao aplica os limiares (thresholds) em FlowRegressor
"""

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("lupa")

from alakoro.processing.calibration import aplica_calibracao, carrega_calibracao_lua
from alakoro.processing.lfdas_processor import LFDASProcessor

EXEMPLO_LUA = (
    Path(__file__).resolve().parents[1] / "examples" / "calibracao_decoupling.lua"
)


class TestCarregaCalibracao:
    def test_carrega_exemplo(self):
        cal = carrega_calibracao_lua(str(EXEMPLO_LUA))
        assert cal["poco"] == "POCO-DEMO-01"

        zonas = cal["zonas_calibracao"]
        assert len(zonas) == 1
        assert zonas[0]["inicio_m"] == pytest.approx(1200.0)
        assert zonas[0]["fim_m"] == pytest.approx(1450.0)
        assert zonas[0]["fraturada"] is False

        assert cal["priors"]["coeficiente_acoplamento_c_por_rad"] == pytest.approx(0.0028)
        assert cal["priors"]["faixa_coeficiente"] == [pytest.approx(0.001), pytest.approx(0.005)]

        thresholds = cal["thresholds"]
        assert thresholds["velocidade_minima_m_s"] == pytest.approx(0.5)
        assert thresholds["razao_energia_banda_minima"] == pytest.approx(0.3)
        assert thresholds["anomalia_sigma"] == pytest.approx(3.0)
        assert thresholds["banda_discriminacao_hz"] == [pytest.approx(15.0), pytest.approx(100.0)]

    def test_lua_inline(self):
        cal = carrega_calibracao_lua(lua='return { priors = { coeficiente_acoplamento_c_por_rad = 0.004 } }')
        assert cal["priors"]["coeficiente_acoplamento_c_por_rad"] == pytest.approx(0.004)
        assert cal["thresholds"] == {}
        assert cal["zonas_calibracao"] == []

    def test_sem_fonte_rejeitado(self):
        with pytest.raises(ValueError, match="caminho"):
            carrega_calibracao_lua()


class TestAplicaCalibracao:
    def _lfdas(self):
        return LFDASProcessor(sampling_rate_hz=10.0, refresh_rate_target_s=0.1)

    def test_aplica_coeficiente_no_exemplo(self):
        cal = carrega_calibracao_lua(str(EXEMPLO_LUA))
        proc = self._lfdas()
        aplicados = aplica_calibracao(proc, cal)
        assert aplicados["thermal_coefficient_c_per_rad"] == pytest.approx(0.0028)
        assert proc.thermal_coefficient_c_per_rad == pytest.approx(0.0028)

    def test_aplica_coeficiente_alterado(self, tmp_path):
        arquivo = tmp_path / "cal.lua"
        arquivo.write_text(
            "return { priors = { coeficiente_acoplamento_c_por_rad = 0.0042 } }",
            encoding="utf-8",
        )
        cal = carrega_calibracao_lua(str(arquivo))
        proc = self._lfdas()
        aplica_calibracao(proc, cal)
        assert proc.thermal_coefficient_c_per_rad == pytest.approx(0.0042)
        # e o processador passa a usar o novo fator
        data = np.full((40, 8), 1.0)
        result = proc.process(data, trace_interval_s=0.1)
        assert result["temperature"][10, 4] == pytest.approx(0.0042, rel=1e-6)

    def test_aplica_thresholds_em_flow_regressor(self):
        from alakoro.ml.models import FlowRegressor

        cal = carrega_calibracao_lua(str(EXEMPLO_LUA))
        modelo = FlowRegressor(input_shape=(16, 8), n_zones=2)
        aplicados = aplica_calibracao(modelo, cal)

        assert aplicados["velocidade_minima_m_s"] == pytest.approx(0.5)
        assert modelo.velocidade_minima_m_s == pytest.approx(0.5)
        assert modelo.razao_energia_banda_minima == pytest.approx(0.3)
        assert modelo.anomalia_sigma == pytest.approx(3.0)
        assert modelo.banda_discriminacao_hz == [15.0, 100.0]
        # threshold sem atributo correspondente é ignorado (snr_min_db)
        assert "snr_min_db" not in aplicados
        # nenhum atributo térmico espúrio é criado no regressor
        assert not hasattr(modelo, "thermal_coefficient_c_per_rad")

    def test_alvo_generico_com_atributos_de_classe(self):
        class MotorFake:
            velocidade_minima_m_s = 0.0
            anomalia_sigma = 3.0

        cal = carrega_calibracao_lua(str(EXEMPLO_LUA))
        motor = MotorFake()
        aplicados = aplica_calibracao(motor, cal)
        assert aplicados["velocidade_minima_m_s"] == pytest.approx(0.5)
        assert motor.anomalia_sigma == pytest.approx(3.0)
        assert not hasattr(motor, "thermal_coefficient_c_per_rad")
