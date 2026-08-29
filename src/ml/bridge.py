"""
Alakoro FiberSense — Bridge ML ↔ Ontologia

Converte predições de modelos ML em entidades ontológicas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from src.ontology.core import OntologyModel
from src.ontology.events import Event


class MLOntoBridge:
    """
    Conecta predições ML à ontologia Alakoro.

    Exemplo:
        event_pred = predict_event(model, patch)
        bridge.add_event(event_pred, well_id="Well-01")
    """

    def __init__(self, ontology: Optional[OntologyModel] = None):
        self.onto = ontology or OntologyModel()

    def add_event(self,
                  prediction: Dict,
                  well_id: str,
                  event_type: str = "DetectedEvent",
                  confidence_threshold: float = 0.5) -> bool:
        """
        Adiciona um evento predito à ontologia, se confiança for suficiente.

        Args:
            prediction: saída de predict_event
            well_id: identificador do poço
            event_type: tipo de evento
            confidence_threshold: limiar mínimo de confiança
        """
        if not prediction.get("event", False):
            return False

        confidence = prediction.get("confidence", 0.0)
        if confidence < confidence_threshold:
            return False

        location = prediction.get("location", (None, None))
        depth_md = float(location[1]) if location[1] is not None else None

        event = Event(
            identifier=f"{event_type}_{well_id}_{id(prediction)}",
            name=f"ML Detected {event_type}",
            event_type=event_type,
            timestamp=datetime.now(),
            depth_md=depth_md,
            confidence=float(confidence),
            severity="medium" if confidence < 0.8 else "high",
            recommendation="Verify with additional measurements",
        )
        self.onto.add(event)
        return True

    def get_ontology(self) -> OntologyModel:
        """Retorna a ontologia populada."""
        return self.onto
