"""
Alakoro FiberSense — Motor de Inferência (wrapper Python)
InferenceEngine wrapper

Autor/Author: Luiz Paulo Colombiano
Licença/License: MIT

Este módulo expõe o InferenceEngine implementado em C++20 (com corrotinas
internas e metaprogramação) de forma Pythonica, convertendo os resultados
cru do C++ em instâncias da ontologia Alakoro (Event).
"""

from datetime import datetime, timezone
from typing import Optional
import warnings

import numpy as np

from alakoro_core import (
    InferenceMetadata as CppInferenceMetadata,
    CanonicalInferenceEngine,
)

try:  # Binding CL-03 pode estar ausente em builds antigos / may be missing in old builds.
    from alakoro_core import decouple_strain_temperature_d as _cpp_decouple
except ImportError:  # pragma: no cover - fallback NumPy puro / pure NumPy fallback
    _cpp_decouple = None

from .events import (
    Event,
    JouleThomsonEvent,
    LeakEvent,
    FlowEvent,
    WarmBackEvent,
    SlopeVelocityEvent,
    GasLiftValveEvent,
    GLVBellowRuptureEvent,
    ValveChatterEvent,
    FracScreenoutEvent,
    FracProppantDistributionEvent,
    FracHeightGrowthEvent,
    PerforationEffectivenessEvent,
    CementBondEvaluationEvent,
    ReCementingAssessmentEvent,
    CrossflowZonalEvent,
    CementChannelingEvent,
)

# Mapeamento de códigos de evento do C++ para classes da ontologia.
# Cobre os 15 eventos canônicos + "flow_discrimination" (16ª regra, CL-04),
# cujos campos cinemáticos (apparent_velocity_ms, flow_direction,
# discrimination) têm casa natural na FlowEvent estendida.
# Mapping from C++ event codes to ontology classes. Covers the 15 canonical
# events plus "flow_discrimination" (16th rule, CL-04), whose kinematic
# fields fit the extended FlowEvent.
_EVENT_CLASS_MAP = {
    "joule_thomson": JouleThomsonEvent,
    "slope_velocity": SlopeVelocityEvent,
    "warm_back": WarmBackEvent,
    "valve_chatter": ValveChatterEvent,
    "slugging_cycle": Event,
    "leak_path": LeakEvent,
    "glv_bellow_rupture": GLVBellowRuptureEvent,
    "perforation_effectiveness": PerforationEffectivenessEvent,
    "frac_screenout": FracScreenoutEvent,
    "frac_proppant_distribution": FracProppantDistributionEvent,
    "frac_height_growth": FracHeightGrowthEvent,
    "cement_bond_evaluation": CementBondEvaluationEvent,
    "re_cementing_assessment": ReCementingAssessmentEvent,
    "crossflow_zonal": CrossflowZonalEvent,
    "cement_channeling": CementChannelingEvent,
    "flow_discrimination": FlowEvent,
}


def _map_severity(severity: str) -> str:
    """Normaliza severidade para os valores canônicos da ontologia.

    Inclui "Critical" (JSON Schema v1.1.0, payload.diagnosis.severity),
    emitido pelo C++ quando a confiança do glv_bellow_rupture excede 0.95.
    """
    return severity if severity in {"Low", "Medium", "High", "Critical"} else "Low"


def _resolve_sampling_rate_hz(signature: dict) -> float:
    """Deriva a taxa de amostragem temporal (Hz) de um dict de assinatura.

    Estratégia (primeira fonte válida vence):
      1. ``signature['parameters']['sampling_rate_hz']`` (ou alias ``fs_hz``);
      2. ``signature['parameters']['trace_interval_s']`` (ou ``dt_s``) → 1/dt;
      3. objeto ou dict em ``signature['acq']``/``signature['acquisition_config']``;
      4. fallback histórico de 1000.0 Hz.

    Returns
    -------
    float
        Taxa em Hz (> 0). Valores não positivos são retornados como estão e
        rejeitados posteriormente por ``InferenceEngine.infer``.
    """
    params = signature.get("parameters") or {}
    for key in ("sampling_rate_hz", "fs_hz", "sample_rate_hz"):
        value = params.get(key)
        if value is not None:
            return float(value)
    for key in ("trace_interval_s", "dt_s"):
        dt = params.get(key)
        if dt is not None:
            return 1.0 / float(dt)

    acq = signature.get("acq") or signature.get("acquisition_config")
    if acq is not None:
        if isinstance(acq, dict):
            for key in ("sampling_rate_hz", "fs_hz", "sample_rate_hz"):
                value = acq.get(key)
                if value is not None:
                    return float(value)
            dt = acq.get("trace_interval_s") or acq.get("dt_s")
            if dt is not None:
                return 1.0 / float(dt)
        else:
            value = getattr(acq, "sampling_rate_hz", None)
            if value is not None:
                return float(value)
            dt = getattr(acq, "trace_interval_s", None)
            if dt is not None:
                return 1.0 / float(dt)

    return 1000.0


def _finite_or_none(value) -> Optional[float]:
    """Converte um float C++ (possivelmente NaN) em float ou None.

    O contrato do InferenceResult usa NaN para velocidade indeterminada;
    a ontologia usa None (ausência de tripla). / The InferenceResult
    contract uses NaN for an undetermined velocity; the ontology uses
    None (no triple emitted).
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if np.isfinite(v) else None


def _result_to_event(result, timestamp: Optional[datetime] = None) -> Event:
    """Converte um InferenceResult do C++ em uma instância de Event."""
    event_cls = _EVENT_CLASS_MAP.get(result.event_type, Event)
    kwargs = {
        "event_type": result.event_type,
        "name": result.event_label_pt or result.event_label_en,
        "timestamp": timestamp or datetime.now(timezone.utc),
        "depth_md": result.depth_md,
        "confidence": result.confidence,
        "severity": _map_severity(result.severity),
        "recommendation": result.recommendation,
    }

    if event_cls is JouleThomsonEvent:
        kwargs["interface_depth"] = result.depth_md
    elif event_cls is LeakEvent:
        kwargs["leak_depth"] = result.depth_md
    elif issubclass(event_cls, FlowEvent):
        # CL-04: campos cinemáticos do InferenceResult. NaN → None via
        # _finite_or_none. SlopeVelocityEvent herda de FlowEvent, então
        # "slope_velocity" e "flow_discrimination" passam por aqui.
        # CL-04 kinematic fields from the InferenceResult. NaN → None via
        # _finite_or_none. SlopeVelocityEvent subclasses FlowEvent, so both
        # "slope_velocity" and "flow_discrimination" flow through here.
        kwargs["apparent_velocity_ms"] = _finite_or_none(result.apparent_velocity_ms)
        kwargs["flow_direction"] = result.flow_direction or None
        kwargs["discrimination"] = result.discrimination or None
        # Sem estimativa física de vazão disponível no resultado C++: o campo
        # opcional flow_rate_ms fica None. A confiança da regra já é propagada
        # via kwargs["confidence"]. Uma estimativa metrológica real (ex.:
        # velocidade da SlopeVelocityRule convertida em vazão com PVT do poço)
        # deve preencher flow_rate_ms no futuro — nunca usar confidence como
        # proxy, pois são grandezas distintas (0..1 vs m/s).
        kwargs["flow_rate_ms"] = None
    elif event_cls is WarmBackEvent:
        kwargs["injection_depths"] = [result.depth_md]

    return event_cls(**kwargs)


class InferenceEngine:
    """
    Wrapper Python do motor de inferência canônica em C++20.

    Atributos de instância / Instance attributes:
        quality_flags : dict
            IE:J-03 — populado a cada chamada de ``infer()`` com as chaves
            ``canais_invalidos`` (nº de canais DTS/DAS com ao menos um valor
            NaN/Inf na entrada) e ``canais_mortos`` (nº de canais sem
            amostras válidas ou com variância nula). A entrada é sanitizada
            (Inf → NaN) antes de ir ao C++. / Populated by each ``infer()``
            call: channels with NaN/Inf samples and dead channels (no valid
            samples or zero variance). Input is sanitized (Inf → NaN).

    Exemplo:
        >>> from alakoro.simulation import SignatureGenerator, WellGeometry, AcquisitionConfig
        >>> from alakoro.ontology.inference_engine import InferenceEngine
        >>> gen = SignatureGenerator(WellGeometry(), AcquisitionConfig())
        >>> sig = gen.generate_joule_thomson()
        >>> engine = InferenceEngine()
        >>> events = engine.infer(sig["dts"], sig["das"], sampling_rate_hz=1000.0, depth_step_m=1.0)
    """

    def __init__(self):
        self._engine = CanonicalInferenceEngine()
        self.quality_flags: dict = {}

    def infer(
        self,
        dts: np.ndarray,
        das: Optional[np.ndarray] = None,
        *,
        sampling_rate_hz: float = 1000.0,
        depth_step_m: float = 1.0,
        surface_temp_c: float = 20.0,
        geo_gradient_cpm: float = 0.03,
        timestamp: Optional[datetime] = None,
        low_freq_band_hz: float = 0.05,
        high_freq_band_hz: float = 1.0,
        discrim_low_freq_hz: float = 15.0,
        discrim_high_freq_hz: float = 100.0,
        apply_band_filter: bool = True,
    ) -> list[Event]:
        """
        Executa todas as regras canônicas sobre dados DTS (e opcionalmente DAS).

        Parameters
        ----------
        dts : np.ndarray
            Array 2D com shape (n_times, n_channels).
        das : np.ndarray, optional
            Array 2D com shape (n_times, n_channels). Pode ser None.
        sampling_rate_hz : float
            Taxa de amostragem no tempo.
        depth_step_m : float
            Espaçamento entre canais/profundidades.
        surface_temp_c : float
            Temperatura superficial para baseline geotérmico.
        geo_gradient_cpm : float
            Gradiente geotérmico em °C/m.
        timestamp : datetime, optional
            Timestamp dos eventos detectados.
        low_freq_band_hz : float
            Banda LF-DAS inferior (Hz) do condicionamento CL-08 aplicado ao
            traço DAS antes das regras quando ``apply_band_filter`` é True.
            LF band lower edge (Hz) for the CL-08 DAS conditioning.
        high_freq_band_hz : float
            Banda LF-DAS superior (Hz). / LF band upper edge (Hz).
        discrim_low_freq_hz : float
            Banda de energia hidráulica inferior (Hz) da discriminação
            ternária de fluxo (CL-04). Hydraulic energy band lower edge (Hz).
        discrim_high_freq_hz : float
            Banda de energia hidráulica superior (Hz). / Upper edge (Hz).
        apply_band_filter : bool
            Se True, aplica bandpass Butterworth na banda LF-DAS no traço
            DAS antes das regras (CL-08). / Apply the LF band-pass (CL-08).

        Returns
        -------
        list[Event]
            Eventos da ontologia inferidos pelas regras C++. Flags de
            qualidade da chamada ficam em ``self.quality_flags`` (IE:J-03).
        """
        dts = np.asarray(dts, dtype=np.float64)
        if dts.ndim != 2:
            raise ValueError("dts must be a 2D array (time, channel)")

        if sampling_rate_hz <= 0:
            raise ValueError(
                f"sampling_rate_hz must be > 0, got {sampling_rate_hz}. "
                "The SlopeVelocityRule divides by the sampling rate; a null or "
                "negative rate would silently corrupt velocity estimates."
            )

        if low_freq_band_hz < 0 or high_freq_band_hz <= low_freq_band_hz:
            raise ValueError(
                f"Invalid LF band: expected 0 <= low < high, got "
                f"[{low_freq_band_hz}, {high_freq_band_hz}] Hz"
            )
        if discrim_low_freq_hz < 0 or discrim_high_freq_hz <= discrim_low_freq_hz:
            raise ValueError(
                f"Invalid discrimination band: expected 0 <= low < high, got "
                f"[{discrim_low_freq_hz}, {discrim_high_freq_hz}] Hz"
            )

        if das is not None:
            das = np.asarray(das, dtype=np.float64)
            if das.shape != dts.shape:
                raise ValueError("das must have the same shape as dts")

        # IE:J-03 — validação de entrada: conta canais com NaN/Inf, sanitiza
        # (Inf → NaN) e detecta canais mortos (sem amostras válidas ou com
        # variância nula). / Input validation: count NaN/Inf channels,
        # sanitize (Inf → NaN) and detect dead channels.
        dts, das, self.quality_flags = self._sanitize_and_flag(dts, das)

        meta = CppInferenceMetadata()
        meta.sampling_rate_hz = float(sampling_rate_hz)
        meta.depth_step_m = float(depth_step_m)
        meta.surface_temp_c = float(surface_temp_c)
        meta.geo_gradient_cpm = float(geo_gradient_cpm)
        # CL-08 (lado Python): bandas LF-DAS e hidráulica repassadas ao
        # metadata C++. / CL-08 (Python side): LF and hydraulic bands
        # forwarded to the C++ metadata.
        meta.low_freq_band_hz = float(low_freq_band_hz)
        meta.high_freq_band_hz = float(high_freq_band_hz)
        meta.discrim_low_freq_hz = float(discrim_low_freq_hz)
        meta.discrim_high_freq_hz = float(discrim_high_freq_hz)
        meta.apply_band_filter = bool(apply_band_filter)

        results = self._engine.infer(dts, das, meta)
        return [_result_to_event(r, timestamp=timestamp) for r in results]

    @staticmethod
    def _sanitize_and_flag(dts: np.ndarray, das: Optional[np.ndarray]
                           ) -> tuple[np.ndarray, Optional[np.ndarray], dict]:
        """Sanitiza Inf → NaN e computa quality_flags (IE:J-03).

        ``canais_invalidos``: canais (de dts e das) com ao menos uma
        amostra não-finita na entrada. ``canais_mortos``: canais sem
        nenhuma amostra válida ou com variância nula entre as amostras
        válidas (fibra morta/constante). / Counts channels with non-finite
        samples and dead channels (all-NaN or zero variance).
        """
        dts = np.where(np.isinf(dts), np.nan, dts)
        arrays = [dts]
        if das is not None:
            das = np.where(np.isinf(das), np.nan, das)
            arrays.append(das)

        invalid = 0
        dead = 0
        for arr in arrays:
            finite = np.isfinite(arr)
            invalid += int(np.count_nonzero(~finite.all(axis=0)))
            n_valid = finite.sum(axis=0)
            var = np.zeros(arr.shape[1], dtype=np.float64)
            enough = n_valid >= 2
            if np.any(enough):
                with warnings.catch_warnings():
                    # Colunas quase-NaN (1 amostra válida) → variância 0;
                    # nanvar emitaria RuntimeWarning de graus de liberdade.
                    # Near-NaN columns (1 valid sample) → variance 0; nanvar
                    # would emit a degrees-of-freedom RuntimeWarning.
                    warnings.simplefilter("ignore", RuntimeWarning)
                    var[enough] = np.nanvar(arr[:, enough], axis=0)
            dead_mask = (n_valid == 0) | (var == 0)
            dead += int(np.count_nonzero(dead_mask))

        quality_flags = {
            "canais_invalidos": invalid,
            "canais_mortos": dead,
        }
        return dts, das, quality_flags

    def decouple_strain_temperature(self, strain: np.ndarray, temp: np.ndarray,
                                    win_t: int = 24, win_z: int = 12,
                                    constrain_cs: bool = True) -> dict:
        """Desacoplamento tensão-temperatura (CL-03) sobre campos 2D.

        Usa o binding C++ ``alakoro_core.decouple_strain_temperature_d``
        quando disponível; caso contrário recai num fallback NumPy puro
        (janelas sem sobreposição, Theil-Sen via ``scipy.stats.theilslopes``
        por janela ou mínimos quadrados quando scipy não estiver instalado —
        ver ``_decouple_fallback``). / Uses the C++ binding when available,
        otherwise falls back to a pure NumPy implementation (non-overlapping
        windows; per-window Theil-Sen via scipy, or least squares without
        scipy — see ``_decouple_fallback``).

        Parameters
        ----------
        strain : np.ndarray
            Campo de strain 2D (t × z), float64. / 2D strain field (t × z).
        temp : np.ndarray
            Campo de temperatura 2D (t × z), mesmo shape de ``strain``.
            2D temperature field, same shape as ``strain``.
        win_t : int
            Janela temporal (>= 8). / Temporal window (>= 8).
        win_z : int
            Janela espacial (>= 8). / Spatial window (>= 8).
        constrain_cs : bool
            Se True, impõe a restrição física C <= 0 (coeficiente espúrio
            positivo desviado para zero). / Enforce the physical C <= 0
            constraint.

        Returns
        -------
        dict
            Chaves ``decoupled`` (2D), ``coefficient_map`` (2D t × z — o
            binding C++ devolve o mapa achatado; o wrapper faz reshape),
            ``global_coefficient`` (float) e ``constrained`` (bool).
            Keys ``decoupled`` (2D), ``coefficient_map`` (2D t × z — the C++
            binding returns the flattened map; the wrapper reshapes it),
            ``global_coefficient`` (float) and ``constrained`` (bool).
        """
        strain = np.asarray(strain, dtype=np.float64)
        temp = np.asarray(temp, dtype=np.float64)
        if strain.ndim != 2 or temp.ndim != 2:
            raise ValueError("strain and temp must be 2D arrays (time, channel)")
        if strain.shape != temp.shape:
            raise ValueError("strain and temp must have the same shape (time, channel)")
        if strain.size == 0:
            raise ValueError("strain and temp must not be empty")
        if win_t < 8 or win_z < 8:
            raise ValueError(f"win_t and win_z must be >= 8, got {win_t}, {win_z}")

        if _cpp_decouple is not None:
            out = _cpp_decouple(strain, temp, int(win_t), int(win_z), bool(constrain_cs))
            out["decoupled"] = np.asarray(out["decoupled"], dtype=np.float64).reshape(strain.shape)
            out["coefficient_map"] = np.asarray(out["coefficient_map"], dtype=np.float64).reshape(strain.shape)
            out["global_coefficient"] = float(out["global_coefficient"])
            out["constrained"] = bool(out["constrained"])
            return out

        return _decouple_fallback(strain, temp, int(win_t), int(win_z), bool(constrain_cs))

    def infer_from_signature(self, signature: dict, timestamp: Optional[datetime] = None) -> list[Event]:
        """
        Executa inferência diretamente sobre um dict retornado por
        SignatureGenerator.

        Parameters
        ----------
        signature : dict
            Dict com chaves 'dts', 'das' e 'parameters'.
        timestamp : datetime, optional
            Timestamp dos eventos.

        Returns
        -------
        list[Event]
            Eventos inferidos.
        """
        dts = signature.get("dts")
        das = signature.get("das")
        params = signature.get("parameters", {})
        depth_step_m = params.get("depth_step_m", 1.0)
        return self.infer(
            dts=dts,
            das=das,
            sampling_rate_hz=_resolve_sampling_rate_hz(signature),
            depth_step_m=depth_step_m,
            timestamp=timestamp,
        )


def infer_events(
    dts: np.ndarray,
    das: Optional[np.ndarray] = None,
    *,
    sampling_rate_hz: float = 1000.0,
    depth_step_m: float = 1.0,
    surface_temp_c: float = 20.0,
    geo_gradient_cpm: float = 0.03,
    timestamp: Optional[datetime] = None,
    low_freq_band_hz: float = 0.05,
    high_freq_band_hz: float = 1.0,
    discrim_low_freq_hz: float = 15.0,
    discrim_high_freq_hz: float = 100.0,
    apply_band_filter: bool = True,
) -> list[Event]:
    """Função helper de alto nível. Cria um InferenceEngine e executa inferência."""
    engine = InferenceEngine()
    return engine.infer(
        dts=dts,
        das=das,
        sampling_rate_hz=sampling_rate_hz,
        depth_step_m=depth_step_m,
        surface_temp_c=surface_temp_c,
        geo_gradient_cpm=geo_gradient_cpm,
        timestamp=timestamp,
        low_freq_band_hz=low_freq_band_hz,
        high_freq_band_hz=high_freq_band_hz,
        discrim_low_freq_hz=discrim_low_freq_hz,
        discrim_high_freq_hz=discrim_high_freq_hz,
        apply_band_filter=apply_band_filter,
    )


def _robust_slope(x: np.ndarray, y: np.ndarray) -> float:
    """Inclinação robusta y~x: Theil-Sen (scipy) ou mínimos quadrados.

    Preferimos ``scipy.stats.theilslopes`` (mesmo estimador do núcleo C++);
    sem scipy, recai em ``np.polyfit`` de grau 1 (regressão simples —
    simplificação documentada, sensível a outliers). / Robust slope y~x:
    Theil-Sen via scipy (same estimator as the C++ core); without scipy,
    plain least squares (documented simplification, outlier-sensitive).
    """
    x = np.asarray(x, dtype=np.float64).ravel()
    y = np.asarray(y, dtype=np.float64).ravel()
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if x.size < 2 or np.ptp(x) == 0.0:
        return 0.0
    try:
        from scipy.stats import theilslopes
    except ImportError:  # pragma: no cover - depende do ambiente / environment-dependent
        return float(np.polyfit(x, y, 1)[0])
    return float(theilslopes(y, x).slope)


def _decouple_fallback(strain: np.ndarray, temp: np.ndarray,
                       win_t: int = 24, win_z: int = 12,
                       constrain_cs: bool = True) -> dict:
    """Fallback NumPy puro do desacoplamento tensão-temperatura (CL-03).

    Simplificações em relação ao núcleo C++ (documentado): janelas
    ``win_t × win_z`` NÃO sobrepostas cobrindo o campo todo (o C++ usa
    janelas centradas com ponderação triangular e média suave nas bordas);
    coeficiente local por Theil-Sen das diferenças contra a linha de
    referência ``temp[0]``/``strain[0]``; coeficiente global por Theil-Sen
    sobre o campo inteiro. Com ``constrain_cs=True``, valores positivos de C
    (espúrios fisicamente) são desviados para 0, como o núcleo.

    Pure NumPy fallback for strain-temperature decoupling (CL-03).
    Documented simplifications vs. the C++ core: non-overlapping
    ``win_t × win_z`` windows covering the whole field (the C++ uses
    centered windows with triangular weighting and smooth edge averaging);
    per-window Theil-Sen slope against the reference row; global Theil-Sen
    over the whole field. With ``constrain_cs=True``, positive C values are
    clipped to 0, as the core does.
    """
    n_t, n_z = strain.shape
    dtemp = temp - temp[0, :]
    dstrain = strain - strain[0, :]

    coefficient_map = np.zeros((n_t, n_z), dtype=np.float64)
    constrained = False
    for t0 in range(0, n_t, win_t):
        t1 = min(t0 + win_t, n_t)
        for z0 in range(0, n_z, win_z):
            z1 = min(z0 + win_z, n_z)
            c_local = _robust_slope(dtemp[t0:t1, z0:z1], dstrain[t0:t1, z0:z1])
            if constrain_cs and c_local > 0.0:
                c_local = 0.0
                constrained = True
            coefficient_map[t0:t1, z0:z1] = c_local

    global_coefficient = _robust_slope(dtemp, dstrain)
    if constrain_cs and global_coefficient > 0.0:
        global_coefficient = 0.0

    decoupled = strain - coefficient_map * dtemp
    return {
        "decoupled": decoupled,
        "coefficient_map": coefficient_map,
        "global_coefficient": float(global_coefficient),
        "constrained": constrained,
    }


__all__ = [
    "InferenceEngine",
    "infer_events",
]
