"""Alakoro FiberSense Pro - Main Application Entry Point."""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.redis_client import event_bus
from app.routers import das, dts, dss, upload, simulation, export, wavelet
from app.consumers import start_event_consumers

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("=" * 60)
    print("  Alakoro FiberSense Pro - Starting up")
    print(f"  Version: {settings.APP_VERSION}")
    print(f"  Mode: {'DEBUG' if settings.DEBUG else 'PRODUCTION'}")
    print("=" * 60)

    # Connect to Redis
    await event_bus.connect()
    print("[OK] Redis event bus connected")

    # Start event consumers
    await start_event_consumers()
    print("[OK] Event consumers started")

    yield

    # Shutdown
    print("\n[SHUTDOWN] Disconnecting from Redis...")
    await event_bus.disconnect()
    print("[OK] Redis disconnected")
    print("=" * 60)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Alakoro FiberSense Pro - Signal Processing Platform",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(das.router, prefix="/api/das", tags=["DAS"])
app.include_router(dts.router, prefix="/api/dts", tags=["DTS"])
app.include_router(dss.router, prefix="/api/dss", tags=["DSS"])
app.include_router(simulation.router, prefix="/api/simulation", tags=["Simulation"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])
app.include_router(wavelet.router, prefix="/api/wavelet", tags=["Wavelet"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "service": "Alakoro FiberSense Pro",
    }


@app.get("/api/info")
async def info():
    """Service information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Signal processing for DAS, DTS, and DSS",
        "features": [
            "DAS - Distributed Acoustic Sensing",
            "DTS - Distributed Temperature Sensing",
            "DSS - Distributed Strain Sensing",
            "CWT Wavelet Transforms (Morlet) for Transient Detection",
            "Wavelet Scalogram Analysis",
            "Wavelet Denoising (VisuShrink / SureShrink)",
            "Real-time Signal Simulation",
            "Multi-format Export (HDF5, NetCDF, CSV)",
        ],
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Alakoro FiberSense Pro API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
