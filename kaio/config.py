"""KAIO configuration: physical constants, the action set and ``SimConfig``.

Every numeric assumption of the simulated spacecraft lives in ``SimConfig`` so that a
reviewer can find (and challenge) it in one place.
"""
from __future__ import annotations

import math
import os
import datetime as _dt
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
MU_EARTH = 398600.4418          # km^3 s^-2
R_EARTH = 6378.137              # km
J2 = 1.08262668e-3              # Earth oblateness coefficient
SIGMA_SB = 5.670374419e-8       # W m^-2 K^-4
KELVIN = 273.15

ACTIONS = ("STORE", "PROCESS", "TRANSMIT", "OFFLOAD_ISLL")
ACTION_CODE = {a: i for i, a in enumerate(ACTIONS)}
RESOURCE_ACTION = {"gpu": "PROCESS", "dl": "TRANSMIT", "isl": "OFFLOAD_ISLL"}

# Scene catalogue: occurrence probability and ground-truth scientific value.
# The engine never sees the scene label -- only the thumbnail entropy and the
# instrument priority flag. Ground truth is used exclusively for scoring.
SCENES = {
    #            prob   true value
    "ocean":    (0.40, 0.05),
    "cloud":    (0.28, 0.02),
    "land":     (0.20, 0.45),
    "urban":    (0.08, 0.65),
    "anomaly":  (0.04, 3.00),   # thermal anomaly (fire, flare, volcanic hot spot)
}

# Real ground-station sites (lat, lon in degrees).
GROUND_STATIONS = {
    "Svalbard (KSAT SvalSat)": (78.2297, 15.3975),
    "Matera (ASI CGS)": (40.6486, 16.7046),
}
PKG_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(PKG_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "data")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@dataclass
class SimConfig:
    # --- time ---
    epoch: Tuple[int, int, int, int, int, int] = (2026, 8, 26, 0, 0, 0)   # start of the real-data window
    start_day: int = 0                  # offset (days) into the real 30-day window
    duration_h: float = 24.0
    dt: float = 10.0                    # slot length [s]
    seed: int = 7

    # --- orbit ---
    orbit_model: str = "sgp4"           # "sgp4" = real PHISAT-2 TLE; "rk4_j2" = idealised circular SSO
    tle_path: str = ""                  # default: data/phisat2_tle.txt
    workload: str = "real"              # "real" = NASA GIBS atlas; "synthetic" = procedural thumbnails
    atlas_path: str = ""                # default: data/elotus_gibs_atlas.bin
    fire_trigger_px: int = 128          # TIR trigger: >= 12.5 % of the quick-look flagged by VIIRS 375 m fires
    estimator: str = "entropy_land"     # "entropy_land" (default), "entropy" (raw), "land" (prior only)
    altitude_km: float = 500.0
    inclination_deg: float = 97.40
    ltan_h: float = 22.5                # local time of ascending node [h]
    elevation_mask_deg: float = 10.0
    ground_stations: Dict[str, Tuple[float, float]] = field(
        default_factory=lambda: dict(GROUND_STATIONS))

    # --- power ---
    battery_wh: float = 100.0           # LiFePO4 pack
    soc0: float = 0.70
    e_crit_wh: float = 20.0             # hard floor -> payload load-shedding
    e_reserve_wh: float = 30.0          # policy reserve (soft floor, E-LOTUS)
    eta_charge: float = 0.95
    eta_discharge: float = 0.95
    p_charge_max_w: float = 40.0        # 0.4 C charge limit, CV taper above 90 % SOC
    p_face_w: float = 20.0              # per body-mounted face at normal incidence
    p_bus_w: float = 5.0                # OBC, ADCS, EPS, receivers
    p_gpu_idle_w: float = 1.5
    p_gpu_active_w: float = 15.0        # Jetson Orin-class module, 15 W mode
    p_tx_w: float = 12.0                # S/X-band transmitter (DC input)
    p_isl_w: float = 8.0                # optical ISL terminal (DC input)

    # --- compute ---
    gpu_gflops: float = 1000.0          # effective sustained GFLOP/s (derated)
    gflop_per_mb: float = 900.0         # onboard pipeline cost per MB of raw data
    product_ratio: float = 0.03         # product size / raw size after processing
    eta_process: float = 0.90           # fraction of information kept by a product

    # --- thermal (lumped node, radiator to deep space) ---
    emissivity: float = 0.85
    radiator_area_m2: float = 0.045
    k_thermal: float = 1.0              # dissipation coefficient multiplier (slider)
    heat_capacity_j_per_k: float = 1500.0
    q_sun_w: float = 6.0                # absorbed solar + albedo when sunlit
    q_earth_ir_w: float = 3.0           # absorbed Earth IR (always)
    t_space_k: float = 3.0
    t0_c: float = 15.0
    t_safe_c: float = 45.0              # soft limit (Lyapunov thermal deficit)
    t_max_c: float = 60.0               # hard limit -> GPU throttled

    # --- links ---
    downlink_mbps: float = 10.0
    isl_mbps: float = 100.0
    isl_enabled: bool = True
    isl_phase_deg: float = 30.0         # leading / trailing neighbour in-plane phase
    isl_graze_km: float = 100.0         # minimum ray altitude for line of sight
    nb_spare_gflops: float = 400.0      # donor spare compute while sunlit
    nb_bucket_gflop: float = 60000.0    # donor spare-compute token bucket

    # --- storage ---
    storage_mb: float = 8000.0

    # --- workload ---
    lam_sunlit: float = 1.0 / 45.0      # task arrivals per second (sunlit)
    lam_eclipse: float = 1.0 / 120.0    # task arrivals per second (eclipse, TIR only)
    size_median_mb: float = 50.0
    size_sigma: float = 0.40
    deadline_alert_s: float = 5400.0
    deadline_tasked_s: float = 6 * 3600.0
    deadline_routine_s: float = 12 * 3600.0
    tasked_fraction: float = 0.10
    load_scale: float = 1.0             # multiplies both arrival rates (stress tests)

    # --- derived helpers ---
    @property
    def n_slots(self) -> int:
        return int(round(self.duration_h * 3600.0 / self.dt))

    @property
    def epoch_jd(self) -> float:
        e = _dt.datetime(*self.epoch) + _dt.timedelta(days=self.start_day)
        j2000 = _dt.datetime(2000, 1, 1, 12, 0, 0)
        return 2451545.0 + (e - j2000).total_seconds() / 86400.0

    @property
    def rad_coeff(self) -> float:        # epsilon * sigma * A * k   [W K^-4]
        return self.emissivity * SIGMA_SB * self.radiator_area_m2 * self.k_thermal

    @property
    def dl_mb_per_s(self) -> float:
        return self.downlink_mbps / 8.0

    @property
    def isl_mb_per_s(self) -> float:
        return self.isl_mbps / 8.0

    @property
    def p_idle_w(self) -> float:
        return self.p_bus_w + self.p_gpu_idle_w

