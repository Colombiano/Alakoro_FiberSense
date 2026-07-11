"""Wavelet analysis endpoints for DAS acoustic transient detection.

Provides CWT (Continuous Wavelet Transform), scalogram computation,
transient detection, and wavelet denoising via the C++ engine.

References:
    - Torrence & Compo (1998) - A Practical Guide to Wavelet Analysis
    - SPE papers on wavelet-based DAS transient detection
"""
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class WaveletConfigRequest(BaseModel):
    """Configuration for wavelet transforms."""
    central_freq: float = Field(default=6.0, ge=1.0, le=20.0,
                                 description="Morlet central frequency omega0")
    num_scales: int = Field(default=128, ge=16, le=512,
                            description="Number of scales for CWT")
    scale_min: float = Field(default=1.0, ge=0.1,
                              description="Minimum scale")
    scale_max: float = Field(default=512.0, ge=1.0,
                              description="Maximum scale")
    dwt_levels: int = Field(default=4, ge=1, le=10,
                             description="DWT decomposition levels")
    denoise_threshold: float = Field(default=3.0, ge=0.5, le=10.0,
                                      description="Threshold multiplier")
    threshold_mode: str = Field(default="soft",
                                 description="'soft' or 'hard' thresholding")


class CWTRequest(BaseModel):
    """Request for Continuous Wavelet Transform."""
    signal: List[float] = Field(..., description="1D signal vector")
    fs: float = Field(..., gt=0, description="Sampling frequency in Hz")
    config: Optional[WaveletConfigRequest] = None


class ScalogramRequest(BaseModel):
    """Request for scalogram computation."""
    signal: List[float] = Field(..., description="1D signal vector")
    fs: float = Field(..., gt=0, description="Sampling frequency in Hz")
    config: Optional[WaveletConfigRequest] = None


class TransientDetectRequest(BaseModel):
    """Request for transient detection via CWT ridges."""
    signal: List[float] = Field(..., description="1D signal vector")
    fs: float = Field(..., gt=0, description="Sampling frequency in Hz")
    threshold: float = Field(default=4.0, ge=1.0, le=10.0,
                              description="Ridge detection threshold (std dev)")
    config: Optional[WaveletConfigRequest] = None


class DenoiseRequest(BaseModel):
    """Request for wavelet denoising."""
    signal: List[float] = Field(..., description="Noisy signal vector")
    levels: int = Field(default=-1, ge=-1, le=10,
                         description="Decomposition levels (-1=auto)")
    method: str = Field(default="visu",
                         description="'visu' (VisuShrink) or 'sure' (SureShrink)")
    config: Optional[WaveletConfigRequest] = None


class ScaleAverageRequest(BaseModel):
    """Request for scale-averaged wavelet power."""
    scalogram: List[List[float]] = Field(..., description="CWT scalogram [scales x time]")
    scales: List[float] = Field(..., description="Analysis scales")
    frequencies: List[float] = Field(..., description="Equivalent frequencies")
    fmin: float = Field(..., description="Minimum frequency for averaging")
    fmax: float = Field(..., description="Maximum frequency for averaging")


# ---------------------------------------------------------------------------
# Helper: C++ engine wrapper
# ---------------------------------------------------------------------------

def _get_wavelet_processor(config: Optional[WaveletConfigRequest] = None):
    """Get or create a WaveletProcessor from the C++ engine."""
    try:
        import alakoro_engine as ae

        if config:
            cfg = ae.WaveletConfig()
            cfg.central_freq = config.central_freq
            cfg.num_scales = config.num_scales
            cfg.scale_min = config.scale_min
            cfg.scale_max = config.scale_max
            cfg.dwt_levels = config.dwt_levels
            cfg.denoise_threshold = config.denoise_threshold
            cfg.threshold_mode = config.threshold_mode
            return ae.WaveletProcessor(cfg)
        return ae.WaveletProcessor()
    except ImportError:
        logger.warning("C++ engine not available, using Python fallback")
        return None


def _py_cwt_fallback(signal: list, fs: float, config: WaveletConfigRequest):
    """Pure Python CWT fallback when C++ engine is unavailable."""
    n = len(signal)
    dt = 1.0 / fs
    mean = np.mean(signal)
    sig = np.array(signal) - mean

    # Log-spaced scales
    scales = np.logspace(
        np.log2(config.scale_min),
        np.log2(config.scale_max),
        config.num_scales,
        base=2
    )
    n_scales = len(scales)
    omega0 = config.central_freq

    # Time axis
    time = np.arange(n) * dt

    # Frequencies
    frequencies = omega0 / (2 * np.pi * scales / fs)

    # Morlet wavelet in frequency domain (more efficient)
    # FFT of signal
    sig_fft = np.fft.fft(sig)
    freqs_fft = np.fft.fftfreq(n, dt)

    scalogram = np.zeros((n_scales, n))
    coeffs = []

    for j, scale in enumerate(scales):
        # Normalized Morlet in frequency domain
        norm = np.sqrt(scale) * np.pi ** 0.25
        exponent = -0.5 * (scale * 2 * np.pi * freqs_fft - omega0) ** 2
        daughter = norm * np.exp(exponent)
        daughter[freqs_fft < 0] = 0  # Heaviside step

        # Inverse FFT for convolution
        conv = np.fft.ifft(sig_fft * daughter)
        scalogram[j, :] = np.abs(conv) ** 2
        coeffs.append(conv.tolist())

    return {
        "scalogram": scalogram.tolist(),
        "coeffs": coeffs,
        "scales": scales.tolist(),
        "frequencies": frequencies.tolist(),
        "time": time.tolist(),
    }


def _py_denoise_fallback(signal: list, levels: int, method: str):
    """Pure Python wavelet denoising fallback using PyWavelets if available."""
    try:
        import pywt
        sig = np.array(signal)
        if levels < 0:
            levels = min(pywt.dwt_max_level(len(sig), 'db4'), 4)

        # DWT
        coeffs = pywt.wavedec(sig, 'db4', level=levels)

        # Threshold detail coefficients
        for i in range(1, len(coeffs)):
            sigma = np.median(np.abs(coeffs[i])) / 0.6745
            thresh = sigma * np.sqrt(2 * np.log(len(coeffs[i])))
            if method == "sure":
                # Simplified SURE
                thresh *= 0.7
            coeffs[i] = pywt.threshold(coeffs[i], thresh, mode='soft')

        return pywt.waverec(coeffs, 'db4').tolist()[:len(signal)]
    except ImportError:
        # Very basic fallback: just return signal unchanged
        logger.warning("PyWavelets not available, returning signal as-is")
        return signal


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/cwt")
async def compute_cwt(request: CWTRequest):
    """Compute Continuous Wavelet Transform (CWT) with Morlet wavelet.

    Returns the full CWT result including complex coefficients, scalogram,
    scales, and equivalent Fourier frequencies. The Morlet wavelet is
    optimal for detecting oscillatory transients in DAS signals.
    """
    wp = _get_wavelet_processor(request.config)

    if wp is not None:
        try:
            result = wp.cwt(request.signal, request.fs)
            return {
                "scalogram": result.scalogram,
                "scales": result.scales,
                "frequencies": result.frequencies,
                "time": result.time,
                "engine": "cpp",
            }
        except Exception as e:
            logger.error(f"C++ CWT failed: {e}, falling back to Python")

    # Python fallback
    result = _py_cwt_fallback(request.signal, request.fs,
                               request.config or WaveletConfigRequest())
    result["engine"] = "python"
    return result


@router.post("/scalogram")
async def compute_scalogram(request: ScalogramRequest):
    """Compute CWT scalogram (magnitude squared) only.

    Faster than full CWT when only the scalogram visualization is needed.
    Returns the scalogram matrix [scales x time] with axes.
    """
    wp = _get_wavelet_processor(request.config)

    if wp is not None:
        try:
            scalogram = wp.scalogram(request.signal, request.fs)
            # Get scales and frequencies from a mini-CWT
            cfg = request.config or WaveletConfigRequest()
            scales = np.logspace(
                np.log2(cfg.scale_min), np.log2(cfg.scale_max),
                cfg.num_scales, base=2
            )
            frequencies = cfg.central_freq / (2 * np.pi * scales / request.fs)
            time = np.arange(len(request.signal)) / request.fs
            return {
                "scalogram": scalogram,
                "scales": scales.tolist(),
                "frequencies": frequencies.tolist(),
                "time": time.tolist(),
                "engine": "cpp",
            }
        except Exception as e:
            logger.error(f"C++ scalogram failed: {e}, falling back to Python")

    # Python fallback
    result = _py_cwt_fallback(request.signal, request.fs,
                               request.config or WaveletConfigRequest())
    result["engine"] = "python"
    return result


@router.post("/transients")
async def detect_transients(request: TransientDetectRequest):
    """Detect transient acoustic events using CWT ridge detection.

    Identifies ridges in the scalogram that correspond to transient events.
    This method is significantly more sensitive than STFT-based approaches
    for short-duration acoustic events common in hydraulic fracturing
    and well monitoring applications.

    Returns a list of detected transients with (time, frequency, amplitude).
    """
    wp = _get_wavelet_processor(request.config)

    if wp is not None:
        try:
            transients = wp.detect_transients(
                request.signal, request.fs, request.threshold
            )
            return {
                "transients": [
                    {"time": t, "frequency": f, "amplitude": a}
                    for t, f, a in transients
                ],
                "count": len(transients),
                "engine": "cpp",
            }
        except Exception as e:
            logger.error(f"C++ transient detection failed: {e}")

    # Python fallback: simple energy-based detection on CWT
    cfg = request.config or WaveletConfigRequest()
    cwt_result = _py_cwt_fallback(request.signal, request.fs, cfg)
    scalogram = np.array(cwt_result["scalogram"])

    # Find local maxima above threshold
    threshold = np.mean(scalogram) + request.threshold * np.std(scalogram)
    transients = []

    for j in range(1, scalogram.shape[0] - 1):
        for i in range(1, scalogram.shape[1] - 1):
            val = scalogram[j, i]
            if val > threshold:
                # Check local maximum
                neighborhood = scalogram[j-1:j+2, i-1:i+2]
                if val == neighborhood.max():
                    transients.append({
                        "time": cwt_result["time"][i],
                        "frequency": cwt_result["frequencies"][j],
                        "amplitude": float(np.sqrt(val)),
                    })

    return {
        "transients": transients,
        "count": len(transients),
        "engine": "python_fallback",
    }


@router.post("/denoise")
async def wavelet_denoise(request: DenoiseRequest):
    """Apply wavelet denoising to a signal.

    Uses DWT with Daubechies-4 wavelet and thresholding of detail
    coefficients. Two methods available:

    - **visu**: VisuShrink with universal threshold (MAD-based)
    - **sure**: SureShrink with Stein's Unbiased Risk Estimate

    Particularly effective for DAS signals where noise is distributed
    across all scales but acoustic transients concentrate at specific
    scales.
    """
    wp = _get_wavelet_processor(request.config)

    if wp is not None:
        try:
            if request.method == "sure":
                denoised = wp.denoise_sure(request.signal, request.levels)
            else:
                denoised = wp.denoise(request.signal, request.levels)
            return {
                "denoised": denoised,
                "original_length": len(request.signal),
                "method": request.method,
                "engine": "cpp",
            }
        except Exception as e:
            logger.error(f"C++ denoising failed: {e}, falling back to Python")

    # Python fallback
    denoised = _py_denoise_fallback(
        request.signal, request.levels, request.method
    )
    return {
        "denoised": denoised,
        "original_length": len(request.signal),
        "method": request.method,
        "engine": "python_fallback",
    }


@router.post("/scale-average")
async def scale_average_power(request: ScaleAverageRequest):
    """Compute scale-averaged wavelet power over a frequency band.

    Averages the scalogram over scales corresponding to the specified
    frequency range. Useful for identifying energy concentration in
    specific frequency bands (e.g., fracture events at 50-200 Hz).
    """
    scalogram = np.array(request.scalogram)
    frequencies = np.array(request.frequencies)

    # Find scale indices for the frequency band
    mask = (frequencies >= request.fmin) & (frequencies <= request.fmax)
    indices = np.where(mask)[0]

    if len(indices) == 0:
        raise HTTPException(400, "No scales in specified frequency band")

    # Average power over selected scales
    avg_power = np.mean(scalogram[indices, :], axis=0)

    return {
        "average_power": avg_power.tolist(),
        "scales_used": len(indices),
        "frequency_range": [float(request.fmin), float(request.fmax)],
    }


@router.get("/info")
async def wavelet_info():
    """Get information about available wavelet capabilities."""
    cpp_available = False
    try:
        import alakoro_engine as ae
        cpp_available = ae.have_wavelets()
    except ImportError:
        pass

    pywt_available = False
    try:
        import pywt
        pywt_available = True
    except ImportError:
        pass

    return {
        "wavelet_support": True,
        "cpp_engine": cpp_available,
        "pywavelets": pywt_available,
        "available_methods": {
            "cwt": True,
            "scalogram": True,
            "transient_detection": True,
            "denoising": ["visu", "sure"],
        },
        "wavelets": {
            "cwt": ["morlet"],
            "dwt": ["db4"],
        },
        "references": [
            "Torrence & Compo (1998) - A Practical Guide to Wavelet Analysis",
            "Mallat (2008) - A Wavelet Tour of Signal Processing",
            "SPE papers on wavelet-based DAS transient detection",
        ],
    }
