"""Safety guard: an independent layer that can veto any decision.

Real flight software keeps protection separate from optimisation (FDIR: fault detection,
isolation and recovery). KAIO does the same. The E-LOTUS engine proposes actions; the guard
checks each proposal against hard limits *before* it starts and blocks it if:

* the battery would fall below the eclipse-survival floor (the energy needed to carry the
  platform bus through the rest of this eclipse, or the next one, plus a hard reserve), or
* the compute module would end the job above its thermal limit.

The guard uses the same simple predictors an onboard computer could run: a linear energy
budget and a first-order thermal model (radiator conductance G = 4·ε·σ·A·T³).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np

from .config import KELVIN


@dataclass
class SafetyGuard:
    energy_margin_wh: float = 0.5      # stay this far above the eclipse-survival floor
    thermal_limit: str = "safe"        # "safe" = soft limit t_safe_c (default), "max" = hard limit t_max_c
    thermal_margin_k: float = 0.0
    alert_override: bool = True        # fire alerts may use the margin up to the hardware limit

    def t_limits_k(self, cfg, priority):
        """Per-job thermal limit: urgent alerts (priority 4) may run up to the hardware limit."""
        soft = self.t_limit_k(cfg)
        if not self.alert_override:
            return soft
        hard = cfg.t_max_c - 1.0 + KELVIN - self.thermal_margin_k
        return np.where(np.asarray(priority) >= 4, max(soft, hard), soft)

    def t_limit_k(self, cfg) -> float:
        base = cfg.t_safe_c if self.thermal_limit == "safe" else cfg.t_max_c - 1.0
        return base + KELVIN - self.thermal_margin_k

    # ---- predictors -------------------------------------------------------
    @staticmethod
    def predict(sim, tau, dP):
        """Battery energy [Wh] and temperature [K] at the end of a job of length tau [s] adding dP [W].

        Works on scalars or numpy arrays. Returns (E_store, E_act, T_store, T_act, idx), where *store*
        is the prediction if the satellite stays idle and *act* if it runs the job.
        """
        cfg, node, k = sim.cfg, sim.node, sim.k
        tau = np.asarray(tau, float)
        n_eph = len(sim.eph.t)
        idx = np.minimum(k + np.ceil(tau / cfg.dt).astype(int), n_eph - 1)
        p_net0 = node.p_solar_series[k] - cfg.p_idle_w
        eff = cfg.eta_charge if p_net0 > 0 else 1.0 / cfg.eta_discharge
        E_s = np.clip(node.E + eff * p_net0 * tau / 3600.0, 0.0, cfg.battery_wh)
        E_a = E_s - dP * tau / 3600.0 / cfg.eta_discharge
        G = node.thermal_gain()
        C = cfg.heat_capacity_j_per_k
        dT_free = (cfg.p_idle_w + node.q_env_series[k] - node.q_rad()) / G
        decay = 1.0 - np.exp(-G * tau / C)
        T_s = node.T + dT_free * decay
        T_a = T_s + dP / G * decay
        return E_s, E_a, T_s, T_a, idx

    # ---- checks -----------------------------------------------------------
    def feasible(self, sim, E_a, T_a, idx, floor=None, priority=1) -> np.ndarray:
        """Vectorised hard-limit check used by the engine to prune candidates."""
        floor = sim.e_survive if floor is None else floor
        return (E_a > floor[idx] + self.energy_margin_wh) & (T_a < self.t_limits_k(sim.cfg, priority))

    def check(self, sim, res: str, task, floor=None) -> Tuple[bool, str]:
        """Scalar check of one proposed job, with a human-readable reason when it is blocked."""
        cfg = sim.cfg
        if res == "gpu":
            tau, dP = task.gflops / cfg.gpu_gflops, cfg.p_gpu_active_w - cfg.p_gpu_idle_w
        elif res == "dl":
            tau, dP = task.size_mb / cfg.dl_mb_per_s, cfg.p_tx_w
        else:
            tau, dP = task.size_mb / cfg.isl_mb_per_s, cfg.p_isl_w
        _, E_a, _, T_a, idx = self.predict(sim, tau, dP)
        E_a, T_a, idx = float(E_a), float(T_a), int(idx)
        floor = float((sim.e_survive if floor is None else floor)[idx]) + self.energy_margin_wh
        if E_a <= floor:
            return False, f"battery would end at {E_a:.1f} Wh, below the {floor:.1f} Wh eclipse-survival floor"
        lim = float(self.t_limits_k(cfg, task.priority))
        if T_a >= lim:
            return False, f"would heat to {T_a - KELVIN:.1f} °C, above the {lim - KELVIN:.0f} °C limit"
        return True, ""
