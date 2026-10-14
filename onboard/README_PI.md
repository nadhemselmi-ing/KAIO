# KAIO on a Raspberry Pi

This folder shows that the KAIO decision engine can run on a small embedded computer like the ones
that fly on CubeSats. You can run two programs:

| Program | What it shows | Time |
|---|---|---|
| `pi_benchmark.py` | Measures how fast KAIO decides, how much CPU and memory it uses | about 1–2 min |
| `live_demo.py` | Flies one real day and prints every decision with its reason, live | as long as you want |

## 1. Copy the project to the Pi

Use a USB stick, or from the laptop: `scp -r kaio-project pi@<pi-address>:~/`

## 2. Install the two libraries (once, needs internet)

```bash
sudo apt update
sudo apt install -y python3-numpy python3-pip
pip3 install sgp4 --break-system-packages
```

That's all KAIO needs onboard: **numpy** and **sgp4**. No GPU, no AI framework, no training.

## 3. Measure it

```bash
cd ~/kaio-project
python3 onboard/pi_benchmark.py
```

Write down the numbers it prints. The ones for the pitch are:
- **decision time** (median and worst case), compared with the 10 s decision cycle
- **CPU used by the engine** (% of one core)
- **peak memory**

It also saves `results/pi_benchmark.json`. Copy that file back into the project on the laptop and
rebuild the dashboard (`python web/pack_page.py`) so the dashboard shows your Pi's real numbers.

**Optional (power):** plug the Pi through a USB-C power meter. Note the watts at idle, then while
`pi_benchmark.py` runs. Pass the difference: `python3 onboard/pi_benchmark.py --watts 1.1`.

## 4. Live demo for the pitch

```bash
python3 onboard/live_demo.py            # starts just before a ground pass, 120x real time
python3 onboard/live_demo.py --speed 60 # slower, easier to read on stage
```

Connect the Pi to a screen (HDMI) or SSH in from the laptop and put that terminal next to the
dashboard. Every line shows what the satellite decided, why, and how many milliseconds the Pi took.
Ctrl+C stops it and prints a summary.

## What to say

> "This Raspberry Pi is running the actual KAIO flight logic, the same code as the dashboard.
> It makes each decision in about X milliseconds. The satellite only needs one every 10 seconds,
> so the engine uses less than Y % of one core, and the rest stays free for the cameras and the AI."

## If something goes wrong

- `ModuleNotFoundError: sgp4`: run the `pip3 install` line again.
- `externally-managed-environment`: keep the `--break-system-packages` flag, or use
  `python3 -m venv ~/kv && ~/kv/bin/pip install numpy sgp4` and run with `~/kv/bin/python`.
- Very old Pi (Pi 3 / Zero 2): it still works, just slower. The numbers are still far below the
  10 s cycle.
