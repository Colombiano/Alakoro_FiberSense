"""
Alakoro FiberSense — Test Suite Unitário v1.1.0
Unit Test Suite

Autor/Author: Luiz Paulo Colombiano
Data/Date: 2026-07-18
Licença/License: MIT

Cobertura: 15 assinaturas + LF-DAS + Validator + Schema
Coverage: 15 signatures + LF-DAS + Validator + Schema
"""

import pytest
import numpy as np
import json
import uuid
from datetime import datetime

from src.simulation.signature_generator import (
    SignatureGenerator, WellGeometry, AcquisitionConfig,
    EventSignatureType, SurveyPhaseType
)
from src.processing.lfdas_processor import LFDASProcessor
from src.validation.signature_validator import SignatureValidator


# ═══════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def well():
    return WellGeometry(depth_top=0, depth_bottom=3000, n_channels=3000)

@pytest.fixture
def acq():
    return AcquisitionConfig(sampling_rate_hz=1000, trace_interval_s=2.0, duration_s=3600)

@pytest.fixture
def generator(well, acq):
    return SignatureGenerator(well, acq)

@pytest.fixture
def validator(well, acq):
    return SignatureValidator(well, acq)

@pytest.fixture
def lfdas():
    return LFDASProcessor(cutoff_hz=1.0, refresh_rate_target_s=2.0)


# ═══════════════════════════════════════════════════════════
# TESTES DE ESTRUTURA / STRUCTURE TESTS
# ═══════════════════════════════════════════════════════════

class TestWellGeometry:
    def test_depth_array_shape(self, well):
        assert well.depth_array.shape == (well.n_channels,)
        assert well.depth_array[0] == well.depth_top
        assert well.depth_array[-1] == well.depth_bottom

    def test_channel_spacing(self, well):
        expected_spacing = (well.depth_bottom - well.depth_top) / (well.n_channels - 1)
        assert np.isclose(well.channel_spacing, expected_spacing, rtol=0.01)


class TestAcquisitionConfig:
    def test_n_time_samples(self, acq):
        expected = int(acq.duration_s / acq.trace_interval_s)
        assert acq.n_time_samples == expected

    def test_sampling_parameters(self, acq):
        assert acq.sampling_rate_hz == 1000.0
        assert acq.trace_interval_s == 2.0
        assert acq.duration_s == 3600.0


# ═══════════════════════════════════════════════════════════
# TESTES DAS 15 ASSINATURAS / 15 SIGNATURES TESTS
# ═══════════════════════════════════════════════════════════

class TestSignatures:
    """Testa todas as 15 assinaturas canônicas / Tests all 15 canonical signatures"""

    def _assert_signature_structure(self, sig, expected_type):
        assert sig['signature_type'] == expected_type
        assert sig['dts'].shape == (1800, 3000)
        assert sig['das'].shape == (1800, 3000)
        assert 'parameters' in sig
        assert not np.any(np.isnan(sig['dts']))
        assert not np.any(np.isinf(sig['dts']))
        assert not np.any(np.isnan(sig['das']))
        assert not np.any(np.isinf(sig['das']))

    def test_joule_thomson(self, generator):
        sig = generator.generate_joule_thomson(interface_depth=1500.0)
        self._assert_signature_structure(sig, EventSignatureType.JOULE_THOMSON)
        assert sig['parameters']['interface_depth_m'] == 1500.0

    def test_slope_velocity(self, generator):
        sig = generator.generate_slope_velocity(flow_start_depth=1000.0)
        self._assert_signature_structure(sig, EventSignatureType.SLOPE_VELOCITY)
        assert sig['parameters']['flow_start_depth_m'] == 1000.0

    def test_warm_back(self, generator):
        sig = generator.generate_warm_back(injection_depths=[1200.0, 1500.0])
        self._assert_signature_structure(sig, EventSignatureType.WARM_BACK)
        assert len(sig['parameters']['injection_depths_m']) == 2

    def test_valve_chatter(self, generator):
        sig = generator.generate_valve_chatter(valve_depth=1400.0)
        self._assert_signature_structure(sig, EventSignatureType.VALVE_CHATTER)
        assert sig['parameters']['valve_depth_m'] == 1400.0

    def test_slugging_cycle(self, generator):
        sig = generator.generate_slugging_cycle(slug_depth_range=(1000.0, 2000.0))
        self._assert_signature_structure(sig, EventSignatureType.SLUGGING_CYCLE)

    def test_leak_path(self, generator):
        sig = generator.generate_leak_path(leak_depth=1914.0)
        self._assert_signature_structure(sig, EventSignatureType.LEAK_PATH)
        assert sig['parameters']['leak_depth_m'] == 1914.0

    def test_glv_bellow_rupture(self, generator):
        sig = generator.generate_glv_bellow_rupture(valve_depth=1400.0, n_valves=5)
        self._assert_signature_structure(sig, EventSignatureType.GLV_BELLOW_RUPTURE)
        assert len(sig['parameters']['valve_depths_m']) == 5

    def test_perforation_effectiveness(self, generator):
        sig = generator.generate_perforation_effectiveness(
            perf_depths=[(1500.0, 1520.0)], effective_perfs=[True])
        self._assert_signature_structure(sig, EventSignatureType.PERFORATION_EFFECTIVENESS)

    def test_frac_screenout(self, generator):
        sig = generator.generate_frac_screenout(perf_depth=2000.0)
        self._assert_signature_structure(sig, EventSignatureType.FRAC_SCREENOUT)
        assert sig['parameters']['perf_depth_m'] == 2000.0

    def test_frac_proppant_distribution(self, generator):
        sig = generator.generate_frac_proppant_distribution(perf_depth=2000.0)
        self._assert_signature_structure(sig, EventSignatureType.FRAC_PROPPANT_DISTRIBUTION)
        assert len(sig['parameters']['proppant_stages']) == 5

    def test_frac_height_growth(self, generator):
        sig = generator.generate_frac_height_growth(perf_depth=2000.0)
        self._assert_signature_structure(sig, EventSignatureType.FRAC_HEIGHT_GROWTH)
        assert sig['parameters']['target_height_m'] == 80.0

    def test_cement_bond_evaluation(self, generator):
        sig = generator.generate_cement_bond_evaluation()
        self._assert_signature_structure(sig, EventSignatureType.CEMENT_BOND_EVALUATION)
        assert len(sig['parameters']['cement_quality']) == 5

    def test_re_cementing_assessment(self, generator):
        sig = generator.generate_re_cementing_assessment()
        self._assert_signature_structure(sig, EventSignatureType.RE_CEMENTING_ASSESSMENT)
        assert len(sig['parameters']['squeeze_zones']) == 2

    def test_crossflow_zonal(self, generator):
        sig = generator.generate_crossflow_zonal(zone_depths=[1200.0, 1800.0])
        self._assert_signature_structure(sig, EventSignatureType.CROSSFLOW_ZONAL)
        assert len(sig['parameters']['zone_depths_m']) == 2

    def test_cement_channeling(self, generator):
        sig = generator.generate_cement_channeling(channel_depths=[1300.0, 1700.0])
        self._assert_signature_structure(sig, EventSignatureType.CEMENT_CHANNELING)
        assert len(sig['parameters']['channel_depths_m']) == 2


# ═══════════════════════════════════════════════════════════
# TESTES LF-DAS / LF-DAS TESTS
# ═══════════════════════════════════════════════════════════

class TestLFDASProcessor:
    def test_init_defaults(self, lfdas):
        assert lfdas.cutoff_hz == 1.0
        assert lfdas.refresh_rate_target_s == 2.0
        assert lfdas.decimation_factor == 2000
        assert lfdas.refresh_rate_s == 2.0

    def test_process_shape(self, generator, lfdas):
        sig = generator.generate_joule_thomson()
        result = lfdas.process(sig['das'], trace_interval_s=2.0)
        assert result['temperature'].shape[1] == 3000
        assert result['refresh_rate_s'] == 2.0
        assert result['metadata']['refresh_rate_target_s'] == 2.0
        assert result['metadata']['refresh_rate_actual_s'] == 2.0

    def test_thermal_coefficient(self, generator, lfdas):
        sig = generator.generate_joule_thomson()
        result = lfdas.process(sig['das'], trace_interval_s=2.0)
        assert result['metadata']['thermal_coefficient'] == 100.0

    def test_compute_relative_difference(self, generator, lfdas):
        sig = generator.generate_joule_thomson()
        result = lfdas.process(sig['das'], trace_interval_s=2.0)
        rel_diff = lfdas.compute_relative_difference(result['temperature'])
        assert rel_diff.shape == result['temperature'].shape

    def test_compute_dtdz(self, generator, lfdas, well):
        sig = generator.generate_joule_thomson()
        result = lfdas.process(sig['das'], trace_interval_s=2.0)
        dtdz = lfdas.compute_dtdz(result['temperature'], well.depth_array)
        assert dtdz.shape == result['temperature'].shape


# ═══════════════════════════════════════════════════════════
# TESTES DE VALIDAÇÃO / VALIDATOR TESTS
# ═══════════════════════════════════════════════════════════

class TestSignatureValidator:
    def test_thresholds_configurable(self, validator):
        assert validator.MIN_SNR_DB == 0.5
        assert validator.LOC_TOLERANCE_M == 150.0
        assert validator.LF_DAS_MIN_AMP == 0.0

    def test_validate_joule_thomson(self, generator, validator, lfdas):
        sig = generator.generate_joule_thomson(interface_depth=1500.0)
        lfdas_result = lfdas.process(sig['das'], trace_interval_s=2.0)
        result = validator.validate_signature(sig, lfdas_result)

        assert result['signature'] == 'dipolo_thermal_jt'
        assert result['total'] >= 6
        assert result['success_rate'] >= 85.0

        localization_tests = [t for t in result['tests'] if 'interface' in t['message']]
        if localization_tests:
            assert localization_tests[0]['passed'], f"Localização falhou: {localization_tests[0]['message']}"

    def test_validate_all_signatures(self, generator, validator):
        signatures = {
            'jt': generator.generate_joule_thomson(),
            'sv': generator.generate_slope_velocity(),
            'wb': generator.generate_warm_back(),
            'vc': generator.generate_valve_chatter(),
            'sc': generator.generate_slugging_cycle(),
            'lp': generator.generate_leak_path(),
            'glv': generator.generate_glv_bellow_rupture(),
            'pe': generator.generate_perforation_effectiveness(),
            'fs': generator.generate_frac_screenout(),
            'fp': generator.generate_frac_proppant_distribution(),
            'fh': generator.generate_frac_height_growth(),
            'cb': generator.generate_cement_bond_evaluation(),
            'rc': generator.generate_re_cementing_assessment(),
            'cf': generator.generate_crossflow_zonal(),
            'cc': generator.generate_cement_channeling(),
        }

        all_results, success_rate = validator.run_full_validation(signatures)
        assert len(all_results) == 15
        assert success_rate >= 85.0, f"Taxa de sucesso {success_rate:.1f}% abaixo de 85%"

    def test_thermal_gradient_check(self, generator, validator):
        sig = generator.generate_joule_thomson()
        result = validator.validate_signature(sig)
        gradient_tests = [t for t in result['tests'] if 'Gradiente' in t['message']]
        assert len(gradient_tests) > 0
        assert gradient_tests[0]['passed']


# ═══════════════════════════════════════════════════════════
# TESTES DE SCHEMA JSON / JSON SCHEMA TESTS
# ═══════════════════════════════════════════════════════════

class TestEventSchema:
    def test_schema_version(self):
        from src.events import EVENT_SCHEMA
        assert EVENT_SCHEMA is not None
        assert EVENT_SCHEMA['version'] == '1.1.0'

    def test_required_fields(self):
        from src.events import EVENT_SCHEMA
        required = EVENT_SCHEMA['required']
        assert 'event_id' in required
        assert 'event_type' in required
        assert 'timestamp' in required
        assert 'version' in required
        assert 'payload' in required

    def test_event_types_coverage(self):
        from src.events import EVENT_SCHEMA
        event_types = EVENT_SCHEMA['properties']['event_type']['enum']
        assert len(event_types) == 18
        assert 'WarmBackDetected' in event_types
        assert 'PerforationEffectivenessEvaluated' in event_types
        assert 'ProppantDistributionMapped' in event_types
        assert 'FractureHeightGrowthDetected' in event_types

    def test_payload_structure(self):
        from src.events import EVENT_SCHEMA
        payload = EVENT_SCHEMA['properties']['payload']
        assert 'survey_id' in payload['required']
        assert 'well_id' in payload['required']
        assert 'survey_phase' in payload['properties']

    def test_valid_event_example(self):
        from src.events import EVENT_SCHEMA
        event = {
            'event_id': str(uuid.uuid4()),
            'event_type': 'JouleThomsonSignature',
            'timestamp': datetime.now().isoformat(),
            'version': '1.1.0',
            'payload': {
                'survey_id': 'SURV-001',
                'well_id': 'WELL-42',
                'survey_phase': 'Baseline',
                'depth_md': 1500.0,
                'evidence': [
                    {'type': 'thermal_dipole', 'channel_range': [1400, 1600], 'confidence': 0.95}
                ],
                'estimates': [
                    {'parameter': 'interface_depth', 'value': 1500.0, 'unit': 'm', 'uncertainty': 10.0}
                ],
                'diagnosis': {
                    'severity': 'Medium',
                    'recommendation': 'Monitorar pressão do ânulo',
                    'confidence_score': 0.92
                }
            }
        }
        assert event['event_type'] in EVENT_SCHEMA['properties']['event_type']['enum']
        assert event['version'] == EVENT_SCHEMA['version']


# ═══════════════════════════════════════════════════════════
# TESTES DE INTEGRAÇÃO / INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════

class TestIntegration:
    def test_full_pipeline(self, well, acq, generator, lfdas, validator):
        sig = generator.generate_joule_thomson(interface_depth=1500.0)
        lfdas_result = lfdas.process(sig['das'], trace_interval_s=acq.trace_interval_s)
        result = validator.validate_signature(sig, lfdas_result)
        assert result['success_rate'] >= 85.0
        assert result['passed'] >= 6

    def test_signature_to_event_mapping(self, generator):
        mapping = {
            EventSignatureType.JOULE_THOMSON: 'JouleThomsonSignature',
            EventSignatureType.WARM_BACK: 'WarmBackDetected',
            EventSignatureType.PERFORATION_EFFECTIVENESS: 'PerforationEffectivenessEvaluated',
            EventSignatureType.FRAC_PROPPANT_DISTRIBUTION: 'ProppantDistributionMapped',
            EventSignatureType.FRAC_HEIGHT_GROWTH: 'FractureHeightGrowthDetected',
        }

        from src.events import EVENT_SCHEMA
        event_types = EVENT_SCHEMA['properties']['event_type']['enum']

        for sig_type, event_type in mapping.items():
            assert event_type in event_types, f"{event_type} não encontrado no schema"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
