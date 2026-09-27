"""
Alakoro FiberSense — Bridge Simulador ↔ Ontologia
Signature Simulator → Ontology Bridge

Converte assinaturas sintéticas geradas pelo SignatureGenerator em
instâncias da ontologia Alakoro.
"""

from datetime import datetime
from typing import Optional
from ..simulation import SignatureGenerator, WellGeometry, AcquisitionConfig, EventSignatureType
from .core import OntologyModel
from .petroleum import Well, Wellbore, FiberOpticCable
from .sensing import Interrogator, DASMeasurement, DTSMeasurement
from .events import JouleThomsonEvent, LeakEvent, FlowEvent, WarmBackEvent, Event


class SignatureOntologyBridge:
    """Converte assinaturas do simulador em entidades ontológicas."""

    def __init__(self, model: Optional[OntologyModel] = None):
        self.model = model or OntologyModel()

    def build_from_signature(self, signature_data: dict,
                             well: Optional[Well] = None,
                             wellbore: Optional[Wellbore] = None,
                             cable: Optional[FiberOpticCable] = None,
                             interrogator: Optional[Interrogator] = None):
        """Popula a ontologia a partir de uma assinatura gerada."""
        params = signature_data.get("parameters", {})
        sig_type = signature_data.get("signature_type")
        dts = signature_data.get("dts")
        das = signature_data.get("das")

        if well is None:
            well = Well(name="Synthetic Well", operator="Alakoro", status="active")
        if wellbore is None:
            wellbore = Wellbore(name="Synthetic Wellbore",
                                measured_depth_top=0.0,
                                measured_depth_bottom=3000.0)
            well.add_wellbore(wellbore)
        if cable is None:
            cable = FiberOpticCable(name="Synthetic Fiber",
                                    depth_top=0.0,
                                    depth_bottom=3000.0,
                                    n_channels=dts.shape[1] if dts is not None else None)
            wellbore.add_cable(cable)
        if interrogator is None:
            interrogator = Interrogator(name="Synthetic Interrogator",
                                        manufacturer="Alakoro",
                                        model="Sim-1")

        self.model.add(well)
        self.model.add(interrogator)

        if dts is not None:
            dts_measurement = DTSMeasurement(
                name="Synthetic DTS Measurement",
                n_channels=dts.shape[1],
                n_time_samples=dts.shape[0],
                start_time=datetime.now(),
            )
            dts_measurement.wellbore = wellbore
            dts_measurement.cable = cable
            dts_measurement.interrogator = interrogator
            self.model.add(dts_measurement)
        else:
            dts_measurement = None

        if das is not None:
            das_measurement = DASMeasurement(
                name="Synthetic DAS Measurement",
                n_channels=das.shape[1],
                n_time_samples=das.shape[0],
                start_time=datetime.now(),
            )
            das_measurement.wellbore = wellbore
            das_measurement.cable = cable
            das_measurement.interrogator = interrogator
            self.model.add(das_measurement)
        else:
            das_measurement = None

        event = self._create_event(sig_type, params)
        if event is not None:
            if dts_measurement is not None:
                event.add_measurement(dts_measurement)
            if das_measurement is not None:
                event.add_measurement(das_measurement)
            self.model.add(event)

        return self.model

    def _create_event(self, sig_type: EventSignatureType, params: dict) -> Optional[Event]:
        """Cria o evento apropriado com base no tipo de assinatura."""
        code = sig_type.code if hasattr(sig_type, "code") else str(sig_type)

        mapping = {
            "dipolo_thermal_jt": lambda: JouleThomsonEvent(
                interface_depth=params.get("interface_depth_m"),
                depth_md=params.get("interface_depth_m"),
                confidence=0.92,
                severity="Medium",
                recommendation="Monitorar pressão do ânulo",
            ),
            "leak_path_tubing_annulus": lambda: LeakEvent(
                leak_depth=params.get("leak_depth_m"),
                depth_md=params.get("leak_depth_m"),
                confidence=0.85,
                severity="High",
                recommendation="Investigar vazamento tubing↔ânulo",
            ),
            "slope_velocity_tracking": lambda: FlowEvent(
                flow_rate_ms=params.get("flow_velocity_ms"),
                depth_md=params.get("flow_start_depth_m"),
                confidence=0.78,
                severity="Low",
                recommendation="Acompanhar fronte de fluxo",
            ),
            "warm_back_recovery": lambda: WarmBackEvent(
                injection_depths=params.get("injection_depths_m", []),
                depth_md=params.get("injection_depths_m", [0])[0] if params.get("injection_depths_m") else None,
                confidence=0.88,
                severity="Medium",
                recommendation="Avaliar recuperação térmica",
            ),
        }

        factory = mapping.get(code)
        if factory is None:
            return Event(
                event_type=code,
                name=sig_type.en if hasattr(sig_type, "en") else code,
                depth_md=None,
                confidence=0.7,
                severity="Medium",
                recommendation="Revisar assinatura",
            )
        return factory()
