"""Slotted mission simulator: arrivals -> interlocks -> decisions -> RK4 physics -> telemetry and metrics."""
from __future__ import annotations

import heapq
from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Tuple

import numpy as np

from .config import ACTION_CODE, ACTIONS, KELVIN, RESOURCE_ACTION, SimConfig
from .engine import Policy
from .orbit import Ephemeris, build_ephemeris
from .physics import SatelliteNode
from .workload import Task, generate_workload


@dataclass
class SimResult:
    policy: str
    telemetry: Dict[str, np.ndarray]
    events: List[dict]
    metrics: Dict[str, float]
    deliveries: List[dict]


class Simulation:
    """Slotted simulation: arrivals -> interlocks -> service/decisions -> RK4 physics -> logs."""

    def __init__(self, cfg: SimConfig, policy: Policy, eph: Optional[Ephemeris] = None,
                 arrivals: Optional[List[List[Task]]] = None, max_events: int = 60000):
        self.cfg = cfg
        self.policy = policy
        self.eph = eph if eph is not None else build_ephemeris(cfg)
        base = arrivals if arrivals is not None else generate_workload(cfg, self.eph)
        # fresh copies so several controllers can share one arrival stream
        self.arrivals = [[replace(t) for t in slot] for slot in base]
        self.node = SatelliteNode(cfg, self.eph)
        self.raw_q: List[Task] = []
        self.prod_q: List[Task] = []
        self.jobs: Dict[str, Optional[Task]] = {"gpu": None, "dl": None, "isl": None}
        self.job_meta: Dict[str, dict] = {"gpu": {}, "dl": {}, "isl": {}}
        self.nb_bucket = {"lead": cfg.nb_bucket_gflop, "trail": cfg.nb_bucket_gflop}
        self.pending_nb: List[Tuple[float, int, Task]] = []
        self.k, self.t = 0, 0.0
        self.shed, self.throttled = False, False
        self.max_events = max_events
        self.events: List[dict] = []
        self.deliveries: List[dict] = []
        self.backlog_mb = 0.0
        self.aoi_u = 0.0         # generation time of freshest delivered update
        self.cnt = dict(generated=0, overflow=0, expired=0, processed=0, offloaded=0,
                        tx_raw=0, tx_prod=0, delivered=0, alerts=0, alerts_ok=0, vetoed=0)
        self.value_lost_overflow = 0.0
        self._build_energy_floor()

    # --- eclipse-aware soft energy floor E_min(t) ----------------------------
    def _build_energy_floor(self):
        c, e = self.cfg, self.eph
        p_svc = c.p_idle_w + 0.5 * (c.p_gpu_active_w - c.p_gpu_idle_w)   # eclipse service load
        p_sun = float(np.mean(c.p_face_w * e.solar_factor[e.sunlit])) if e.sunlit.any() else 0.0
        need_ecl = p_svc * e.ecl_remaining_s / c.eta_discharge
        need_sun = np.maximum(0.0, p_svc * e.next_ecl_dur_s / c.eta_discharge
                              - max(0.0, p_sun - c.p_idle_w) * c.eta_charge * e.t_to_eclipse_s)
        need = np.where(e.sunlit, need_sun, need_ecl) / 3600.0
        self.e_min = c.e_reserve_wh + need
        # hard eclipse-survival floor: energy needed to carry the idle load to eclipse exit
        surv_ecl = c.p_idle_w * e.ecl_remaining_s / c.eta_discharge
        surv_sun = np.maximum(0.0, c.p_idle_w * e.next_ecl_dur_s / c.eta_discharge
                              - max(0.0, p_sun - c.p_idle_w) * c.eta_charge * e.t_to_eclipse_s)
        self.e_survive = c.e_crit_wh + np.where(e.sunlit, surv_sun, surv_ecl) / 3600.0
        self.e_survive_static = np.full_like(self.e_survive, c.e_crit_wh)
        max_ecl = float(e.ecl_remaining_s.max())
        self.e_min_static = np.full_like(self.e_min, c.e_reserve_wh + p_svc * max_ecl / c.eta_discharge / 3600.0)

    # --- helpers -------------------------------------------------------------
    def best_isl_side(self) -> Optional[str]:
        c, k = self.cfg, self.k
        if not c.isl_enabled or self.shed:
            return None
        if self.eph.sunlit[k]:          # swarm offload only during local eclipse
            return None
        sides = [s for s in ("lead", "trail") if self.node.isl_available(k, s)]
        if not sides:
            return None
        return max(sides, key=lambda s: self.nb_bucket[s])

    def _log(self, action: str, task: Task, detail: str = "", score: float = float("nan"), why: str = ""):
        if len(self.events) < self.max_events:
            self.events.append(dict(t_h=self.t / 3600.0, task_id=task.task_id, action=action,
                                    kind=task.kind, scene=task.scene, entropy=round(task.entropy, 3),
                                    priority=task.priority, size_mb=round(task.size_mb, 2),
                                    w_est=round(task.est_value, 4), score=score,
                                    lat=round(task.lat, 2), lon=round(task.lon, 2),
                                    soc=round(self.node.E / self.cfg.battery_wh * 100, 1),
                                    temp_c=round(self.node.T - KELVIN, 2), detail=detail, why=why))

    def _deliver(self, task: Task, t_del: float, route: str):
        f = task.freshness(t_del)
        val = task.true_value * f
        self.cnt["delivered"] += 1
        if task.priority == 4 and f > 0:
            self.cnt["alerts_ok"] += 1
        self.aoi_u = max(self.aoi_u, task.t_gen)
        self.deliveries.append(dict(t_h=t_del / 3600.0, task_id=task.task_id, route=route,
                                    scene=task.scene, priority=task.priority, value=val,
                                    latency_min=(t_del - task.t_gen) / 60.0))

    def _start(self, res: str, task: Task, meta: dict):
        if task.kind == "raw":
            self.raw_q.remove(task)
        else:
            self.prod_q.remove(task)
        self.jobs[res] = task
        self.job_meta[res] = meta
        if res == "gpu":
            task.remaining = task.gflops
        else:
            task.remaining = task.size_mb
        if res == "isl":
            self.nb_bucket[meta["side"]] -= task.gflops
        self._log(RESOURCE_ACTION[res], task, meta.get("side") or "", meta.get("phi", float("nan")),
                  meta.get("why", ""))

    def _complete(self, res: str, task: Task, t_c: float):
        c = self.cfg
        if res == "gpu":
            self.cnt["processed"] += 1
            prod = replace(task, size_mb=task.size_mb * c.product_ratio, gflops=0.0,
                           true_value=task.true_value * c.eta_process,
                           est_value=task.est_value * c.eta_process, kind="product", parent_id=task.task_id,
                           remaining=0.0)
            self.prod_q.append(prod)
        elif res == "dl":
            if task.kind == "raw":
                self.cnt["tx_raw"] += 1
            else:
                self.cnt["tx_prod"] += 1
            self._deliver(task, t_c, "downlink-" + task.kind)
        else:  # isl
            self.cnt["offloaded"] += 1
            side = self.job_meta["isl"]["side"]
            t_p = t_c + task.gflops / c.nb_spare_gflops
            kk = min(int(t_p / c.dt), len(self.eph.t) - 1)
            t_del = t_p + self.eph.nb_wait_contact[side][kk]
            prod = replace(task, kind="product", true_value=task.true_value * c.eta_process,
                           size_mb=task.size_mb * c.product_ratio)
            heapq.heappush(self.pending_nb, (t_del, task.task_id, prod))

    def _storage_used(self) -> float:
        s = sum(t.size_mb for t in self.raw_q) + sum(t.size_mb for t in self.prod_q)
        for r in ("gpu", "dl", "isl"):
            j = self.jobs[r]
            if j is not None:
                s += j.size_mb
        return s

    # --- main loop -----------------------------------------------------------
    def run(self, progress=None) -> SimResult:
        c, e, node = self.cfg, self.eph, self.node
        N = c.n_slots
        dt = c.dt
        tel = {name: np.zeros(N) for name in (
            "t_h", "soc", "E_wh", "E_min_wh", "temp_c", "q_mb", "m_mb", "gpu_util", "dl_mb", "isl_mb",
            "action", "sunlit", "contact", "isl_avail", "p_solar_w", "p_load_w", "theta_deg",
            "lat", "lon", "H_bar", "aoi_min", "value_cum", "energy_wh_cum", "D_E", "D_T", "shed",
            "throttled", "lyapunov")}
        value_cum, energy_cum = 0.0, 0.0
        gpu_cap = c.gpu_gflops * dt
        dl_cap = c.dl_mb_per_s * dt
        isl_cap = c.isl_mb_per_s * dt
        Tsafe = c.t_safe_c + KELVIN
        for k in range(N):
            self.k, self.t = k, k * dt
            t = self.t
            sunlit = bool(e.sunlit[k])
            # 1. neighbour deliveries that became due
            while self.pending_nb and self.pending_nb[0][0] <= t:
                t_del, _, prod = heapq.heappop(self.pending_nb)
                self._deliver(prod, t_del, "isl-neighbour")
            # 2. arrivals with ring-buffer overflow protection
            for task in self.arrivals[k] if k < len(self.arrivals) else []:
                self.cnt["generated"] += 1
                if task.priority == 4:
                    self.cnt["alerts"] += 1
                self.raw_q.append(task)
                self._log("STORE", task, "arrival")
            used = self._storage_used()
            if used > c.storage_mb and (self.raw_q or self.prod_q):
                victims = self.policy.evict(self, used - c.storage_mb)
                ids = {id(v) for v in victims}
                self.raw_q = [x for x in self.raw_q if id(x) not in ids]
                self.prod_q = [x for x in self.prod_q if id(x) not in ids]
                for victim in victims:
                    self.cnt["overflow"] += 1
                    self.value_lost_overflow += victim.true_value
                    self._log("DROP", victim, "storage full")
            # 3. AoI expiry
            if k % 6 == 0:
                keep_r = [x for x in self.raw_q if t - x.t_gen <= x.aoi_deadline_s]
                keep_p = [x for x in self.prod_q if t - x.t_gen <= x.aoi_deadline_s]
                self.cnt["expired"] += (len(self.raw_q) - len(keep_r)) + (len(self.prod_q) - len(keep_p))
                self.raw_q, self.prod_q = keep_r, keep_p
            # 4. hardware interlocks (identical for every controller)
            if self.shed:
                self.shed = node.E < c.e_crit_wh + 5.0
            elif node.E < c.e_crit_wh:
                self.shed = True
            if self.throttled:
                self.throttled = node.T > c.t_max_c + KELVIN - 5.0
            elif node.T >= c.t_max_c + KELVIN:
                self.throttled = True
            # neighbour spare-compute buckets refill while the donor is sunlit
            for side in ("lead", "trail"):
                if e.nb_sunlit[side][k]:
                    self.nb_bucket[side] = min(c.nb_bucket_gflop, self.nb_bucket[side] + c.nb_spare_gflops * dt)
            isl_ok = self.best_isl_side() is not None
            budget = {"gpu": gpu_cap if not (self.shed or self.throttled) else 0.0,
                      "dl": dl_cap if (e.contact[k] and not self.shed) else 0.0,
                      "isl": isl_cap if isl_ok else 0.0}
            spent = {"gpu": 0.0, "dl": 0.0, "isl": 0.0}
            self.backlog_mb = sum(x.size_mb for x in self.raw_q) + sum(x.size_mb for x in self.prod_q)
            # 5. service + decisions
            for _ in range(40):
                for res in ("gpu", "dl", "isl"):
                    job = self.jobs[res]
                    if job is not None and budget[res] > 1e-9:
                        use = min(budget[res], job.remaining)
                        job.remaining -= use
                        budget[res] -= use
                        spent[res] += use
                        if job.remaining <= 1e-9:
                            cap = {"gpu": gpu_cap, "dl": dl_cap, "isl": isl_cap}[res]
                            self._complete(res, job, t + dt * spent[res] / cap)
                            self.jobs[res] = None
                free = [r for r in ("gpu", "dl", "isl") if self.jobs[r] is None and budget[r] > 1e-6]
                if not free or not (self.raw_q or self.prod_q):
                    break
                assigned = self.policy.decide(self, free)
                if not assigned:
                    break
                guard = getattr(self.policy, "guard", None)
                for res, task, meta in assigned:
                    if res in free and self.jobs[res] is None:
                        if guard is not None:
                            ok, reason = guard.check(self, res, task, self.policy.survival_floor(self))
                            if not ok:
                                self.cnt["vetoed"] += 1
                                self._log("VETO", task, res, why=reason)
                                continue
                        self._start(res, task, meta)
                self.backlog_mb = sum(x.size_mb for x in self.raw_q) + sum(x.size_mb for x in self.prod_q)
            # 6. power and physics (RK4)
            f_gpu = spent["gpu"] / gpu_cap
            f_dl = spent["dl"] / dl_cap
            f_isl = spent["isl"] / isl_cap
            if self.shed:
                p_load = c.p_bus_w
            else:
                p_load = (c.p_bus_w + c.p_gpu_idle_w * (1 - f_gpu) + c.p_gpu_active_w * f_gpu
                          + c.p_tx_w * f_dl + c.p_isl_w * f_isl)
            node.step(k, p_load, dt)
            energy_cum += p_load * dt / 3600.0
            # 7. telemetry
            action = ("OFFLOAD_ISLL" if f_isl > 0 else "TRANSMIT" if f_dl > 0
                      else "PROCESS" if f_gpu > 0 else "STORE")
            q_mb = sum(x.size_mb for x in self.raw_q) + sum(x.size_mb for x in self.prod_q)
            D_E = max(0.0, self.e_min[k] - node.E)
            D_T = max(0.0, node.T - Tsafe)
            tel["t_h"][k] = (t + dt) / 3600.0
            tel["soc"][k] = node.E / c.battery_wh * 100.0
            tel["E_wh"][k] = node.E
            tel["E_min_wh"][k] = self.e_min[k]
            tel["temp_c"][k] = node.T - KELVIN
            tel["q_mb"][k] = q_mb
            tel["m_mb"][k] = self._storage_used()
            tel["gpu_util"][k] = f_gpu
            tel["dl_mb"][k] = spent["dl"]
            tel["isl_mb"][k] = spent["isl"]
            tel["action"][k] = ACTION_CODE[action]
            tel["sunlit"][k] = sunlit
            tel["contact"][k] = e.contact[k]
            tel["isl_avail"][k] = isl_ok
            tel["p_solar_w"][k] = node.p_solar_series[k]
            tel["p_load_w"][k] = p_load
            tel["theta_deg"][k] = e.theta_deg[k]
            tel["lat"][k] = e.lat[k]
            tel["lon"][k] = e.lon[k]
            tel["H_bar"][k] = (np.mean([x.entropy for x in self.raw_q]) if self.raw_q else 0.0)
            tel["aoi_min"][k] = (t + dt - self.aoi_u) / 60.0
            tel["energy_wh_cum"][k] = energy_cum
            tel["D_E"][k] = D_E
            tel["D_T"][k] = D_T
            tel["shed"][k] = self.shed
            tel["throttled"][k] = self.throttled
            tel["lyapunov"][k] = 0.5 * ((q_mb / c.storage_mb) ** 2 + (D_E / 5.0) ** 2 + (D_T / 5.0) ** 2)
            if progress is not None and k % 500 == 0:
                progress(k / N)
        # cumulative delivered value on the telemetry grid
        if self.deliveries:
            dt_h = np.array([d["t_h"] for d in self.deliveries])
            dv = np.array([d["value"] for d in self.deliveries])
            order = np.argsort(dt_h)
            cum = np.cumsum(dv[order])
            pos = np.searchsorted(dt_h[order], tel["t_h"], side="right")
            tel["value_cum"] = np.where(pos > 0, cum[np.maximum(pos - 1, 0)], 0.0)
        return SimResult(self.policy.name, tel, self.events, self._metrics(tel), self.deliveries)

    def _metrics(self, tel) -> Dict[str, float]:
        c = self.cfg
        gen_value = sum(t.true_value for slot in self.arrivals[:c.n_slots] for t in slot)
        # contact-limited ceiling: every task delivered at the first ground contact after
        # generation with zero processing/transfer time and unlimited resources
        ceiling = 0.0
        for kk, slot in enumerate(self.arrivals[:c.n_slots]):
            w = self.eph.wait_contact[kk]
            for t in slot:
                if kk * c.dt + w < c.n_slots * c.dt:
                    ceiling += t.true_value * t.freshness(t.t_gen + w)
        val = sum(d["value"] for d in self.deliveries)
        lat = np.array([d["latency_min"] for d in self.deliveries]) if self.deliveries else np.array([np.nan])
        dur_s = c.n_slots * c.dt
        contact_s = float(tel["contact"].sum() * c.dt)
        payload_wh = float(np.sum(tel["p_load_w"] - c.p_bus_w) * c.dt / 3600.0)
        Tsafe = c.t_safe_c
        return dict(
            value=val,
            value_capture_pct=100.0 * val / gen_value if gen_value else 0.0,
            ceiling_value=ceiling,
            ceiling_pct=100.0 * val / ceiling if ceiling else 0.0,
            generated=self.cnt["generated"],
            delivered=self.cnt["delivered"],
            completion_pct=100.0 * self.cnt["delivered"] / max(1, self.cnt["generated"]),
            alerts=self.cnt["alerts"],
            alerts_on_time_pct=100.0 * self.cnt["alerts_ok"] / max(1, self.cnt["alerts"]),
            processed=self.cnt["processed"],
            offloaded=self.cnt["offloaded"],
            tx_raw=self.cnt["tx_raw"],
            tx_prod=self.cnt["tx_prod"],
            overflow=self.cnt["overflow"],
            vetoed=self.cnt["vetoed"],
            expired=self.cnt["expired"],
            energy_total_wh=float(tel["energy_wh_cum"][-1]),
            energy_payload_wh=payload_wh,
            value_per_wh=val / max(1e-9, payload_wh),
            latency_mean_min=float(np.nanmean(lat)) if self.deliveries else float("nan"),
            latency_p95_min=float(np.nanpercentile(lat, 95)) if self.deliveries else float("nan"),
            aoi_mean_min=float(np.mean(tel["aoi_min"])),
            soc_min_pct=float(tel["soc"].min()),
            soc_mean_pct=float(tel["soc"].mean()),
            shed_pct=100.0 * float(tel["shed"].mean()),
            below_emin_pct=100.0 * float((tel["E_wh"] < tel["E_min_wh"]).mean()),
            temp_max_c=float(tel["temp_c"].max()),
            above_tsafe_pct=100.0 * float((tel["temp_c"] > Tsafe).mean()),
            throttled_pct=100.0 * float(tel["throttled"].mean()),
            gpu_duty_pct=100.0 * float(tel["gpu_util"].mean()),
            dl_util_pct=100.0 * float(tel["dl_mb"].sum()) / max(1e-9, contact_s * c.dl_mb_per_s),
            isl_gb=float(tel["isl_mb"].sum()) / 1000.0,
            contact_min_per_day=contact_s / 60.0 / (dur_s / 86400.0),
            backlog_mean_mb=float(tel["q_mb"].mean()),
        )

