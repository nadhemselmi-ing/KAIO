#!/usr/bin/env python3
"""KAIO on real embedded hardware: how fast is the onboard decision engine?

Runs one full real day (Φsat-2 orbit, real NASA scenes) and times ONLY the parts that would run on
the spacecraft computer:

* the value estimator (quick-look entropy + land-mask lookup) for every new image, and
* every call of the E-LOTUS decision engine (scoring, SafetyGuard checks, explanations).

The battery/thermal physics and the orbit propagation are the *simulated world*, not flight
software, so they are timed separately.

    python3 onboard/pi_benchmark.py              # 24 h (takes ~1 min on a Raspberry Pi 4)
    python3 onboard/pi_benchmark.py --hours 6    # quicker
    python3 onboard/pi_benchmark.py --watts 1.2  # optional: extra power you measured with a USB meter

Writes results/pi_benchmark.json (copy it back to the laptop for the dashboard).
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from kaio import (ELotusEngine, SimConfig, Simulation, build_ephemeris, generate_workload,  # noqa: E402
                  semantic_estimate, shannon_entropy)


def board_name() -> str:
    for p in ("/proc/device-tree/model", "/sys/firmware/devicetree/base/model"):
        try:
            return open(p).read().strip("\x00\n ")
        except OSError:
            pass
    return f"{platform.system()} {platform.machine()} ({platform.processor() or 'cpu'})"


def cpu_temp_c():
    try:
        return int(open("/sys/class/thermal/thermal_zone0/temp").read()) / 1000.0
    except (OSError, ValueError):
        return None


class TimedEngine(ELotusEngine):
    """E-LOTUS with a stopwatch around every decision."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.lat_ns, self.cpu_ns = [], []
        self.n_jobs = 0

    def decide(self, sim, free):
        w0, c0 = time.perf_counter_ns(), time.process_time_ns()
        out = super().decide(sim, free)
        self.lat_ns.append(time.perf_counter_ns() - w0)
        self.cpu_ns.append(time.process_time_ns() - c0)
        self.n_jobs += len(out)
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=24.0)
    ap.add_argument("--day", type=int, default=0, help="real day 0..19 (0 = 2026-08-26)")
    ap.add_argument("--watts", type=float, default=None,
                    help="extra board power while the engine runs, measured with a USB power meter")
    args = ap.parse_args()

    board = board_name()
    print(f"\nKAIO onboard benchmark on: {board}")
    print(f"Python {platform.python_version()}, numpy {np.__version__}, {os.cpu_count()} CPU cores")
    t_start = cpu_temp_c()

    # ---- the simulated world (not flight software) ----
    t0 = time.perf_counter()
    cfg = SimConfig(seed=2026 + args.day, start_day=args.day, duration_h=args.hours)
    eph = build_ephemeris(cfg)
    arr = generate_workload(cfg, eph)
    t_world = time.perf_counter() - t0
    tasks = [t for s in arr for t in s]
    print(f"Real orbit + real NASA scenes for {args.hours:g} h: {len(tasks)} images ({t_world:.1f} s to prepare)")

    # ---- 1. value estimator, per image ----
    rng = np.random.default_rng(0)
    thumbs = rng.integers(0, 256, size=(200, 32, 32), dtype=np.uint8)
    w0 = time.perf_counter_ns()
    for th in thumbs:
        shannon_entropy(th)
    ent_us = (time.perf_counter_ns() - w0) / len(thumbs) / 1e3
    w0 = time.perf_counter_ns()
    for t in tasks:
        semantic_estimate(t.entropy, t.priority, 0.0 if t.land != t.land else t.land, t.optical)
    est_us = (time.perf_counter_ns() - w0) / max(1, len(tasks)) / 1e3

    # ---- 2. the decision engine, inside a full mission day ----
    eng = TimedEngine()
    w0, c0 = time.perf_counter(), time.process_time()
    res = Simulation(cfg, eng, eph, arr, max_events=0).run()
    wall_total, cpu_total = time.perf_counter() - w0, time.process_time() - c0
    lat = np.array(eng.lat_ns) / 1e6
    cpu_engine_s = float(np.sum(eng.cpu_ns)) / 1e9
    sim_s = cfg.n_slots * cfg.dt
    duty = 100.0 * cpu_engine_s / sim_s
    rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    if sys.platform == "darwin":
        rss_mb /= 1024.0
    t_end = cpu_temp_c()
    m = res.metrics

    out = dict(
        board=board, machine=platform.machine(), python=platform.python_version(), numpy=np.__version__,
        hours=args.hours, day=args.day, images=len(tasks),
        entropy_us_per_thumbnail=round(ent_us, 1), estimator_us_per_image=round(est_us, 2),
        decisions=int(len(lat)), jobs_started=int(eng.n_jobs),
        decision_ms_median=round(float(np.median(lat)), 3), decision_ms_p95=round(float(np.percentile(lat, 95)), 3),
        decision_ms_p99=round(float(np.percentile(lat, 99)), 3), decision_ms_max=round(float(lat.max()), 3),
        decision_period_s=cfg.dt, engine_cpu_s=round(cpu_engine_s, 2), engine_cpu_duty_pct=round(duty, 4),
        whole_sim_wall_s=round(wall_total, 1), whole_sim_cpu_s=round(cpu_total, 1),
        speedup_vs_real_time=round(sim_s / wall_total, 0), peak_ram_mb=round(rss_mb, 1),
        cpu_temp_start_c=t_start, cpu_temp_end_c=t_end,
        value_pct_of_ceiling=round(m["ceiling_pct"], 1), load_shed_pct=m["shed_pct"],
        time_above_45c_pct=round(m["above_tsafe_pct"], 2),
    )
    if args.watts is not None:
        out["engine_energy_wh_per_day"] = round(args.watts * cpu_engine_s / 3600.0 * 24.0 / args.hours, 4)

    print("\n=== Onboard cost of KAIO ===")
    print(f"Quick-look entropy (32x32 px) : {ent_us:8.1f} µs per image")
    print(f"Value estimate                : {est_us:8.2f} µs per image")
    print(f"E-LOTUS decision              : median {out['decision_ms_median']:.2f} ms, "
          f"p99 {out['decision_ms_p99']:.2f} ms, worst {out['decision_ms_max']:.2f} ms")
    print(f"                                ({out['decisions']} decisions, one cycle every {cfg.dt:g} s)")
    print(f"CPU used by the engine        : {cpu_engine_s:.1f} s per {args.hours:g} h  = {duty:.3f} % of one core")
    print(f"Peak memory (whole program)   : {rss_mb:.0f} MB")
    if t_start is not None:
        print(f"CPU temperature               : {t_start:.1f} °C -> {t_end:.1f} °C")
    if "engine_energy_wh_per_day" in out:
        print(f"Engine energy                 : {out['engine_energy_wh_per_day']:.3f} Wh per day")
    print(f"\nMission result that day       : {m['ceiling_pct']:.1f} % of the reachable value, "
          f"load-shed {m['shed_pct']:.1f} %, time above 45 °C {m['above_tsafe_pct']:.1f} %")
    print(f"(The whole {args.hours:g}-hour simulation, physics included, ran {out['speedup_vs_real_time']:.0f}x faster than real time.)")

    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    path = os.path.join(ROOT, "results", "pi_benchmark.json")
    json.dump(out, open(path, "w"), indent=1)
    print(f"\nSaved {path}")


if __name__ == "__main__":
    main()
