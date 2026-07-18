"""
Módulo de Eventos / Events Module
"""

import json
import os

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'fibersense_event_schema_v1.1.0.json')

EVENT_SCHEMA = None
try:
    with open(_SCHEMA_PATH, 'r', encoding='utf-8') as f:
        EVENT_SCHEMA = json.load(f)
except FileNotFoundError:
    pass

__all__ = ['EVENT_SCHEMA']
