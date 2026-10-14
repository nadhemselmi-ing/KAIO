"""KAIO benchmark: every scenario x every controller x 20 real days (24 h each).

    python benchmark.py               # full suite (~15 min on 2 cores)
    python benchmark.py --days 4      # quick smoke test

Protocol
* Day d (0..19) = 24 h on the real Φsat-2 orbit starting 2026-08-26 + d days, with the real NASA
  scenes under the track that day. Workload seed = 2026 + d (the engine weights were chosen on
  other seeds), so every controller sees exactly the same images on a given day.
* Results are per-day means with a 95 % confidence interval (Student t, n = number of days), and the
  number of days on which E-LOTUS beats each baseline (paired comparison).

Outputs
  results/benchmark_runs.csv      one row per (scenario, controller, day)
  results/summary.json            aggregated numbers used by the dashboard and the pitch
  results/summary.md              human-readable tables
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import time
from multiprocessing import Pool

import numpy as np

from kaio import (AlwaysTransmit, BandwidthRules, ELotusEngine, GreedyProcess, RuleBased, SCENARIOS, SimConfig,
                  SafetyGuard, Simulation, StoreAndForward, build_ephemeris, generate_workload, RealAtlas)

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
SEED0 = 2026

KEYS = ["value", "ceiling_value", "ceiling_pct", "value_capture_pct", "completion_pct", "alerts_on_time_pct",
        "energy_payload_wh", "energy_total_wh", "value_per_wh", "latency_mean_min", "latency_p95_min",
        "aoi_mean_min", "soc_min_pct", "soc_mean_pct", "shed_pct", "below_emin_pct", "temp_max_c",
        "above_tsafe_pct", "throttled_pct", "gpu_duty_pct", "dl_util_pct", "isl_gb", "overflow", "expired",
        "processed", "offloaded", "tx_raw", "tx_prod", "generated", "delivered", "backlog_mean_mb",
        "contact_min_per_day", "alerts", "vetoed"]

POLICIES = {
    "E-LOTUS": lambda: ELotusEngine(explain=False),
    "Rule-Based": RuleBased,
    "Bandwidth-Rules": BandwidthRules,
    "Greedy-Process": GreedyProcess,
    "Store-and-Forward": StoreAndForward,
    "Always-Transmit": AlwaysTransmit,
}
ABLATIONS = {
    "E-LOTUS static E_min": lambda: ELotusEngine(eclipse_aware=False, explain=False, label="E-LOTUS static E_min"),
    "E-LOTUS w/o ISLL": lambda: ELotusEngine(use_isl=False, explain=False, label="E-LOTUS w/o ISLL"),
    "E-LOTUS raw entropy": lambda: ELotusEngine(estimator="entropy", explain=False, label="E-LOTUS raw entropy"),
    "E-LOTUS land only": lambda: ELotusEngine(estimator="land", explain=False, label="E-LOTUS land only"),
    "E-LOTUS soft thermal": lambda: ELotusEngine(guard=SafetyGuard(thermal_limit="max"), explain=False,
                                                 label="E-LOTUS soft thermal"),
}
ABLATION_SCENARIOS = ("nominal", "energy_starved", "battery_starved", "degraded_radiator")


def _run(job):
    scen, day, names = job
    cfg = SimConfig(seed=SEED0 + day, start_day=day, duration_h=24.0, **SCENARIOS[scen]["over"])
    eph = build_ephemeris(cfg)
    arr = generate_workload(cfg, eph)
    rows = []
    for nm in names:
        pol = {**POLICIES, **ABLATIONS}[nm]()
        t0 = time.time()
        m = Simulation(cfg, pol, eph, arr, max_events=10).run().metrics
        rows.append(dict(scenario=scen, policy=nm, day=day, runtime_s=round(time.time() - t0, 2),
                         **{k: float(m[k]) for k in KEYS}))
    print(f"  {scen:18s} day {day:2d} done", flush=True)
    return rows


def ci95(x):
    x = np.asarray([v for v in x if v == v], float)
    n = len(x)
    if n < 2:
        return float(x.mean()) if n else float("nan"), 0.0
    from scipy.stats import t
    return float(x.mean()), float(t.ppf(0.975, n - 1) * x.std(ddof=1) / math.sqrt(n))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=0, help="number of real days (default: all in the atlas)")
    ap.add_argument("--procs", type=int, default=os.cpu_count() or 2)
    args = ap.parse_args()
    os.makedirs(RES, exist_ok=True)
    n_days = args.days or RealAtlas.load(SimConfig()).days_done
    jobs = []
    for scen in SCENARIOS:
        names = list(POLICIES) + (list(ABLATIONS) if scen in ABLATION_SCENARIOS else [])
        for d in range(n_days):
            jobs.append((scen, d, names))
    t0 = time.time()
    print(f"{len(jobs)} scenario-days on {args.procs} processes ...", flush=True)
    with Pool(args.procs) as pool:
        rows = [r for rr in pool.map(_run, jobs, chunksize=1) for r in rr]
    print(f"done in {time.time() - t0:.0f} s", flush=True)

    with open(os.path.join(RES, "benchmark_runs.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    summary = {"days": n_days, "seed0": SEED0, "date0": "2026-08-26", "scenarios": {}, "protocol":
               "24-h runs on n real days; mean and 95% CI (Student t) over days; paired days-won vs E-LOTUS"}
    for scen, sd in SCENARIOS.items():
        sr = [r for r in rows if r["scenario"] == scen]
        pols = sorted({r["policy"] for r in sr}, key=lambda p: list({**POLICIES, **ABLATIONS}).index(p))
        block = {"label": sd["label"], "over": {k: v for k, v in sd["over"].items()}, "policies": {}}
        ref = {r["day"]: r["value"] for r in sr if r["policy"] == "E-LOTUS"}
        for p in pols:
            pr = sorted([r for r in sr if r["policy"] == p], key=lambda r: r["day"])
            block["policies"][p] = {k: ci95([r[k] for r in pr]) for k in KEYS}
            block["policies"][p]["elotus_wins_days"] = int(sum(ref[r["day"]] > r["value"] for r in pr))
            block["policies"][p]["n_days"] = len(pr)
        summary["scenarios"][scen] = block

    # backward-compatible blocks for the dashboard
    nom = summary["scenarios"]["nominal"]["policies"]
    summary["main"] = {p: {k: v[0] for k, v in d.items() if isinstance(v, (list, tuple))} for p, d in nom.items()}
    summary["main_ci"] = {p: {k: v[1] for k, v in d.items() if isinstance(v, (list, tuple))} for p, d in nom.items()}
    summary["stress"] = {SCENARIOS[s]["label"]: {p: {k: list(v) for k, v in d.items() if isinstance(v, (list, tuple))}
                                                 for p, d in b["policies"].items()
                                                 if p in ("E-LOTUS", "Rule-Based", "Greedy-Process")}
                         for s, b in summary["scenarios"].items() if s != "nominal"}
    json.dump(summary, open(os.path.join(RES, "summary.json"), "w"), indent=1)
    write_md(summary)
    print(open(os.path.join(RES, "summary.md")).read())


def write_md(summary):
    lines = [f"# KAIO benchmark ({summary['days']} real days per cell, mean ± 95 % CI)\n"]
    cols = [("ceiling_pct", "Value % of ceiling"), ("completion_pct", "Completion %"),
            ("alerts_on_time_pct", "Alerts on time %"), ("energy_payload_wh", "Payload Wh/day"),
            ("latency_mean_min", "Latency min"), ("soc_min_pct", "Min battery %"), ("shed_pct", "Load-shed %"),
            ("above_tsafe_pct", "Time > 45 °C %")]
    for scen, b in summary["scenarios"].items():
        lines.append(f"\n## {b['label']} (`{scen}`)\n")
        lines.append("| Controller | " + " | ".join(c[1] for c in cols) + " | E-LOTUS better on |")
        lines.append("|---" * (len(cols) + 2) + "|")
        for p, d in b["policies"].items():
            cells = [f"{d[k][0]:.1f} ± {d[k][1]:.1f}" for k, _ in cols]
            won = "—" if p == "E-LOTUS" else f"{d['elotus_wins_days']}/{d['n_days']} days"
            lines.append(f"| {p} | " + " | ".join(cells) + f" | {won} |")
    open(os.path.join(RES, "summary.md"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
