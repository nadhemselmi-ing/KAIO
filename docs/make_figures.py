"""Figures for the KAIO report and slides, generated from results/ and the simulator.

    python docs/make_figures.py        # writes docs/figures/*.svg
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)

for f in os.listdir(os.path.join(HERE, "fonts")):
    if f.endswith(".ttf"):
        font_manager.fontManager.addfont(os.path.join(HERE, "fonts", f))

INK, MUTED, FAINT, GRID, SURF = "#121A2B", "#55617A", "#8C97AC", "#E3E8F0", "#FFFFFF"
BLUE, ORANGE, MAGENTA, GREY = "#1E63C4", "#C9661C", "#A1487A", "#A3ACB9"
ECL = "#4F5AA0"
plt.rcParams.update({
    "font.family": "Space Grotesk", "font.size": 10, "text.color": INK, "axes.labelcolor": MUTED,
    "axes.edgecolor": GRID, "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": False,
    "svg.fonttype": "none", "figure.facecolor": SURF, "axes.facecolor": SURF,
    "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False,
})

S = json.load(open(os.path.join(ROOT, "results", "summary.json")))
RD = json.load(open(os.path.join(ROOT, "results", "realdata_stats.json")))
SC = S["scenarios"]


def save(fig, name):
    fig.savefig(os.path.join(FIG, name + ".svg"), bbox_inches="tight", pad_inches=0.08)
    os.makedirs(os.path.join(HERE, "latex", "figures"), exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(HERE, "latex", "figures", name + "." + ext), bbox_inches="tight", pad_inches=0.08, dpi=300)
    plt.close(fig)


def hbars(ax, labels, vals, cis, colors, fmt="{:.1f}%", xmax=100):
    y = np.arange(len(labels))[::-1]
    ax.barh(y, vals, height=0.62, color=colors, zorder=2)
    for yi, v, c in zip(y, vals, cis):
        if c and c > 0.05:
            ax.errorbar(v, yi, xerr=c, color=INK, lw=1, capsize=3, capthick=1, zorder=3)
        ax.text(v + (c or 0) + xmax * 0.012, yi, fmt.format(v), va="center", ha="left", fontsize=9.5, color=INK)
    ax.set_yticks(y, labels)
    ax.set_xlim(0, xmax * 1.1)
    ax.tick_params(axis="y", length=0, labelsize=10, labelcolor=INK)
    ax.tick_params(axis="x", labelsize=8.5)
    ax.spines["left"].set_visible(False)
    ax.xaxis.grid(True, color=GRID, lw=0.8, zorder=0)


# 1. main result -----------------------------------------------------------
order = ["E-LOTUS", "Rule-Based", "Bandwidth-Rules", "Store-and-Forward", "Greedy-Process", "Always-Transmit"]
P = SC["nominal"]["policies"]
fig, ax = plt.subplots(figsize=(6.4, 2.7))
hbars(ax, ["E-LOTUS (KAIO)"] + order[1:], [P[p]["ceiling_pct"][0] for p in order], [P[p]["ceiling_pct"][1] for p in order],
      [BLUE] + [GREY] * 5)
ax.set_xlabel("Share of the reachable value delivered to the ground (%, mean ± 95 % CI, 20 real days)")
save(fig, "fig_value")

# 2. stress tests ------------------------------------------------------------
keys = ["nominal", "energy_starved", "battery_starved", "storage_tight", "downlink_starved", "event_surge",
        "compute_starved", "degraded_radiator"]
labels = [SC[k]["label"].replace("Small battery (40 Wh) + solar -30 %", "Battery 40 Wh + solar −30 %")
          .replace("-30 %", "−30 %").replace("-25 %", "−25 %").replace("2.5x", "2.5×").replace("3x", "3×")
          .replace("20 deg", "20°") for k in keys]
el = [SC[k]["policies"]["E-LOTUS"]["ceiling_pct"] for k in keys]
rb = [SC[k]["policies"]["Rule-Based"]["ceiling_pct"] for k in keys]
fig, ax = plt.subplots(figsize=(6.6, 4.0))
y = np.arange(len(keys))[::-1] * 1.0
h = 0.36
ax.barh(y + h / 2, [v[0] for v in el], height=h, color=BLUE, label="E-LOTUS (KAIO)", zorder=2)
ax.barh(y - h / 2, [v[0] for v in rb], height=h, color=MAGENTA, label="Rule-Based", zorder=2)
for yi, a, b, k in zip(y, el, rb, keys):
    ax.text(a[0] + 1.2, yi + h / 2, f"{a[0]:.1f}", va="center", fontsize=8.5)
    ax.text(b[0] + 1.2, yi - h / 2, f"{b[0]:.1f}", va="center", fontsize=8.5, color=MUTED)
    hot = SC[k]["policies"]["Rule-Based"]["above_tsafe_pct"][0]
    if b[0] > a[0] and hot > 5:
        ax.text(101, yi, f"rules run >45 °C\n{hot:.0f} % of the day", va="center", fontsize=8, color=MAGENTA)
ax.set_yticks(y, labels)
ax.tick_params(axis="y", length=0, labelsize=9.5, labelcolor=INK)
ax.set_xlim(0, 125)
ax.set_xticks([0, 20, 40, 60, 80, 100])
ax.xaxis.grid(True, color=GRID, lw=0.8, zorder=0)
ax.spines["left"].set_visible(False)
ax.set_xlabel("% of reachable value (mean of 20 real days)")
ax.legend(loc="lower left", frameon=False, fontsize=9, ncol=2, bbox_to_anchor=(0.0, 1.0))
save(fig, "fig_stress")

# 3. triage on real data ---------------------------------------------------------
tri = RD["heldout_capture_top30"]
tk = ["random", "raw entropy", "land prior", "E-LOTUS", "oracle"]
tl = ["Random pick", "Raw entropy", "Land mask only", "E-LOTUS estimator", "Perfect oracle"]
fig, ax = plt.subplots(figsize=(5.6, 2.2))
hbars(ax, tl, [100 * tri[k] for k in tk], [0] * 5, [GREY, "#C0392B", GREY, BLUE, "#3B4352"], fmt="{:.0f}%")
ax.set_xlabel("Value held by the top 30 % of scenes chosen by each ranking (held-out days)")
save(fig, "fig_triage")

# 4. entropy by class -------------------------------------------------------------
H = RD["H_by_class_optical"]
share = RD["share_by_class_pct"]
cls = ["cloud", "fire", "coast", "ocean", "land", "dark"]
cl_l = {"cloud": "Cloud", "fire": "Fire", "coast": "Coast", "ocean": "Ocean", "land": "Clear land", "dark": "Polar night"}
fig, ax = plt.subplots(figsize=(5.6, 2.4))
hbars(ax, [f"{cl_l[c]} ({share[c]:.0f} % of scenes)" for c in cls], [H[c][0] for c in cls], [0] * 6,
      ["#C0392B" if c == "cloud" else GREY for c in cls], fmt="{:.1f}", xmax=8)
ax.set_xlabel("Median quick-look entropy (bit/px), real VIIRS scenes")
save(fig, "fig_entropy")

# 5. one real day of telemetry ------------------------------------------------------
from kaio import ELotusEngine, GreedyProcess, RuleBased, SimConfig, Simulation, build_ephemeris, generate_workload  # noqa

cfg = SimConfig(seed=2026, start_day=0, duration_h=24.0)
eph = build_ephemeris(cfg)
arr = generate_workload(cfg, eph)
runs = {n: Simulation(cfg, p, eph, arr, max_events=10).run() for n, p in
        [("E-LOTUS (KAIO)", ELotusEngine(explain=False)), ("Greedy-Process", GreedyProcess()), ("Rule-Based", RuleBased())]}
col = {"E-LOTUS (KAIO)": BLUE, "Greedy-Process": ORANGE, "Rule-Based": MAGENTA}
t = runs["E-LOTUS (KAIO)"].telemetry["t_h"]
sun = runs["E-LOTUS (KAIO)"].telemetry["sunlit"]
fig, axes = plt.subplots(3, 1, figsize=(6.6, 5.4), sharex=True, gridspec_kw={"hspace": 0.32})
for ax, key, lab, lines in [(axes[0], "soc", "Battery (%)", [(20, "#C0392B", "payload cut-off 20 %")]),
                            (axes[1], "temp_c", "Computer temperature (°C)", [(45, MUTED, "limit 45 °C"), (60, "#C0392B", "throttle 60 °C")]),
                            (axes[2], "value_cum", "Value delivered (cumulative)", [])]:
    edges = np.diff(np.r_[0, (sun == 0).astype(int), 0])
    for s0, e0 in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)):
        ax.axvspan(t[s0], t[min(e0, len(t) - 1)], color=ECL, alpha=0.07, lw=0)
    for n, r in runs.items():
        ax.plot(t, r.telemetry[key], color=col[n], lw=1.6 if "E-LOTUS" in n else 1.3,
                ls="--" if n == "Rule-Based" else "-", label=n)
    for v, c, txt in lines:
        ax.axhline(v, color=c, lw=0.9, ls=":")
        ax.text(24.2, v, txt, fontsize=7.5, color=c, va="center")
    ax.set_ylabel(lab, fontsize=8.5)
    ax.yaxis.grid(True, color=GRID, lw=0.7)
    ax.tick_params(labelsize=8)
axes[0].set_ylim(0, 105)
axes[2].set_xlabel("Hours since 2026-08-26 00:00 UTC (shaded = eclipse)")
axes[2].set_xticks(range(0, 25, 3))
axes[0].legend(ncol=3, frameon=False, fontsize=8.5, loc="lower left", bbox_to_anchor=(0, 1.0))
save(fig, "fig_telemetry")

# 6. ablation ----------------------------------------------------------------------------
abl = [("E-LOTUS", "Full E-LOTUS"), ("E-LOTUS land only", "Without entropy (land mask only)"),
       ("E-LOTUS raw entropy", "Without land mask (raw entropy)"), ("E-LOTUS w/o ISLL", "Without laser offload"),
       ("E-LOTUS static E_min", "Without eclipse-aware battery floor")]
json.dump({"ablation": {lab: {s: SC[s]["policies"][k]["ceiling_pct"][0] for s in
                              ["nominal", "energy_starved", "battery_starved", "degraded_radiator"]} for k, lab in abl}},
          open(os.path.join(FIG, "ablation.json"), "w"), indent=1)
print("figures written to", FIG)
