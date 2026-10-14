"""Pack web/kaio_template.html + web/kaio_data.json + Earth textures + three.js into ONE self-contained page
that works offline (no internet needed in the pitch room).
Run after build_web_data.py:   python web/pack_page.py
"""
import base64
import gzip
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from kaio import SimConfig, build_ephemeris  # noqa: E402

D = json.load(open(os.path.join(HERE, "kaio_data.json")))
# benchmark tables and Pi numbers are refreshed from results/ without re-running the replay simulations
_S = json.load(open(os.path.join(os.path.dirname(HERE), "results", "summary.json")))
D["main"], D["main_ci"], D["days"] = _S["main"], _S["main_ci"], _S["days"]
D["scen"] = {s: dict(label=b["label"], pol={p: {**{k: v for k, v in d.items() if isinstance(v, list)},
                                                "wins": d["elotus_wins_days"], "n": d["n_days"]}
                                            for p, d in b["policies"].items()})
             for s, b in _S["scenarios"].items()}
_pi = os.path.join(os.path.dirname(HERE), "results", "pi_benchmark.json")
if os.path.exists(_pi):
    D["pi"] = json.load(open(_pi))
G = D["grid"]


def fk(x):
    return str(x)


rep = {}
for key, v in D["replay"].items():
    parts = key.split("|")
    if parts[0] == "E-LOTUS":
        _, V, s, k, st, i = parts
        rep["e_%d_%d_%d_%d_%d" % (G["V"].index(float(V)), G["soc"].index(int(s)), G["k"].index(float(k)),
                                  G["st"].index(int(st)), G["isl"].index(int(i)))] = v
    else:
        p, s, k, st, i = parts
        tag = "gp" if p == "Greedy-Process" else "rb"
        rep["%s_%d_%d_%d_%d" % (tag, G["soc"].index(int(s)), G["k"].index(float(k)),
                                G["st"].index(int(st)), G["isl"].index(int(i)))] = v
orb = {}
for key, v in D["orbits"].items():
    if key == "real":
        orb["real"] = v
    else:
        inc, lt = key.split("|")
        orb["o_%d_%d" % (G["inc"].index(float(inc)), G["ltan"].index(float(lt)))] = v
D["replay"], D["orbits"] = rep, orb

# real orbit plane: inclination and ascending-node local time
c = SimConfig()
e = build_ephemeris(c, extra_h=0.0)
h = np.cross(e.r[0], e.v[0])
node = np.cross([0.0, 0.0, 1.0], h)
raan = math.degrees(math.atan2(node[1], node[0]))
ra_sun = math.degrees(math.atan2(e.sun[0, 1], e.sun[0, 0]))
D["real_orbit"] = dict(inc=round(math.degrees(math.acos(h[2] / np.linalg.norm(h))), 2),
                       ltan=round(((raan - ra_sun) / 15.0 + 12.0) % 24.0, 3), alt=G["alt"])

def _clean(x):
    """JSON has no NaN: turn NaN/inf into null so the browser can parse the data."""
    if isinstance(x, float) and not math.isfinite(x):
        return None
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_clean(v) for v in x]
    return x


D = _clean(D)
blob = base64.b64encode(gzip.compress(json.dumps(D, separators=(",", ":"), allow_nan=False).encode(), 9)).decode()


def uri(name, mime="image/jpeg"):
    return f"data:{mime};base64," + base64.b64encode(open(os.path.join(HERE, "assets", name), "rb").read()).decode()


html = open(os.path.join(HERE, "kaio_template.html")).read()
LATIN = "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD"
LATIN_EXT = "U+0100-02AF,U+0304,U+0308,U+0329,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF"
FONTS = [("Space Grotesk", w, f"space-grotesk-latin-{w}-normal.woff2", LATIN) for w in (400, 500, 600, 700)]
FONTS += [("Space Grotesk", w, f"space-grotesk-latin-ext-{w}-normal.woff2", LATIN_EXT) for w in (400, 600)]
font_css = "\n".join(
    "@font-face{font-family:'Instrument Serif';font-style:%s;font-weight:400;font-display:swap;src:url(data:font/woff2;base64,%s) format('woff2')}"
    % (st, base64.b64encode(open(os.path.join(HERE, "assets", "fonts", f"instrument-serif-latin-400-{st}.woff2"), "rb").read()).decode())
    for st in ("normal", "italic")) + "\n" + "\n".join(
    "@font-face{font-family:'%s';font-style:normal;font-weight:%d;font-display:swap;src:url(data:font/woff2;base64,%s) format('woff2');unicode-range:%s}"
    % (fam, w, base64.b64encode(open(os.path.join(HERE, "assets", "fonts", fn), "rb").read()).decode(), rng)
    for fam, w, fn, rng in FONTS)
three = open(os.path.join(HERE, "assets", "three.min.js")).read()
for face in ("px", "nx", "py", "ny", "pz", "nz"):
    html = html.replace(f"__SKY_{face.upper()}__", uri(f"sky/{face}.jpg"))
html = (html.replace("__MILKYWAY__", uri("milkyway_bg.jpg")).replace("__EARTH_LIGHT__", uri("earth_light_bg.jpg")).replace("__EARTH_CLOUDS__", uri("earth_clouds_alpha.jpg"))
            .replace("/*__FONTS__*/", font_css).replace("/*__I18N__*/", open(os.path.join(HERE, "i18n.js")).read()).replace("__DATA__", blob)
            .replace("__EARTH_DAY__", uri("earth_day_2k.jpg"))
            .replace("__EARTH_NIGHT__", uri("earth_night_2k.jpg"))
            .replace("__EARTH_MAP__", uri("earth_day_1k.jpg"))
            .replace('<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>',
                     "<script>" + three + "</script>"))
out = os.path.join(HERE, "KAIO_Mission_Control.html")
open(out, "w").write(html)
print(f"wrote {out}: {os.path.getsize(out) / 1e6:.2f} MB (data {len(blob) / 1e6:.2f} MB)")
