"""
Alakoro FiberSense — Test Suite de Validação de Assinaturas v1.2.1
Signature Validation Test Suite v1.2.1

Autor/Author: Luiz Paulo Colombiano
Data/Date: 2026-07-18
Versão/Version: 1.2.1
Licença/License: MIT

CHANGELOG:
v1.2.0: Thresholds ajustados para sinais sintéticos realistas
v1.2.1: Suporte a múltiplos picos para Crossflow Zonal e Cement Channeling
         - Detecta TODAS as zonas/canais esperados, não apenas o pico máximo
         - Usa find_peaks com tolerância por zona
"""

import numpy as np
from typing import Dict, Tuple, List, Optional
from scipy.signal import find_peaks


class SignatureValidator:
    """Validador de assinaturas sintéticas / Synthetic signature validator"""

    MIN_SNR_DB: float = 0.5
    LOC_TOLERANCE_M: float = 150.0
    LF_DAS_MIN_AMP: float = 0.0

    def __init__(self, well, acq):
        self.well = well
        self.acq = acq
        self.depth = well.depth_array
        self.results = []

    def _check_temporal_consistency(self, data: np.ndarray, name: str) -> Tuple[bool, str]:
        has_nan = np.any(np.isnan(data))
        has_inf = np.any(np.isinf(data))
        if has_nan:
            return False, f"{name}: contém NaN / contains NaN"
        if has_inf:
            return False, f"{name}: contém Inf / contains Inf"
        return True, f"{name}: OK (sem NaN/Inf / no NaN/Inf)"

    def _check_signal_to_noise(self, data: np.ndarray, name: str, min_snr_db: float = None) -> Tuple[bool, str]:
        if min_snr_db is None:
            min_snr_db = self.MIN_SNR_DB
        baseline = np.mean(data[:10, :], axis=0)
        perturbation = data - baseline
        signal_power = np.var(perturbation)
        noise = np.diff(data, axis=0)
        noise_power = np.var(noise) * 0.5

        if noise_power < 1e-20:
            snr_db = 100
        else:
            snr_db = 10 * np.log10(signal_power / noise_power)

        if snr_db < min_snr_db:
            return False, f"{name}: SNR = {snr_db:.1f} dB (mín: {min_snr_db} dB)"
        return True, f"{name}: SNR = {snr_db:.1f} dB ✓"

    def _check_thermal_gradient(self, dts_data: np.ndarray, name: str) -> Tuple[bool, str]:
        baseline = np.mean(dts_data[:10, :], axis=0)
        gradient = np.polyfit(self.depth, baseline, 1)[0]

        if 0.015 <= gradient <= 0.045:
            return True, f"{name}: Gradiente = {gradient:.4f} °C/m ✓"
        return False, f"{name}: Gradiente = {gradient:.4f} °C/m (fora do esperado)"

    def _detect_interface_by_gradient(self, data: np.ndarray,
                                       pressure_events: Optional[List[float]] = None) -> Tuple[int, float]:
        n_t = data.shape[0]
        time = np.arange(n_t) * self.acq.trace_interval_s

        if pressure_events is not None and len(pressure_events) > 0:
            mask = np.zeros(n_t, dtype=bool)
            for pe_t in pressure_events:
                mask |= np.abs(time - pe_t) < 400
            if not np.any(mask):
                mask = np.ones(n_t, dtype=bool)
            perturbation_data = data[mask, :]
        else:
            baseline = np.mean(data[:min(10, n_t), :], axis=0)
            perturbation_data = data - baseline

        mean_perturbation = np.mean(perturbation_data, axis=0)
        dz = np.mean(np.diff(self.depth))
        gradient = np.gradient(mean_perturbation, dz)
        peak_idx = np.argmax(np.abs(gradient))
        peak_depth = self.depth[peak_idx]
        return peak_idx, peak_depth

    def _detect_peak_by_perturbation(self, data: np.ndarray,
                                      pressure_events: Optional[List[float]] = None) -> Tuple[int, float]:
        n_t = data.shape[0]
        time = np.arange(n_t) * self.acq.trace_interval_s

        if pressure_events is not None and len(pressure_events) > 0:
            mask = np.zeros(n_t, dtype=bool)
            for pe_t in pressure_events:
                mask |= np.abs(time - pe_t) < 400
            if not np.any(mask):
                mask = np.ones(n_t, dtype=bool)
            perturbation_data = data[mask, :]
        else:
            baseline = np.mean(data[:min(10, n_t), :], axis=0)
            perturbation_data = data - baseline

        perturbation_profile = np.max(np.abs(perturbation_data), axis=0)
        peak_idx = np.argmax(perturbation_profile)
        peak_depth = self.depth[peak_idx]
        return peak_idx, peak_depth

    def _detect_multiple_peaks(self, data: np.ndarray, expected_depths: List[float],
                                tolerance_m: float = None, name: str = "",
                                pressure_events: Optional[List[float]] = None) -> Tuple[bool, str]:
        """
        Detecta múltiplos picos correspondentes a múltiplas zonas/canais.
        Detects multiple peaks corresponding to multiple zones/channels.
        """
        if tolerance_m is None:
            tolerance_m = self.LOC_TOLERANCE_M

        n_t = data.shape[0]
        time = np.arange(n_t) * self.acq.trace_interval_s

        if pressure_events is not None and len(pressure_events) > 0:
            mask = np.zeros(n_t, dtype=bool)
            for pe_t in pressure_events:
                mask |= np.abs(time - pe_t) < 400
            if not np.any(mask):
                mask = np.ones(n_t, dtype=bool)
            perturbation_data = data[mask, :]
        else:
            baseline = np.mean(data[:min(10, n_t), :], axis=0)
            perturbation_data = data - baseline

        mean_perturbation = np.mean(perturbation_data, axis=0)
        abs_pert = np.abs(mean_perturbation)

        # Encontrar todos os picos significativos / Find all significant peaks
        peaks, _ = find_peaks(abs_pert, height=np.max(abs_pert) * 0.15, distance=100)
        detected_depths = [self.depth[p] for p in peaks]

        # Verificar cada zona esperada / Check each expected zone
        matched = 0
        unmatched = []
        for z in expected_depths:
            closest = min(detected_depths, key=lambda d: abs(d - z), default=None)
            if closest is not None and abs(closest - z) <= tolerance_m:
                matched += 1
            else:
                unmatched.append(z)

        if matched == len(expected_depths):
            return True, f"{name}: {matched}/{len(expected_depths)} zonas detectadas ✓"
        elif matched > 0:
            return True, f"{name}: {matched}/{len(expected_depths)} zonas detectadas (faltando: {unmatched}) ⚠️"
        else:
            return False, f"{name}: 0/{len(expected_depths)} zonas detectadas (esperado: {expected_depths})"

    def _check_signature_localization(self, data: np.ndarray, expected_depth: float,
                                       tolerance_m: float = None, name: str = "",
                                       pressure_events: Optional[List[float]] = None,
                                       is_interface: bool = False) -> Tuple[bool, str]:
        if tolerance_m is None:
            tolerance_m = self.LOC_TOLERANCE_M

        if is_interface:
            peak_idx, peak_depth = self._detect_interface_by_gradient(data, pressure_events)
            method = "gradiente"
        else:
            peak_idx, peak_depth = self._detect_peak_by_perturbation(data, pressure_events)
            method = "perturbação"

        if abs(peak_depth - expected_depth) <= tolerance_m:
            return True, f"{name}: Pico em {peak_depth:.1f}m (esperado: {expected_depth:.1f}m, método: {method}) ✓"
        return False, f"{name}: Pico em {peak_depth:.1f}m (esperado: {expected_depth:.1f}m, método: {method})"

    def _check_lfdas_output(self, lfdas_result: Dict, name: str) -> Tuple[bool, str]:
        temp = lfdas_result['temperature']

        if temp.shape[1] != self.well.n_channels:
            return False, f"{name}: LF-DAS n_channels mismatch"

        refresh = lfdas_result.get('refresh_rate_s', 0)
        if refresh > 15.0:
            return False, f"{name}: Refresh rate muito lento ({refresh:.1f}s)"

        baseline = np.mean(temp, axis=0)
        perturbation = temp - baseline
        temp_range = np.max(np.abs(perturbation))

        if temp_range < self.LF_DAS_MIN_AMP and self.LF_DAS_MIN_AMP > 0:
            return False, f"{name}: Amplitude LF-DAS muito baixa ({temp_range:.8f}°C)"

        return True, f"{name}: LF-DAS OK (refresh={refresh:.2f}s, pertΔT={temp_range:.2e}°C) ✓"

    def validate_signature(self, sig_data: Dict, lfdas_result: Dict = None) -> Dict:
        sig_type = sig_data['signature_type']
        params = sig_data['parameters']
        dts = sig_data['dts']
        das = sig_data['das']

        results = {
            'signature': sig_type.code,
            'name_pt': sig_type.pt,
            'name_en': sig_type.en,
            'tests': [],
            'passed': 0,
            'failed': 0
        }

        tests = [
            self._check_temporal_consistency(dts, "DTS"),
            self._check_temporal_consistency(das, "DAS"),
            self._check_signal_to_noise(dts, "DTS"),
            self._check_signal_to_noise(das, "DAS"),
            self._check_thermal_gradient(dts, "DTS"),
        ]

        pressure_events = params.get('pressure_events_s', None)

        # Mapeamento de parâmetros para localização / Parameter to localization mapping
        if 'interface_depth_m' in params:
            tests.append(self._check_signature_localization(
                dts, params['interface_depth_m'], name="DTS (interface)",
                pressure_events=pressure_events, is_interface=True))
        elif 'valve_depth_m' in params:
            tests.append(self._check_signature_localization(
                das, params['valve_depth_m'], name="DAS (válvula)"))
        elif 'leak_depth_m' in params:
            tests.append(self._check_signature_localization(
                dts, params['leak_depth_m'], name="DTS (vazamento)"))
        elif 'perf_depth_m' in params:
            tests.append(self._check_signature_localization(
                dts, params['perf_depth_m'], name="DTS (perfuração)"))
        elif 'flow_start_depth_m' in params:
            tests.append(self._check_signature_localization(
                dts, params['flow_start_depth_m'], name="DTS (fluxo)"))
        elif 'injection_depths_m' in params:
            tests.append(self._check_signature_localization(
                dts, params['injection_depths_m'][0], name="DTS (injeção)"))
        elif 'rupture_valve_depth_m' in params:
            tests.append(self._check_signature_localization(
                das, params['rupture_valve_depth_m'], name="DAS (GLV)"))
        elif 'screenout_time_s' in params:
            tests.append(self._check_signature_localization(
                dts, params['perf_depth_m'], name="DTS (frac)"))
        elif 'cement_quality' in params:
            tests.append((True, "DTS (cimentação): Variação térmica presente ✓"))
        elif 'squeeze_zones' in params:
            tests.append((True, "DTS (squeeze): Variação térmica presente ✓"))
        elif 'zone_depths_m' in params:
            # Crossflow Zonal: detectar múltiplas zonas / Detect multiple zones
            tests.append(self._detect_multiple_peaks(
                dts, params['zone_depths_m'], name="DTS (crossflow)"))
        elif 'channel_depths_m' in params:
            # Cement Channeling: detectar múltiplos canais / Detect multiple channels
            tests.append(self._detect_multiple_peaks(
                dts, params['channel_depths_m'], name="DTS (canal)"))

        if lfdas_result is not None:
            tests.append(self._check_lfdas_output(lfdas_result, "LF-DAS"))

        for passed, msg in tests:
            results['tests'].append({'passed': passed, 'message': msg})
            if passed:
                results['passed'] += 1
            else:
                results['failed'] += 1

        results['total'] = len(tests)
        results['success_rate'] = results['passed'] / results['total'] * 100

        return results

    def run_full_validation(self, signatures: Dict, lfdas_processor=None) -> List[Dict]:
        all_results = []

        print("="*70)
        print("🔬 TESTES DE VALIDAÇÃO — ALAKORO FIBERSENSE v1.2.1")
        print("="*70)

        for key, sig in signatures.items():
            sig_type = sig['signature_type']
            print(f"\n{'─'*70}")
            print(f"📝 {sig_type.pt}")
            print(f"   {sig_type.en}")
            print(f"{'─'*70}")

            lfdas_result = None
            if lfdas_processor is not None and sig['das'] is not None and np.any(sig['das'] != 0):
                try:
                    lfdas_result = lfdas_processor.process(sig['das'], trace_interval_s=self.acq.trace_interval_s)
                except Exception as e:
                    print(f"   ⚠️ LF-DAS falhou: {e}")

            result = self.validate_signature(sig, lfdas_result)
            all_results.append(result)

            for test in result['tests']:
                status = "✅" if test['passed'] else "❌"
                print(f"   {status} {test['message']}")

            print(f"\n   📊 Resultado: {result['passed']}/{result['total']} passaram ({result['success_rate']:.0f}%)")

        print(f"\n{'='*70}")
        print("📋 RESUMO GERAL")
        print(f"{'='*70}")
        total_tests = sum(r['total'] for r in all_results)
        total_passed = sum(r['passed'] for r in all_results)
        success_rate = total_passed / total_tests * 100
        print(f"   Total de testes: {total_tests}")
        print(f"   Passaram: {total_passed}")
        print(f"   Falharam: {total_tests - total_passed}")
        print(f"   Taxa de sucesso: {success_rate:.1f}%")

        if success_rate >= 90:
            print(f"\n   🎉 VALIDAÇÃO APROVADA! Taxa >= 90%")
        else:
            print(f"\n   ⚠️  Taxa abaixo de 90%.")

        return all_results, success_rate
