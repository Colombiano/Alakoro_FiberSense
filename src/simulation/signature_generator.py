"""
Alakoro FiberSense — Simulador de Assinaturas Canônicas (M15) v4.1
Canonical Signature Simulator v4.1

Autor/Author: Luiz Paulo Colombiano
Data/Date: 2026-07-18
Licença/License: MIT

15 assinaturas: 6 originais + 5 fraturamento/canhoneio/GLV + 4 cimentação/fluxo cruzado
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum, auto


class SurveyPhaseType(Enum):
    BASELINE = ("Baseline", "Baseline")
    ANNULUS_BLEED = ("Bleed de Ânulo", "Annulus Bleed")
    SHUT_IN = ("Shut-In", "Shut-In")
    PRODUCTION = ("Produção", "Production")
    PRESSURIZATION = ("Pressurização", "Pressurization")
    WARM_BACK = ("Warm-Back", "Warm-Back")
    STEP_RATE_TEST = ("Step Rate Test", "Step Rate Test")
    INJECTION = ("Injeção", "Injection")
    PERFORATION = ("Canhoneio", "Perforation")
    FRAC_STIMULATION = ("Estimulação por Fraturamento", "Fracture Stimulation")
    CEMENTING = ("Cimentação", "Cementing")
    RE_CEMENTING = ("Recimentação", "Re-Cementing")

    def __init__(self, pt, en):
        self.pt = pt
        self.en = en


class EventSignatureType(Enum):
    JOULE_THOMSON = ("dipolo_thermal_jt", "Dipolo Térmico Joule-Thomson", "Joule-Thomson Thermal Dipole")
    SLOPE_VELOCITY = ("slope_velocity_tracking", "Rastreamento de Inclinação (Velocidade)", "Slope Tracking (Velocity)")
    WARM_BACK = ("warm_back_recovery", "Recuperação Térmica (Warm-Back)", "Thermal Recovery (Warm-Back)")
    VALVE_CHATTER = ("valve_chatter_multipointing", "Chatter/Multipointing de Válvula", "Valve Chatter/Multipointing")
    SLUGGING_CYCLE = ("slugging_cyclic", "Ciclo de Slugging", "Slugging Cycle")
    LEAK_PATH = ("leak_path_tubing_annulus", "Caminho de Vazamento Tubing↔Ânulo", "Leak Path Tubing↔Annulus")
    GLV_BELLOW_RUPTURE = ("glv_bellow_rupture", "Fole Furado de Válvula de Gás Lift (GLV)", "Gas Lift Valve Bellow Rupture")
    PERFORATION_EFFECTIVENESS = ("perforation_effectiveness", "Efetividade de Canhoneio", "Perforation Effectiveness")
    FRAC_SCREENOUT = ("frac_screenout", "Embuchamento de Fratura (Screen-out)", "Fracture Screen-out")
    FRAC_PROPPANT_DISTRIBUTION = ("frac_proppant_distribution", "Distribuição de Propante", "Proppant Distribution")
    FRAC_HEIGHT_GROWTH = ("frac_height_growth", "Crescimento de Altura de Fratura", "Fracture Height Growth")
    CEMENT_BOND_EVALUATION = ("cement_bond_evaluation", "Avaliação de Cimentação (CBL/VDL)", "Cement Bond Evaluation (CBL/VDL)")
    RE_CEMENTING_ASSESSMENT = ("re_cementing_assessment", "Avaliação de Recimentação", "Re-Cementing Assessment")
    CROSSFLOW_ZONAL = ("crossflow_zonal", "Fluxo Cruzado Zonal", "Zonal Crossflow")
    CEMENT_CHANNELING = ("cement_channeling", "Canalização de Cimento", "Cement Channeling")

    def __init__(self, code, pt, en):
        self.code = code
        self.pt = pt
        self.en = en


@dataclass
class WellGeometry:
    depth_top: float = 0.0
    depth_bottom: float = 3000.0
    n_channels: int = 3000
    channel_spacing: float = 1.0

    @property
    def depth_array(self) -> np.ndarray:
        return np.linspace(self.depth_top, self.depth_bottom, self.n_channels)


@dataclass
class AcquisitionConfig:
    spatial_resolution_m: float = 1.0
    gauge_length_m: float = 5.0
    sampling_rate_hz: float = 1000.0
    trace_interval_s: float = 2.0
    duration_s: float = 3600.0

    @property
    def n_time_samples(self) -> int:
        return int(self.duration_s / self.trace_interval_s)


class SignatureGenerator:
    """Gerador de 15 assinaturas canônicas de poço de petróleo / 
    Generator of 15 canonical oil well signatures"""

    # Parâmetros físicos padrão / Default physical parameters
    T_GRADIENT: float = 0.03       # °C/m
    T_SURFACE: float = 20.0      # °C
    SNR_DTS: float = 25.0          # dB
    SNR_DAS: float = 20.0        # dB

    def __init__(self, well: WellGeometry, acq: AcquisitionConfig):
        self.well = well
        self.acq = acq
        self.depth = well.depth_array
        self.time = np.arange(0, acq.duration_s, acq.trace_interval_s)
        self.n_t = len(self.time)
        self.n_z = well.n_channels
        self._baseline_temp = self.T_SURFACE + self.T_GRADIENT * self.depth

    # ─────────────────────────────────────────────────────────
    # MÉTODOS UTILITÁRIOS / UTILITY METHODS
    # ─────────────────────────────────────────────────────────

    def _add_noise(self, data: np.ndarray, snr_db: float = 25) -> np.ndarray:
        signal_power = np.mean(data**2) if np.mean(data**2) > 0 else 1e-10
        noise_power = signal_power / (10**(snr_db/10))
        noise = np.random.normal(0, np.sqrt(noise_power), data.shape)
        return data + noise

    def _init_arrays(self) -> Tuple[np.ndarray, np.ndarray]:
        """Inicializa arrays DTS e DAS zerados / Initialize zeroed DTS and DAS arrays"""
        return np.zeros((self.n_t, self.n_z)), np.zeros((self.n_t, self.n_z))

    def _get_baseline(self) -> np.ndarray:
        """Retorna perfil de temperatura base geotérmica / Returns geothermal baseline temperature profile"""
        return self._baseline_temp.copy()

    def _finalize(self, dts: np.ndarray, das: np.ndarray, sig_type: EventSignatureType,
                  parameters: Dict) -> Dict:
        """Finaliza assinatura com ruído e metadados / Finalizes signature with noise and metadata"""
        dts = self._add_noise(dts, snr_db=self.SNR_DTS)
        if np.any(das != 0):
            das = self._add_noise(das, snr_db=self.SNR_DAS)
        return {
            'dts': dts, 'das': das,
            'signature_type': sig_type,
            'parameters': parameters
        }

    # ─────────────────────────────────────────────────────────
    # 15 ASSINATURAS CANÔNICAS / 15 CANONICAL SIGNATURES
    # ─────────────────────────────────────────────────────────

    # --- 1. Joule-Thomson ---
    def generate_joule_thomson(self, interface_depth=1500.0, delta_t_cold=-50.0,
                                delta_t_hot=30.0, transition_width=15.0,
                                pressure_event_times=None, das_lf_amplitude=2e-1):
        if pressure_event_times is None:
            pressure_event_times = [300, 900, 1500, 2100, 2700]
        dts_data, das_data = self._init_arrays()

        for i, t in enumerate(self.time):
            temp_profile = self._get_baseline()
            for pe_t in pressure_event_times:
                if abs(t - pe_t) < 400:
                    strength = np.exp(-((t - pe_t)/150)**2)
                    transition = 0.5 * (1 + np.tanh((self.depth - interface_depth) / (transition_width/2)))
                    temp_profile += strength * (delta_t_cold * (1 - transition) + delta_t_hot * transition)
                    lf_signal = das_lf_amplitude * strength * np.sin(2 * np.pi * 0.1 * t) *                                 np.exp(-0.5 * ((self.depth - interface_depth) / 50)**2)
                    dc_component = das_lf_amplitude * 0.5 * strength * ((1 - transition) * 0.8 + transition * (-0.5))
                    das_data[i, :] = lf_signal + dc_component
            dts_data[i, :] = temp_profile

        return self._finalize(dts_data, das_data, EventSignatureType.JOULE_THOMSON, {
            'interface_depth_m': interface_depth, 'delta_t_cold_c': delta_t_cold,
            'delta_t_hot_c': delta_t_hot, 'pressure_events_s': pressure_event_times,
            'das_lf_amplitude': das_lf_amplitude
        })

    # --- 2. Slope Velocity ---
    def generate_slope_velocity(self, flow_start_depth=1000.0, flow_velocity_ms=0.3,
                                 flow_duration_s=600.0, start_time_s=300.0):
        dts_data, das_data = self._init_arrays()

        for i, t in enumerate(self.time):
            temp_profile = self._get_baseline()
            if start_time_s <= t <= (start_time_s + flow_duration_s):
                elapsed = t - start_time_s
                front_depth = flow_start_depth + flow_velocity_ms * elapsed
                delta_t = -50.0 * np.exp(-0.5 * ((self.depth - front_depth) / 50)**2)
                temp_profile += delta_t
                flow_sig = np.exp(-0.5 * ((self.depth - front_depth) / 30)**2)
                das_data[i, :] = flow_sig * 5e-4 * np.sin(2 * np.pi * 2 * elapsed)
            dts_data[i, :] = temp_profile

        return self._finalize(dts_data, das_data, EventSignatureType.SLOPE_VELOCITY, {
            'flow_start_depth_m': flow_start_depth, 'flow_velocity_ms': flow_velocity_ms,
            'flow_duration_s': flow_duration_s, 'start_time_s': start_time_s
        })

    # --- 3. Warm-Back ---
    def generate_warm_back(self, injection_depths=None, injection_temp_delta=-60.0,
                            warm_back_tau_s=1800.0, injection_start_s=300.0, injection_duration_s=600.0):
        if injection_depths is None:
            injection_depths = [1200.0, 1500.0, 1800.0]
        dts_data, das_data = self._init_arrays()
        baseline = self._get_baseline()

        for i, t in enumerate(self.time):
            temp_profile = baseline.copy()
            if t < injection_start_s:
                pass
            elif injection_start_s <= t < (injection_start_s + injection_duration_s):
                for z_inj in injection_depths:
                    temp_profile += injection_temp_delta * np.exp(-0.5 * ((self.depth - z_inj) / 30)**2)
            else:
                elapsed_post = t - (injection_start_s + injection_duration_s)
                recovery = 1 - np.exp(-elapsed_post / warm_back_tau_s)
                for z_inj in injection_depths:
                    temp_profile += injection_temp_delta * (1 - recovery) * np.exp(-0.5 * ((self.depth - z_inj) / 30)**2)
            dts_data[i, :] = temp_profile

            # DAS: gerado no mesmo loop para consistência temporal
            if injection_start_s <= t:
                das_data[i, :] = 5e-3 * np.sin(2 * np.pi * 0.05 * t) * np.exp(-0.5 * ((self.depth - 1500) / 200)**2)

        return self._finalize(dts_data, das_data, EventSignatureType.WARM_BACK, {
            'injection_depths_m': injection_depths, 'injection_temp_delta_c': injection_temp_delta,
            'warm_back_tau_s': warm_back_tau_s
        })

    # --- 4. Valve Chatter ---
    def generate_valve_chatter(self, valve_depth=1400.0, chatter_frequency_hz=0.5,
                                multipointing_cycle_min=30.0, n_cycles=8, start_time_s=600.0):
        dts_data, das_data = self._init_arrays()

        for i, t in enumerate(self.time):
            temp_profile = self._get_baseline()
            if t >= start_time_s:
                elapsed = t - start_time_s
                cycle_period_s = multipointing_cycle_min * 60
                cycle_phase = (elapsed % cycle_period_s) / cycle_period_s
                if cycle_phase < 0.3:
                    activity = np.sin(np.pi * cycle_phase / 0.3)
                    chatter = activity * np.sin(2 * np.pi * chatter_frequency_hz * elapsed) *                               np.exp(-0.5 * ((self.depth - valve_depth) / 5)**2)
                    das_data[i, :] = chatter * 5e-3
                    temp_profile += activity * 20.0 * np.exp(-0.5 * ((self.depth - valve_depth) / 10)**2)
            dts_data[i, :] = temp_profile

        return self._finalize(dts_data, das_data, EventSignatureType.VALVE_CHATTER, {
            'valve_depth_m': valve_depth, 'chatter_frequency_hz': chatter_frequency_hz,
            'multipointing_cycle_min': multipointing_cycle_min, 'n_cycles': n_cycles
        })

    # --- 5. Slugging Cycle ---
    def generate_slugging_cycle(self, slug_period_min=27.5, slug_depth_range=(1000.0, 2000.0),
                                 start_time_s=300.0, n_cycles=8):
        dts_data, das_data = self._init_arrays()

        for i, t in enumerate(self.time):
            temp_profile = self._get_baseline()
            if t >= start_time_s:
                elapsed = t - start_time_s
                period_s = slug_period_min * 60
                phase = 2 * np.pi * elapsed / period_s
                z_mask = (self.depth >= slug_depth_range[0]) & (self.depth <= slug_depth_range[1])
                amplitude = np.zeros_like(self.depth)
                amplitude[z_mask] = 30.0 * np.sin(phase - self.depth[z_mask] / 100)
                das_sig = np.zeros_like(self.depth)
                das_sig[z_mask] = 5e-4 * np.sin(phase) * np.sin(2 * np.pi * 0.1 * self.depth[z_mask] / self.well.depth_bottom)
                temp_profile += amplitude
                das_data[i, :] = das_sig
            dts_data[i, :] = temp_profile

        return self._finalize(dts_data, das_data, EventSignatureType.SLUGGING_CYCLE, {
            'slug_period_min': slug_period_min, 'slug_depth_range_m': slug_depth_range,
            'n_cycles': n_cycles
        })

    # --- 6. Leak Path ---
    def generate_leak_path(self, leak_depth=1914.0, leak_strength=30.0,
                            bleed_start_s=300.0, bleed_duration_s=900.0):
        dts_data, das_data = self._init_arrays()

        for i, t in enumerate(self.time):
            temp_profile = self._get_baseline()
            if bleed_start_s <= t <= (bleed_start_s + bleed_duration_s):
                progress = (t - bleed_start_s) / bleed_duration_s
                temp_profile += leak_strength * progress * np.exp(-0.5 * ((self.depth - leak_depth) / 20)**2)
                das_data[i, :] = 5e-4 * progress * np.sin(2 * np.pi * 3 * self.depth / self.well.depth_bottom) *                                   np.exp(-0.5 * ((self.depth - leak_depth) / 15)**2)
            dts_data[i, :] = temp_profile

        return self._finalize(dts_data, das_data, EventSignatureType.LEAK_PATH, {
            'leak_depth_m': leak_depth, 'leak_strength_c': leak_strength,
            'bleed_duration_s': bleed_duration_s
        })

    # --- 7. GLV Bellow Rupture ---
    def generate_glv_bellow_rupture(self, valve_depth=1400.0, n_valves=5,
                                     rupture_valve_idx=2, start_time_s=600.0,
                                     rupture_duration_s=300.0):
        dts_data, das_data = self._init_arrays()
        valve_spacing = 50.0
        valve_depths = [valve_depth + i * valve_spacing for i in range(n_valves)]

        for i, t in enumerate(self.time):
            temp_profile = self._get_baseline()
            if t >= start_time_s:
                elapsed = t - start_time_s
                cycle_period_s = 30.0 * 60
                cycle_phase = (elapsed % cycle_period_s) / cycle_period_s
                for v_idx, v_depth in enumerate(valve_depths):
                    if v_idx == rupture_valve_idx and elapsed > rupture_duration_s:
                        continue
                    if cycle_phase < 0.3:
                        activity = np.sin(np.pi * cycle_phase / 0.3)
                        chatter = activity * np.sin(2 * np.pi * 0.5 * elapsed) *                                   np.exp(-0.5 * ((self.depth - v_depth) / 5)**2)
                        das_data[i, :] += chatter * 5e-3
                        temp_profile += activity * 15.0 * np.exp(-0.5 * ((self.depth - v_depth) / 10)**2)
            dts_data[i, :] = temp_profile

        return self._finalize(dts_data, das_data, EventSignatureType.GLV_BELLOW_RUPTURE, {
            'valve_depth_m': valve_depth, 'n_valves': n_valves,
            'rupture_valve_idx': rupture_valve_idx,
            'rupture_valve_depth_m': valve_depths[rupture_valve_idx],
            'rupture_duration_s': rupture_duration_s,
            'valve_depths_m': valve_depths
        })

    # --- 8. Perforation Effectiveness ---
    def generate_perforation_effectiveness(self, perf_depths=None, effective_perfs=None,
                                            shot_density_spm=6.0, start_time_s=300.0, flow_duration_s=1800.0):
        if perf_depths is None:
            perf_depths = [(1500.0, 1520.0), (1600.0, 1620.0)]
        if effective_perfs is None:
            effective_perfs = [True, False]
        dts_data, das_data = self._init_arrays()
        baseline = self._get_baseline()

        for i, t in enumerate(self.time):
            temp_profile = baseline.copy()
            if start_time_s <= t <= (start_time_s + flow_duration_s):
                progress = (t - start_time_s) / flow_duration_s
                for (z_top, z_bottom), is_effective in zip(perf_depths, effective_perfs):
                    if is_effective:
                        z_mask = (self.depth >= z_top) & (self.depth <= z_bottom)
                        temp_profile[z_mask] += progress * (-30.0)
                        das_data[i, z_mask] += progress * 2e-4 * np.sin(2 * np.pi * 0.05 * self.depth[z_mask] / (z_bottom - z_top))
                    else:
                        n_shots = int((z_bottom - z_top) * shot_density_spm / 0.3048)
                        n_open = max(1, n_shots // 3)
                        for j in range(n_open):
                            z_shot = z_top + j * (z_bottom - z_top) / n_open
                            temp_profile += progress * (-60.0) * np.exp(-0.5 * ((self.depth - z_shot) / 2)**2)
                            das_data[i, :] += progress * 5e-4 * np.exp(-0.5 * ((self.depth - z_shot) / 2)**2) * np.sin(2 * np.pi * 0.1 * t)
            dts_data[i, :] = temp_profile

        return self._finalize(dts_data, das_data, EventSignatureType.PERFORATION_EFFECTIVENESS, {
            'perf_depths_m': perf_depths, 'effective_perfs': effective_perfs,
            'shot_density_spm': shot_density_spm, 'flow_duration_s': flow_duration_s
        })

    # --- 9. Frac Screen-out ---
    def generate_frac_screenout(self, perf_depth=2000.0, frac_half_length_m=100.0,
                                 screenout_time_s=1800.0, start_time_s=300.0, injection_rate_bpm=10.0):
        dts_data, das_data = self._init_arrays()
        baseline = self._get_baseline()

        for i, t in enumerate(self.time):
            temp_profile = baseline.copy()
            if start_time_s <= t:
                elapsed = t - start_time_s
                if elapsed < screenout_time_s:
                    frac_tip = perf_depth + min(elapsed * 0.05, frac_half_length_m)
                    z_mask = (self.depth >= perf_depth) & (self.depth <= frac_tip + perf_depth)
                    temp_profile[z_mask] += -30.0 * np.exp(-0.5 * ((self.depth[z_mask] - perf_depth) / 30)**2)
                    das_data[i, z_mask] += 1e-4 * np.random.randn(np.sum(z_mask))
                else:
                    post_screen = elapsed - screenout_time_s
                    z_mask = (self.depth >= perf_depth - 20) & (self.depth <= perf_depth + frac_half_length_m + 20)
                    temp_profile[z_mask] += 40.0 * (1 - np.exp(-post_screen / 60)) * np.exp(-0.5 * ((self.depth[z_mask] - perf_depth) / 50)**2)
                    das_data[i, :] += 5e-4 * np.sin(2 * np.pi * 5 * post_screen) * np.exp(-0.5 * ((self.depth - perf_depth) / 30)**2)
                    if post_screen < 60:
                        das_data[i, :] += 2e-3 * np.exp(-post_screen / 10) * np.sin(2 * np.pi * 50 * post_screen)
            dts_data[i, :] = temp_profile

        return self._finalize(dts_data, das_data, EventSignatureType.FRAC_SCREENOUT, {
            'perf_depth_m': perf_depth, 'frac_half_length_m': frac_half_length_m,
            'screenout_time_s': screenout_time_s, 'injection_rate_bpm': injection_rate_bpm
        })

    # --- 10. Frac Proppant Distribution ---
    def generate_frac_proppant_distribution(self, perf_depth=2000.0, frac_height_m=50.0,
                                               proppant_stages=None, start_time_s=300.0, stage_duration_s=300.0):
        if proppant_stages is None:
            proppant_stages = [
                {'name': 'Pad', 'concentration_ppg': 0, 'depth_bias': 0},
                {'name': 'Stage_1', 'concentration_ppg': 1, 'depth_bias': -10},
                {'name': 'Stage_2', 'concentration_ppg': 2, 'depth_bias': 5},
                {'name': 'Stage_3', 'concentration_ppg': 3, 'depth_bias': -5},
                {'name': 'Flush', 'concentration_ppg': 0, 'depth_bias': 0}
            ]
        dts_data, das_data = self._init_arrays()
        baseline = self._get_baseline()

        for i, t in enumerate(self.time):
            temp_profile = baseline.copy()
            if start_time_s <= t:
                elapsed = t - start_time_s
                stage_idx = int(elapsed / stage_duration_s)
                if stage_idx < len(proppant_stages):
                    stage = proppant_stages[stage_idx]
                    stage_progress = (elapsed % stage_duration_s) / stage_duration_s
                    z_top = perf_depth - frac_height_m/2 + stage['depth_bias']
                    z_bottom = perf_depth + frac_height_m/2 + stage['depth_bias']
                    z_mask = (self.depth >= z_top) & (self.depth <= z_bottom)
                    temp_profile[z_mask] += -15.0 * stage_progress * (1 + stage['concentration_ppg'] * 0.5)
                    if stage['concentration_ppg'] > 0:
                        das_data[i, z_mask] += 2e-4 * stage['concentration_ppg'] * np.random.randn(np.sum(z_mask))
                    if stage_progress < 0.1:
                        marker_depth = perf_depth - frac_height_m/2 - 20
                        temp_profile += 5.0 * np.exp(-0.5 * ((self.depth - marker_depth) / 3)**2)
            dts_data[i, :] = temp_profile

        return self._finalize(dts_data, das_data, EventSignatureType.FRAC_PROPPANT_DISTRIBUTION, {
            'perf_depth_m': perf_depth, 'frac_height_m': frac_height_m,
            'proppant_stages': proppant_stages, 'stage_duration_s': stage_duration_s
        })

    # --- 11. Frac Height Growth ---
    def generate_frac_height_growth(self, perf_depth=2000.0, target_height_m=80.0,
                                     actual_height_m=120.0, barrier_depth=2050.0,
                                     start_time_s=300.0, injection_duration_s=1800.0):
        dts_data, das_data = self._init_arrays()
        baseline = self._get_baseline()

        for i, t in enumerate(self.time):
            temp_profile = baseline.copy()
            if start_time_s <= t <= (start_time_s + injection_duration_s):
                elapsed = t - start_time_s
                progress = elapsed / injection_duration_s
                target_top = perf_depth - target_height_m/2
                target_bottom = perf_depth + target_height_m/2
                actual_top = perf_depth - actual_height_m/2 * progress
                actual_bottom = perf_depth + actual_height_m/2 * progress
                z_target = (self.depth >= target_top) & (self.depth <= target_bottom)
                temp_profile[z_target] += -20.0 * progress
                z_excess = ((self.depth >= actual_top) & (self.depth < target_top)) |                            ((self.depth > target_bottom) & (self.depth <= actual_bottom))
                temp_profile[z_excess] += -8.0 * progress * 0.5
                if progress > 0.5:
                    n_events = int(5 * progress)
                    for _ in range(n_events):
                        z_event = np.random.choice(self.depth[z_excess]) if np.any(z_excess) else perf_depth
                        das_data[i, :] += 2e-4 * np.exp(-0.5 * ((self.depth - z_event) / 5)**2) * np.sin(2 * np.pi * np.random.uniform(10, 100) * elapsed)
            dts_data[i, :] = temp_profile

        return self._finalize(dts_data, das_data, EventSignatureType.FRAC_HEIGHT_GROWTH, {
            'perf_depth_m': perf_depth, 'target_height_m': target_height_m,
            'actual_height_m': actual_height_m, 'barrier_depth_m': barrier_depth,
            'injection_duration_s': injection_duration_s
        })

    # --- 12. Cement Bond Evaluation ---
    def generate_cement_bond_evaluation(self, casing_depths=None,
                                         cement_quality=None,
                                         start_time_s=300.0,
                                         evaluation_duration_s=600.0):
        if casing_depths is None:
            casing_depths = [(500.0, 3000.0)]
        if cement_quality is None:
            cement_quality = [
                {'depth_range': (500, 1000), 'quality': 0.9},
                {'depth_range': (1000, 1500), 'quality': 0.7},
                {'depth_range': (1500, 2000), 'quality': 0.3},
                {'depth_range': (2000, 2500), 'quality': 0.8},
                {'depth_range': (2500, 3000), 'quality': 0.2},
            ]
        dts_data, das_data = self._init_arrays()

        for i, t in enumerate(self.time):
            temp_profile = self._get_baseline()
            if start_time_s <= t <= (start_time_s + evaluation_duration_s):
                progress = (t - start_time_s) / evaluation_duration_s
                for cq in cement_quality:
                    z_top, z_bottom = cq['depth_range']
                    quality = cq['quality']
                    z_mask = (self.depth >= z_top) & (self.depth <= z_bottom)
                    if quality > 0.7:
                        pass
                    elif quality > 0.4:
                        temp_profile[z_mask] += progress * (-10.0 * (1 - quality)) * np.sin(2 * np.pi * self.depth[z_mask] / 100)
                    else:
                        n_channels = max(1, int(5 * (1 - quality)))
                        for _ in range(n_channels):
                            z_channel = np.random.uniform(z_top, z_bottom)
                            temp_profile += progress * (-40.0) * np.exp(-0.5 * ((self.depth - z_channel) / 5)**2)
                            das_data[i, :] += progress * 1e-3 * np.exp(-0.5 * ((self.depth - z_channel) / 3)**2) * np.sin(2 * np.pi * 0.5 * t)
            dts_data[i, :] = temp_profile

        return self._finalize(dts_data, das_data, EventSignatureType.CEMENT_BOND_EVALUATION, {
            'casing_depths_m': casing_depths,
            'cement_quality': cement_quality,
            'evaluation_duration_s': evaluation_duration_s
        })

    # --- 13. Re-Cementing Assessment ---
    def generate_re_cementing_assessment(self, original_cement_depths=None,
                                          squeeze_zones=None,
                                          start_time_s=300.0,
                                          squeeze_duration_s=900.0):
        if original_cement_depths is None:
            original_cement_depths = [(1500, 1600)]
        if squeeze_zones is None:
            squeeze_zones = [
                {'depth_range': (1500, 1550), 'effectiveness': 0.8},
                {'depth_range': (1550, 1600), 'effectiveness': 0.3},
            ]
        dts_data, das_data = self._init_arrays()
        baseline = self._get_baseline()

        for i, t in enumerate(self.time):
            temp_profile = baseline.copy()
            if start_time_s <= t:
                elapsed = t - start_time_s
                if elapsed < squeeze_duration_s:
                    progress = elapsed / squeeze_duration_s
                    for sz in squeeze_zones:
                        z_top, z_bottom = sz['depth_range']
                        z_mask = (self.depth >= z_top) & (self.depth <= z_bottom)
                        temp_profile[z_mask] += progress * (-40.0)
                        das_data[i, z_mask] += progress * 2e-4 * np.random.randn(np.sum(z_mask))
                else:
                    post_squeeze = elapsed - squeeze_duration_s
                    recovery = 1 - np.exp(-post_squeeze / 600)
                    for sz in squeeze_zones:
                        z_top, z_bottom = sz['depth_range']
                        effectiveness = sz['effectiveness']
                        z_mask = (self.depth >= z_top) & (self.depth <= z_bottom)
                        if effectiveness > 0.6:
                            temp_profile[z_mask] += -40.0 * (1 - recovery) * 0.5
                        else:
                            temp_profile[z_mask] += -40.0 * (1 - recovery * 0.3)
                            das_data[i, z_mask] += 2e-4 * (1 - recovery) * np.sin(2 * np.pi * 0.1 * post_squeeze)
            dts_data[i, :] = temp_profile

        return self._finalize(dts_data, das_data, EventSignatureType.RE_CEMENTING_ASSESSMENT, {
            'original_cement_depths_m': original_cement_depths,
            'squeeze_zones': squeeze_zones,
            'squeeze_duration_s': squeeze_duration_s
        })

    # --- 14. Crossflow Zonal ---
    def generate_crossflow_zonal(self, zone_depths=None,
                                  crossflow_rate_ms=None,
                                  start_time_s=300.0,
                                  crossflow_duration_s=1800.0):
        if zone_depths is None:
            zone_depths = [1200.0, 1800.0, 2400.0]
        if crossflow_rate_ms is None:
            crossflow_rate_ms = [0.1, -0.05, 0.08]
        dts_data, das_data = self._init_arrays()
        baseline = self._get_baseline()

        for i, t in enumerate(self.time):
            temp_profile = baseline.copy()
            if start_time_s <= t <= (start_time_s + crossflow_duration_s):
                elapsed = t - start_time_s
                progress = elapsed / crossflow_duration_s
                for z_idx, (z_depth, z_rate) in enumerate(zip(zone_depths, crossflow_rate_ms)):
                    front_depth = z_depth + z_rate * elapsed
                    if z_rate > 0:
                        delta_t = -20.0 * progress * np.exp(-0.5 * ((self.depth - front_depth) / 40)**2)
                    else:
                        delta_t = 15.0 * progress * np.exp(-0.5 * ((self.depth - front_depth) / 40)**2)
                    temp_profile += delta_t
                    flow_sig = np.exp(-0.5 * ((self.depth - z_depth) / 25)**2)
                    das_data[i, :] += flow_sig * 1e-4 * np.sin(2 * np.pi * abs(z_rate) * 10 * elapsed)
                for j in range(len(zone_depths) - 1):
                    z_mid = (zone_depths[j] + zone_depths[j+1]) / 2
                    temp_profile += 8.0 * progress * np.exp(-0.5 * ((self.depth - z_mid) / 30)**2)
            dts_data[i, :] = temp_profile

        return self._finalize(dts_data, das_data, EventSignatureType.CROSSFLOW_ZONAL, {
            'zone_depths_m': zone_depths,
            'crossflow_rate_ms': crossflow_rate_ms,
            'crossflow_duration_s': crossflow_duration_s
        })

    # --- 15. Cement Channeling ---
    def generate_cement_channeling(self, channel_depths=None,
                                     channel_widths=None,
                                     start_time_s=300.0,
                                     flow_duration_s=1800.0):
        if channel_depths is None:
            channel_depths = [1300.0, 1700.0, 2200.0]
        if channel_widths is None:
            channel_widths = [5.0, 8.0, 3.0]
        dts_data, das_data = self._init_arrays()
        baseline = self._get_baseline()

        for i, t in enumerate(self.time):
            temp_profile = baseline.copy()
            if start_time_s <= t <= (start_time_s + flow_duration_s):
                progress = (t - start_time_s) / flow_duration_s
                for z_chan, w_chan in zip(channel_depths, channel_widths):
                    z_mask = (self.depth >= z_chan - w_chan/2) & (self.depth <= z_chan + w_chan/2)
                    temp_profile[z_mask] += progress * (-25.0)
                    das_data[i, z_mask] += progress * 2e-4 * np.random.randn(np.sum(z_mask))
                    channel_extension = 50.0
                    z_ext_mask = (self.depth >= z_chan - channel_extension) & (self.depth <= z_chan + channel_extension)
                    distance_factor = np.exp(-0.5 * ((self.depth - z_chan) / (channel_extension/2))**2)
                    temp_profile += progress * (-10.0) * distance_factor
            dts_data[i, :] = temp_profile

        return self._finalize(dts_data, das_data, EventSignatureType.CEMENT_CHANNELING, {
            'channel_depths_m': channel_depths,
            'channel_widths_m': channel_widths,
            'flow_duration_s': flow_duration_s
        })
