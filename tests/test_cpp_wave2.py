"""
Alakoro FiberSense — Testes da Onda 2 C++ (CL-03/04/07/08, SP:B-05)
Wave-2 C++ tests: LF/HF band metadata, signed apparent velocity, ternary
flow discrimination, strain-temperature decoupling, Brillouin metadata,
DTS trailing mask and single-ended attenuation correction.
"""

import numpy as np
import pytest

try:
    from alakoro_core import (
        AcquisitionMetadata,
        CanonicalInferenceEngine,
        InferenceMetadata,
        attenuation_correct_single_ended_d,
        decouple_strain_temperature_d,
        mask_trailing_meters_d,
    )
    _CPP_DISPONIVEL = True
except ImportError:  # pragma: no cover - extensão opcional
    _CPP_DISPONIVEL = False

pytestmark = pytest.mark.skipif(not _CPP_DISPONIVEL,
                                reason="extensão C++ alakoro_core indisponível")


class TestMetadadosOnda2:
    """Defaults dos novos campos de metadados (CL-08, SP:B-05)."""

    def test_brillouin_defaults(self):
        a = AcquisitionMetadata()
        assert a.brillouin_c11_mhz_per_ustrain == pytest.approx(0.05)
        assert a.brillouin_c12_mhz_per_c == pytest.approx(1.0)
        assert a.thermal_reference_modality == "dts"
        assert a.dual_fiber_config is False

    def test_bandas_lf_hf_defaults(self):
        m = InferenceMetadata()
        assert m.low_freq_band_hz == pytest.approx(0.05)
        assert m.high_freq_band_hz == pytest.approx(1.0)
        assert m.discrim_low_freq_hz == pytest.approx(15.0)
        assert m.discrim_high_freq_hz == pytest.approx(100.0)
        assert m.apply_band_filter is True

    def test_infer_com_e_sem_band_filter(self):
        engine = CanonicalInferenceEngine()
        dts = np.full((64, 128), 60.0)
        das = np.random.default_rng(0).normal(0.0, 0.1, (64, 128))
        for flag in (True, False):
            meta = InferenceMetadata()
            meta.sampling_rate_hz = 1000.0
            meta.depth_step_m = 1.0
            meta.apply_band_filter = flag
            resultados = engine.infer(dts, das, meta)
            assert isinstance(resultados, list)


class TestDecoupling:
    """Desacoplamento tensão-temperatura (CL-03): regressão Theil-Sen
    janelada 2D, restrição física CS ≤ 0 via política de template."""

    @staticmethod
    def _campo_acoplado(n_t=120, n_z=40, coeficiente=-2800.0, seed=1):
        rng = np.random.default_rng(seed)
        base = 20.0 + 8.0 * np.sin(2.0 * np.pi * np.arange(n_t) / n_t)
        T = base[:, None] + rng.normal(0.0, 0.02, (n_t, n_z))
        sinal = np.zeros((n_t, n_z))
        sinal[60:70, 20:25] = 500.0
        dtemp = T - T[0, :]  # referência da primeira linha (contrato do núcleo)
        strain = sinal + coeficiente * dtemp + rng.normal(0.0, 2.0, (n_t, n_z))
        return strain, T, sinal

    def test_recupera_sinal_e_coeficiente(self):
        strain, T, sinal = self._campo_acoplado()
        out = decouple_strain_temperature_d(strain, T, 24, 12, True)
        assert set(out) == {"decoupled", "coefficient_map",
                            "global_coefficient", "constrained"}
        res = np.asarray(out["decoupled"])
        assert res.shape == strain.shape
        assert out["global_coefficient"] == pytest.approx(-2800.0, rel=0.05)
        cm = np.asarray(out["coefficient_map"]).reshape(strain.shape)
        assert np.nanmedian(cm[5:, :]) == pytest.approx(-2800.0, rel=0.10)
        # Região do sinal recuperada (fora da 1ª linha, peso triangular nulo).
        assert np.abs(res[60:70, 20:25] - 500.0).max() < 60.0
        assert out["constrained"] is False

    def test_restricao_cs_ativa(self):
        rng = np.random.default_rng(2)
        n_t, n_z = 120, 40
        base = 20.0 + 8.0 * np.sin(2.0 * np.pi * np.arange(n_t) / n_t)
        T = base[:, None] + rng.normal(0.0, 0.02, (n_t, n_z))
        dtemp = T - T[0, :]
        strain = 500.0 * dtemp + rng.normal(0.0, 2.0, (n_t, n_z))  # C > 0 espúrio

        out = decouple_strain_temperature_d(strain, T, 24, 12, True)
        assert out["constrained"] is True
        cm = np.asarray(out["coefficient_map"]).reshape(strain.shape)
        assert cm[5:, :].max() <= 1e-6

        out_nc = decouple_strain_temperature_d(strain, T, 24, 12, False)
        cm_nc = np.asarray(out_nc["coefficient_map"]).reshape(strain.shape)
        assert np.nanmedian(cm_nc[5:, :]) > 100.0
        assert out_nc["constrained"] is False

    def test_determinismo(self):
        strain, T, _ = self._campo_acoplado()
        a = decouple_strain_temperature_d(strain, T, 24, 12, True)
        b = decouple_strain_temperature_d(strain, T, 24, 12, True)
        np.testing.assert_array_equal(np.asarray(a["decoupled"]),
                                      np.asarray(b["decoupled"]))

    def test_janela_menor_8_rejeitada(self):
        strain, T, _ = self._campo_acoplado()
        with pytest.raises(ValueError):
            decouple_strain_temperature_d(strain, T, 4, 12, True)

    def test_shapes_incompativeis_rejeitados(self):
        strain, T, _ = self._campo_acoplado()
        with pytest.raises(ValueError):
            decouple_strain_temperature_d(strain, T[:, :30], 24, 12, True)

    def test_sem_variacao_termica_rejeitado(self):
        strain = np.zeros((120, 40))
        T = np.full((120, 40), 20.0)
        with pytest.raises(ValueError):
            decouple_strain_temperature_d(strain, T, 24, 12, True)


class TestMascaraEAtenuacao:
    """CL-07-C++: máscara de ponta do cabo e correção de atenuação
    single-ended (double-ended fica como extension point experimental)."""

    def test_mascara_ponta(self):
        data = np.random.default_rng(0).normal(size=(10, 40))
        out = np.asarray(mask_trailing_meters_d(data, 0.5, 5.0))
        assert out.shape == data.shape
        assert np.isfinite(out[:, :30]).all()
        assert np.isnan(out[:, 30:]).all()

    def test_atenuacao_single_ended(self):
        # Fundo térmico com deriva linear-in-distância de 0.6 °C/m.
        campo = 20.0 + 0.6 * (np.arange(40) * 0.5)[None, :] + np.zeros((10, 40))
        out = attenuation_correct_single_ended_d(campo, 0.5, 2.0, 8.0)
        assert set(out) == {"corrected", "slope_per_m", "intercept"}
        assert out["slope_per_m"] == pytest.approx(0.6, rel=1e-3)
        corrigido = np.asarray(out["corrected"])
        assert np.abs(corrigido).max() < 1e-6


class TestVelocidadeEDiscriminacao:
    """CL-04: velocidade aparente COM SINAL por correlação cruzada e
    discriminação ternária de fluxo (hydraulic/thermal/inconclusive)."""

    FS = 1000.0
    N_T = 4000
    N_Z = 200

    @classmethod
    def _das_evento_movel(cls, velocidade_m_s, seed=3):
        """Pulso gaussiano coerente deslocando-se ao longo da fibra.

        Um evento real aparece em canais adjacentes com o mesmo atraso
        (consenso espacial do estimador CL-04), então o pulso é aplicado
        em todos os canais, não em uma subamostragem.
        """
        rng = np.random.default_rng(seed)
        t = np.arange(cls.N_T) / cls.FS
        z = np.arange(cls.N_Z, dtype=float)
        atrasos = z / velocidade_m_s                       # (n_z,)
        dt = t[:, None] - atrasos[None, :]                 # (n_t, n_z)
        forma = np.exp(-0.5 * (dt / 0.02) ** 2) * np.sin(2.0 * np.pi * 80.0 * dt)
        return forma + rng.normal(0.0, 0.02, (cls.N_T, cls.N_Z))

    @staticmethod
    def _meta():
        meta = InferenceMetadata()
        meta.sampling_rate_hz = TestVelocidadeEDiscriminacao.FS
        meta.depth_step_m = 1.0
        meta.apply_band_filter = False
        return meta

    @staticmethod
    def _por_tipo(resultados, tipo):
        return [r for r in resultados if r.event_type == tipo]

    def test_velocidade_com_sinal_e_rejeicao_de_subida(self):
        # CL-04: evento descendente (v > 0) é emitido com velocidade e
        # direção; evento ascendente (v < 0) é REJEITADO — a regra não
        # emite produção espúria (apenas fluxo descendente é válido aqui).
        engine = CanonicalInferenceEngine()
        dts = np.zeros((self.N_T, self.N_Z))
        descendo = self._das_evento_movel(+50.0, seed=3)
        subindo = self._das_evento_movel(-50.0, seed=3)

        r_desc = self._por_tipo(engine.infer(dts, descendo, self._meta()),
                                "slope_velocity")
        r_sub = self._por_tipo(engine.infer(dts, subindo, self._meta()),
                               "slope_velocity")
        assert r_desc, "evento descendente deve ser emitido"
        assert not r_sub, "evento ascendente (v < 0) deve ser rejeitado"
        v_desc = r_desc[0].apparent_velocity_ms
        assert np.isfinite(v_desc)
        assert 25.0 < v_desc < 100.0
        assert r_desc[0].flow_direction == "down"

    def test_ruido_puro_velocidade_indeterminada(self):
        engine = CanonicalInferenceEngine()
        dts = np.zeros((self.N_T, self.N_Z))
        rng = np.random.default_rng(9)
        das = rng.normal(0.0, 0.05, (self.N_T, self.N_Z))
        resultados = engine.infer(dts, das, self._meta())
        for r in self._por_tipo(resultados, "slope_velocity"):
            assert not np.isfinite(r.apparent_velocity_ms)

    def test_discriminacao_termica_vs_hidraulica(self):
        engine = CanonicalInferenceEngine()
        n_t, n_z = self.N_T, self.N_Z
        t = np.arange(n_t) / self.FS
        z = np.arange(n_z, dtype=float)

        # Caso térmico: anomalia quente localizada, DAS SEM energia (zeros —
        # tem que zerar a condição (ii) e a velocidade, senão o ruído
        # gaussiano plano dispara band_ok espuriamente).
        dts_term = np.full((n_t, n_z), 60.0)
        dts_term[:, 80:120] += 8.0
        das_fraco = np.zeros((n_t, n_z))
        res_t = self._por_tipo(engine.infer(dts_term, das_fraco, self._meta()),
                               "flow_discrimination")
        assert res_t, "esperado flow_discrimination no caso térmico"
        assert res_t[0].discrimination == "thermal"

        # Caso hidráulico: anomalia térmica + energia 15–100 Hz + evento
        # móvel coerente (velocidade > 0 determinada).
        das_hid = self._das_evento_movel(+50.0, seed=5)
        tom = 0.5 * np.sin(2.0 * np.pi * 30.0 * t)
        das_hid[:, 60:140] += tom[:, None]
        res_h = self._por_tipo(engine.infer(dts_term, das_hid, self._meta()),
                               "flow_discrimination")
        assert res_h, "esperado flow_discrimination no caso hidráulico"
        assert res_h[0].discrimination == "hydraulic"
