"""
Testes da Onda 2 — Processamento (SP:I-03, SP:A-03, SP:C-03, SP:C-04, SP:C-05, PP:A-03)

- Fator térmico default 0.0028 °C/rad e conversão fase→temperatura
- process_lf: remoção de DC e detecção de saltos de unwrapping
- process_hf: clipping de transientes (mediana + 8·MAD)
- DTS: máscara de ponta e correção de atenuação single-ended (fallback NumPy)
- extract_lfdas / extract_hf_das: isolamento de bandas por PSD
"""

import numpy as np
import pytest
from scipy import signal as scipy_signal

import alakoro.processing.dts_processor as dts_mod
from alakoro.processing.advanced_processors import extract_hf_das, extract_lfdas
from alakoro.processing.dts_processor import DTSThermalProcessor
from alakoro.processing.lfdas_processor import LFDASProcessor


def _lfdas_fast(**kwargs) -> LFDASProcessor:
    """LFDASProcessor barato para testes (fs baixa, decimação mínima)."""
    kwargs.setdefault("sampling_rate_hz", 10.0)
    kwargs.setdefault("refresh_rate_target_s", 0.1)
    kwargs.setdefault("spatial_smooth_sigma", 0.0)
    return LFDASProcessor(**kwargs)


class TestFatorTermico:
    """SP:I-03 — coeficiente térmico calibrável com default 0.0028 °C/rad."""

    def test_default_e_literatura(self):
        proc = _lfdas_fast()
        assert proc.thermal_coefficient_c_per_rad == pytest.approx(0.0028)

    def test_conversao_fase_para_temperatura(self):
        # fase X rad → X · 0.0028 °C (rota legada process())
        proc = _lfdas_fast()
        fase_rad = 2.0
        data = np.full((40, 8), fase_rad)
        result = proc.process(data, trace_interval_s=0.1)
        assert result["temperature"][10, 4] == pytest.approx(fase_rad * 0.0028, rel=1e-6)
        assert result["metadata"]["thermal_coefficient"] == pytest.approx(0.0028)

    def test_conversao_process_lf(self):
        proc = _lfdas_fast()
        t = np.arange(400) / 10.0
        data = 0.5 * np.sin(2.0 * np.pi * 0.3 * t)[:, None] * np.ones((1, 8))
        result = proc.process_lf(data, trace_interval_s=0.1)
        assert result["metadata"]["thermal_coefficient"] == pytest.approx(0.0028)
        # amplitude preservada pela banda (0.3 Hz está em 0.05–1.0 Hz);
        # mede no miolo do sinal para evitar transientes de borda do filtro
        recuperado = result["temperature"][:, 0] / 0.0028
        assert np.abs(recuperado[100:300]).max() == pytest.approx(0.5, rel=0.15)

    def test_parametro_construtor_rejeita_nao_positivo(self):
        with pytest.raises(ValueError, match="thermal_coefficient"):
            _lfdas_fast(thermal_coefficient_c_per_rad=-1.0)


class TestRotaLF:
    """SP:C-03 (i, ii) — demean obrigatório e detector de unwrap jumps."""

    def test_process_lf_remove_dc(self):
        proc = _lfdas_fast()
        data = np.full((50, 6), 3.0)  # constante: puro DC
        result = proc.process_lf(data, trace_interval_s=0.1)
        assert np.abs(result["temperature"]).max() < 1e-12

    def test_unwrap_jumps_flagados(self):
        proc = _lfdas_fast()
        t = np.arange(60) / 10.0
        data = 0.1 * np.sin(2.0 * np.pi * 0.2 * t)[:, None] * np.ones((1, 6))
        data[25, 3] += 2.0 * np.pi  # salto de unwrapping espúrio
        result = proc.process_lf(data, trace_interval_s=0.1)
        jumps = result["quality_flags"]["unwrap_jumps"]
        assert (24, 3) in jumps  # índice sobre np.diff: salto entre t=24 e t=25
        assert all(z == 3 for _, z in jumps)  # somente o canal afetado

    def test_sem_saltos_nao_flaga(self):
        proc = _lfdas_fast()
        t = np.arange(60) / 10.0
        data = 0.5 * np.sin(2.0 * np.pi * 0.4 * t)[:, None] * np.ones((1, 6))
        result = proc.process_lf(data, trace_interval_s=0.1)
        assert result["quality_flags"]["unwrap_jumps"] == []

    def test_salto_menor_que_08_2pi_nao_flaga(self):
        proc = _lfdas_fast()
        data = np.zeros((60, 6))
        data[25, 3] += np.pi  # 0.5·2π < 0.8·2π: não é salto de unwrap
        result = proc.process_lf(data, trace_interval_s=0.1)
        assert result["quality_flags"]["unwrap_jumps"] == []

    def test_banda_lf_configuravel_validada(self):
        with pytest.raises(ValueError, match="lf_band_hz"):
            _lfdas_fast(lf_band_hz=(0.05, 8.0))  # high > Nyquist (5 Hz)


class TestRotaHF:
    """SP:C-03 (iii) — clipping de transientes HF."""

    def test_clipping_conta_transientes(self):
        proc = _lfdas_fast()
        rng = np.random.default_rng(0)
        data = rng.normal(0.0, 1.0, (300, 8))
        data[30, 1] = 60.0
        data[200, 5] = -55.0
        result = proc.process_hf(data)
        assert result["quality_flags"]["clipped_samples"] == 2
        limite = result["metadata"]["clip_limit"]
        assert np.abs(result["hf_data"]).max() <= limite + 1e-12

    def test_sem_transientes_nao_clipa(self):
        proc = _lfdas_fast()
        rng = np.random.default_rng(1)
        data = rng.normal(0.0, 0.1, (300, 8))
        result = proc.process_hf(data)
        assert result["quality_flags"]["clipped_samples"] == 0

    def test_hf_isola_banda_alta(self):
        proc = _lfdas_fast(sampling_rate_hz=20.0)
        t = np.arange(400) / 20.0
        data = np.sin(2.0 * np.pi * 0.3 * t)[:, None] * np.ones((1, 4))
        data += 0.5 * np.sin(2.0 * np.pi * 5.0 * t)[:, None] * np.ones((1, 4))
        result = proc.process_hf(data)
        f, psd = scipy_signal.welch(result["hf_data"][:, 0], fs=20.0, nperseg=128)
        assert f[np.argmax(psd)] == pytest.approx(5.0, abs=0.5)
        assert psd[f < 2.0].sum() < 0.05 * psd.sum()  # banda ≤ 1 Hz removida


class TestDTSMascaraEAtenuacao:
    """SP:C-04/SP:C-05 — máscara de ponta, atenuação single-ended e flags."""

    @staticmethod
    def _campo_com_deriva():
        # Fundo térmico com deriva linear-in-distância de 0.6 °C/m (40 canais @ 0.5 m)
        return 20.0 + 0.6 * (np.arange(40) * 0.5)[None, :] + np.zeros((10, 40))

    def test_mascara_ponta_numpy_fallback(self, monkeypatch):
        monkeypatch.setattr(dts_mod, "_CPP_ONDA2_DISPONIVEL", False)
        proc = DTSThermalProcessor(depth_step_m=0.5, use_cpp_backend=False,
                                   mask_end_meters=5.0, spatial_median_window=1)
        result = proc.process(self._campo_com_deriva())
        corrigido = result["temperature_corrected"]
        assert np.isnan(corrigido[:, 30:]).all()      # últimos 5 m mascarados
        assert np.isfinite(corrigido[:, :30]).all()   # restante íntegro
        assert result["metadata"]["end_mask_m"] == pytest.approx(5.0)
        assert result["metadata"]["mask_backend"] == "numpy"

    def test_atenuacao_single_ended_numpy_fallback(self, monkeypatch):
        monkeypatch.setattr(dts_mod, "_CPP_ONDA2_DISPONIVEL", False)
        proc = DTSThermalProcessor(depth_step_m=0.5, use_cpp_backend=False,
                                   attenuation_correction=True,
                                   reference_zone_m=(2.0, 8.0),
                                   spatial_median_window=1)
        result = proc.process(self._campo_com_deriva())
        att = result["metadata"]["attenuation"]
        assert att["enabled"] is True
        assert att["slope_per_m"] == pytest.approx(0.6, rel=1e-3)
        assert att["backend"] == "numpy"
        # campo corrigido ≈ 0 antes da remoção do baseline geotérmico
        assert np.abs(result["temperature_preprocessed"]).max() < 1e-6

    def test_mascara_e_atenuacao_backend_cpp(self):
        # Mesmos cenários com o alakoro_core disponível (caminho default)
        proc = DTSThermalProcessor(depth_step_m=0.5, use_cpp_backend=False,
                                   attenuation_correction=True,
                                   reference_zone_m=(2.0, 8.0),
                                   mask_end_meters=5.0,
                                   spatial_median_window=1)
        result = proc.process(self._campo_com_deriva())
        assert result["metadata"]["attenuation"]["backend"] == "cpp"
        assert result["metadata"]["attenuation"]["slope_per_m"] == pytest.approx(0.6, rel=1e-3)
        assert np.isnan(result["temperature_corrected"][:, 30:]).all()
        assert np.abs(result["temperature_preprocessed"][:, :30]).max() < 1e-6

    def test_quality_flags_dts(self):
        n_t, n_z = 64, 12
        campo = 20.0 + 0.03 * np.arange(n_z)[None, :] + 0.5 * np.random.default_rng(2).normal(
            size=(n_t, n_z)
        )
        campo[:, 7] = 25.0  # canal morto (constante)
        proc = DTSThermalProcessor(use_cpp_backend=False, spatial_median_window=1)
        result = proc.process(campo)

        snr = result["quality_flags"]["snr_db"]
        assert snr.shape == (n_z,)
        assert np.isnan(snr[7]) or np.isfinite(snr[7])
        assert np.all(np.isfinite(snr[np.arange(n_z) != 7]))

        dead = result["quality_flags"]["dead_channel_mask"]
        assert dead.shape == (n_z,)
        assert dead[7]
        assert not dead[3]

        # expostos também em self.quality_flags
        assert proc.quality_flags["dead_channel_mask"][7]


class TestExtracaoBandas:
    """PP:A-03 — extract_lfdas / extract_hf_das isolam as bandas (PSD)."""

    @staticmethod
    def _das_duas_bandas(fs=20.0, n_t=800):
        t = np.arange(n_t) / fs
        data = np.sin(2.0 * np.pi * 0.3 * t)[:, None] * np.ones((1, 6))   # LF
        data += 0.5 * np.sin(2.0 * np.pi * 5.0 * t)[:, None] * np.ones((1, 6))  # HF
        return data

    def test_extract_lfdas_isola_banda(self):
        data = self._das_duas_bandas()
        lf = extract_lfdas(data, fs_hz=20.0)
        assert lf.shape == data.shape
        f, psd = scipy_signal.welch(lf[:, 0], fs=20.0, nperseg=256)
        assert f[np.argmax(psd)] == pytest.approx(0.3, abs=0.2)
        assert psd[f > 2.0].sum() < 0.05 * psd.sum()  # HF fortemente atenuado

    def test_extract_hf_das_isola_banda(self):
        data = self._das_duas_bandas()
        hf = extract_hf_das(data, fs_hz=20.0)
        assert hf.shape == data.shape
        f, psd = scipy_signal.welch(hf[:, 0], fs=20.0, nperseg=256)
        assert f[np.argmax(psd)] == pytest.approx(5.0, abs=0.5)
        assert psd[f < 2.0].sum() < 0.05 * psd.sum()  # LF removida

    def test_banda_customizavel(self):
        data = self._das_duas_bandas()
        lf = extract_lfdas(data, fs_hz=20.0, band_hz=(0.2, 0.5))
        f, psd = scipy_signal.welch(lf[:, 0], fs=20.0, nperseg=256)
        assert f[np.argmax(psd)] == pytest.approx(0.3, abs=0.2)

    def test_banda_invalida_rejeitada(self):
        data = self._das_duas_bandas()
        with pytest.raises(ValueError, match="Banda"):
            extract_lfdas(data, fs_hz=20.0, band_hz=(0.05, 15.0))  # high > Nyquist
