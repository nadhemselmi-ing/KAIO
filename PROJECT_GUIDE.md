# KAIO: the complete guide

*Everything about the project in plain words: why it exists, what it does, how it was built, where the
data comes from, and what each part of the code does.*

---

## 1. Why this project exists

An Earth-observation satellite like ESA's **Φsat-2** takes pictures all day. It can only send data to the
ground when it flies over a ground station: about **79 minutes per day**, at a limited speed. It produces
far more data than it can ever send down.

So for every image, the satellite has to choose:

| Action | What it means | Cost |
|---|---|---|
| **Process** | An onboard AI computer turns a 50 MB raw image into a 1.5 MB useful product | battery + heat |
| **Keep** | Leave it in memory for later | memory |
| **Transmit** | Send it to the ground during a pass | radio time + battery |
| **Offload** | Send it by laser to a neighbour satellite that is in sunlight | laser link time |

It has to choose **without draining the battery, without overheating, and without filling the memory**.
This is exactly **IASTAM 6.0, Track 1, Problem 1: "Process or Transmit?"**

**KAIO** is our onboard decision system. **E-LOTUS** is the decision engine inside it.

---

## 2. What it is used for

- **On a real satellite:** KAIO would run on the onboard computer and make this decision every 10 seconds,
  on its own, even when no ground station is in contact.
- **For the competition:** we show, on a real orbit with real NASA data, that KAIO delivers more useful
  information to the ground than the usual strategies, and never puts the spacecraft in danger.
- **For operators on the ground:** every decision comes with a one-line reason, so humans can check what
  the satellite did and why.

---

## 3. The whole system in one picture

```
 REAL DATA (inputs)                  SIMULATED SATELLITE              THE BRAIN
 ─────────────────                   ───────────────────              ─────────
 Φsat-2 orbit (TLE + SGP4)   ──►  where am I? sun or shadow?  ──►
 NASA images under the track ──►  new image arrives (texture,   ──►   E-LOTUS engine
 NASA fires, NASA clouds          land %, fire flag)                  (every 10 s)
 Ground stations              ──►  is a station in view?                │
                                   battery model (RK4)       ◄──────────┤  decision:
                                   thermal model             ◄──────────┤  process / keep /
                                   memory, radio, GPU        ◄──────────┘  transmit / offload
                                          │
                                          ▼
                     RESULTS → benchmark (20 real days) → dashboard + Raspberry Pi demo
```

**Mechatronics view:** it is a closed control loop.
- **Sensors:** battery level, temperature, memory, position, pass schedule.
- **Controller:** E-LOTUS.
- **Actuators:** GPU, radio, laser link.
- **Plant:** the simulated satellite.

---

## 4. The real data: where it comes from and how we treated it

### 4.1 The orbit
- **Source:** the real **TLE** of Φsat-2 (NORAD ID 60470) from **CelesTrak**. A TLE is the standard two-line
  text that describes a satellite's orbit. File: `data/phisat2_tle.txt`.
- **Treatment:** the TLE goes into **SGP4**, the official propagation algorithm used by NORAD and every
  satellite-tracking site. It gives the exact position every 10 seconds: about 472 km altitude, a 94-minute
  orbit, about 35 minutes of eclipse per orbit.
- **Independent check:** we also wrote our own **RK4 integrator with Earth flattening (J2)**. It stays within
  25 km of SGP4 over 6 hours (automatic test `tests/test_orbit.py`).
- From the position we compute, every 10 seconds:
  - **sun or eclipse:** Earth-shadow model plus the sun position,
  - **ground contact:** the satellite must be above 10° of elevation, seen from KSAT **Svalbard** (Norway) or
    ASI **Matera** (Italy),
  - **laser-link line of sight** to neighbour satellites.

### 4.2 The Earth data under the satellite
**Source: NASA GIBS** (Global Imagery Browse Services), NASA's free global imagery service.
**Period:** 20 days, 26 Aug to 14 Sep 2026.

| What | NASA layer | What we extracted |
|---|---|---|
| Daytime images | `VIIRS_NOAA20_CorrectedReflectance_TrueColor` | image texture (Shannon entropy) |
| Night images | `VIIRS_NOAA20_Brightness_Temp_BandI5_Night` | night texture |
| Fires | `VIIRS_NOAA20_Thermal_Anomalies_375m_All` (FIRMS) | number of fire pixels |
| Clouds | `MODIS_Aqua_Cloud_Fraction_Day/Night` | % cloud cover |
| Land / sea | `OSM_Land_Water_Map` | % land |

**How we sampled it** (script `data/gibs_sampler.js`, run in a browser on the NASA GIBS website):
1. Compute Φsat-2's real ground track every 30 seconds for the whole period.
2. For each point, cut a **32 × 32-pixel block (about 313 km)** from NASA's daily global map, exactly under
   the satellite on that day.
3. Summarise each block into a few numbers:
   - **texture:** Shannon entropy of the brightness,
   - **land %**,
   - **cloud %:** decoded from NASA's colour scale back into numbers,
   - **fire pixels**.
4. Save everything in one compact binary file: `data/elotus_gibs_atlas.bin`. It holds 57,600 real footprints.

So when the simulated satellite takes a picture at a given time and place, it gets **the real NASA scene
that was under Φsat-2 at that moment** (`kaio/workload.py`).

### 4.3 The discovery from the real data
The textbook idea is "more texture = more interesting image". On real data, this is **wrong**:
- clouds are the most textured scenes (median entropy 6.9 bit/px), and they cover **64 %** of everything
  the satellite sees;
- ranking images by raw texture keeps only **27 %** of the value in the top 30 %, worse than random (30 %).

**Fix:** multiply the texture by the **land fraction from a map stored onboard**. This reaches **79 %**,
close to a perfect oracle (**82 %**). This is our most original finding.

### 4.4 The hidden "true value" (used only for scoring)
Every image gets a hidden true value: high for clear land, low for cloud or ocean, very high for fires.
**The engine never sees it.** It only sees what a real satellite could see onboard.

An automatic test proves it (`tests/test_engine.py`): if we shuffle the hidden values, the engine makes
exactly the same decisions.

---

## 5. The simulated satellite (modelled, not real)

All numbers live in **`kaio/config.py`**, so anyone can check or challenge them.

| Part | Model |
|---|---|
| Battery | 100 Wh, charge/discharge integrated with **RK4**, charging efficiency and taper near full. Payload is switched off below 20 Wh (load-shed). |
| Solar panels | Body-mounted. Power depends on the angle to the sun; zero in eclipse. |
| Thermal | Single thermal mass. Cools by radiation (**Stefan–Boltzmann**, ∝ T⁴), heats with GPU work, sun and Earth infrared. **45 °C** = operating limit, **60 °C** = hardware throttle. |
| Compute | Jetson-Orin-class GPU, 15 W |
| Links | 10 Mbps downlink, 100 Mbps laser link to a neighbour |
| Memory | 8 GB |

**How to say it in the pitch:** *"Real orbit, real NASA data, simulated spacecraft."*

---

## 6. The brain: how E-LOTUS decides (every 10 seconds)

### Step 1: value
Each image gets an estimated value:
```
value = priority × (0.1 + 0.9 × land) × (entropy / 8)³
```
`priority` is 4 for a fire alert and 1 otherwise. It is computed in microseconds (`kaio/estimator.py`).

### Step 2: score
The engine tracks three "debts" it wants to keep near zero:
- **storage backlog** (memory filling up),
- **energy debt** (battery below what the next eclipse needs),
- **heat debt** (temperature above 45 °C).

For every possible action it computes
```
score = (increase of the debts − V × value delivered) ÷ time the action takes
```
and starts the best one (`kaio/engine.py`).

This comes from **Lyapunov optimisation** ("drift-plus-penalty"). For a mechatronics engineer, it is like a
cost function in optimal control: the Lyapunov part keeps the system stable, and **V** is a single tuning
knob between safety and value. Say *"inspired by Lyapunov optimisation"*, not *"proven optimal"*.

### Step 3: safety guard
A separate layer, like fault protection (FDIR) on real spacecraft (`kaio/safety.py`). Before any job starts,
it predicts:
- **battery:** will it stay above the energy needed to survive the next eclipse?
- **temperature:** will the computer stay under 45 °C? Only fire alerts may go up to 60 °C.

If not, the job is blocked and the reason is logged.

### Step 4: explain
Every decision gets a sentence, for example:
> *Process now: est. value 0.68 (optical H 7.5, land 79%). 20 MB raw → 0.6 MB product, next pass in 476 min;
> battery 69 Wh after (floor 20), 9.3 °C.*

---

## 7. How we prove it works

**Strategies we compare against** (`kaio/baselines.py`):

| Strategy | What it does |
|---|---|
| Always-Transmit | Sends everything raw |
| Greedy-Process | Processes everything |
| Store-and-Forward | No onboard processing |
| Rule-Based | Hand-tuned rules with the same information as E-LOTUS |
| Bandwidth-Rules | Smarter rules that look at the coming passes (from the satsched prototype) |

**Protocol** (`benchmark.py`):
- **20 real days**, each an independent 24-hour run. Every strategy sees exactly the same images.
- **8 scenarios:** nominal, plus one degraded resource at a time (solar −30 %, small battery, storage ÷3,
  GPU 2.5× slower, downlink ÷2, fire season, radiator −25 %). Nothing is retuned.
- **Score:** "% of the reachable value". It compares with a perfect satellite that sends every image at its
  first pass, instantly and with unlimited resources. 100 % is physically impossible.
- **Statistics:** mean ± 95 % confidence interval over the 20 days, plus "on how many days E-LOTUS was better".

### Results (nominal scenario, 20 real days)

| Strategy | % reachable | Load-shed | Time > 45 °C | E-LOTUS better on |
|---|---|---|---|---|
| **E-LOTUS** | **85.3 ± 0.6** | 0 | 0.1 % | — |
| Rule-Based | 81.5 ± 0.7 | 0 | 0 % | 20/20 days |
| Bandwidth-Rules | 81.6 ± 0.8 | 0 | 0 % | 20/20 days |
| Store-and-Forward | 41.1 ± 2.4 | 0 | 0 % | 20/20 days |
| Greedy-Process | 31.0 ± 3.5 | 18.5 % | 53.4 % | 20/20 days |
| Always-Transmit | 2.1 ± 0.5 | 0 | 0 % | 20/20 days |

**Stress tests:** E-LOTUS wins 6 of 8 scenarios. It loses with a slower GPU (79.6 vs 80.6) and a weaker
radiator (71.2 vs 79.8). In both cases, the rule engine only scores higher because it runs above 45 °C for
37 % and 81 % of the day. Full tables: `results/summary.md`.

---

## 8. Backend and frontend: the technologies

### 8.1 Backend: Python (folder `kaio/`)
There is **no server and no database**. The backend is a simulation and analysis pipeline that produces
result files.

| File | Role | Main libraries |
|---|---|---|
| `config.py` | All parameters | — |
| `orbit.py` | SGP4 orbit, RK4/J2 check, eclipse, contacts, laser geometry | **sgp4**, **numpy** |
| `workload.py` | Turns the NASA atlas into a stream of images | numpy |
| `estimator.py` | The value formula | numpy |
| `physics.py` | Battery and thermal models (RK4) | numpy |
| `engine.py` | E-LOTUS decision engine + explanations | numpy |
| `safety.py` | Safety guard | numpy |
| `baselines.py` | The 5 competitor strategies | — |
| `simulator.py` | The loop: every 10 s, new images → checks → decisions → physics → logs | numpy |
| `scenarios.py` | The 8 stress scenarios | — |

Around the package:
- `benchmark.py` runs every scenario × strategy × 20 days (about 1,360 simulations, ~17 minutes) and writes
  `results/summary.json`. It uses **scipy** for the confidence intervals.
- `tests/` holds **18 automatic checks**, run with **pytest**.
- `app.py` is a second interactive tool built with **Streamlit** (Python), where you can run new
  simulations live.

### 8.2 Frontend: the dashboard (folder `web/`)
| File | Role |
|---|---|
| `build_web_data.py` | Pre-computes everything the dashboard shows: 270 what-if replays + 81 orbits → `kaio_data.json` |
| `kaio_template.html` | The page: plain **HTML + CSS + JavaScript**, no framework |
| `pack_page.py` | Packs data (gzip), textures, three.js and the font into **one HTML file** that works offline |

Inside the page:
- **three.js** (WebGL 3D) draws the Earth with NASA Blue Marble / Black Marble textures and the real sun
  direction.
- **HTML Canvas** draws the map, the charts and the heat map.
- **Live backgrounds:** the real Milky Way drifts slowly in dark mode, and the real Earth turns with moving
  clouds in light mode. Both run at most 30 fps and pause when the tab is hidden.
- **Light / dark mode** with a switch; **Space Grotesk** font; everything works without internet.

Visual sources:
- NASA Blue Marble and Black Marble (public domain).
- Milky Way skybox and Earth textures from the **three.js** GitHub repository (MIT licence).

### 8.3 Embedded: the Raspberry Pi (folder `onboard/`)
| File | Role |
|---|---|
| `pi_benchmark.py` | Measures decision time, CPU and memory over a full real day |
| `live_demo.py` | Prints every decision live, with its reason and how many milliseconds it took |
| `README_PI.md` | Step-by-step instructions |

On the Pi, KAIO needs only **numpy** and **sgp4**: no GPU and no training. On a laptop, one decision takes
**0.16 ms** (median), and the satellite needs one every 10 s.

### 8.4 How everything connects
```
data/ (TLE + NASA atlas)
   └─► kaio/ (simulation + E-LOTUS)
         ├─► benchmark.py ──────────► results/summary.json ─┐
         ├─► web/build_web_data.py ─► web/kaio_data.json ───┤
         │                                                  └─► web/pack_page.py ─► KAIO_Mission_Control.html
         └─► onboard/ ──────────────► Raspberry Pi demo
```

**Commands:**
```bash
pip install -r requirements.txt
python -m pytest -q                 # 18 checks
python benchmark.py                 # all scenarios, 20 real days (~17 min)
python web/build_web_data.py        # dashboard scenarios (~10 min)
python web/pack_page.py             # one-file dashboard (seconds)
python onboard/pi_benchmark.py      # engine cost (on the Pi)
python onboard/live_demo.py         # live decision feed
streamlit run app.py                # interactive explorer
```

---

## 9. How we built it (the story)

1. **Phase 2, two prototypes.**
   - **E-LOTUS** (Nadhem): the real orbit, NASA data, the Lyapunov engine and the 3D dashboard.
   - **satsched** (@Mahmoud35amri): a value-aware pricing engine, a clean tested package, calibrated
     scenarios and decision explanations.
2. **Review.** Both reached the same conclusion: a smart engine beats a tuned rule engine by a few points.
   The two did not look different because they disagreed; they used different orbits, data and scoring.
3. **Merge into KAIO.** We kept the real-data world, the engine and the dashboard from E-LOTUS, and took the
   structure, tests, explanations, drop rule, bandwidth baseline and statistics method from satsched.
4. **Fixes found during the merge.**
   - The old engine ran above 45 °C 10 % of the time. The new safety guard brings this to 0.1 %
     (fire alerts only).
   - "Proven guarantee" became "inspired by Lyapunov optimisation".
   - One name everywhere: KAIO.
5. **Honest benchmark:** 20 days × 8 scenarios × 6 strategies, with confidence intervals, including where we
   lose.
6. **Real-life proof:** the Raspberry Pi benchmark and live demo.
7. **Dashboard redesign:** Space Grotesk font, real space imagery, light/dark mode, frosted-glass panels,
   live backgrounds, fully offline.

---

## 10. Honest limits (say them before the judges do)

- The spacecraft hardware and the "true value" of images are our model, not a real mission.
- Pass and eclipse predictions are perfect in the simulation. In reality they are very close but not
  perfect.
- The neighbour satellite for laser offload is modelled. Without it, E-LOTUS loses only 1.6 points and still
  wins.
- The TLE dates from 26 Sep, so August positions are propagated about one month backwards. That causes a few
  kilometres of error, tiny compared with the 313 km image blocks.
- In the nominal case, the land mask alone scores slightly higher (87.1 vs 85.3). Texture matters when
  resources are scarce: without it, E-LOTUS drops to 78 (solar −30 %) and 66 (small battery).
- E-LOTUS is compared with heuristics, not with a hindsight-optimal schedule.

---

## 11. Why it could really fly

- Every input already exists on a satellite:
  - battery and temperature sensors,
  - a pass schedule uploaded from the ground,
  - a land/water map indexed by GPS position,
  - an image thumbnail.
- The engine is a few hundred lines with two libraries; no GPU and no training.
- It decides in fractions of a millisecond, and it needs to decide once every 10 seconds.
- Precedent: ESA's **Φsat-1** (2020) already discarded cloudy images onboard. KAIO flies the real orbit of
  its successor.

**Roadmap:**
- **Done:** engine, simulation, real data, dashboard, Pi.
- **3 months:** hardware-in-the-loop test on a flight-like computer; imperfect forecasts.
- **6 months:** small onboard cloud-detection model to replace the static land map.
- **12 months:** constellation coordination; partnership for a CubeSat flight test.

---

## 12. Glossary

| Term | Meaning |
|---|---|
| **TLE** | Two-Line Element set: standard text describing a satellite's orbit |
| **SGP4** | The standard algorithm that turns a TLE into positions over time |
| **RK4** | Runge–Kutta 4th order: a classic method to integrate differential equations |
| **J2** | The main effect of Earth's flattening on an orbit |
| **Eclipse** | When the satellite is in Earth's shadow: no solar power |
| **Pass / contact** | When a ground station can see the satellite and receive data |
| **Entropy (Shannon)** | A measure of how much texture/information an image has |
| **Load-shed** | Switching off the payload to protect the battery |
| **FDIR** | Fault Detection, Isolation and Recovery: the protection layer of spacecraft software |
| **Lyapunov / drift-plus-penalty** | A control method that keeps "debts" small while maximising a reward |
| **Confidence interval (95 %)** | The range where the true average most likely lies, given day-to-day variation |
| **GIBS** | NASA Global Imagery Browse Services |
| **VIIRS / MODIS / FIRMS** | NASA/NOAA satellite instruments and fire-alert system providing the data |
