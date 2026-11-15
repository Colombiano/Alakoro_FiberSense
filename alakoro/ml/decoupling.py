"""
Alakoro FiberSense — Desacoplamento tensão-temperatura para o pipeline ML
Strain-temperature decoupling for the ML pipeline

Autor/Author: Luiz Paulo Colombiano
Licença/License: MIT

Função de alto nível `decouple_for_pipeline` (ML:D-03, ML:E-05, ML:F-04,
ML:I-03) que combina o processamento da Onda 2 (máscara de ponta do cabo,
CL-07) com o núcleo C++20 `alakoro_core.decouple_strain_temperature_d`
(CL-03), incluindo fallback NumPy quando a extensão compilada não está
disponível. O retorno é um dict padronizado independente do backend.

High-level `decouple_for_pipeline` combining Wave-2 processing (cable-end
masking) with the C++20 core routine, with a NumPy fallback. Returns a
backend-independent standardized dict.
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np

try:  # CL-03 / CL-07 — núcleo C++20 da Onda 2
    from alakoro_core import (
        decouple_strain_temperature_d as _cpp_decouple,
        mask_trailing_meters_d as _cpp_mask_trailing,
    )

    _CPP_DISPONIVEL = True
except ImportError:  # pragma: no cover - extensão C++ opcional
    _cpp_decouple = None
    _cpp_mask_trailing = None
    _CPP_DISPONIVEL = False


def _mask_trailing_numpy(data: np.ndarray, step_m: float, mask_m: float) -> np.ndarray:
    """Fallback NumPy de mask_trailing_meters_d (NaN nos últimos mask_m metros)."""
    n_z = data.shape[1]
    first = int(np.floor(((n_z - 1) * step_m - mask_m) / step_m)) + 1
    first = max(0, min(first, n_z))
    out = np.array(data, dtype=np.float64, copy=True)
    out[:, first:] = np.nan
    return out


def _decouple_numpy(strain: np.ndarray,
                    temp: np.ndarray,
                    constrain_cs: bool) -> Dict:
    """
    Fallback NumPy do desacoplamento: regressão Theil-Sen global de
    strain ~ C·ΔT (ΔT = T - T[0, :], contrato do núcleo C++), com
    restrição física C ≤ 0 quando constrain_cs.
    """
    from scipy import stats as scipy_stats

    dtemp = temp - temp[0, :]
    x = dtemp.ravel()
    y = strain.ravel()
    valid = np.isfinite(x) & np.isfinite(y)
    slope, intercept, _, _ = scipy_stats.theilslopes(y[valid], x[valid], 0.95)

    constrained = False
    if constrain_cs and slope > 0.0:
        slope = 0.0
        constrained = True

    decoupled = strain - slope * dtemp
    coefficient_map = np.full_like(strain, slope)
    return {
        "decoupled": decoupled,
        "coefficient_map": coefficient_map,
        "global_coefficient": float(slope),
        "intercept": float(intercept),
        "constrained": constrained,
        "backend": "numpy",
    }


def decouple_for_pipeline(strain: np.ndarray,
                          temp: np.ndarray,
                          *,
                          win_t: int = 24,
                          win_z: int = 12,
                          constrain_cs: bool = True,
                          mask_end_meters: Optional[float] = None,
                          step_m: float = 1.0) -> Dict:
    """
    Desacopla o campo de strain do termo térmico acoplado, pronto para o
    pipeline de inferência. / Decouples the strain field from the coupled
    thermal term, ready for the inference pipeline.

    Args:
        strain: Array 2D (time, channel) do DAS (strain/phase).
        temp: Array 2D (time, channel) da temperatura de referência (mesmo shape).
        win_t: Janela temporal (amostras) da regressão Theil-Sen janelada (C++).
        win_z: Janela espacial (canais) da regressão janelada (C++).
        constrain_cs: Se True, impõe a restrição física C ≤ 0 (coeficiente de
            acoplamento strain-temperatura não positivo).
        mask_end_meters: Se informado, aplica NaN nos últimos metros de fibra
            (CL-07) em ambos os campos antes do ajuste.
        step_m: Espaçamento entre canais [m] (usado pela máscara de ponta).

    Returns:
        Dict padronizado com chaves: "decoupled" (campo corrigido 2D),
        "coefficient_map" (mapa 2D do coeficiente), "global_coefficient",
        "constrained", "backend" ("cpp" ou "numpy") e, quando a máscara é
        usada, "end_mask_m".
    """
    strain = np.ascontiguousarray(np.asarray(strain, dtype=np.float64))
    temp = np.ascontiguousarray(np.asarray(temp, dtype=np.float64))

    if strain.ndim != 2 or temp.ndim != 2:
        raise ValueError("strain e temp devem ser arrays 2D (time, channel)")
    if strain.shape != temp.shape:
        raise ValueError(
            f"shape de strain {strain.shape} incompatível com temp {temp.shape}"
        )

    result: Dict = {}
    if mask_end_meters is not None:
        if _CPP_DISPONIVEL:
            strain = np.asarray(_cpp_mask_trailing(strain, step_m, float(mask_end_meters)))
            temp = np.asarray(_cpp_mask_trailing(temp, step_m, float(mask_end_meters)))
        else:
            strain = _mask_trailing_numpy(strain, step_m, float(mask_end_meters))
            temp = _mask_trailing_numpy(temp, step_m, float(mask_end_meters))
        result["end_mask_m"] = float(mask_end_meters)

    if _CPP_DISPONIVEL:
        out = _cpp_decouple(strain, temp, int(win_t), int(win_z), bool(constrain_cs))
        coefficient_map = np.asarray(out["coefficient_map"], dtype=np.float64)
        if coefficient_map.size == strain.size:
            # O núcleo C++ devolve o mapa achatado; padroniza para 2D.
            coefficient_map = coefficient_map.reshape(strain.shape)
        result.update({
            "decoupled": np.asarray(out["decoupled"], dtype=np.float64),
            "coefficient_map": coefficient_map,
            "global_coefficient": float(out["global_coefficient"]),
            "constrained": bool(out["constrained"]),
            "backend": "cpp",
        })
        return result

    result.update(_decouple_numpy(strain, temp, bool(constrain_cs)))
    return result


__all__ = ["decouple_for_pipeline"]
