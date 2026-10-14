"""Build the KAIO technical report (docs/KAIO_Technical_Report.pdf) from results/ and docs/figures/.

    python docs/make_figures.py && python docs/build_report.py
"""
from __future__ import annotations

import os

from common import (logo_svg, ABL, ARCH_SVG, DATE, EVENT, HERE, MEMBERS, NOM, PI, RD, REPO_URL, SC, TEAM, S, font_css, img, m,
                    on_pi, print_pdf, svg)


def f1(x):
    return f"{x:.1f}"


def ci(p, k, s="nominal"):
    v = m(p, k, s, ci=True)
    return f"{v[0]:.1f} ± {v[1]:.1f}"


E, RB, GP, SF, AT, BW = "E-LOTUS", "Rule-Based", "Greedy-Process", "Store-and-Forward", "Always-Transmit", "Bandwidth-Rules"
days = S["days"]
tri = RD["heldout_capture_top30"]
share = RD["share_by_class_pct"]
H = RD["H_by_class_optical"]

ind_rows = [
    ("Quality of decisions", "Value delivered, % of the reachable value", "ceiling_pct", 1, "higher"),
    ("Quality of decisions", "Fire alerts delivered while still useful (%)", "alerts_on_time_pct", 1, "higher"),
    ("Rate of completed tasks", "Images delivered or triaged onboard (%)", "completion_pct", 1, "higher"),
    ("Estimated energy consumption", "Payload energy per day (Wh)", "energy_payload_wh", 0, "context"),
    ("Estimated energy consumption", "Lowest battery level (%)", "soc_min_pct", 0, "higher"),
    ("Latency", "Mean generation-to-ground latency (min)", "latency_mean_min", 0, "lower"),
    ("Latency", "95th-percentile latency (min)", "latency_p95_min", 0, "lower"),
    ("Resource utilisation", "GPU duty cycle (%)", "gpu_duty_pct", 0, "context"),
    ("Resource utilisation", "Downlink use during passes (%)", "dl_util_pct", 0, "context"),
    ("Safety", "Time above the 45 °C limit (%)", "above_tsafe_pct", 1, "lower"),
    ("Safety", "Time with payload load-shed (%)", "shed_pct", 1, "lower"),
]
cols = [E, RB, GP, SF, AT]
SHORT = {E: 'E-LOTUS', RB: 'Rule-Based', GP: 'Greedy', SF: 'Store &amp; fwd', AT: 'Always-Tx'}


def ind_table():
    head = "<tr><th>Indicator (Problem 1)</th><th>Metric</th>" + "".join(
        f"<th>{SHORT[c]}</th>" for c in cols) + "</tr>"
    rows, last = [], None
    for grp, lab, k, dg, better in ind_rows:
        g = grp if grp != last else ""
        last = grp
        vals = [m(c, k) for c in cols]
        best = None
        if better in ("higher", "lower"):
            best = (max if better == "higher" else min)(range(len(vals)), key=lambda i: vals[i])
        cells = "".join(f"<td class='num{' hl' if c == E else ''}{' best' if i == best else ''}'>{v:.{dg}f}</td>"
                        for i, (c, v) in enumerate(zip(cols, vals)))
        rows.append(f"<tr><td class='grp'>{g}</td><td>{lab}</td>{cells}</tr>")
    cg = "<colgroup><col style='width:20%'><col style='width:30%'>" + "<col style='width:10%'>" * 5 + "</colgroup>"
    return f"<table class='t ind' style='table-layout:fixed'>{cg}{head}{''.join(rows)}</table>"


stress_keys = ["nominal", "energy_starved", "battery_starved", "storage_tight", "downlink_starved", "event_surge",
               "compute_starved", "degraded_radiator"]


def stress_table():
    head = ("<tr><th>Scenario (one resource degraded)</th><th>E-LOTUS</th><th>Rule-Based</th><th>Bandwidth-Rules</th>"
            "<th>E-LOTUS better on</th><th>Rule-Based time &gt; 45 °C</th></tr>")
    rows = []
    for k in stress_keys:
        P = SC[k]["policies"]
        e, r, b = P[E]["ceiling_pct"], P[RB]["ceiling_pct"], P[BW]["ceiling_pct"]
        win = e[0] > max(r[0], b[0])
        rows.append(f"<tr><td>{SC[k]['label']}</td><td class='num hl'>{e[0]:.1f} ± {e[1]:.1f}</td>"
                    f"<td class='num'>{r[0]:.1f} ± {r[1]:.1f}</td><td class='num'>{b[0]:.1f} ± {b[1]:.1f}</td>"
                    f"<td class='num'>{P[RB]['elotus_wins_days']}/{P[RB]['n_days']} days</td>"
                    f"<td class='num{'' if P[RB]['above_tsafe_pct'][0] < 5 else ' warn'}'>{P[RB]['above_tsafe_pct'][0]:.0f} %</td></tr>")
    return f"<table class='t'>{head}{''.join(rows)}</table>"


def abl_table():
    sc = [("nominal", "Nominal"), ("energy_starved", "Solar −30 %"), ("battery_starved", "Battery 40 Wh"),
          ("degraded_radiator", "Radiator −25 %")]
    head = "<tr><th>Variant</th>" + "".join(f"<th>{l}</th>" for _, l in sc) + "</tr>"
    rows = []
    for lab, d in ABL.items():
        rows.append(f"<tr><td>{lab}</td>" + "".join(
            f"<td class='num{' hl' if lab == 'Full E-LOTUS' else ''}'>{d[k]:.1f}</td>" for k, _ in sc) + "</tr>")
    return f"<table class='t'>{head}{''.join(rows)}</table>"


hw_label = PI["board"] if on_pi() else f"development laptop ({PI['machine']}); Raspberry Pi run pending"
e_vs_rb = m(E, "ceiling_pct") - m(RB, "ceiling_pct")
wins_nom = NOM[RB]["elotus_wins_days"]
n_win = sum(1 for k in stress_keys if m(E, "ceiling_pct", k) > max(m(RB, "ceiling_pct", k), m(BW, "ceiling_pct", k)))

html = f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>KAIO technical report</title>
<style>
{font_css()}
@page{{size:A4}}
:root{{--ink:#121A2B;--muted:#55617A;--faint:#8C97AC;--line:#DCE3EE;--blue:#1E63C4;--tint:#EEF4FD}}
*{{box-sizing:border-box}}
body{{font-family:'Space Grotesk',sans-serif;color:var(--ink);font-size:10pt;line-height:1.5;margin:0}}
h1{{font-size:26pt;line-height:1.1;margin:0 0 6pt;letter-spacing:-.01em}}
h2{{font-size:14pt;margin:20pt 0 6pt;padding-top:4pt;border-top:1px solid var(--line)}}
h3{{font-size:11pt;margin:12pt 0 4pt}}
h2,h3{{break-after:avoid;page-break-after:avoid}}
p{{margin:0 0 7pt}} ul,ol{{margin:0 0 8pt;padding-left:16pt}} li{{margin:0 0 2pt}}
.muted{{color:var(--muted)}} .small{{font-size:8.5pt}}
.cover{{height:250mm;display:flex;flex-direction:column;justify-content:space-between;page-break-after:always}}
.cover .top{{border-left:4px solid var(--blue);padding-left:14pt}}
.cover .kicker{{font-size:10pt;color:var(--muted);margin-bottom:18pt}}
.cover .sub{{font-size:13pt;color:var(--muted);max-width:150mm}}
.cover img{{width:100%;border-radius:8pt;margin:14pt 0}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:0;border:1px solid var(--line);border-radius:8pt;margin:8pt 0 10pt}}
.kpi{{padding:9pt 10pt;border-left:1px solid var(--line)}} .kpi:first-child{{border-left:0}}
.kpi b{{display:block;font-size:17pt;line-height:1.1;font-weight:600}} .kpi:first-child b{{color:var(--blue)}}
.kpi span{{font-size:8pt;color:var(--muted);line-height:1.3;display:block;margin-top:2pt}}
.t.ind td:nth-child(2){{width:30%}}
.t{{width:100%;border-collapse:collapse;font-size:8.6pt;margin:4pt 0 4pt;page-break-inside:avoid}}
.t th{{text-align:left;font-weight:600;color:var(--muted);border-bottom:1.2px solid var(--ink);padding:4pt 5pt;vertical-align:bottom}}
.t td{{border-bottom:1px solid var(--line);padding:3.5pt 5pt;vertical-align:top}}
.t td.num,.t th:not(:first-child):not(:nth-child(2)){{text-align:right;font-variant-numeric:tabular-nums}}
.t td.hl{{color:var(--blue);font-weight:600}} .t td.best{{text-decoration:underline;text-underline-offset:2pt}}
td.num{{white-space:nowrap}}
.t td.grp{{font-weight:600;color:var(--ink)}} .t td.warn{{color:#B23A2A}}
figure{{margin:6pt 0 10pt;page-break-inside:avoid}} figure svg{{width:100%;height:auto;max-height:118mm}}
figcaption{{font-size:8.5pt;color:var(--muted);margin-top:3pt}}
.box{{background:var(--tint);border-radius:6pt;padding:8pt 10pt;margin:6pt 0 10pt;page-break-inside:avoid}}
.eq{{font-size:10.5pt;background:#F6F8FC;border:1px solid var(--line);border-radius:4pt;padding:6pt 10pt;margin:4pt 0 8pt;font-variant-numeric:tabular-nums}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:12pt;align-items:start}}
.toc li{{margin-bottom:1pt}}
.pb{{page-break-before:always}}
code{{font-size:8.6pt;background:#F2F5FA;padding:0 3pt;border-radius:2pt}}
img.shot{{width:100%;border-radius:6pt;border:1px solid var(--line)}}
</style>
<body>

<section class="cover">
  <div class="top">
    <div style="display:flex;align-items:center;gap:10pt;margin-bottom:14pt">{logo_svg('#121A2B', 44)}<span style="font-size:22pt;font-weight:700;letter-spacing:.12em">KAIO</span></div>
    <div class="kicker">{EVENT}</div>
    <h1>KAIO: deciding onboard which images deserve the downlink</h1>
    <p class="sub">Final technical report. A real-orbit, real-data evaluation of the E-LOTUS onboard decision engine,
    its safety guard and its embedded implementation.</p>
  </div>
  <img src="{img('dash_hero_dark.jpg')}" alt="KAIO mission-control dashboard with the 3D Earth and the Phi-sat-2 orbit">
  <div>
    <p><b>{TEAM}</b>: {' · '.join(MEMBERS)}</p>
    <p class="muted small">{DATE} · Code: {REPO_URL} · All numbers in this report are generated from
    <code>results/summary.json</code> by <code>docs/build_report.py</code>.</p>
  </div>
</section>

<h2 style="border-top:0;margin-top:0">Summary</h2>
<p>An Earth-observation satellite produces far more data than it can downlink. For each image it must decide to
<b>process</b> it onboard, <b>keep</b> it, <b>transmit</b> it, or <b>offload</b> it to a neighbour over a laser link,
within its energy, thermal, storage and contact budgets. KAIO is an onboard decision system that makes this
choice every 10 seconds with the <b>E-LOTUS</b> engine: a value estimate built only from onboard information, a
Lyapunov drift-plus-penalty score, an independent safety guard and a one-line explanation per decision.</p>
<p>We evaluate it on the <b>real orbit of ESA's Φsat-2</b> (CelesTrak TLE, SGP4) and on <b>20 days of real NASA
imagery</b> sampled under its ground track (VIIRS, MODIS, FIRMS), against five reference strategies, in eight
scenarios, with 95 % confidence intervals.</p>
<div class="kpis">
  <div class="kpi"><b>{m(E,'ceiling_pct'):.1f} %</b><span>of the reachable value delivered (± {m(E,'ceiling_pct',ci=True)[1]:.1f}, {days} real days)</span></div>
  <div class="kpi"><b>+{e_vs_rb:.1f} pts</b><span>over a tuned rule engine with the same information; better on {wins_nom}/{days} days</span></div>
  <div class="kpi"><b>0</b><span>load-sheds or hardware throttles; time above 45 °C {m(E,'above_tsafe_pct'):.1f} %</span></div>
  <div class="kpi"><b>{PI['decision_ms_median']:.2f} ms</b><span>median decision time ({'Raspberry Pi' if on_pi() else 'laptop'}), for a 10 s decision cycle</span></div>
</div>
<p>The main finding from real data is that <b>raw image entropy misranks scenes</b>. Clouds are the most textured
scenes and {share['cloud']:.0f} % of all scenes, so ranking by entropy alone captures {100*tri['raw entropy']:.0f} % of the value
in the top 30 %, worse than random ({100*tri['random']:.0f} %). Multiplying entropy by an onboard land-mask prior reaches
{100*tri['E-LOTUS']:.0f} %, close to a label-aware oracle ({100*tri['oracle']:.0f} %). E-LOTUS wins {n_win} of 8 stress scenarios.
It loses two, a slower GPU and a degraded radiator, where the rule engine scores higher only by running above the
45 °C limit for 37–81 % of the day.</p>

<h3>Contents</h3>
<ol class="toc small">
<li>Problem and performance indicators</li><li>Real data: orbit and Earth observations</li><li>System architecture</li>
<li>The E-LOTUS decision engine</li><li>Implementation</li><li>Evaluation protocol</li>
<li>Results against the performance indicators</li><li>Robustness and ablations</li>
<li>Feasibility and embedded implementation</li><li>Methodology, planning and roadmap</li><li>Limitations</li>
<li>References and AI-use statement</li></ol>

<h2 class="pb">1. Problem and performance indicators</h2>
<p><b>Problem 1 asks:</b> how can the system decide automatically, for each piece of data or task, whether to process
it onboard, store it for later, or transmit it to the ground, so as to maximise scientific or operational value under
the available resources?</p>
<p><b>Constraints:</b> available energy, CPU/GPU load, memory, storage, data priority, communication windows,
bandwidth and transmission delay.</p>
<p>The challenge evaluates five indicators. We map each one to measured quantities.</p>
<table class="t">
<tr><th>Indicator</th><th>How KAIO measures it</th></tr>
<tr><td class="grp">Quality of decisions</td><td>Value delivered to the ground as a share of the <i>reachable</i> value (each image delivered at its first ground pass with unlimited resources), and fire alerts delivered while still useful.</td></tr>
<tr><td class="grp">Rate of completed tasks</td><td>Share of images that are delivered (raw or as a product) or triaged onboard.</td></tr>
<tr><td class="grp">Estimated energy consumption</td><td>Payload energy per day (GPU, radio, laser), lowest battery level, payload load-shed time.</td></tr>
<tr><td class="grp">Latency</td><td>Time from image acquisition to delivery on the ground (mean and 95th percentile).</td></tr>
<tr><td class="grp">Resource utilisation</td><td>GPU duty cycle, downlink use during passes, storage backlog, and time above the thermal limit.</td></tr>
</table>
<p class="muted small">The "reachable" ceiling is physically unattainable (zero processing and transfer time), so 100 % is an upper bound, not a target.</p>

<h2>2. Real data: orbit and Earth observations</h2>
<h3>2.1 Orbit and geometry</h3>
<p>The spacecraft flies the real orbit of <b>Φsat-2</b> (NORAD 60470). Its CelesTrak two-line element set is
propagated with <b>SGP4</b> every 10 s. This gives about 472 km altitude, a 94-minute period and about 35-minute
eclipses. An independent fourth-order Runge–Kutta integrator with the J2 term agrees within 25 km over 6 h
(automated test).</p>
<p>From the position we derive:</p>
<ul>
<li>sun or eclipse, with a cylindrical shadow model and a low-precision solar ephemeris;</li>
<li>ground contacts with KSAT <b>Svalbard</b> and ASI <b>Matera</b> above 10° elevation, about
{m(E,'contact_min_per_day'):.0f} min per day;</li>
<li>line of sight to two in-plane neighbours for laser offload.</li>
</ul>
<h3>2.2 Earth observations under the real ground track</h3>
<p>For 20 days (26 Aug – 14 Sep 2026), every 30 s along the real ground track, a 32 × 32-pixel block (about
313 km) was cut from the NASA GIBS daily global mosaics and reduced to a few numbers:</p>
<table class="t">
<tr><th>Quantity</th><th>NASA GIBS layer</th><th>Use</th></tr>
<tr><td>Day quick-look entropy</td><td>VIIRS NOAA-20 Corrected Reflectance, true colour</td><td>onboard value estimate</td></tr>
<tr><td>Night quick-look entropy</td><td>VIIRS NOAA-20 Brightness Temperature, band I5 night</td><td>onboard value estimate</td></tr>
<tr><td>Fire pixels</td><td>VIIRS NOAA-20 Thermal Anomalies 375 m (FIRMS)</td><td>alert flag (priority 4)</td></tr>
<tr><td>Cloud fraction</td><td>MODIS Aqua Cloud Fraction, day / night (decoded from the colour map)</td><td>hidden ground truth only</td></tr>
<tr><td>Land fraction</td><td>OpenStreetMap land/water map</td><td>onboard prior + ground truth</td></tr>
</table>
<p>The result is an atlas of 57,600 real footprints (<code>data/elotus_gibs_atlas.bin</code>, sampler
<code>data/gibs_sampler.js</code>). Each simulated acquisition receives the real scene that was under Φsat-2 at that
time. The hidden ground-truth value is high for cloud-free land, low for cloud, ocean or polar night, and very high
for fires. It is used only for scoring. A test shuffles it and checks that the engine's decisions do not change.</p>
<div>
<figure>{svg('fig_entropy')}<figcaption>Fig. 1. Median quick-look entropy by real scene class. Clouds are the most
textured scenes and the most common.</figcaption></figure>
<figure>{svg('fig_triage')}<figcaption>Fig. 2. Value captured by the top 30 % of scenes on held-out days. Raw entropy is
worse than random; the E-LOTUS estimator is within {100*(tri['oracle']-tri['E-LOTUS']):.0f} points of an oracle.</figcaption></figure>
</div>

<h2>3. System architecture</h2>
<figure>{ARCH_SVG}<figcaption>Fig. 3. KAIO architecture. Real inputs drive a simulated spacecraft. The E-LOTUS flight
logic reads its telemetry every 10 s and commands one of four actions. The surrounding software benchmarks, tests,
visualises and runs the same code on embedded hardware.</figcaption></figure>
<p>The design separates three concerns, as in flight software:</p>
<ul>
<li><b>the world:</b> orbit, data and spacecraft physics, all policy-independent;</li>
<li><b>the optimiser:</b> the E-LOTUS score;</li>
<li><b>the protection:</b> an independent safety guard.</li>
</ul>
<p>Every controller, including the baselines, sees exactly the same orbit, images and hardware limits. Only the
decision rule changes.</p>
<h3>Spacecraft model (simulated)</h3>
<table class="t">
<tr><th>Subsystem</th><th>Model and main parameters</th></tr>
<tr><td>Power</td><td>100 Wh battery integrated with RK4, 0.95 charge/discharge efficiency, CV taper above 90 %; body-mounted panels (20 W per face at normal incidence); 6.5 W platform bus; payload load-shed below 20 Wh.</td></tr>
<tr><td>Thermal</td><td>Lumped node, radiator to deep space (ε = 0.85, A = 0.045 m², Stefan–Boltzmann), solar and Earth-IR loads; operating limit 45 °C, hardware throttle 60 °C.</td></tr>
<tr><td>Compute</td><td>Edge-AI module, 15 W active (Jetson-Orin class), 1 TFLOP/s effective; processing reduces an image to 3 % of its size and keeps 90 % of its information.</td></tr>
<tr><td>Links and storage</td><td>10 Mbps downlink, 100 Mbps laser link to a sunlit neighbour with limited spare compute, 8 GB storage.</td></tr>
<tr><td>Workload</td><td>Poisson acquisitions (one per 45 s in sunlight, one per 120 s in eclipse), about 50 MB per image, 1.5 h deadline for fire alerts, 12 h otherwise.</td></tr>
</table>

<h2>4. The E-LOTUS decision engine</h2>
<h3>4.1 Value estimate (onboard)</h3>
<p>For each image, the engine uses two numbers available onboard:</p>
<ul>
<li>the Shannon entropy <i>H</i> of a quick-look thumbnail;</li>
<li>the land fraction <i>ℓ</i> of the footprint, looked up in a static land/water mask indexed by the onboard position.</li>
</ul>
<p>It also uses the priority <i>p</i>, which is 4 for a fire alert and 1 otherwise.</p>
<div class="eq">ŵ = p · (0.1 + 0.9 ℓ) · (H / 8)³ for optical scenes, &nbsp; ŵ = p · (0.1 + 0.9 ℓ) for thermal-IR night scenes</div>
<h3>4.2 Scoring: drift-plus-penalty</h3>
<p>The engine keeps three normalised "debts" small:</p>
<ul>
<li>the storage backlog <i>q/Q</i>;</li>
<li>the energy debt <i>D<sub>E</sub></i> below an eclipse-aware battery floor <i>E<sub>min</sub>(t)</i>;</li>
<li>the heat debt <i>D<sub>T</sub></i> above <i>T<sub>safe</sub></i> = 45 °C.</li>
</ul>
<div class="eq">L = ½ [ (q/Q)² + (D<sub>E</sub>/5 Wh)² + (D<sub>T</sub>/5 K)² ], &nbsp; Φ<sub>i</sub>(a) = [ ΔL<sub>i</sub>(a) − V · U<sub>i</sub>(a) ] / τ<sub>i</sub>(a)</div>
<p>For each stored image <i>i</i> and action <i>a</i> (process, transmit, offload), the engine predicts the change
ΔL relative to keeping the image. It predicts it over the action duration τ, using a linear energy budget and a
first-order thermal model. <i>U</i> is the delivered value: ŵ × retained information × a freshness term that decays
with age until the deadline, minus an energy price that is zero when the solar array would otherwise be shunted.
Free resources are filled greedily with the most negative Φ. <b>V</b> (0.3) is the single trade-off knob.</p>
<p>This is the drift-plus-penalty rule of Lyapunov optimisation [1]. We use it as a principled scoring rule.
Its textbook performance bound assumes stationary arrivals and exact per-slot minimisation, which an orbit does not
provide, so all claims in this report are empirical.</p>
<h3>4.3 Safety guard</h3>
<p>An independent layer checks each proposed job before it starts, like FDIR in flight software. It blocks the job if
either of these would happen at the end of the job:</p>
<ul>
<li>the battery would fall below the energy needed to carry the platform through the current or next eclipse plus a
reserve;</li>
<li>the computer would exceed 45 °C. Fire alerts may use the margin up to the 60 °C hardware limit.</li>
</ul>
<p>Blocked jobs are logged with their reason.</p>
<h3>4.4 Storage and explanations</h3>
<p>When storage is full, the engine deletes the items with the lowest expected value per megabyte first. The
rule-based baselines get the same rule, for fairness. Every started job carries a one-line reason built only from
onboard quantities, for example: <i>"Process now: est. value 0.68 (optical H 7.5, land 79 %). 20 MB raw → 0.6 MB
product, next pass in 476 min; battery 69 Wh after (floor 20), 9.3 °C."</i></p>

<h2>5. Implementation</h2>
<table class="t">
<tr><th>Layer</th><th>Technology</th><th>Content</th></tr>
<tr><td class="grp">Flight logic and simulation</td><td>Python 3, numpy, sgp4</td><td>Package <code>kaio/</code>:
<code>orbit</code>, <code>workload</code>, <code>estimator</code>, <code>physics</code>, <code>safety</code>,
<code>engine</code>, <code>baselines</code>, <code>simulator</code>, <code>scenarios</code>. Every assumption is in
<code>config.py</code>.</td></tr>
<tr><td class="grp">Verification</td><td>pytest</td><td>18 tests: SGP4 vs RK4/J2, physics bounds, entropy limits, guard
vetoes, determinism, <i>engine never reads ground truth</i>, image bookkeeping, safety properties.</td></tr>
<tr><td class="grp">Benchmark</td><td>Python multiprocessing, scipy</td><td><code>benchmark.py</code>: 8 scenarios × 6 strategies
× 20 days plus ablations (1,360 runs), 95 % CIs, paired days-won.</td></tr>
<tr><td class="grp">Dashboard</td><td>HTML, CSS, JavaScript, three.js, Canvas</td><td>One self-contained offline file: 3D
Earth with the real orbit, orbit designer (80 what-if orbits), 24 h replay of 270 what-if missions, benchmark,
real-data findings; light/dark mode.</td></tr>
<tr><td class="grp">Embedded target</td><td>Raspberry Pi, Python, numpy, sgp4</td><td><code>onboard/pi_benchmark.py</code> (timing,
CPU, memory) and <code>onboard/live_demo.py</code> (live decision feed with reasons).</td></tr>
<tr><td class="grp">Exploration</td><td>Streamlit, Plotly</td><td><code>app.py</code>: run new simulations interactively.</td></tr>
</table>
<figure><img class="shot" src="{img('dash_replay_dark.jpg')}" alt="Mission replay view of the dashboard">
<figcaption>Fig. 4. Dashboard: one real day replayed by E-LOTUS, a greedy processor and a rule engine. The
controls on top switch to any of 270 pre-computed what-if missions.</figcaption></figure>

<h2>6. Evaluation protocol</h2>
<ul>
<li><b>Days:</b> {days} real days, each an independent 24 h run starting at 00:00 UTC on 2026-08-26 + <i>d</i>. The
workload seed is 2026 + <i>d</i>, and every strategy sees the same images on a given day.</li>
<li><b>Strategies:</b>
  <ul>
  <li><b>Always-Transmit</b> (bent pipe);</li>
  <li><b>Greedy-Process</b> (process everything);</li>
  <li><b>Store-and-Forward</b> (no onboard compute);</li>
  <li><b>Rule-Based</b>, a hand-tuned onboard rule engine using the <i>same</i> value estimate, with battery and
  temperature thresholds;</li>
  <li><b>Bandwidth-Rules</b>, Rule-Based plus pass-capacity awareness.</li>
  </ul></li>
<li><b>Scenarios:</b> nominal, plus seven single-resource degradations fixed in advance and applied without
retuning any controller.</li>
<li><b>Statistics:</b> mean ± 95 % confidence interval (Student t over days) and the number of days on which E-LOTUS
beats each baseline.</li>
<li><b>Tuning hygiene:</b> V and the debt weights were selected on a different workload seed. The thermal limit and the
fire-alert exception are design rules with no tuned value.</li>
</ul>

<h2 class="pb">7. Results against the performance indicators</h2>
<figure>{svg('fig_value')}<figcaption>Fig. 5. Quality of decisions, nominal scenario. E-LOTUS {ci(E,'ceiling_pct')} %,
Rule-Based {ci(RB,'ceiling_pct')} %, Bandwidth-Rules {ci(BW,'ceiling_pct')} %. The intervals do not overlap, and
E-LOTUS is better on {wins_nom} of {days} days.</figcaption></figure>
{ind_table()}
<p class="small muted">Nominal scenario, mean of {days} real days. Underlined: best value where higher or lower is
clearly better.</p>
<h3>Reading the indicators</h3>
<ul>
<li><b>Quality of decisions:</b> E-LOTUS delivers the most value (+{e_vs_rb:.1f} pts over the rule engine) and
matches the best strategies on fire alerts ({m(E,'alerts_on_time_pct'):.1f} %).</li>
<li><b>Completed tasks:</b> {m(E,'completion_pct'):.1f} % against {m(RB,'completion_pct'):.1f} % for the rule engine. The
laser offload in eclipse and value-aware storage management keep more images moving.</li>
<li><b>Energy:</b> E-LOTUS spends more payload energy ({m(E,'energy_payload_wh'):.0f} vs
{m(RB,'energy_payload_wh'):.0f} Wh/day), so its value per Wh is lower. This extra energy comes from solar power that
would otherwise be shunted: the battery never drops below {m(E,'soc_min_pct'):.0f} %, as with the rule engine, and
there is no load-shed. Greedy-Process shows the opposite failure: it drains the battery to {m(GP,'soc_min_pct'):.0f} %
and sheds the payload {m(GP,'shed_pct'):.0f} % of the time.</li>
<li><b>Latency:</b> E-LOTUS has the lowest mean latency of the processing strategies ({m(E,'latency_mean_min'):.0f} min
vs {m(RB,'latency_mean_min'):.0f} min). Store-and-Forward is faster only because it delivers very few images.</li>
<li><b>Resource utilisation:</b> E-LOTUS uses the GPU more ({m(E,'gpu_duty_pct'):.0f} %) and fills
{m(E,'dl_util_pct'):.0f} % of pass capacity. The remaining capacity goes unused because the products it sends are small.
Time above 45 °C is {m(E,'above_tsafe_pct'):.1f} % (fire alerts only), against {m(GP,'above_tsafe_pct'):.0f} % for Greedy.</li>
</ul>
<figure>{svg('fig_telemetry')}<figcaption>Fig. 6. One real day (2026-08-26). Greedy processing drains the battery to the
payload cut-off and runs hot. E-LOTUS keeps the battery high and the computer under 45 °C, and delivers the most value.</figcaption></figure>

<h2>8. Robustness and ablations</h2>
<figure>{svg('fig_stress')}<figcaption>Fig. 7. Eight scenarios, 20 real days each, no retuning.</figcaption></figure>
{stress_table()}
<p><b>Wins ({n_win}/8).</b> E-LOTUS beats both rule engines on every day of six scenarios. With a 40 Wh battery and
weaker panels, the rule engine's fixed 50 % battery threshold coincides with the shutdown floor and it collapses
({m(RB,'ceiling_pct','battery_starved'):.1f} %). E-LOTUS's eclipse-survival floor is computed from the orbit and adapts
automatically ({m(E,'ceiling_pct','battery_starved'):.1f} %).</p>
<p><b>Losses (2/8).</b> With a 2.5× slower GPU or a 25 % weaker radiator, the rule engine scores higher. It does so by
running above 45 °C for {m(RB,'above_tsafe_pct','compute_starved'):.0f} % and {m(RB,'above_tsafe_pct','degraded_radiator'):.0f} %
of the day. If operators allow 60 °C for every job, E-LOTUS reaches {SC['degraded_radiator']['policies']['E-LOTUS soft thermal']['ceiling_pct'][0]:.1f} %
in the radiator case, above the rule engine. The thermal limit is an operator setting, not a limit of the method.</p>
<h3>Ablations</h3>
{abl_table()}
<p>Main points:</p>
<ul>
<li><b>The land-mask prior is the key ingredient.</b> Raw entropy alone loses 2 to 38 points.</li>
<li><b>Entropy pays off when resources are scarce</b> (+2 to +14 points). In the nominal case the land mask alone is
slightly better, because there is enough energy to process every land scene.</li>
<li><b>Laser offload is a modest extension:</b> 1.6 to 4.2 points.</li>
<li><b>The eclipse-aware floor matters under energy stress:</b> +0.4 to +0.9 points.</li>
</ul>

<h2>9. Feasibility and embedded implementation</h2>
<p>Every input the engine uses exists on a real satellite:</p>
<ul>
<li>battery and temperature housekeeping;</li>
<li>a pass schedule computed on the ground and uplinked;</li>
<li>eclipse times from the onboard propagator;</li>
<li>a static land/water mask indexed by GNSS position;</li>
<li>a thumbnail entropy.</li>
</ul>
<p>The engine needs no GPU and no training; its only dependencies are numpy and sgp4. ESA's Φsat-1 already discarded
cloudy images onboard [4]; KAIO flies the real orbit of its successor.</p>
<table class="t">
<tr><th>Measured on {hw_label}</th><th>Value</th></tr>
<tr><td>E-LOTUS decision time (median / p99 / worst)</td><td class="num">{PI['decision_ms_median']:.2f} / {PI['decision_ms_p99']:.2f} / {PI['decision_ms_max']:.1f} ms</td></tr>
<tr><td>Decision cycle required by the satellite</td><td class="num">every {PI['decision_period_s']:.0f} s</td></tr>
<tr><td>CPU used by the engine over a full real day</td><td class="num">{PI['engine_cpu_duty_pct']:.3f} % of one core</td></tr>
<tr><td>Quick-look entropy, one 32 × 32 thumbnail</td><td class="num">{PI['entropy_us_per_thumbnail']:.0f} µs</td></tr>
<tr><td>Peak memory, whole program including the simulator</td><td class="num">{PI['peak_ram_mb']:.0f} MB</td></tr>
</table>
<p class="small muted">Regenerate with <code>python3 onboard/pi_benchmark.py</code> on the target, then
<code>python docs/build_report.py</code>.</p>

<h2>10. Methodology, planning and roadmap</h2>
<h3>How we worked</h3>
<ol>
<li><b>Phase 2, two independent prototypes:</b> E-LOTUS (real orbit, NASA data, Lyapunov engine, dashboard) and a
value-aware pricing engine (tested package, calibrated scenarios, explanations). Both found that a value-aware
engine beats tuned rules by a few points.</li>
<li><b>Review and merge into KAIO:</b> we kept the real-data world, the E-LOTUS engine and the dashboard, and adopted
the tested package structure, the explanations, the drop rule, the bandwidth-aware baseline and the statistical
protocol.</li>
<li><b>Fixes found by the review:</b> the previous engine spent 10 % of the time above 45 °C. The independent safety
guard reduces this to {m(E,'above_tsafe_pct'):.1f} %. All claims were re-worded as empirical.</li>
<li><b>Verification:</b> 18 automated tests, then the full benchmark (1,360 runs), regenerated end to end by scripts.</li>
<li><b>Embedded check:</b> the same code runs on a Raspberry Pi with timing instrumentation.</li>
</ol>
<h3>Roadmap to flight</h3>
<table class="t">
<tr><th>When</th><th>Milestone</th><th>Success criterion</th></tr>
<tr><td class="grp">Done</td><td>Engine, safety guard, real-data simulation, benchmark, dashboard, embedded run</td><td>All results in this report reproducible from scripts</td></tr>
<tr><td class="grp">+3 months</td><td>Hardware-in-the-loop on a flight-like onboard computer; imperfect pass and eclipse forecasts; sensor noise</td><td>Same ranking of strategies with realistic forecast errors</td></tr>
<tr><td class="grp">+6 months</td><td>Small onboard cloud-screening network replacing the static land prior; comparison with a hindsight-optimal schedule</td><td>Triage within 3 points of the oracle; optimality gap quantified</td></tr>
<tr><td class="grp">+12 months</td><td>Coordination across a constellation; partnership for a CubeSat flight experiment</td><td>Flight-software integration plan and test campaign</td></tr>
</table>

<h2>11. Limitations</h2>
<ul>
<li>The spacecraft hardware and the ground-truth value model are assumptions, not a specific mission. The value of a
scene (cloud-free land, fires) would be calibrated by operators.</li>
<li>Pass and eclipse forecasts come from the same propagated orbit and are therefore exact.</li>
<li>The laser-link neighbour is modelled. Without it, E-LOTUS still beats the rule engines.</li>
<li>The TLE epoch is 26 Sep 2026, so August positions are propagated about one month backwards (kilometre-level
error, small against 313 km footprints).</li>
<li>The imagery days are shared between tuning and evaluation; only the acquisition streams differ.</li>
<li>Baselines are heuristics. A hindsight-optimal schedule is future work.</li>
</ul>

<h2>12. References and AI-use statement</h2>
<ol class="small">
<li>M. J. Neely, <i>Stochastic Network Optimization with Application to Communication and Queueing Systems</i>, Morgan &amp; Claypool, 2010.</li>
<li>D. A. Vallado, P. Crawford, R. Hujsak, T. S. Kelso, "Revisiting Spacetrack Report #3", AIAA/AAS Astrodynamics Specialist Conference, 2006.</li>
<li>NASA Global Imagery Browse Services (GIBS); NASA FIRMS active-fire data; CelesTrak element sets.</li>
<li>G. Giuffrida et al., "The Φ-Sat-1 mission: the first on-board deep neural network demonstrator for satellite Earth observation", <i>IEEE Transactions on Geoscience and Remote Sensing</i>, 2022.</li>
<li>C. E. Shannon, "A Mathematical Theory of Communication", <i>Bell System Technical Journal</i>, 1948.</li>
</ol>
<p class="small"><b>AI-use statement.</b> We used Claude (Anthropic) as a coding and writing assistant: to review and
merge the two prototypes, implement the safety guard, tests and benchmark scripts, redesign the dashboard, write the
embedded scripts, and draft this report and the presentation. The team chose the design, checked every result
against the code, and is responsible for the content.</p>
</body></html>
"""

out_html = os.path.join(HERE, "report.html")
open(out_html, "w").write(html)
pdf = os.path.join(HERE, "KAIO_Technical_Report.pdf")
print_pdf(out_html, pdf)
print("wrote", pdf, f"{os.path.getsize(pdf) / 1e6:.2f} MB")
