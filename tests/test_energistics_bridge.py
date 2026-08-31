"""
Testes da ponte semantica Energistics (ProdML ↔ WITSML).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from src.io import energistics_bridge as bridge
from src.io.alakoro_spool import AlakoroPatch
from src.io.dasdae import DASDAEAdapter
from src.io import prodml, witsml


def _make_patch(n_t=10, n_c=3) -> AlakoroPatch:
    data = np.random.randn(n_t, n_c)
    dc_patch = DASDAEAdapter.array_to_patch(
        data, modality="das", dt_s=0.001, dx_m=1.0, units="1/s"
    )
    return AlakoroPatch(dc_patch, well_id="W-01", modality="das")


def _make_well_xml(path: Path, uid: str = "W-01", name: str = "Well-01"):
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<witsml:wells xmlns:witsml="http://www.witsml.org/schemas/141" version="1.4.1.1">
  <witsml:well uid="{uid}">
    <witsml:name>{name}</witsml:name>
    <witsml:field>Campo-01</witsml:field>
    <witsml:country>Brasil</witsml:country>
    <witsml:operator>Op-01</witsml:operator>
  </witsml:well>
</witsml:wells>
"""
    path.write_text(xml, encoding="utf-8")


def _make_wellbore_xml(path: Path, uid: str = "WB-01", well_uid: str = "W-01"):
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<witsml:wellbores xmlns:witsml="http://www.witsml.org/schemas/141" version="1.4.1.1">
  <witsml:wellbore uid="{uid}">
    <witsml:name>{uid}</witsml:name>
    <witsml:nameWell>{well_uid}</witsml:nameWell>
  </witsml:wellbore>
</witsml:wellbores>
"""
    path.write_text(xml, encoding="utf-8")


def test_from_alakoro_patch():
    patch = _make_patch(n_t=8, n_c=2)
    acquisition = bridge.from_alakoro_patch(patch)

    assert acquisition.shape == (8, 2)
    assert acquisition.modality == "das"
    assert acquisition.sampling_rate_hz == 1000.0
    assert acquisition.well.uid == "W-01"
    assert len(acquisition.channels) == 2


def test_sensing_acquisition_to_alakoro_patch():
    data = np.random.randn(5, 4)
    acquisition = bridge.SensingAcquisition(
        data=data,
        modality="dts",
        units="degC",
        sampling_rate_hz=500.0,
        spatial_resolution_m=2.0,
        gauge_length_m=10.0,
        well=bridge.WellReference(uid="W-02", name="Well-02"),
        wellbore=bridge.WellboreReference(uid="WB-02", name="WB-02", well_uid="W-02"),
    )
    patch = acquisition.to_alakoro_patch()

    assert patch.shape == (5, 4)
    assert patch.modality == "dts"
    assert patch.well_id == "W-02"
    np.testing.assert_allclose(patch.data, data)


def test_cross_reference_prodml_with_witsml():
    patch = _make_patch(n_t=6, n_c=2)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        prodml_path = tmp / "acq.prodml"
        well_path = tmp / "well.witsml"
        wellbore_path = tmp / "wellbore.witsml"

        prodml.write(patch, prodml_path)
        _make_well_xml(well_path)
        _make_wellbore_xml(wellbore_path)

        acquisition = bridge.cross_reference(prodml_path, well_path, wellbore_path)

        assert acquisition.shape == (6, 2)
        assert acquisition.well.uid == "W-01"
        assert acquisition.well.name == "Well-01"
        assert acquisition.well.country == "Brasil"
        assert acquisition.wellbore.uid == "WB-01"
        assert acquisition.wellbore.well_uid == "W-01"
        assert acquisition.source_format == "prodml"


def test_cross_reference_mismatch_raises():
    patch = _make_patch()

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        prodml_path = tmp / "acq.prodml"
        well_path = tmp / "well.witsml"

        prodml.write(patch, prodml_path, well_id="W-99")
        _make_well_xml(well_path, uid="W-01")

        with pytest.raises(ValueError):
            bridge.cross_reference(prodml_path, well_path)


def test_roundtrip_prodml_via_bridge():
    data = np.random.randn(7, 2)
    acquisition = bridge.SensingAcquisition(
        data=data,
        modality="das",
        units="1/s",
        sampling_rate_hz=1000.0,
        spatial_resolution_m=1.0,
        well=bridge.WellReference(uid="W-03", name="Well-03"),
        wellbore=bridge.WellboreReference(uid="WB-03", name="WB-03", well_uid="W-03"),
    )

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "round.prodml"
        bridge.to_prodml(acquisition, path)
        back = bridge.cross_reference(path)

        assert back.shape == (7, 2)
        assert back.well.uid == "W-03"
        assert back.wellbore.uid == "WB-03"
        np.testing.assert_allclose(back.data, data, rtol=1e-4)


def test_roundtrip_witsml_via_bridge():
    data = np.random.randn(5, 3)
    acquisition = bridge.SensingAcquisition(
        data=data,
        modality="das",
        units="1/s",
        sampling_rate_hz=1000.0,
        well=bridge.WellReference(uid="W-04", name="Well-04"),
        wellbore=bridge.WellboreReference(uid="WB-04", name="WB-04", well_uid="W-04"),
        channels=[
            bridge.ChannelInfo(mnemonic="CH0", unit="1/s", index=0),
            bridge.ChannelInfo(mnemonic="CH1", unit="1/s", index=1),
            bridge.ChannelInfo(mnemonic="CH2", unit="1/s", index=2),
        ],
    )

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "round.witsml"
        bridge.to_witsml_log(acquisition, path, log_name="DAS-04")
        back = bridge.from_witsml_log(path)

        assert back.shape == (5, 3)
        assert back.well.uid == "W-04"
        np.testing.assert_allclose(back.data, data, rtol=1e-4)


def test_from_witsml_log_enriched_by_prodml():
    patch = _make_patch(n_t=4, n_c=2)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        log_path = tmp / "log.witsml"
        prodml_path = tmp / "acq.prodml"

        witsml.write_log(patch, log_path, well_id="W-05", wellbore_id="WB-05")
        prodml.write(patch, prodml_path)

        back = bridge.from_witsml_log(log_path, prodml_path)

        assert back.shape == (4, 2)
        assert back.well.uid == "W-05"
        assert back.source_format == "witsml"
