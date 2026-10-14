"""Shared helpers for the report and the slides: numbers from results/, fonts, figures, PDF printing."""
from __future__ import annotations

import base64
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIG = os.path.join(HERE, "figures")

# --- edit these if needed ----------------------------------------------------------------
TEAM = "Team KAIO"
MEMBERS = ["Nadhem Selmi", "Mahmoud Amri"]
EVENT = "IASTAM 6.0 Technical Challenge · Track 1 · Problem 1 “Process or Transmit?”"
REPO_URL = "github.com/<team>/kaio"          # replace with the submitted repository
DATE = "15 October 2026"
# ------------------------------------------------------------------------------------------

S = json.load(open(os.path.join(ROOT, "results", "summary.json")))
RD = json.load(open(os.path.join(ROOT, "results", "realdata_stats.json")))
PI = json.load(open(os.path.join(ROOT, "results", "pi_benchmark.json")))
ABL = json.load(open(os.path.join(FIG, "ablation.json")))["ablation"]
SC = S["scenarios"]
NOM = SC["nominal"]["policies"]


def m(policy, key, scen="nominal", ci=False):
    v = SC[scen]["policies"][policy][key]
    return v if ci else v[0]


def svg(name):
    return open(os.path.join(FIG, name + ".svg")).read().split("?>", 1)[-1]


def img(name):
    data = base64.b64encode(open(os.path.join(FIG, name), "rb").read()).decode()
    return f"data:image/jpeg;base64,{data}"


def font_css():
    out = []
    for w in (400, 500, 600, 700):
        p = os.path.join(ROOT, "web", "assets", "fonts", f"space-grotesk-latin-{w}-normal.woff2")
        b = base64.b64encode(open(p, "rb").read()).decode()
        out.append(f"@font-face{{font-family:'Space Grotesk';font-weight:{w};src:url(data:font/woff2;base64,{b}) format('woff2')}}")
    return "\n".join(out)


def on_pi():
    return any(k in (PI.get("board", "") + PI.get("machine", "")).lower() for k in ("raspberry", "aarch64", "arm"))


def print_pdf(html_path, pdf_path, landscape=False, page="A4"):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto("file://" + html_path)
        pg.wait_for_timeout(800)
        if page == "slide":
            pg.pdf(path=pdf_path, width="1280px", height="720px", print_background=True,
                   margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        else:
            pg.pdf(path=pdf_path, format=page, landscape=landscape, print_background=True,
                   margin={"top": "16mm", "right": "16mm", "bottom": "16mm", "left": "16mm"},
                   display_header_footer=True,
                   header_template="<span></span>",
                   footer_template="<div style='font-size:8px;color:#8C97AC;width:100%;text-align:center;font-family:sans-serif'>"
                                   "KAIO · technical report · page <span class='pageNumber'></span> of <span class='totalPages'></span></div>")
        b.close()


ARCH_SVG = """
<svg viewBox="0 0 960 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="KAIO system architecture"
     style="width:100%;height:auto;font-family:'Space Grotesk',sans-serif">
  <defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="#55617A"/></marker></defs>
  <style>
    .bx{fill:#FFFFFF;stroke:#C9D3E3;stroke-width:1.2}
    .hd{font-size:13px;font-weight:700;fill:#121A2B}
    .tx{font-size:11px;fill:#55617A}
    .ln{stroke:#55617A;stroke-width:1.4;fill:none;marker-end:url(#ar)}
    .zone{font-size:11px;font-weight:600;fill:#8C97AC;letter-spacing:.04em}
  </style>
  <text x="10" y="16" class="zone">REAL INPUTS</text>
  <text x="250" y="16" class="zone">SIMULATED SPACECRAFT</text>
  <text x="500" y="16" class="zone">ONBOARD FLIGHT LOGIC (runs every 10 s)</text>
  <text x="810" y="16" class="zone">ACTIONS</text>

  <rect class="bx" x="10" y="28" width="210" height="72" rx="8"/>
  <text x="22" y="50" class="hd">Real orbit</text>
  <text x="22" y="68" class="tx">Phi-sat-2 TLE (CelesTrak)</text>
  <text x="22" y="84" class="tx">SGP4, RK4 + J2 cross-check</text>

  <rect class="bx" x="10" y="112" width="210" height="88" rx="8"/>
  <text x="22" y="134" class="hd">Real Earth data</text>
  <text x="22" y="152" class="tx">NASA GIBS: VIIRS images,</text>
  <text x="22" y="168" class="tx">MODIS clouds, FIRMS fires,</text>
  <text x="22" y="184" class="tx">OSM land mask · 57,600 samples</text>

  <rect class="bx" x="10" y="212" width="210" height="56" rx="8"/>
  <text x="22" y="234" class="hd">Ground stations</text>
  <text x="22" y="252" class="tx">Svalbard, Matera · 10° mask</text>

  <rect class="bx" x="250" y="28" width="220" height="240" rx="8"/>
  <text x="262" y="50" class="hd">Spacecraft model</text>
  <text x="262" y="72" class="tx">Battery 100 Wh (RK4)</text>
  <text x="262" y="90" class="tx">Body-mounted solar panels</text>
  <text x="262" y="108" class="tx">Radiative thermal node</text>
  <text x="262" y="126" class="tx">Edge GPU 15 W</text>
  <text x="262" y="144" class="tx">Storage 8 GB</text>
  <text x="262" y="162" class="tx">Downlink 10 Mbps</text>
  <text x="262" y="180" class="tx">Laser link 100 Mbps</text>
  <text x="262" y="210" class="hd" style="font-size:12px">Telemetry to the engine</text>
  <text x="262" y="228" class="tx">battery, temperature, backlog,</text>
  <text x="262" y="244" class="tx">sun/eclipse, pass schedule,</text>
  <text x="262" y="260" class="tx">new image features</text>

  <rect x="500" y="28" width="280" height="240" rx="10" fill="#EEF4FD" stroke="#1E63C4" stroke-width="1.6"/>
  <text x="514" y="50" class="hd" style="fill:#1E63C4">E-LOTUS decision engine</text>
  <rect class="bx" x="514" y="62" width="252" height="40" rx="6"/>
  <text x="526" y="80" class="hd" style="font-size:12px">1 · Value estimate</text>
  <text x="526" y="95" class="tx">p · (0.1 + 0.9·land) · (H/8)³</text>
  <rect class="bx" x="514" y="108" width="252" height="40" rx="6"/>
  <text x="526" y="126" class="hd" style="font-size:12px">2 · Score every action</text>
  <text x="526" y="141" class="tx">(Δ debts − V · value) / duration</text>
  <rect class="bx" x="514" y="154" width="252" height="40" rx="6"/>
  <text x="526" y="172" class="hd" style="font-size:12px">3 · Safety guard (veto)</text>
  <text x="526" y="187" class="tx">eclipse-survival floor, 45 °C limit</text>
  <rect class="bx" x="514" y="200" width="252" height="40" rx="6"/>
  <text x="526" y="218" class="hd" style="font-size:12px">4 · Explain</text>
  <text x="526" y="233" class="tx">one-line reason per decision</text>

  <rect class="bx" x="810" y="28" width="140" height="50" rx="8"/><text x="822" y="50" class="hd">Process</text><text x="822" y="66" class="tx">GPU, 50 MB → 1.5 MB</text>
  <rect class="bx" x="810" y="88" width="140" height="50" rx="8"/><text x="822" y="110" class="hd">Keep</text><text x="822" y="126" class="tx">store for later</text>
  <rect class="bx" x="810" y="148" width="140" height="50" rx="8"/><text x="822" y="170" class="hd">Transmit</text><text x="822" y="186" class="tx">during a pass</text>
  <rect class="bx" x="810" y="208" width="140" height="60" rx="8"/><text x="822" y="230" class="hd">Offload</text><text x="822" y="246" class="tx">laser link to a</text><text x="822" y="261" class="tx">sunlit neighbour</text>

  <path class="ln" d="M220,64 H250"/><path class="ln" d="M220,156 H250"/><path class="ln" d="M220,240 H250"/>
  <path class="ln" d="M470,148 H500"/>
  <path class="ln" d="M780,53 H810"/><path class="ln" d="M780,113 H810"/><path class="ln" d="M780,173 H810"/><path class="ln" d="M780,238 H810"/>
  <path class="ln" d="M640,268 V292 H360 V272" style="stroke-dasharray:4 3"/>
  <text x="430" y="306" class="tx">actions change battery, heat and storage (closed loop)</text>

  <text x="10" y="340" class="zone">SOFTWARE AROUND IT</text>
  <rect class="bx" x="10" y="352" width="225" height="60" rx="8"/><text x="22" y="374" class="hd">Benchmark</text><text x="22" y="392" class="tx">8 scenarios × 6 strategies</text><text x="22" y="406" class="tx">× 20 real days, 95 % CI</text>
  <rect class="bx" x="250" y="352" width="220" height="60" rx="8"/><text x="262" y="374" class="hd">Tests</text><text x="262" y="392" class="tx">18 automated checks (pytest)</text><text x="262" y="406" class="tx">incl. "never reads ground truth"</text>
  <rect class="bx" x="500" y="352" width="220" height="60" rx="8"/><text x="512" y="374" class="hd">Mission-control dashboard</text><text x="512" y="392" class="tx">one offline HTML file,</text><text x="512" y="406" class="tx">three.js 3D Earth, 270 replays</text>
  <rect class="bx" x="735" y="352" width="215" height="60" rx="8"/><text x="747" y="374" class="hd">Embedded target</text><text x="747" y="392" class="tx">Raspberry Pi: numpy + sgp4,</text><text x="747" y="406" class="tx">timing + live decision feed</text>
</svg>
"""


LOGO_MARK = '<rect x="18" y="8" width="9" height="64" rx="2" fill="{c}"/><path d="M27 42 L58 10" stroke="{c}" stroke-width="9" stroke-linecap="round"/><path d="M37 33 L62 70" stroke="{c}" stroke-width="9" stroke-linecap="round"/><ellipse cx="40" cy="40" rx="36" ry="11" fill="none" stroke="#E9A23B" stroke-width="3.2" transform="rotate(-20 40 40)"/><circle cx="74" cy="28" r="5" fill="#E9A23B"/>'


def logo_svg(color="#121A2B", size=64):
    """KAIO K-orbit mark as inline SVG."""
    return f'<svg width="{size}" height="{size}" viewBox="0 0 80 80" aria-hidden="true">' + LOGO_MARK.format(c=color) + '</svg>'
