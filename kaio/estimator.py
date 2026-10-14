"""Onboard value estimator.

This is the part of KAIO that would run on the spacecraft for every new image. It needs only
two numbers per scene, both available onboard in real life:

* the Shannon entropy of a small quick-look thumbnail (computed in microseconds), and
* the land fraction of the footprint, looked up in a static land/water mask stored onboard
  and indexed by the satellite position from GNSS / the onboard orbit propagator.

Finding on real NASA data: raw entropy alone misranks scenes because clouds are the most
textured scenes. Multiplying by the land prior fixes the ranking.
"""
from __future__ import annotations

import numpy as np

def semantic_value(entropy: float, priority: int, alpha: float = 3.0, h_max: float = 8.0) -> float:
    """w_i = p_i * (H_i / H_max)^alpha  (entropy-sharpened semantic weight)."""
    return priority * (entropy / h_max) ** alpha


def semantic_estimate(entropy: float, priority: int, land_prior: float, optical: bool,
                      estimator: str = "entropy_land", eps: float = 0.1, alpha: float = 3.0) -> float:
    """Onboard value estimate from quick-look entropy and the static land-mask prior of the footprint.

    entropy_land : p * (eps + (1-eps) * land) * (H/8)^alpha for optical quick-looks,
                   p * (eps + (1-eps) * land) for thermal-IR quick-looks (night-time TIR entropy is
                   dominated by cloud-top texture and anti-correlated with value on real data)
    entropy      : p * (H/8)^alpha            (raw semantic entropy)
    land         : p * (eps + (1-eps) * land)
    """
    g = eps + (1.0 - eps) * land_prior
    if estimator == "entropy":
        return priority * (entropy / 8.0) ** alpha
    if estimator == "land":
        return priority * g
    return priority * g * ((entropy / 8.0) ** alpha if optical else 1.0)



def shannon_entropy(img: np.ndarray) -> float:
    """H(S) = -sum p(x) log2 p(x) over the 8-bit grey-level histogram of a quick-look."""
    hist = np.bincount(np.asarray(img, dtype=np.uint8).ravel(), minlength=256).astype(float)
    p = hist[hist > 0] / hist.sum()
    return float(-(p * np.log2(p)).sum())
