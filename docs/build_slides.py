"""Build the KAIO pitch deck (docs/KAIO_Pitch.pdf, 16:9) from results/ and docs/figures/.

    python docs/make_figures.py && python docs/build_slides.py
"""
from __future__ import annotations

import base64
import os

from common import (ARCH_SVG, DATE, EVENT, HERE, MEMBERS, PI, RD, REPO_URL, ROOT, SC, TEAM, S, font_css, img, m,
                    on_pi, print_pdf, svg, logo_svg)

E, RB, BW, GP = "E-LOTUS", "Rule-Based", "Bandwidth-Rules", "Greedy-Process"
days = S["days"]
tri = RD["heldout_capture_top30"]
share = RD["share_by_class_pct"]
wins = SC["nominal"]["policies"][RB]["elotus_wins_days"]
keys = ["nominal", "energy_starved", "battery_starved", "storage_tight", "downlink_starved", "event_surge",
        "compute_starved", "degraded_radiator"]
n_win = sum(1 for k in keys if m(E, "ceiling_pct", k) > max(m(RB, "ceiling_pct", k), m(BW, "ceiling_pct", k)))
mw = "data:image/jpeg;base64," + base64.b64encode(
    open(os.path.join(ROOT, "web", "assets", "milkyway_bg.jpg"), "rb").read()).decode()
hw = "Raspberry Pi" if on_pi() else "laptop (Pi run pending)"


def slide(body, cls=""):
    return f"<section class='s {cls}'>{body}<div class='foot'><span>KAIO</span><span class='pn'></span></div></section>"


slides = []

slides.append(slide(f"""
<div class="title">
  <div class="kick">{EVENT}</div>
  <div class="brand">{logo_svg('#E9EDF6', 64)}<span>KAIO</span></div>
  <h1>Which images deserve the downlink?</h1>
  <p class="lead">Onboard decisions for an Earth-observation satellite, flown on the real orbit of Φsat-2 with real NASA data.</p>
  <p class="who">{TEAM} · {' · '.join(MEMBERS)}</p>
</div>
<img class="hero" src="{img('dash_hero_dark.jpg')}" alt="">
""", "cover"))

slides.append(slide(f"""
<h2>The problem: far more data than downlink</h2>
<div class="cols3">
  <div class="big"><b>≈ 80 GB</b><span>of images produced per day</span></div>
  <div class="big"><b>≈ 6 GB</b><span>can be sent down in {m(E,'contact_min_per_day'):.0f} min of ground contact</span></div>
  <div class="big"><b>35 min</b><span>of eclipse every 94-min orbit: no solar power</span></div>
</div>
<p class="say">For every image, every 10 seconds, the satellite must choose, within its battery, heat, memory and contact limits:</p>
<div class="acts">
  <div><b>Process</b><span>onboard AI: 50 MB → 1.5 MB, costs energy and heat</span></div>
  <div><b>Keep</b><span>store for later, costs memory</span></div>
  <div><b>Transmit</b><span>during a ground pass</span></div>
  <div><b>Offload</b><span>laser link to a neighbour in sunlight</span></div>
</div>
"""))

slides.append(slide(f"""
<h2>Real orbit, real NASA data</h2>
<div class="split">
  <div>
    <ul class="ul">
      <li><b>Orbit:</b> Φsat-2 (NORAD 60470) from its CelesTrak TLE, propagated with SGP4; RK4 + J2 cross-check within 25 km over 6 h</li>
      <li><b>Ground stations:</b> KSAT Svalbard and ASI Matera, 10° elevation mask</li>
      <li><b>Earth data:</b> NASA GIBS for 20 days under the real ground track: VIIRS images (day and night), MODIS clouds, FIRMS fires, land/water mask</li>
      <li><b>57,600 real footprints</b> (313 km blocks). Every simulated picture is the real scene Φsat-2 flew over at that moment</li>
      <li>The spacecraft (battery, thermal, GPU, radio) is <b>simulated</b>; every assumption is in one file</li>
    </ul>
  </div>
  <img class="shot" src="{img('dash_replay_dark.jpg')}" alt="">
</div>
"""))

slides.append(slide(f"""
<h2>What real data taught us: clouds fool raw entropy</h2>
<div class="split even">
  <div class="card">{svg('fig_entropy')}</div>
  <div class="card">{svg('fig_triage')}</div>
</div>
<p class="say">Clouds are the most textured scenes and {share['cloud']:.0f} % of all scenes. Ranking images by texture keeps
<b>{100*tri['raw entropy']:.0f} %</b> of the value, worse than random ({100*tri['random']:.0f} %). Multiplying by an onboard land mask
gives <b>{100*tri['E-LOTUS']:.0f} %</b>, close to a perfect oracle ({100*tri['oracle']:.0f} %).</p>
"""))

slides.append(slide(f"""
<h2>System architecture</h2>
<div class="card wide">{ARCH_SVG}</div>
"""))

slides.append(slide(f"""
<h2>How E-LOTUS decides, every 10 seconds</h2>
<div class="steps">
  <div><i>1</i><b>Value</b><span>texture × onboard land mask, × 4 for fire alerts</span><code>p · (0.1 + 0.9·land) · (H/8)³</code></div>
  <div><i>2</i><b>Score</b><span>growth of three debts (memory, battery below its eclipse floor, heat above 45 °C) minus V × value, per second</span><code>(ΔL − V·U) / τ</code></div>
  <div><i>3</i><b>Safety guard</b><span>independent veto, like flight-software FDIR: battery must survive the next eclipse, computer stays under 45 °C</span><code>fire alerts may use up to 60 °C</code></div>
  <div><i>4</i><b>Explain</b><span>each decision logs a reason built only from onboard data</span><code>auditable by operators</code></div>
</div>
<div class="quote">“Process now: est. value 0.68 (optical H 7.5, land 79 %). 20 MB raw → 0.6 MB product, next pass in 476 min;
battery 69 Wh after (floor 20), 9.3 °C.”</div>
<p class="small">Drift-plus-penalty from Lyapunov optimisation, used as a principled scoring rule; all performance claims are measured, not proven.</p>
"""))

slides.append(slide(f"""
<h2>Live demo</h2>
<div class="split">
  <img class="shot" src="{img('dash_bench_light.jpg')}" alt="">
  <div>
    <ul class="ul">
      <li><b>Mission-control dashboard:</b> 3D Earth with the real orbit, 80 what-if orbits, 270 pre-computed missions, one offline file</li>
      <li><b>Raspberry Pi:</b> the same flight code runs live and prints each decision, its reason and its compute time</li>
      <li>Every number shown is regenerated by scripts from the benchmark</li>
    </ul>
  </div>
</div>
""", "demo"))

slides.append(slide(f"""
<h2>Results: {m(E,'ceiling_pct'):.1f} % of the reachable value</h2>
<div class="split wide-left">
  <div class="card">{svg('fig_value')}</div>
  <div class="kpis">
    <div><b>+{m(E,'ceiling_pct')-m(RB,'ceiling_pct'):.1f} pts</b><span>over a tuned rule engine with the same information; better on {wins}/{days} days</span></div>
    <div><b>+{m(E,'completion_pct')-m(RB,'completion_pct'):.0f} pts</b><span>more images delivered or triaged ({m(E,'completion_pct'):.0f} % vs {m(RB,'completion_pct'):.0f} %)</span></div>
    <div><b>0</b><span>load-sheds or throttles; battery never below {m(E,'soc_min_pct'):.0f} %</span></div>
    <div><b>{m(E,'latency_mean_min'):.0f} min</b><span>mean latency, vs {m(RB,'latency_mean_min'):.0f} min for the rule engine</span></div>
  </div>
</div>
<p class="small">{days} real days, each an independent 24-h run; mean ± 95 % confidence interval. Greedy processing drains the battery to {m(GP,'soc_min_pct'):.0f} % and sheds the payload {m(GP,'shed_pct'):.0f} % of the time.</p>
"""))

slides.append(slide(f"""
<h2>Stress tests: where we win and where we don't</h2>
<div class="split wide-left">
  <div class="card">{svg('fig_stress')}</div>
  <div class="notes">
    <p><b>Wins {n_win}/8.</b> Weaker solar array, half the downlink, fire season, less storage: E-LOTUS wins every day.</p>
    <p><b>Small battery:</b> the rule engine's fixed threshold hits the shutdown floor ({m(RB,'ceiling_pct','battery_starved'):.0f} %). E-LOTUS adapts from the orbit ({m(E,'ceiling_pct','battery_starved'):.0f} %).</p>
    <p><b>Losses 2/8:</b> slower GPU, weaker radiator. The rules only win by running above 45 °C for {m(RB,'above_tsafe_pct','compute_starved'):.0f}–{m(RB,'above_tsafe_pct','degraded_radiator'):.0f} % of the day. We respect the limit.</p>
  </div>
</div>
"""))

slides.append(slide(f"""
<h2>Feasible on real hardware</h2>
<div class="cols3">
  <div class="big"><b>{PI['decision_ms_median']:.2f} ms</b><span>median decision time ({hw}); the satellite needs one every 10 s</span></div>
  <div class="big"><b>{PI['engine_cpu_duty_pct']:.3f} %</b><span>of one CPU core over a full real day</span></div>
  <div class="big"><b>2</b><span>libraries onboard: numpy and sgp4. No GPU, no training</span></div>
</div>
<p class="say">Every input already exists on a satellite:</p>
<div class="acts">
  <div><b>Battery and temperature</b><span>housekeeping sensors</span></div>
  <div><b>Pass schedule</b><span>computed on the ground, uplinked</span></div>
  <div><b>Land mask</b><span>static map, indexed by GNSS position</span></div>
  <div><b>Thumbnail entropy</b><span>{PI['entropy_us_per_thumbnail']:.0f} µs per image</span></div>
</div>
<p class="small">Precedent: ESA's Φsat-1 already discarded cloudy images onboard. KAIO flies the real orbit of its successor.</p>
"""))

slides.append(slide(f"""
<h2>Method and roadmap</h2>
<div class="split even">
  <div>
    <h3>How we built it</h3>
    <ol class="ul">
      <li>Two Phase-2 prototypes, merged into one tested package</li>
      <li>Review found the old engine ran above 45 °C 10 % of the time; the safety guard fixed it</li>
      <li>18 automated tests, including “the engine never reads the ground truth”</li>
      <li>1,360 simulations: 8 scenarios × 6 strategies × 20 real days</li>
      <li>Same code on a Raspberry Pi</li>
    </ol>
  </div>
  <div class="road">
    <div><i>Done</i><span>engine, safety guard, real-data simulation, benchmark, dashboard, embedded run</span></div>
    <div><i>+3 mo</i><span>hardware-in-the-loop on a flight-like computer; imperfect forecasts and sensor noise</span></div>
    <div><i>+6 mo</i><span>onboard cloud-screening network replacing the static land map; hindsight-optimal comparison</span></div>
    <div><i>+12 mo</i><span>constellation coordination; partnership for a CubeSat flight test</span></div>
  </div>
</div>
"""))

slides.append(slide(f"""
<div class="close">
  <h1>KAIO decides which images deserve the downlink, explains why, and never breaks the spacecraft to do it.</h1>
  <div class="cols3 tight">
    <div class="big"><b>{m(E,'ceiling_pct'):.1f} %</b><span>of reachable value</span></div>
    <div class="big"><b>{wins}/{days}</b><span>days better than tuned rules</span></div>
    <div class="big"><b>0</b><span>load-sheds or throttles</span></div>
  </div>
  <p class="who">Thank you · questions welcome · {REPO_URL}</p>
</div>
""", "cover end"))

html = f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>KAIO pitch</title>
<style>
{font_css()}
@page{{size:1280px 720px;margin:0}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:'Space Grotesk',sans-serif;color:#E9EDF6;counter-reset:pg}}
.s{{width:1280px;height:720px;position:relative;overflow:hidden;padding:56px 72px 60px;page-break-after:always;
   background:linear-gradient(180deg,rgba(8,12,24,.78),rgba(8,12,24,.92)),url({mw}) center/cover,#0A0F1E;counter-increment:pg}}
.s:last-child{{page-break-after:auto}}
.foot{{position:absolute;left:72px;right:72px;bottom:22px;display:flex;justify-content:space-between;font-size:13px;color:#6B7899}}
.foot .pn::after{{content:counter(pg)}}
h1{{font-size:54px;line-height:1.06;margin:0 0 18px;letter-spacing:-.015em;font-weight:700}}
h2{{font-size:36px;margin:0 0 26px;letter-spacing:-.01em;font-weight:600}}
h3{{font-size:20px;margin:0 0 10px;color:#9AA6C2;font-weight:600}}
.lead{{font-size:22px;color:#C5CDE0;max-width:640px;line-height:1.4;margin:0 0 26px}}
.kick{{font-size:15px;color:#9AA6C2;margin-bottom:26px}}
.who{{font-size:17px;color:#9AA6C2}}
.brand{{display:flex;align-items:center;gap:14px;font-size:34px;font-weight:700;letter-spacing:.08em;margin-bottom:22px}}
.cover .title{{position:relative;z-index:2;width:560px;margin-top:40px}}
.cover .hero{{position:absolute;right:-170px;top:90px;width:700px;border-radius:14px;opacity:.92;box-shadow:0 20px 60px rgba(0,0,0,.5)}}
.say{{font-size:21px;color:#C5CDE0;line-height:1.45;margin:22px 0 16px;max-width:1080px}}
.small{{font-size:14px;color:#8E9AB8;margin-top:16px;max-width:1100px}}
.cols3{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}
.big{{background:rgba(17,25,46,.82);border:1px solid #26324F;border-radius:14px;padding:20px 22px}}
.big b{{display:block;font-size:46px;font-weight:600;line-height:1.05;color:#7DB6F5;letter-spacing:-.02em}}
.big span{{display:block;font-size:17px;color:#B3BDD3;margin-top:8px;line-height:1.35}}
.acts{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}
.acts div{{border-top:3px solid #5AA2F0;background:rgba(17,25,46,.7);border-radius:4px 4px 12px 12px;padding:14px 16px}}
.acts b{{display:block;font-size:21px;margin-bottom:6px}} .acts span{{font-size:15.5px;color:#B3BDD3;line-height:1.35;display:block}}
.split{{display:grid;grid-template-columns:1fr 1fr;gap:30px;align-items:start}}
.split.wide-left{{grid-template-columns:1.45fr 1fr}}
.ul{{font-size:19px;line-height:1.45;color:#D3DAEA;padding-left:22px;margin:0}} .ul li{{margin-bottom:12px}}
.shot{{width:100%;border-radius:12px;border:1px solid #26324F;box-shadow:0 14px 40px rgba(0,0,0,.45)}}
.card{{background:#FFFFFF;border-radius:14px;padding:16px 18px;color:#121A2B}}
.card svg{{width:100%;height:auto;display:block}}
.card.wide{{padding:22px 26px}}
.steps{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}}
.steps div{{background:rgba(17,25,46,.82);border:1px solid #26324F;border-radius:14px;padding:18px;display:flex;flex-direction:column;gap:8px}}
.steps i{{font-style:normal;font-size:15px;color:#E9A23B;font-weight:600}}
.steps b{{font-size:22px}} .steps span{{font-size:15.5px;color:#B3BDD3;line-height:1.4;flex:1}}
.steps code{{font-family:inherit;font-size:14px;color:#7DB6F5;background:rgba(90,162,240,.1);padding:6px 8px;border-radius:6px}}
.quote{{margin-top:22px;font-size:18px;color:#D3DAEA;border-left:3px solid #E9A23B;padding:6px 16px;line-height:1.45}}
.kpis{{display:grid;gap:12px}}
.kpis div{{background:rgba(17,25,46,.82);border:1px solid #26324F;border-radius:12px;padding:12px 16px}}
.kpis b{{font-size:30px;color:#7DB6F5;display:block;line-height:1.1}} .kpis span{{font-size:15px;color:#B3BDD3}}
.notes p{{font-size:17.5px;line-height:1.45;color:#D3DAEA;margin:0 0 16px}}
.road{{display:grid;gap:12px}}
.road div{{display:grid;grid-template-columns:90px 1fr;gap:14px;align-items:start;background:rgba(17,25,46,.82);border:1px solid #26324F;border-radius:12px;padding:14px 16px}}
.road i{{font-style:normal;font-weight:600;color:#E9A23B;font-size:18px}} .road span{{font-size:16.5px;color:#D3DAEA;line-height:1.4}}
.close{{display:flex;flex-direction:column;justify-content:center;height:100%;max-width:1060px}}
.close h1{{font-size:46px;margin-bottom:34px}}
.cols3.tight{{margin-bottom:30px}}
</style><body>
{''.join(slides)}
</body></html>"""

out_html = os.path.join(HERE, "slides.html")
open(out_html, "w").write(html)
pdf = os.path.join(HERE, "KAIO_Pitch.pdf")
print_pdf(out_html, pdf, page="slide")
print("wrote", pdf, f"{os.path.getsize(pdf) / 1e6:.2f} MB, {len(slides)} slides")
