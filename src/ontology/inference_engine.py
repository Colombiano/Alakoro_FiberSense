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

import numpy as np

from alakoro_core import (
    InferenceMetadata as CppInferenceMetadata,
    CanonicalInferenceEngine,
)
from .events import (
    Event,
    JouleThomsonEvent,
    LeakEvent,
    FlowEvent,
    WarmBackEvent,
)

# Mapeamento de códigos de evento do C++ para classes da ontologia.
_EVENT_CLASS_MAP = {
    "joule_thomson": JouleThomsonEvent,
    "slope_velocity": FlowEvent,
    "warm_back": WarmBackEvent,
    "valve_chatter": Event,
    "slugging_cycle": Event,
    "leak_path": LeakEvent,
    "glv_bellow_rupture": Event,
    "perforation_effectiveness": Event,
    "frac_screenout": Event,
    "frac_proppant_distribution": Event,
    "frac_height_growth": Event,
    "cement_bond_evaluation": Event,
    "re_cementing_assessment": Event,
    "crossflow_zonal": Event,
    "cement_channeling": Event,
}


def _map_severity(severity: str) -> str:
    """Normaliza severidade para os valores canônicos da ontologia."""
    return severity if severity in {"Low", "Medium", "High"} else "Low"


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
    elif event_cls is FlowEvent:
        kwargs["flow_rate_ms"] = result.confidence  # proxy para PoC
    elif event_cls is WarmBackEvent:
        kwargs["injection_depths"] = [result.depth_md]

    return event_cls(**kwargs)


class InferenceEngine:
    """
    Wrapper Python do motor de inferência canônica em C++20.

    Exemplo:
        >>> from src.simulation import SignatureGenerator, WellGeometry, AcquisitionConfig
        >>> from src.ontology.inference_engine import InferenceEngine
        >>> gen = SignatureGenerator(WellGeometry(), AcquisitionConfig())
        >>> sig = gen.generate_joule_thomson()
        >>> engine = InferenceEngine()
        >>> events = engine.infer(sig["dts"], sig["das"], sampling_rate_hz=1000.0, depth_step_m=1.0)
    """

    def __init__(self):
        self._engine = CanonicalInferenceEngine()

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

        Returns
        -------
        list[Event]
            Eventos da ontologia inferidos pelas regras C++.
        """
        dts = np.asarray(dts, dtype=np.float64)
        if dts.ndim != 2:
            raise ValueError("dts must be a 2D array (time, channel)")

        if das is not None:
            das = np.asarray(das, dtype=np.float64)
            if das.shape != dts.shape:
                raise ValueError("das must have the same shape as dts")

        meta = CppInferenceMetadata()
        meta.sampling_rate_hz = float(sampling_rate_hz)
        meta.depth_step_m = float(depth_step_m)
        meta.surface_temp_c = float(surface_temp_c)
        meta.geo_gradient_cpm = float(geo_gradient_cpm)

        results = self._engine.infer(dts, das, meta)
        return [_result_to_event(r, timestamp=timestamp) for r in results]

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
            sampling_rate_hz=1000.0,
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
    )


__all__ = [
    "InferenceEngine",
    "infer_events",
]
