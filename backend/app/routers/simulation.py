"""
Alakoro FiberSense - Simulation Router
Endpoints para simulacao de sinais DAS, DTS e DSS.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.controllers import SignalStore
from app.core.events import EventType, publish_event
from app.models import SignalData, SignalType
from app.simulation.das_simulator import DASSimulator
from app.simulation.dss_simulator import DSSSimulator
from app.simulation.dts_simulator import DTSSimulator

router = APIRouter()


@router.post("/das")
async def simulate_das(config: dict):
    """Simula dados DAS."""
    try:
        sim = DASSimulator(
            fiber_length=config.get("fiber_length", 10000.0),
            spatial_resolution=config.get("spatial_resolution", 1.0),
            sampling_rate=config.get("sampling_rate", 1000.0),
            duration=config.get("duration", 10.0),
        )
        data = sim.generate(events=config.get("events", []))

        signal = SignalData(
            signal_type=SignalType.DAS,
            raw_data=data,
            params=sim.params,
        )
        SignalStore.add(signal)

        await publish_event(EventType.SIMULATION_COMPLETED, {
            "simulation_id": signal.id,
            "signal_type": "das",
            "shape": list(data.shape),
        })

        return {
            "signal_id": signal.id,
            "signal_type": "das",
            "shape": list(data.shape),
            "params": sim.params.to_dict(),
            "events_injected": len(config.get("events", [])),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dts")
async def simulate_dts(config: dict):
    """Simula dados DTS."""
    try:
        sim = DTSSimulator(
            fiber_length=config.get("fiber_length", 10000.0),
            spatial_resolution=config.get("spatial_resolution", 1.0),
            sampling_rate=config.get("sampling_rate", 1.0),
            duration=config.get("duration", 3600.0),
        )
        data = sim.generate(events=config.get("events", []))

        signal = SignalData(
            signal_type=SignalType.DTS,
            raw_data=data,
            params=sim.params,
        )
        SignalStore.add(signal)

        await publish_event(EventType.SIMULATION_COMPLETED, {
            "simulation_id": signal.id,
            "signal_type": "dts",
            "shape": list(data.shape),
        })

        return {
            "signal_id": signal.id,
            "signal_type": "dts",
            "shape": list(data.shape),
            "params": sim.params.to_dict(),
            "events_injected": len(config.get("events", [])),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dss")
async def simulate_dss(config: dict):
    """Simula dados DSS."""
    try:
        sim = DSSSimulator(
            fiber_length=config.get("fiber_length", 10000.0),
            spatial_resolution=config.get("spatial_resolution", 1.0),
            sampling_rate=config.get("sampling_rate", 100.0),
            duration=config.get("duration", 3600.0),
        )
        data = sim.generate(events=config.get("events", []))

        signal = SignalData(
            signal_type=SignalType.DSS,
            raw_data=data,
            params=sim.params,
        )
        SignalStore.add(signal)

        await publish_event(EventType.SIMULATION_COMPLETED, {
            "simulation_id": signal.id,
            "signal_type": "dss",
            "shape": list(data.shape),
        })

        return {
            "signal_id": signal.id,
            "signal_type": "dss",
            "shape": list(data.shape),
            "params": sim.params.to_dict(),
            "events_injected": len(config.get("events", [])),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def get_templates():
    """Retorna templates de simulacao pre-configurados."""
    return {
        "das": {
            "name": "DAS Standard",
            "description": "Simulacao padrao para DAS",
            "default_config": {
                "fiber_length": 10000.0,
                "spatial_resolution": 1.0,
                "sampling_rate": 1000.0,
                "duration": 10.0,
                "noise_level": 0.01,
            },
        },
        "dts": {
            "name": "DTS Standard",
            "description": "Simulacao padrao para DTS",
            "default_config": {
                "fiber_length": 10000.0,
                "spatial_resolution": 1.0,
                "sampling_rate": 1.0,
                "duration": 3600.0,
                "noise_level": 0.1,
            },
        },
        "dss": {
            "name": "DSS Standard",
            "description": "Simulacao padrao para DSS",
            "default_config": {
                "fiber_length": 5000.0,
                "spatial_resolution": 0.5,
                "sampling_rate": 100.0,
                "duration": 3600.0,
                "noise_level": 0.001,
            },
        },
    }
