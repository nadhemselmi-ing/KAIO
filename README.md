# KAIO: process, store, transmit or offload?

**IASTAM 6.0 Technical Challenge · Track 1, Problem 1 "Process or Transmit?"**
KAIO is an onboard decision system for an Earth-observation satellite. Its decision engine is **E-LOTUS**.

A satellite like ESA's Φsat-2 produces far more images than it can send to the ground. Every 10 seconds,
E-LOTUS decides for each stored image whether to **process it onboard now**, **keep it** for later,
**transmit it** during a ground pass, or **offload it** over a laser link to a neighbour in sunlight. It
keeps the battery, the temperature and the storage in check while doing so.

## What is real and what is simulated

| Real | Simulated |
|---|---|
| Orbit of **Φsat-2** (NORAD 60470), CelesTrak TLE, propagated with SGP4 | Battery (RK4) and radiative thermal model |
| 20 days of **NASA** imagery under the real ground track: VIIRS true colour and night IR, VIIRS/FIRMS fires, MODIS cloud fraction, OSM land mask | Image sizes, processing cost, acquisition timing |
| Ground stations: KSAT Svalbard, ASI Matera | 15 W edge-AI computer, 10 Mbps downlink, 100 Mbps laser link, neighbour satellite |

## How KAIO decides (runs every 10 s)

1. **Value.** Estimate each image's worth from two onboard numbers: quick-look entropy (texture) and the land
   fraction of the footprint, looked up in a land/water mask stored onboard. Fire alerts count ×4.
2. **Score.** Each action is scored by how much it grows three "debts" (storage backlog, battery below an
   eclipse-aware floor, heat above 45 °C) minus V × value delivered, per second of resource used. This is the
   drift-plus-penalty rule from Lyapunov optimisation. We use it as a principled heuristic, **not** as a proof:
   the textbook guarantee needs assumptions a real orbit does not meet.
3. **Guard.** An independent **SafetyGuard** vetoes any job that would leave the battery below the energy
   needed to survive the next eclipse, or end above 45 °C. Fire alerts may use the margin up to the 60 °C
   hardware limit.
4. **Explain.** Every started job logs a one-line reason built only from onboard data.

## Results (20 real days, each an independent 24-h run; mean ± 95 % CI)

"% reachable" is the value delivered as a share of what the ground-contact geometry allows (every image sent at
its first pass, with infinite resources).

| Controller | % reachable | Completion | Alerts on time | Min battery | Time > 45 °C | Load-shed | E-LOTUS better on |
|---|---|---|---|---|---|---|---|
| **E-LOTUS** | **85.3 ± 0.6** | 71.9 % | 72.7 % | 69 % | 0.1 % | 0 | — |
| Rule-Based (same value estimate) | 81.5 ± 0.7 | 47.8 % | 72.8 % | 68 % | 0.0 % | 0 | 20 / 20 days |
| Bandwidth-Rules | 81.6 ± 0.8 | 47.7 % | 72.8 % | 68 % | 0.0 % | 0 | 20 / 20 days |
| Store-and-Forward | 41.1 ± 2.4 | 7.5 % | 63.7 % | 69 % | 0 | 0 | 20 / 20 days |
| Greedy-Process | 31.0 ± 3.5 | 47.2 % | 21.4 % | 19 % | 53.4 % | 18.5 % | 20 / 20 days |
| Always-Transmit | 2.1 ± 0.5 | 7.4 % | 0 % | 69 % | 0 | 0 | 20 / 20 days |

### Stress tests: one resource degraded, nothing retuned

| Scenario | E-LOTUS | Best rule engine | Verdict |
|---|---|---|---|
| Solar array −30 % | 83.3 | 81.1 | win, 20/20 days |
| Small battery (40 Wh) + solar −30 % | 80.1 | 2.9 | win: the rules' fixed 50 % battery threshold now equals the shutdown floor, so they load-shed 53 % of the time |
| Storage ÷ 3 | 86.6 | 81.6 | win: storage barely matters, because the images that get deleted are low-value ones |
| Downlink ÷ 2, 20° mask | 84.5 | 80.5 | win, 20/20 days |
| Fire season (3× alerts) | 86.8 | 84.5 | win, 20/20 days |
| GPU 2.5× slower | 79.6 | 80.6 | **loss**: the rule engine runs above 45 °C for 37 % of the day |
| Radiator −25 % | 71.2 | 79.8 | **loss**: the rule engine runs above 45 °C for 81 % of the day. With the 60 °C limit allowed for every job, E-LOTUS reaches 82.1 |

Every point a rule engine wins back, it buys by running hotter than the limit KAIO respects.

### Ablations (what each part is worth)

| Remove… | Nominal | Solar −30 % | Battery 40 Wh | Radiator −25 % |
|---|---|---|---|---|
| nothing (E-LOTUS) | 85.3 | 83.3 | 80.1 | 71.2 |
| entropy (land mask only) | 87.1 | 78.3 | 66.3 | 69.3 |
| land mask (raw entropy only) | 83.5 | 51.7 | 41.7 | 63.4 |
| laser-link offload | 83.7 | 81.6 | 77.8 | 67.0 |
| eclipse-aware battery floor | 85.3 | 82.9 | 79.2 | 71.2 |

The land mask is the key ingredient. Entropy adds value only when resources are scarce. In the nominal case
the land mask alone is slightly better, because there is enough energy to process every land scene.

## Real-life deployment

Every input already exists on a real satellite: battery and temperature housekeeping, the pass schedule
(computed on the ground and uploaded in advance), a static land/water mask indexed by GNSS position, and a
thumbnail entropy computed in about 15 µs. The engine needs only `numpy` and `sgp4`: no GPU and no training.
`onboard/` runs it on a Raspberry Pi and measures decision time, CPU and memory. See `onboard/README_PI.md`.

On a laptop, one decision takes 0.16 ms (median) and the engine uses 0.002 % of one core over a real day.

## Quick start

```bash
pip install -r requirements.txt
python -m pytest -q                      # 18 tests: physics, guard, engine never reads ground truth, bookkeeping
python benchmark.py                      # 8 scenarios x 6 controllers x 20 real days (~17 min on 2 cores)
python web/build_web_data.py             # dashboard scenarios (~10 min)
python web/pack_page.py                  # -> web/KAIO_Mission_Control.html (one file, works offline)
python onboard/pi_benchmark.py           # engine cost on this computer / on the Pi
python onboard/live_demo.py              # live decision feed for the pitch
streamlit run app.py                     # interactive what-if explorer
```

## Repository map

| Path | Contents |
|---|---|
| `kaio/config.py` | Every numeric assumption (`SimConfig`) |
| `kaio/orbit.py` | SGP4 orbit, RK4/J2 cross-check, eclipses, contacts, laser-link geometry |
| `kaio/estimator.py` | Onboard value estimate (entropy × land mask) |
| `kaio/workload.py` | Image stream from the real NASA atlas (hidden ground truth for scoring only) |
| `kaio/physics.py` | Battery and thermal model |
| `kaio/safety.py` | SafetyGuard (independent veto) |
| `kaio/engine.py` | E-LOTUS decision engine and explanations |
| `kaio/baselines.py` | Always-Transmit, Greedy-Process, Store-and-Forward, Rule-Based, Bandwidth-Rules |
| `kaio/simulator.py` | Mission simulator, telemetry, metrics |
| `kaio/scenarios.py` | Stress scenarios |
| `tests/` | pytest suite |
| `onboard/` | Raspberry Pi benchmark and live demo |
| `web/` | Dashboard builder, template, textures, offline three.js |
| `results/` | `summary.json`, `summary.md`, per-run CSV, real-data statistics |
| `data/` | TLE, NASA atlas, sampler script |
| `archive/phase2/` | Phase-2 paper and engine, kept for reference (its numbers come from the older engine) |

## What changed in the merge

KAIO merges the team's two prototypes: **E-LOTUS** (real orbit, real NASA data, Lyapunov engine, mission-control
dashboard) and **satsched** by @Mahmoud35amri (value-aware pricing engine, tested package, calibrated scenarios,
explanations).

| Change | From | Why |
|---|---|---|
| Split the 1,400-line engine into a package with one job per module | satsched | Reviewable like flight software |
| Test suite, including "the engine never reads the hidden ground truth" | satsched | Proves the comparison is fair |
| Independent SafetyGuard; 45 °C is now enforced, not only penalised | new | The old engine ran above 45 °C 10 % of the time |
| One-line explanation for every decision | satsched | Operators must be able to audit decisions |
| Value-aware deletion when storage is full (low value per MB first) | satsched "drop" | Explicit, sensible drop rule. Rule-Based gets the same rule, for fairness |
| Bandwidth-Rules baseline | satsched | A stronger, independent baseline |
| One stress scenario per resource, 20 days each, 95 % CI, days won | satsched | Honest statistics, including losses |
| Dashboard renamed KAIO, three.js embedded | new | One name everywhere; works without internet |
| Raspberry Pi benchmark and live demo | new | Shows the engine fits on embedded hardware |

## Limitations

- The spacecraft (power, thermal, compute, link rates) and the value model are modelled, not a real mission.
  The ground-truth value of a scene (land, cloud-free, fire) is our assumption.
- Pass and eclipse forecasts come from the same propagated orbit, so they are perfect. Real forecasts are
  very good but not perfect.
- The neighbour satellite for laser-link offload is modelled. Removing it costs 1.6–4.2 points.
- Compared with heuristics, not with a hindsight-optimal schedule.
