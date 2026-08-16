"""
Alakoro FiberSense — Testes de Ontologia
Ontology Tests
"""

import pytest
from datetime import datetime

from src.ontology import (
    OntologyModel, Well, Wellbore, Completion, FiberOpticCable,
    Interrogator, DASMeasurement, DTSMeasurement, DSSMeasurement,
    JouleThomsonEvent, LeakEvent, FlowEvent, WarmBackEvent,
    SignatureOntologyBridge,
)
from src.simulation import SignatureGenerator, WellGeometry, AcquisitionConfig


@pytest.fixture
def model():
    return OntologyModel()


class TestOntologyModel:
    def test_model_creation(self, model):
        assert model is not None
        assert len(model.graph) > 0

    def test_serialization_turtle(self, model):
        ttl = model.to_turtle()
        assert "alakoro" in ttl
        assert "Entity" in ttl

    def test_serialization_jsonld(self, model):
        jld = model.to_jsonld()
        assert "alakoro" in jld


class TestPetroleumEntities:
    def test_well_wellbore_cable(self, model):
        well = Well(name="Well-01", operator="Alakoro", field="Campo A")
        wellbore = Wellbore(name="WB-01", measured_depth_top=0.0, measured_depth_bottom=3000.0)
        cable = FiberOpticCable(name="Fiber-01", depth_top=0.0, depth_bottom=3000.0, n_channels=3000)
        completion = Completion(name="Compl-01", completion_type="cased_hole")

        well.add_wellbore(wellbore)
        wellbore.add_cable(cable)
        wellbore.add_completion(completion)

        model.add(well)
        ttl = model.to_turtle()

        assert "Well-01" in ttl
        assert "WB-01" in ttl
        assert "Fiber-01" in ttl
        assert "Compl-01" in ttl


class TestSensingEntities:
    def test_das_dts_dss_measurements(self, model):
        well = Well(name="Well-02")
        wellbore = Wellbore(name="WB-02", measured_depth_top=0.0, measured_depth_bottom=2000.0)
        well.add_wellbore(wellbore)

        interrogator = Interrogator(name="Interrogator-01", manufacturer="Alakoro", model="Sim")
        das = DASMeasurement(name="DAS-01", n_channels=1000, n_time_samples=500, sampling_rate_hz=1000.0)
        dts = DTSMeasurement(name="DTS-01", n_channels=1000, n_time_samples=100, spatial_resolution_m=1.0)
        dss = DSSMeasurement(name="DSS-01", n_channels=1000, n_time_samples=100)

        das.wellbore = wellbore
        dts.wellbore = wellbore
        dss.wellbore = wellbore
        das.interrogator = interrogator

        model.add(well)
        model.add(interrogator)
        model.add(das)
        model.add(dts)
        model.add(dss)

        ttl = model.to_turtle()
        assert "DAS-01" in ttl
        assert "DTS-01" in ttl
        assert "DSS-01" in ttl


class TestEvents:
    def test_joule_thomson_event(self, model):
        event = JouleThomsonEvent(interface_depth=1500.0, confidence=0.92, severity="Medium")
        model.add(event)
        ttl = model.to_turtle()
        assert "JouleThomsonEvent" in ttl or "Joule-Thomson" in ttl

    def test_leak_event(self, model):
        event = LeakEvent(leak_depth=1914.0, confidence=0.85, severity="High")
        model.add(event)
        ttl = model.to_turtle()
        assert "Leak" in ttl or "leak" in ttl


class TestSignatureOntologyBridge:
    def test_bridge_joule_thomson(self):
        well_geom = WellGeometry(depth_top=0, depth_bottom=3000, n_channels=3000)
        acq = AcquisitionConfig(sampling_rate_hz=1000, trace_interval_s=2.0, duration_s=60)
        generator = SignatureGenerator(well_geom, acq)
        signature = generator.generate_joule_thomson(interface_depth=1500.0)

        bridge = SignatureOntologyBridge()
        model = bridge.build_from_signature(signature)
        ttl = model.to_turtle()

        assert "Synthetic Well" in ttl
        assert "Joule-Thomson" in ttl
        assert "1500.0" in ttl

    def test_bridge_warm_back(self):
        well_geom = WellGeometry(depth_top=0, depth_bottom=3000, n_channels=3000)
        acq = AcquisitionConfig(sampling_rate_hz=1000, trace_interval_s=2.0, duration_s=60)
        generator = SignatureGenerator(well_geom, acq)
        signature = generator.generate_warm_back(injection_depths=[1200.0, 1500.0])

        bridge = SignatureOntologyBridge()
        model = bridge.build_from_signature(signature)
        ttl = model.to_turtle()

        assert "Warm-Back" in ttl
