"""Spacecraft physics: battery state of energy and a lumped radiative thermal node (RK4)."""
from __future__ import annotations

import math
import os
from typing import Dict, List, Optional, Tuple

import numpy as np

from .config import KELVIN, SimConfig
from .orbit import Ephemeris

# ---------------------------------------------------------------------------
# Satellite node physics
# ---------------------------------------------------------------------------
class SatelliteNode:
    """Battery + lumped radiative thermal node, integrated with RK4.

    dE_b/dt = eta_c * min(P_sol - P_load, P_ch,max(SOC))      if P_sol >= P_load
            = (P_sol - P_load) / eta_d                         otherwise
    C dT/dt = P_load + Q_env(t) - eps*sigma*A*k*(T^4 - T_space^4)
    """

    def __init__(self, cfg: SimConfig, eph: Ephemeris):
        self.cfg = cfg
        self.eph = eph
        self.E = cfg.soc0 * cfg.battery_wh          # Wh
        self.T = cfg.t0_c + KELVIN                  # K
        self.p_solar_series = cfg.p_face_w * eph.solar_factor
        self.q_env_series = cfg.q_sun_w * eph.sunlit + cfg.q_earth_ir_w

    # --- geometry accessors -------------------------------------------------
    def solar_incidence_deg(self, k: int) -> float:
        return float(self.eph.theta_deg[k])

    def in_sunlight(self, k: int) -> bool:
        return bool(self.eph.sunlit[k])

    def isl_available(self, k: int, side: str) -> bool:
        """Line of sight to the neighbour AND neighbour in full sunlight."""
        return bool(self.eph.isl_los[side][k] and self.eph.nb_sunlit[side][k])

    # --- dynamics -----------------------------------------------------------
    def _p_solar(self, k: int, frac: float) -> float:
        s = self.p_solar_series
        k1 = min(k + 1, len(s) - 1)
        return (1 - frac) * s[k] + frac * s[k1]

    def _q_env(self, k: int, frac: float) -> float:
        q = self.q_env_series
        k1 = min(k + 1, len(q) - 1)
        return (1 - frac) * q[k] + frac * q[k1]

    def _dE(self, E: float, p_sol: float, p_load: float) -> float:
        c = self.cfg
        net = p_sol - p_load
        if net >= 0.0:
            soc = E / c.battery_wh
            taper = min(1.0, max(0.0, (1.0 - soc) / 0.10))
            return c.eta_charge * min(net, c.p_charge_max_w * taper) / 3600.0
        return net / c.eta_discharge / 3600.0

    def _dT(self, T: float, q_in: float) -> float:
        c = self.cfg
        return (q_in - c.rad_coeff * (T ** 4 - c.t_space_k ** 4)) / c.heat_capacity_j_per_k

    def step(self, k: int, p_load: float, dt: float) -> None:
        """Advance (E_b, T) over one slot with classical RK4; inputs vary inside the slot."""
        E, T = self.E, self.T
        ps0, ps1, ps2 = self._p_solar(k, 0.0), self._p_solar(k, 0.5), self._p_solar(k, 1.0)
        q0, q1, q2 = self._q_env(k, 0.0), self._q_env(k, 0.5), self._q_env(k, 1.0)
        k1E, k1T = self._dE(E, ps0, p_load), self._dT(T, p_load + q0)
        k2E, k2T = self._dE(E + 0.5 * dt * k1E, ps1, p_load), self._dT(T + 0.5 * dt * k1T, p_load + q1)
        k3E, k3T = self._dE(E + 0.5 * dt * k2E, ps1, p_load), self._dT(T + 0.5 * dt * k2T, p_load + q1)
        k4E, k4T = self._dE(E + dt * k3E, ps2, p_load), self._dT(T + dt * k3T, p_load + q2)
        self.E = min(self.cfg.battery_wh, max(0.0, E + dt / 6.0 * (k1E + 2 * k2E + 2 * k3E + k4E)))
        self.T = T + dt / 6.0 * (k1T + 2 * k2T + 2 * k3T + k4T)

    # --- one-step predictors used by the controller -------------------------
    def thermal_gain(self) -> float:
        """Linearised radiative conductance G = 4 eps sigma A k T^3 [W/K]."""
        return 4.0 * self.cfg.rad_coeff * self.T ** 3

    def q_rad(self) -> float:
        c = self.cfg
        return c.rad_coeff * (self.T ** 4 - c.t_space_k ** 4)

