"""
Alakoro FiberSense — Testes das correcoes de auditoria do cluster CL-06 (I/O)

Cobre:
- IN:B-01: inferencia de modality no WITSML read_log a partir do logCurveInfo
- IN:J-02: MQTT marcado como experimental (NotImplementedError) + schema Avro
  com well_id/wellbore_id em round-trip
- IN:J-04: metadados de deployment_type validados no writer ProdML
- IN:B-03: gauge length em round-trip WITSML
- Adicional: AlakoroSpool.chunk respeitando dt_s
- Adicional: write_xdas/read_xdas com well_id, wellbore_id e modality
- Adicional: prodml.read preserva gauge_length_m
"""

import tempfile
import warnings
from pathlib import Path

import numpy as np
import pytest

from alakoro.io import prodml, witsml
from alakoro.io.alakoro_spool import (
    AlakoroPatch,
    AlakoroSpool,
    validate_deployment_metadata,
)
from alakoro.io.avro_format import deserialize_avro
from alakoro.io.dasdae import DASDAEAdapter
from alakoro.io.streaming import MQTTStreamDriver
from alakoro.io.xdas_formats import read_xdas, write_xdas


def _make_patch(n_t=16, n_c=4, modality="das", dt_s=0.5, well_id="W-01") -> AlakoroPatch:
    data = np.random.default_rng(42).standard_normal((n_t, n_c))
    dc_patch = DASDAEAdapter.array_to_patch(data, modality=modality, dt_s=dt_s, dx_m=1.0)
    return AlakoroPatch(dc_patch, well_id=well_id, modality=modality)


def _make_witsml_log_xml(mnemonic: str, unit: str, uid: str = "L-01", name: str = "Log-01") -> str:
    """XML WITSML minimo inline com um unico canal de dados."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<witsml:logs xmlns:witsml="http://www.witsml.org/schemas/141" version="1.4.1.1">
  <witsml:log uid="{uid}">
    <witsml:name>{name}</witsml:name>
    <witsml:nameWell>W-01</witsml:nameWell>
    <witsml:nameWellbore>WB-01</witsml:nameWellbore>
    <witsml:logCurveInfo uid="TIME">
      <witsml:mnemonic>TIME</witsml:mnemonic>
      <witsml:unit>s</witsml:unit>
    </witsml:logCurveInfo>
    <witsml:logCurveInfo uid="{mnemonic}">
      <witsml:mnemonic>{mnemonic}</witsml:mnemonic>
      <witsml:unit>{unit}</witsml:unit>
    </witsml:logCurveInfo>
    <witsml:data>
0.0,21.5
1.0,21.6
2.0,21.7
3.0,21.8
    </witsml:data>
  </witsml:log>
</witsml:logs>
"""


# ─── IN:B-01 — modality no WITSML ───


class TestWitsmlModalityInference:
    def test_temperature_units_infer_dts(self, tmp_path: Path):
        path = tmp_path / "temp.witsml"
        path.write_text(_make_witsml_log_xml("TEMP", "degC"), encoding="utf-8")

        patch = witsml.read_log(path)
        assert patch.modality == "dts"
        assert patch.attrs.data_category == "dts"

    def test_fahrenheit_temperature_units_infer_dts(self, tmp_path: Path):
        path = tmp_path / "tempf.witsml"
        path.write_text(_make_witsml_log_xml("TEMP", "degF"), encoding="utf-8")

        patch = witsml.read_log(path)
        assert patch.modality == "dts"

    def test_strain_units_infer_dss(self, tmp_path: Path):
        path = tmp_path / "strain.witsml"
        path.write_text(_make_witsml_log_xml("STRAIN", "microstrain"), encoding="utf-8")

        patch = witsml.read_log(path)
        assert patch.modality == "dss"

    def test_acoustic_units_infer_das(self, tmp_path: Path):
        path = tmp_path / "acoustic.witsml"
        path.write_text(_make_witsml_log_xml("AMP", "m/s"), encoding="utf-8")

        patch = witsml.read_log(path)
        assert patch.modality == "das"

    def test_ambiguous_log_falls_back_to_das_with_warning(self, tmp_path: Path):
        path = tmp_path / "amb.witsml"
        path.write_text(_make_witsml_log_xml("LENGTH", "m"), encoding="utf-8")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            patch = witsml.read_log(path)

        assert patch.modality == "das"
        assert any("modality" in str(w.message).lower() for w in caught)

    def test_explicit_modality_overrides_inference(self, tmp_path: Path):
        path = tmp_path / "ovr.witsml"
        path.write_text(_make_witsml_log_xml("TEMP", "degC"), encoding="utf-8")

        patch = witsml.read_log(path, modality="dss")
        assert patch.modality == "dss"


# ─── IN:B-03 — gauge length no WITSML ───


class TestWitsmlGaugeLength:
    def test_gauge_length_roundtrip(self, tmp_path: Path):
        patch = _make_patch(n_t=10, n_c=3)
        path = tmp_path / "gauge.witsml"

        witsml.write_log(patch, path, gauge_length_m=8.5)
        back = witsml.read_log(path)

        assert float(back.attrs.gauge_length_m) == pytest.approx(8.5)

    def test_gauge_length_defaults_to_patch_attrs(self, tmp_path: Path):
        import dascore as dc
        from dascore.core.attrs import PatchAttrs

        data = np.random.default_rng(7).standard_normal((6, 2))
        attrs = PatchAttrs(
            data_category="das",
            data_units="1/s",
            time_step=np.timedelta64(500000, "ns"),
            distance_step=1.0,
            gauge_length_m=12.0,
        )
        dc_patch = dc.Patch(
            data=data,
            coords={
                "time": (np.arange(6) * 500000).astype("timedelta64[ns]"),
                "distance": np.arange(2) * 1.0,
            },
            dims=("time", "distance"),
            attrs=attrs,
        )
        patch = AlakoroPatch(dc_patch, well_id="W-01", modality="das")
        path = tmp_path / "gauge2.witsml"

        witsml.write_log(patch, path)
        back = witsml.read_log(path)

        assert float(back.attrs.gauge_length_m) == pytest.approx(12.0)

    def test_gauge_length_absent_when_not_set(self, tmp_path: Path):
        patch = _make_patch(n_t=6, n_c=2)
        path = tmp_path / "nogauge.witsml"

        witsml.write_log(patch, path)
        back = witsml.read_log(path)

        assert "gauge_length_m" not in dict(back.attrs)


# ─── IN:J-02 — MQTT experimental + Avro well_id ───


class TestMQTTExperimental:
    def test_connect_raises_not_implemented(self):
        driver = MQTTStreamDriver("localhost", port=1883)
        with pytest.raises(NotImplementedError, match="experimental"):
            driver.connect()


class TestAvroWellIds:
    def test_serialize_deserialize_propagates_well_ids(self):
        patch = _make_patch(n_t=8, n_c=3, well_id="W-AVRO")
        patch.wellbore_id = "WB-AVRO"

        payload = patch.to_avro_bytes()
        record = deserialize_avro(payload)

        assert record["well_id"] == "W-AVRO"
        assert record["wellbore_id"] == "WB-AVRO"
        assert record["metadata"]["well_id"] == "W-AVRO"

    def test_from_avro_bytes_roundtrip(self):
        patch = _make_patch(n_t=8, n_c=3, well_id="W-AVRO")
        patch.wellbore_id = "WB-AVRO"

        back = AlakoroPatch.from_avro_bytes(patch.to_avro_bytes())

        assert back.well_id == "W-AVRO"
        assert back.wellbore_id == "WB-AVRO"
        assert back.modality == "das"

    def test_from_avro_bytes_explicit_well_id_wins(self):
        patch = _make_patch(n_t=8, n_c=3, well_id="W-AVRO")

        back = AlakoroPatch.from_avro_bytes(patch.to_avro_bytes(), well_id="W-OVERRIDE")

        assert back.well_id == "W-OVERRIDE"

    def test_serialize_array_without_well_ids(self):
        arr = np.random.default_rng(3).standard_normal((4, 2))
        payload = AlakoroPatch.from_array(arr, modality="das").to_avro_bytes()

        record = deserialize_avro(payload)
        assert record["well_id"] is None
        assert record["wellbore_id"] is None


# ─── IN:J-04 — metadados de deploy ───


class TestDeploymentMetadata:
    def test_invalid_deployment_type_raises(self):
        with pytest.raises(ValueError, match="deployment_type"):
            validate_deployment_metadata(deployment_type="wireline")

    def test_validate_normalizes_and_filters(self):
        meta = validate_deployment_metadata(
            deployment_type="E-Line",
            max_tension_kn=45,
            min_bend_radius_m=0.2,
            fiber_limits={"max_temperature_c": 300},
        )
        assert meta == {
            "deployment_type": "e-line",
            "max_tension_kn": 45.0,
            "min_bend_radius_m": 0.2,
            "fiber_limits": {"max_temperature_c": 300},
        }

    def test_prodml_deployment_roundtrip(self, tmp_path: Path):
        patch = _make_patch(n_t=6, n_c=2)
        path = tmp_path / "deploy.prodml"

        prodml.write(
            patch,
            path,
            deployment_type="slickline",
            max_tension_kn=45.0,
            min_bend_radius_m=0.2,
            fiber_limits={"max_temperature_c": 300},
        )
        back = prodml.read(path)

        assert back.attrs.deployment_type == "slickline"
        assert float(back.attrs.max_tension_kn) == pytest.approx(45.0)
        assert float(back.attrs.min_bend_radius_m) == pytest.approx(0.2)
        assert back.attrs.fiber_limits == {"max_temperature_c": 300}

    def test_prodml_write_invalid_deployment_type_raises(self, tmp_path: Path):
        patch = _make_patch(n_t=6, n_c=2)
        path = tmp_path / "bad.prodml"

        with pytest.raises(ValueError, match="deployment_type"):
            prodml.write(patch, path, deployment_type="cable")

    def test_prodml_without_deployment_stays_clean(self, tmp_path: Path):
        patch = _make_patch(n_t=6, n_c=2)
        path = tmp_path / "plain.prodml"

        prodml.write(patch, path)
        back = prodml.read(path)

        assert "deployment_type" not in dict(back.attrs)
        assert "max_tension_kn" not in dict(back.attrs)
        assert "min_bend_radius_m" not in dict(back.attrs)
        assert "fiber_limits" not in dict(back.attrs)


# ─── Adicional — chunk com dt_s ───


class TestChunkWithDt:
    def test_chunk_interprets_time_as_seconds_when_dt_given(self):
        patch = _make_patch(n_t=16, n_c=2, dt_s=0.25)
        spool = AlakoroSpool([patch])

        chunks = spool.chunk(time=2.0, dt_s=0.25)

        # janela de 2.0 s a 4 Hz => 8 amostras por chunk
        assert [c.shape[0] for c in chunks] == [8, 8]

    def test_chunk_overlap_in_seconds_with_dt(self):
        patch = _make_patch(n_t=12, n_c=2, dt_s=0.5)
        spool = AlakoroSpool([patch])

        chunks = spool.chunk(time=4.0, overlap=2.0, dt_s=0.5)

        # janela 8 amostras, passo 4 amostras: starts 0, 4, 8 => [8, 8, 4]
        assert [c.shape[0] for c in chunks] == [8, 8, 4]

    def test_chunk_without_dt_keeps_sample_based_behavior(self):
        patch = _make_patch(n_t=16, n_c=2, dt_s=0.25)
        spool = AlakoroSpool([patch])

        chunks = spool.chunk(time=2.0)

        # comportamento historico: 2 amostras por chunk
        assert [c.shape[0] for c in chunks] == [2] * 8

    def test_chunk_preserves_modality_and_well(self):
        patch = _make_patch(n_t=16, n_c=2, modality="dts", well_id="W-CH")
        spool = AlakoroSpool([patch])

        chunks = spool.chunk(time=2.0, dt_s=0.25)

        assert all(c.modality == "dts" for c in chunks)
        assert all(c.well_id == "W-CH" for c in chunks)


# ─── Adicional — xdas round-trip de well/wellbore/modality ───


class TestXdasMetadataRoundtrip:
    def test_well_wellbore_modality_roundtrip(self):
        patch = _make_patch(n_t=16, n_c=4, modality="dss", well_id="W-XD")
        patch.wellbore_id = "WB-XD"

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "meta.nc"
            write_xdas(patch, path)
            back = read_xdas(path)

        assert isinstance(back, AlakoroPatch)
        assert back.well_id == "W-XD"
        assert back.wellbore_id == "WB-XD"
        assert back.modality == "dss"
        np.testing.assert_allclose(back.data, patch.data)

    def test_modality_roundtrip_without_explicit_read_args(self):
        patch = _make_patch(n_t=8, n_c=2, modality="dts", well_id="W-DT")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dts.nc"
            write_xdas(patch, path)
            back = read_xdas(path)

        assert back.modality == "dts"
        assert back.well_id == "W-DT"


# ─── Adicional — prodml.read preserva gauge_length_m ───


class TestProdmlGaugeLength:
    def test_gauge_length_read_back(self, tmp_path: Path):
        import dascore as dc
        from dascore.core.attrs import PatchAttrs

        data = np.random.default_rng(11).standard_normal((8, 3))
        attrs = PatchAttrs(
            data_category="das",
            data_units="1/s",
            time_step=np.timedelta64(1000000, "ns"),
            distance_step=1.0,
            gauge_length_m=12.5,
        )
        dc_patch = dc.Patch(
            data=data,
            coords={
                "time": (np.arange(8) * 1e6).astype("timedelta64[ns]"),
                "distance": np.arange(3) * 1.0,
            },
            dims=("time", "distance"),
            attrs=attrs,
        )
        patch = AlakoroPatch(dc_patch, well_id="W-01", modality="das")
        path = tmp_path / "gauge.prodml"

        prodml.write(patch, path)
        back = prodml.read(path)

        assert float(back.attrs.gauge_length_m) == pytest.approx(12.5, abs=1e-4)
