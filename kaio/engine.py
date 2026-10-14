"""The E-LOTUS decision engine (the brain of KAIO).

Every 10 s, for every free resource (GPU, radio, laser link), E-LOTUS scores each stored image
and each possible action, and starts the best one. In plain words, each action is scored by

    score = (how much it worsens the spacecraft's state  -  V × value it delivers) / time it takes

where "the spacecraft's state" is three debts that should stay near zero:

* storage backlog            (q / Q)²
* energy debt                below an eclipse-aware battery floor E_min(t)
* heat debt                  above the soft thermal limit T_safe

This is the drift-plus-penalty rule from Lyapunov optimisation (Neely, 2010). We use it as a
well-founded *heuristic*: the textbook performance guarantee assumes stationary arrivals and an
exact per-slot minimisation, which a real orbit does not give us. Hard limits are enforced
separately by the ``SafetyGuard``.

Each started job carries a one-line explanation built only from information the satellite has
onboard (quick-look entropy, land-mask prior, alert flag, battery, temperature, pass schedule),
never from the hidden ground truth.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from .config import KELVIN
from .estimator import semantic_estimate
from .safety import SafetyGuard
from .workload import Task


class Policy:
    name = "policy"
    color = "#888888"

    def decide(self, sim, free: List[str]) -> List[Tuple[str, Task, dict]]:
        raise NotImplementedError

    def evict(self, sim, excess_mb: float) -> List[Task]:
        """Storage is full: choose which stored items to delete (default: oldest raw first, as a ring buffer)."""
        out, freed = [], 0.0
        for q in (sim.raw_q, sim.prod_q):
            for t in q:
                if freed >= excess_mb:
                    return out
                out.append(t)
                freed += t.size_mb
        return out


class ELotusEngine(Policy):
    """Entropy-weighted Lyapunov drift-plus-penalty controller.

    Lyapunov function (normalised):
        L(Theta) = 1/2 [ w_q (q/Q)^2 + w_E (D_E/dE_ref)^2 + w_T (D_T/dT_ref)^2 ]
        D_E = max(0, E_min(t) - E_b),  D_T = max(0, T - T_safe)
    For each candidate (task i, action a) with service time tau:
        Phi_i(a) = [ Delta L_i(a) - V * U_i(a) ] / tau_i(a)
    where Delta L is the predicted drift relative to STORE (Phi(STORE) = 0)
    and U = w_i * eta_a * phi(age + delay) - zeta * energy_Wh.
    The SafetyGuard's hard limits define the feasible set.
    Free resources are filled greedily by the most negative Phi.
    """
    name = "E-LOTUS"
    color = "#0F766E"

    def __init__(self, V: float = 0.3, zeta: float = 0.5, w_q: float = 1.0, w_E: float = 1.0,
                 w_T: float = 1.0, dE_ref_wh: float = 5.0, dT_ref_k: float = 5.0,
                 use_entropy: bool = True, use_isl: bool = True, eclipse_aware: bool = True,
                 estimator: Optional[str] = None, label: Optional[str] = None,
                 guard: Optional[SafetyGuard] = None, smart_evict: bool = True, explain: bool = True):
        self.estimator = estimator
        self.V, self.zeta = V, zeta
        self.w_q, self.w_E, self.w_T = w_q, w_E, w_T
        self.dE_ref, self.dT_ref = dE_ref_wh, dT_ref_k
        self.use_entropy, self.use_isl, self.eclipse_aware = use_entropy, use_isl, eclipse_aware
        self.guard = guard if guard is not None else SafetyGuard()
        self.smart_evict = smart_evict
        self.explain = explain
        if label:
            self.name = label

    # ---- value estimate w_i ---------------------------------------------------
    def _w(self, tasks: List[Task]) -> np.ndarray:
        if self.use_entropy and self.estimator is not None:
            f = 1.0 if tasks and tasks[0].kind == "raw" else 0.9
            return np.fromiter((f * semantic_estimate(t.entropy, t.priority, 0.0 if t.land != t.land else t.land,
                                                      t.optical, self.estimator) for t in tasks), float, len(tasks))
        if self.use_entropy:
            return np.fromiter((t.est_value for t in tasks), float, len(tasks))
        return np.fromiter((0.5 * t.priority for t in tasks), float, len(tasks))

    def survival_floor(self, sim):
        return sim.e_survive if self.eclipse_aware else sim.e_survive_static

    # ---- storage eviction -------------------------------------------------------
    def evict(self, sim, excess_mb: float) -> List[Task]:
        """Delete the items with the lowest expected value per megabyte first."""
        if not self.smart_evict:
            return super().evict(sim, excess_mb)
        items = list(sim.raw_q) + list(sim.prod_q)
        if not items:
            return []
        t = sim.t
        W = np.concatenate([self._w(sim.raw_q) if sim.raw_q else np.zeros(0),
                            self._w(sim.prod_q) if sim.prod_q else np.zeros(0)])
        fresh = np.fromiter((x.freshness(t) for x in items), float, len(items))
        size = np.fromiter((x.size_mb for x in items), float, len(items))
        order = np.argsort(W * fresh / np.maximum(size, 1e-6), kind="stable")
        out, freed = [], 0.0
        for i in order:
            if freed >= excess_mb:
                break
            out.append(items[i])
            freed += size[i]
        return out

    # ---- decision -----------------------------------------------------------------
    def decide(self, sim, free: List[str]):
        cfg, node, k = sim.cfg, sim.node, sim.k
        t_now = sim.t
        raw, prods = sim.raw_q, sim.prod_q
        if not raw and not prods:
            return []
        Q = cfg.storage_mb
        q = sim.backlog_mb
        Emin_arr = sim.e_min if self.eclipse_aware else sim.e_min_static
        Esurv_arr = sim.e_survive if self.eclipse_aware else sim.e_survive_static
        Tsafe = cfg.t_safe_c + KELVIN
        p_net0 = node.p_solar_series[k] - cfg.p_idle_w
        # shunt-aware energy price: marginal energy is free while the array is being shunted
        shunting = sim.eph.sunlit[k] and p_net0 > 0 and node.E >= 0.95 * cfg.battery_wh
        zeta = 0.0 if shunting else self.zeta
        guard = self.guard

        def drift(mu, tau, dP, prio=1):
            """Predicted drift L(a) - L(STORE) over horizon tau (vectorised) and hard-limit feasibility."""
            E_s, E_a, T_s, T_a, idx = guard.predict(sim, tau, dP)
            Emin = Emin_arr[idx]
            dq = 0.5 * self.w_q * (((q - mu) / Q) ** 2 - (q / Q) ** 2)
            dE = 0.5 * self.w_E * ((np.maximum(0, Emin - E_a) / self.dE_ref) ** 2
                                   - (np.maximum(0, Emin - E_s) / self.dE_ref) ** 2)
            dT = 0.5 * self.w_T * ((np.maximum(0, T_a - Tsafe) / self.dT_ref) ** 2
                                   - (np.maximum(0, T_s - Tsafe) / self.dT_ref) ** 2)
            return dq + dE + dT, guard.feasible(sim, E_a, T_a, idx, Esurv_arr, prio)

        def phi(age, D):
            return np.where(age <= D, np.exp(-age / D), 0.0)

        cand = []   # (score_array, resource, pool_name, extra)
        if raw:
            S = np.fromiter((t.size_mb for t in raw), float, len(raw))
            Gf = np.fromiter((t.gflops for t in raw), float, len(raw))
            age = t_now - np.fromiter((t.t_gen for t in raw), float, len(raw))
            D = np.fromiter((t.aoi_deadline_s for t in raw), float, len(raw))
            W = self._w(raw)
            P = np.fromiter((t.priority for t in raw), float, len(raw))
            if "gpu" in free:
                tau = Gf / cfg.gpu_gflops
                dP = cfg.p_gpu_active_w - cfg.p_gpu_idle_w
                idx = np.minimum(k + np.ceil(tau / cfg.dt).astype(int), len(sim.eph.t) - 1)
                delay = tau + sim.eph.wait_contact[idx]
                eWh = dP * tau / 3600.0
                U = W * cfg.eta_process * phi(age + delay, D) - zeta * eWh
                dL, ok = drift(S * (1 - cfg.product_ratio), tau, dP, P)
                score = np.where(ok, (dL - self.V * U) / tau, np.inf)
                cand.append((score, "gpu", "raw", None))
            if "dl" in free:
                tau = S / cfg.dl_mb_per_s
                eWh = cfg.p_tx_w * tau / 3600.0
                U = W * phi(age + tau, D) - zeta * eWh
                dL, ok = drift(S, tau, cfg.p_tx_w, P)
                score = np.where(ok, (dL - self.V * U) / tau, np.inf)
                cand.append((score, "dl", "raw", None))
            if "isl" in free and self.use_isl:
                side = sim.best_isl_side()
                if side is not None:
                    bucket = sim.nb_bucket[side]
                    tau = S / cfg.isl_mb_per_s
                    t_proc = Gf / cfg.nb_spare_gflops
                    idx = np.minimum(k + np.ceil((tau + t_proc) / cfg.dt).astype(int), len(sim.eph.t) - 1)
                    delay = tau + t_proc + sim.eph.nb_wait_contact[side][idx]
                    eWh = cfg.p_isl_w * tau / 3600.0
                    U = W * cfg.eta_process * phi(age + delay, D) - zeta * eWh
                    dL, ok = drift(S, tau, cfg.p_isl_w, P)
                    ok = ok & (Gf <= bucket)
                    score = np.where(ok, (dL - self.V * U) / tau, np.inf)
                    cand.append((score, "isl", "raw", side))
        if prods and "dl" in free:
            S = np.fromiter((t.size_mb for t in prods), float, len(prods))
            age = t_now - np.fromiter((t.t_gen for t in prods), float, len(prods))
            D = np.fromiter((t.aoi_deadline_s for t in prods), float, len(prods))
            W = self._w(prods)
            P = np.fromiter((t.priority for t in prods), float, len(prods))
            tau = S / cfg.dl_mb_per_s
            eWh = cfg.p_tx_w * tau / 3600.0
            U = W * phi(age + tau, D) - zeta * eWh
            dL, ok = drift(S, tau, cfg.p_tx_w, P)
            score = np.where(ok, (dL - self.V * U) / tau, np.inf)
            cand.append((score, "dl", "prod", None))

        out = []
        used_raw, used_res = set(), set()
        for _ in range(len(free)):
            best = (0.0, None)
            for ci, (score, res, pool, extra) in enumerate(cand):
                if res in used_res:
                    continue
                s = score
                if pool == "raw" and used_raw:
                    s = score.copy()
                    s[list(used_raw)] = np.inf
                j = int(np.argmin(s))
                if s[j] < best[0]:
                    best = (float(s[j]), (ci, j))
            if best[1] is None:
                break
            ci, j = best[1]
            score, res, pool, extra = cand[ci]
            task = raw[j] if pool == "raw" else prods[j]
            if pool == "raw":
                used_raw.add(j)
            used_res.add(res)
            meta = {"side": extra, "phi": best[0]}
            if self.explain:
                meta["why"] = self.explain_choice(sim, res, task, extra)
            out.append((res, task, meta))
        return out

    # ---- explanation ---------------------------------------------------------------
    def explain_choice(self, sim, res: str, task: Task, side=None) -> str:
        """One-line reason for a started job, from onboard-observable quantities only."""
        cfg, k = sim.cfg, sim.k
        w = float(self._w([task])[0])
        land = "" if task.land != task.land else f", land {task.land:.0%}"
        what = (f"fire alert{land}" if task.priority == 4
                else f"{'optical' if task.optical else 'thermal-IR'} H {task.entropy:.1f}{land}")
        if task.kind == "product":
            what = "processed product of " + what
        if res == "gpu":
            tau, dP = task.gflops / cfg.gpu_gflops, cfg.p_gpu_active_w - cfg.p_gpu_idle_w
        elif res == "dl":
            tau, dP = task.size_mb / cfg.dl_mb_per_s, cfg.p_tx_w
        else:
            tau, dP = task.size_mb / cfg.isl_mb_per_s, cfg.p_isl_w
        _, E_a, _, T_a, idx = self.guard.predict(sim, tau, dP)
        floor = float(sim.e_survive[int(idx)])
        state = f"battery {float(E_a):.0f} Wh after (floor {floor:.0f}), {float(T_a) - KELVIN:.1f} °C"
        if res == "gpu":
            wait = sim.eph.wait_contact[int(idx)] / 60.0
            return (f"Process now: est. value {w:.2f} ({what}). {task.size_mb:.0f} MB raw -> "
                    f"{task.size_mb * cfg.product_ratio:.1f} MB product, next pass in {wait:.0f} min; {state}.")
        if res == "dl":
            return (f"Downlink {'product' if task.kind == 'product' else 'raw image'}: est. value {w:.2f} "
                    f"({what}), {task.size_mb:.1f} MB, {tau:.0f} s of pass time; {state}.")
        saved = ((cfg.p_gpu_active_w - cfg.p_gpu_idle_w) * task.gflops / cfg.gpu_gflops - cfg.p_isl_w * tau) / 3600.0
        return (f"Eclipse: offload {task.size_mb:.0f} MB over the laser link to the {side}ing neighbour in sunlight "
                f"(est. value {w:.2f}, {what}); saves {saved:.2f} Wh of battery vs processing here.")
