"""Baseline controllers KAIO is compared against.

* Always-Transmit   : "bent pipe", downlink every raw image, oldest first.
* Greedy-Process    : process everything as soon as the GPU is free.
* Store-and-Forward : no onboard compute; downlink by (priority, entropy).
* Rule-Based        : a hand-tuned onboard rule engine using the SAME value estimate as E-LOTUS.
* Bandwidth-Rules   : Rule-Based plus pass-capacity awareness (ported from the satsched
                      "bandwidth_rules" baseline): keeps the best images raw when the coming passes
                      have room for them.
"""
from __future__ import annotations

from typing import List

import numpy as np

from .config import KELVIN
from .engine import Policy
from .workload import Task


class AlwaysTransmit(Policy):
    """Downlink every raw item FIFO whenever a ground station is in view."""
    name = "Always-Transmit"
    color = "#B45309"

    def decide(self, sim, free):
        if "dl" in free and sim.raw_q:
            return [("dl", sim.raw_q[0], {})]
        return []


class GreedyProcess(Policy):
    """Process every raw item FIFO as soon as the GPU is free; downlink products FIFO."""
    name = "Greedy-Process"
    color = "#7C3AED"

    def decide(self, sim, free):
        out = []
        taken = None
        if "gpu" in free and sim.raw_q:
            taken = sim.raw_q[0]
            out.append(("gpu", taken, {}))
        if "dl" in free:
            if sim.prod_q:
                out.append(("dl", sim.prod_q[0], {}))
            else:
                for t in sim.raw_q:
                    if t is not taken:
                        out.append(("dl", t, {}))
                        break
        return out


class StoreAndForward(Policy):
    """Store everything; during contacts forward by (priority, entropy) order. No onboard compute."""
    name = "Store-and-Forward"
    color = "#2563EB"

    def decide(self, sim, free):
        if "dl" in free and sim.raw_q:
            best = max(sim.raw_q, key=lambda t: (t.priority, t.entropy))
            return [("dl", best, {})]
        return []


class RuleBased(Policy):
    """Entropy-aware threshold rules (typical hand-tuned onboard rule engine)."""
    name = "Rule-Based"
    color = "#DB2777"

    def __init__(self, soc_min: float = 0.5, w_min: float = 0.10):
        self.soc_min, self.w_min = soc_min, w_min

    def decide(self, sim, free):
        cfg, node = sim.cfg, sim.node
        out, taken = [], set()
        ranked = sorted(sim.raw_q, key=lambda t: -t.est_value)
        if "dl" in free:
            if sim.prod_q:
                out.append(("dl", max(sim.prod_q, key=lambda t: t.est_value), {}))
            elif ranked:
                out.append(("dl", ranked[0], {}))
                taken.add(ranked[0].task_id)
        if "isl" in free and not sim.eph.sunlit[sim.k]:
            side = sim.best_isl_side()
            if side is not None:
                for t in ranked:
                    if t.task_id not in taken and t.est_value >= self.w_min and t.gflops <= sim.nb_bucket[side]:
                        out.append(("isl", t, {"side": side}))
                        taken.add(t.task_id)
                        break
        if ("gpu" in free and node.E / cfg.battery_wh >= self.soc_min
                and node.T < cfg.t_safe_c + KELVIN):
            for t in ranked:
                if t.task_id not in taken and t.est_value >= self.w_min:
                    out.append(("gpu", t, {}))
                    break
        return out

    def evict(self, sim, excess_mb: float) -> List[Task]:
        """Storage watermark rule: delete the lowest-value items first (same estimate as E-LOTUS)."""
        items = sorted(list(sim.raw_q) + list(sim.prod_q), key=lambda t: (t.est_value, t.t_gen))
        out, freed = [], 0.0
        for t in items:
            if freed >= excess_mb:
                break
            out.append(t)
            freed += t.size_mb
        return out


class BandwidthRules(RuleBased):
    """Rule-Based + bandwidth awareness.

    Processing keeps only ``eta_process`` of an image's information. When the passes in the next
    ``horizon_h`` hours have spare capacity, the highest-value raw images (alerts first) are sent
    raw instead, up to ``fill`` of that capacity; everything else follows Rule-Based.
    """
    name = "Bandwidth-Rules"
    color = "#9333EA"

    def __init__(self, soc_min: float = 0.5, w_min: float = 0.10, horizon_h: float = 3.0,
                 fill: float = 0.8, w_raw: float = 0.5):
        super().__init__(soc_min, w_min)
        self.horizon_h, self.fill, self.w_raw = horizon_h, fill, w_raw

    def decide(self, sim, free):
        out = super().decide(sim, free)
        if "dl" not in free:
            return out
        cfg, k = sim.cfg, sim.k
        n = int(self.horizon_h * 3600 / cfg.dt)
        cap_mb = float(sim.eph.contact[k:k + n].sum()) * cfg.dt * cfg.dl_mb_per_s
        budget = self.fill * cap_mb - sum(t.size_mb for t in sim.prod_q)
        busy = {t.task_id for r, t, _ in out if r != "dl"}
        best = None
        for t in sorted(sim.raw_q, key=lambda t: -t.est_value):
            if t.task_id in busy or t.est_value < self.w_raw:
                continue
            if t.size_mb <= budget:
                best = t
            break
        if best is not None:
            out = [o for o in out if o[0] != "dl"] + [("dl", best, {})]
        return out
