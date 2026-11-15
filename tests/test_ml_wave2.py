"""
Testes da Onda 2 — Machine Learning (ML:D-03, ML:D-04, ML:E-05, ML:F-04, ML:I-03)

- Velocidade aparente COM SINAL em rampa sintética (v = Δz/Δt)
- delta_T_over_xf no DTSFeatureExtractor
- Welch com fs real
- FlowRegressor.physical_inference — regras ternárias (3 casos)
- decouple_for_pipeline recupera sinal acoplado
- predict_flow com apply_decoupling
"""

import numpy as np
import pytest

from alakoro.ml.decoupling import decouple_for_pipeline
from alakoro.ml.features import DASFeatureExtractor, DTSFeatureExtractor
from alakoro.ml.models import FlowRegressor


def _rampa_evento(n_t=200, n_c=16, lag=5, fs=100.0, invertido=False):
    """Evento coerente deslocado de c·lag amostras entre canais adjacentes."""
    t = np.arange(n_t)
    pulso = np.exp(-0.5 * ((t - 80) / 6.0) ** 2)
    data = np.zeros((n_t, n_c))
    for c in range(n_c):
        shift = c * lag if not invertido else -c * lag
        data[:, c] = np.roll(pulso, shift)
    return data


class TestVelocidadeAparente:
    """ML:D-04 — velocidade aparente com sinal via correlação de pico."""

    @staticmethod
    def _extrator():
        return DASFeatureExtractor(stats=False, spectral=False, wavelet=False,
                                   das_specific=True, fs_hz=100.0, channel_spacing_m=2.0)

    def test_velocidade_descendente_positiva(self):
        data = _rampa_evento(lag=5)  # v = 2.0 m · 100 Hz / 5 = +40 m/s
        feats = self._extrator()(data)
        assert feats[1] == pytest.approx(40.0, rel=0.05)

    def test_velocidade_ascendente_negativa(self):
        data = _rampa_evento(lag=5, invertido=True)  # v = -40 m/s
        feats = self._extrator()(data)
        assert feats[1] == pytest.approx(-40.0, rel=0.05)

    def test_sem_unidades_canais_por_amostra(self):
        data = _rampa_evento(lag=5)
        ext = DASFeatureExtractor(stats=False, spectral=False, wavelet=False,
                                  das_specific=True)
        feats = ext(data)
        assert feats[1] == pytest.approx(0.2, rel=0.05)  # 1/5 com sinal

    def test_feature_vector_sem_nan(self):
        rng = np.random.default_rng(3)
        feats = self._extrator()(rng.normal(0.0, 1.0, (64, 8)))
        assert feats.ndim == 1
        assert np.all(np.isfinite(feats))


class TestDTSFeatures:
    """ML:E-05 / ML:I-03 — delta_T_over_xf e Welch com fs real."""

    def test_delta_T_over_xf(self):
        dts = np.full((64, 32), 20.0)
        dts[:, 10:14] += 6.0  # cluster: ΔT = 6 °C, X_f = 4 m → 1.5 °C/m
        ext = DTSFeatureExtractor(stats=False, spectral=False, thermal=True, anomaly=False)
        assert ext.delta_T_over_xf(dts, depth_step_m=1.0) == pytest.approx(1.5, rel=1e-6)

    def test_delta_T_over_xf_campo_plano(self):
        ext = DTSFeatureExtractor(stats=False, spectral=False, thermal=True, anomaly=False)
        assert ext.delta_T_over_xf(np.full((64, 32), 20.0), depth_step_m=1.0) == 0.0

    def test_delta_T_over_xf_no_vetor_de_features(self):
        dts = np.full((64, 32), 20.0)
        dts[:, 10:14] += 6.0
        ext = DTSFeatureExtractor(stats=False, spectral=False, thermal=True, anomaly=False)
        feats = ext(dts, depth_step_m=1.0)
        assert feats[-1] == pytest.approx(1.5, rel=1e-6)

    def test_welch_usa_fs_real(self):
        fs = 64.0
        t = np.arange(128) / fs
        patch = np.tile(np.sin(2.0 * np.pi * 8.0 * t)[:, None], (1, 4))
        ext = DTSFeatureExtractor(stats=False, spectral=True, thermal=False,
                                  anomaly=False, fs_hz=fs)
        feats = ext(patch)
        assert feats[3] == pytest.approx(8.0, abs=1.0)  # frequência de pico da PSD

    def test_das_welch_usa_fs_real(self):
        fs = 64.0
        t = np.arange(128) / fs
        patch = np.tile(np.sin(2.0 * np.pi * 8.0 * t)[:, None], (1, 4))
        ext = DASFeatureExtractor(stats=False, spectral=True, wavelet=False,
                                  das_specific=False, fs_hz=fs)
        feats = ext(patch)
        assert feats[3] == pytest.approx(8.0, abs=1.0)


class TestInferenciaFisica:
    """ML:F-04 — matriz ternária de discriminação de fluxo."""

    @staticmethod
    def _modelo():
        return FlowRegressor(input_shape=(16, 8), n_zones=2)

    def test_caso_hidraulico(self):
        m = self._modelo()
        out = m.physical_inference({
            "apparent_velocity_ms": 40.0,
            "band_energy_ratio": 0.6,
            "thermal_anomaly": True,
        })
        assert out["discrimination"] == "hydraulic"
        assert out["direction"] == "down"
        assert out["velocity_ms"] == pytest.approx(40.0)

    def test_caso_termico(self):
        m = self._modelo()
        out = m.physical_inference({
            "apparent_velocity_ms": float("nan"),
            "band_energy_ratio": 0.0,
            "thermal_anomaly": True,
        })
        assert out["discrimination"] == "thermal"
        assert out["direction"] == "none"
        assert out["velocity_ms"] is None

    def test_caso_inconclusivo(self):
        m = self._modelo()
        out = m.physical_inference({
            "apparent_velocity_ms": 40.0,
            "band_energy_ratio": 0.6,
            "thermal_anomaly": False,
        })
        assert out["discrimination"] == "inconclusive"

    def test_anomalia_por_sigma(self):
        m = self._modelo()
        out = m.physical_inference({
            "apparent_velocity_ms": float("nan"),
            "band_energy_ratio": 0.0,
            "thermal_anomaly_sigma": 4.0,  # >= anomalia_sigma (3.0)
        })
        assert out["discrimination"] == "thermal"

    def test_limiares_sao_atributos_de_classe(self):
        assert FlowRegressor.velocidade_minima_m_s == 0.0
        assert FlowRegressor.banda_discriminacao_hz == (15.0, 100.0)
        assert FlowRegressor.razao_energia_banda_minima == 0.3
        assert FlowRegressor.anomalia_sigma == 3.0


class TestDecouplingPipeline:
    """ML:D-03/E-05/F-04/I-03 — decouple_for_pipeline padronizado."""

    @staticmethod
    def _campo_acoplado(n_t=120, n_z=40, coeficiente=-2800.0, seed=1):
        rng = np.random.default_rng(seed)
        base = 20.0 + 8.0 * np.sin(2.0 * np.pi * np.arange(n_t) / n_t)
        temp = base[:, None] + rng.normal(0.0, 0.02, (n_t, n_z))
        sinal = np.zeros((n_t, n_z))
        sinal[60:70, 20:25] = 500.0
        dtemp = temp - temp[0, :]
        strain = sinal + coeficiente * dtemp + rng.normal(0.0, 2.0, (n_t, n_z))
        return strain, temp, sinal

    def test_recupera_sinal_e_coeficiente(self):
        strain, temp, _ = self._campo_acoplado()
        out = decouple_for_pipeline(strain, temp, win_t=24, win_z=12, constrain_cs=True)
        assert out["backend"] in {"cpp", "numpy"}
        assert out["constrained"] is False
        assert out["global_coefficient"] == pytest.approx(-2800.0, rel=0.05)
        assert out["coefficient_map"].shape == strain.shape
        decoupled = out["decoupled"]
        assert decoupled.shape == strain.shape
        # região do sinal recuperada
        assert np.abs(decoupled[60:70, 20:25] - 500.0).max() < 60.0

    def test_restricao_cs_ativa_no_fallback_numpy(self, monkeypatch):
        import alakoro.ml.decoupling as dec_mod

        monkeypatch.setattr(dec_mod, "_CPP_DISPONIVEL", False)
        strain, temp, _ = self._campo_acoplado(coeficiente=+500.0)  # C > 0 espúrio
        out = decouple_for_pipeline(strain, temp, constrain_cs=True)
        assert out["backend"] == "numpy"
        assert out["constrained"] is True
        assert out["global_coefficient"] <= 0.0

    def test_mascara_de_ponta_aplicada(self):
        strain, temp, _ = self._campo_acoplado()
        out = decouple_for_pipeline(strain, temp, win_t=24, win_z=12,
                                    mask_end_meters=10.0, step_m=1.0)
        assert out["end_mask_m"] == pytest.approx(10.0)
        assert out["decoupled"].shape == strain.shape

    def test_mascara_propaga_nan_no_fallback_numpy(self, monkeypatch):
        import alakoro.ml.decoupling as dec_mod

        monkeypatch.setattr(dec_mod, "_CPP_DISPONIVEL", False)
        strain, temp, _ = self._campo_acoplado()
        out = decouple_for_pipeline(strain, temp, mask_end_meters=10.0, step_m=1.0)
        # no fallback NumPy, decoupled = strain - C·ΔT preserva os NaN da máscara
        assert np.isnan(out["decoupled"][:, 30:]).all()
        assert np.isfinite(out["decoupled"][:, :30]).all()

    def test_shapes_incompativeis_rejeitados(self):
        strain, temp, _ = self._campo_acoplado()
        with pytest.raises(ValueError, match="incompatível"):
            decouple_for_pipeline(strain, temp[:, :30])


class TestPredictFlowDecoupling:
    """predict_flow com apply_decoupling antes do stack."""

    def test_apply_decoupling_anexa_resultado(self):
        from alakoro.ml.api import predict_flow

        n_t, n_z = 120, 40
        strain, temp, _ = TestDecouplingPipeline._campo_acoplado(n_t=n_t, n_z=n_z)
        model = FlowRegressor(input_shape=(n_t, n_z), n_zones=2)
        result = predict_flow(model, strain, temp, apply_decoupling=True)
        assert len(result["zones"]) == 2
        assert "decoupling" in result
        assert result["decoupling"]["global_coefficient"] == pytest.approx(-2800.0, rel=0.05)

    def test_sem_decoupling_mantem_contrato(self):
        from alakoro.ml.api import predict_flow

        model = FlowRegressor(input_shape=(32, 16), n_zones=3)
        rng = np.random.default_rng(0)
        result = predict_flow(model, rng.normal(size=(32, 16)).astype(np.float32),
                              rng.normal(size=(32, 16)).astype(np.float32))
        assert len(result["zones"]) == 3
        assert "decoupling" not in result
