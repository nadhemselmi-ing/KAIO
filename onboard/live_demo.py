#!/usr/bin/env python3
"""Live KAIO demo for the pitch: the Raspberry Pi flies one real day of Φsat-2 and prints every
decision, with its reason and how long the Pi took to make it.

    python3 onboard/live_demo.py                 # starts at the most interesting moment, 120x real time
    python3 onboard/live_demo.py --speed 300     # faster
    python3 onboard/live_demo.py --start 0       # from midnight

Press Ctrl+C to stop; a summary is printed.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from kaio import ELotusEngine, KELVIN, SimConfig, Simulation, build_ephemeris, generate_workload  # noqa: E402

C = dict(rst="\033[0m", dim="\033[2m", b="\033[1m", y="\033[33m", bl="\033[34m", g="\033[32m",
         m="\033[35m", c="\033[36m", r="\033[31m")
TAG = {"gpu": (C["m"], "PROCESS "), "dl": (C["c"], "TRANSMIT"), "isl": (C["g"], "OFFLOAD ")}


def color(on: bool):
    if not on:
        for k in C:
            C[k] = ""


def interesting_start(eph, n):
    """Start a few minutes before the first ground pass that follows an eclipse exit."""
    sl, ct = eph.sunlit[:n], eph.contact[:n]
    for k in range(60, n - 360):
        if ct[k] and not ct[k - 1] and (~sl[max(0, k - 360):k]).any():
            return max(0, k - 30)
    return 0


class LiveEngine(ELotusEngine):
    def __init__(self, speed, start_k, **kw):
        super().__init__(**kw)
        self.speed, self.start_k = speed, start_k
        self.wall0 = None
        self.last_status_k = -10 ** 9
        self.lat_ms = []

    def status(self, sim):
        cfg, n, k = sim.cfg, sim.node, sim.k
        h, mnt = divmod(int(sim.t // 60), 60)
        sun = f"{C['y']}SUNLIT {C['rst']}" if sim.eph.sunlit[k] else f"{C['bl']}ECLIPSE{C['rst']}"
        gs = (f"{C['g']}PASS:{sim.eph.station_names[sim.eph.contact_station[k]].split(' ')[0]:9s}{C['rst']}"
              if sim.eph.contact[k] else f"{C['dim']}no contact    {C['rst']}")
        soc = 100 * n.E / cfg.battery_wh
        tc = n.T - KELVIN
        tcol = C["r"] if tc > cfg.t_safe_c - 2 else ""
        print(f"{C['b']}T+{h:02d}:{mnt:02d}{C['rst']}  {sun}  {gs}  battery {soc:5.1f} %  "
              f"{tcol}temp {tc:4.1f} °C{C['rst']}  storage {sim.backlog_mb / 1000:4.1f} GB  "
              f"value so far {sum(d['value'] for d in sim.deliveries):6.1f}", flush=True)

    def decide(self, sim, free):
        if sim.k >= self.start_k:
            if self.wall0 is None:
                self.wall0 = time.perf_counter() - (sim.k - self.start_k) * sim.cfg.dt / self.speed
            ahead = (sim.k - self.start_k) * sim.cfg.dt / self.speed - (time.perf_counter() - self.wall0)
            if ahead > 0:
                time.sleep(ahead)
            if sim.k - self.last_status_k >= 30:            # every 5 simulated minutes
                self.status(sim)
                self.last_status_k = sim.k
        t0 = time.perf_counter()
        out = super().decide(sim, free)
        ms = (time.perf_counter() - t0) * 1e3
        self.lat_ms.append(ms)
        if sim.k >= self.start_k:
            h, mnt = divmod(int(sim.t // 60), 60)
            for res, task, meta in out:
                col, tag = TAG[res]
                print(f"  {C['dim']}{h:02d}:{mnt:02d}{C['rst']} {col}{C['b']}{tag}{C['rst']} {meta.get('why', '')}  "
                      f"{C['dim']}[decided in {ms:.1f} ms]{C['rst']}", flush=True)
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--speed", type=float, default=120.0, help="simulated seconds per real second")
    ap.add_argument("--start", type=float, default=None, help="start time in hours (default: auto)")
    ap.add_argument("--hours", type=float, default=24.0)
    ap.add_argument("--day", type=int, default=0)
    ap.add_argument("--no-color", action="store_true")
    a = ap.parse_args()
    color(not a.no_color and sys.stdout.isatty())

    print(f"{C['b']}KAIO onboard decision engine (E-LOTUS){C['rst']} - real Φsat-2 orbit, real NASA scenes, "
          f"day {a.day}")
    cfg = SimConfig(seed=2026 + a.day, start_day=a.day, duration_h=a.hours)
    eph = build_ephemeris(cfg)
    arr = generate_workload(cfg, eph)
    start_k = int(a.start * 3600 / cfg.dt) if a.start is not None else interesting_start(eph, cfg.n_slots)
    print(f"Fast-forwarding to T+{start_k * cfg.dt / 3600:.2f} h, then playing at {a.speed:g}x real time. "
          f"Ctrl+C to stop.\n")
    eng = LiveEngine(a.speed, start_k)
    sim = Simulation(cfg, eng, eph, arr, max_events=0)
    try:
        sim.run()
    except KeyboardInterrupt:
        pass
    lat = np.array(eng.lat_ms) if eng.lat_ms else np.array([0.0])
    print(f"\n{C['b']}Summary{C['rst']}: {len(lat)} decisions, median {np.median(lat):.2f} ms, "
          f"worst {lat.max():.1f} ms on this computer. The satellite needs one decision cycle every "
          f"{cfg.dt:g} s, so the engine uses {100 * np.median(lat) / 1000 / cfg.dt:.3f} % of that time.")


if __name__ == "__main__":
    main()
