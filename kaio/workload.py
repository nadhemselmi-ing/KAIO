"""Workload: the stream of images the instruments produce.

``generate_real_workload`` places acquisitions along the real ground track and attaches features
sampled from real NASA imagery (``RealAtlas``). Ground-truth value is hidden from every controller
and used only for scoring.
"""
from __future__ import annotations

import math
import os
from typing import Dict, List, Optional, Tuple

import numpy as np

from dataclasses import dataclass

from .config import DATA_DIR, SCENES, SimConfig
from .estimator import semantic_estimate, semantic_value, shannon_entropy
from .orbit import Ephemeris

# ---------------------------------------------------------------------------
# Tasks and workload
# ---------------------------------------------------------------------------
@dataclass
class Task:
    task_id: int
    t_gen: float                 # generation time [s]
    size_mb: float
    gflops: float                # required compute [GFLOP]
    entropy: float               # Shannon entropy H_i of the quick-look thumbnail [bit/px]
    priority: int                # 1 routine, 2 tasked, 4 alert (instrument trigger)
    aoi_deadline_s: float        # Age-of-Information deadline
    scene: str                   # hidden ground truth (never read by the engine)
    true_value: float            # hidden ground-truth scientific value
    est_value: float = 0.0       # engine-side semantic value estimate w_i
    kind: str = "raw"            # "raw" | "product"
    parent_id: int = -1
    remaining: float = 0.0       # remaining GFLOP (processing) or MB (transfer)
    lat: float = float("nan")    # scene centre (real ground track)
    lon: float = float("nan")
    land: float = float("nan")   # real land fraction (OSM land/water)
    cloud: float = float("nan")  # real cloud fraction (MODIS Aqua)
    fire_px: int = 0             # real VIIRS thermal-anomaly pixels in the scene
    optical: bool = True         # optical (sunlit) or thermal-IR (eclipse) quick-look

    def age(self, t: float) -> float:
        return t - self.t_gen

    def freshness(self, t: float) -> float:
        a = t - self.t_gen
        return math.exp(-a / self.aoi_deadline_s) if a <= self.aoi_deadline_s else 0.0


def synth_tir(scene: str, rng: np.random.Generator, n: int = 16) -> np.ndarray:
    """Thermal-infrared quick-look used by the instrument hot-pixel trigger."""
    img = rng.normal(120.0, 6.0, (n, n))
    if scene == "anomaly":
        i0, j0 = rng.integers(0, n - 4, 2)
        img[i0:i0 + 4, j0:j0 + 4] = rng.uniform(240, 255, (4, 4))
    return np.clip(img, 0, 255).astype(np.uint8)


def synth_thumbnail(scene: str, rng: np.random.Generator, n: int = 32) -> np.ndarray:
    if scene == "ocean":
        img = rng.normal(38.0, 2.0, (n, n))
    elif scene == "cloud":
        img = rng.normal(226.0, 5.0, (n, n))
    elif scene == "land":
        centers = rng.choice([70.0, 105.0, 140.0], size=(n // 4, n // 4), p=[0.4, 0.35, 0.25])
        img = np.kron(centers, np.ones((4, 4))) + rng.normal(0, 8.0, (n, n))
    elif scene == "urban":
        blocks = rng.uniform(20, 230, (n // 4, n // 4))
        img = np.kron(blocks, np.ones((4, 4))) + rng.normal(0, 18.0, (n, n))
    else:  # anomaly = land background + saturated hot spot
        centers = rng.choice([70.0, 105.0, 140.0], size=(n // 4, n // 4), p=[0.4, 0.35, 0.25])
        img = np.kron(centers, np.ones((4, 4))) + rng.normal(0, 8.0, (n, n))
        i0, j0 = rng.integers(0, n - 8, 2)
        img[i0:i0 + 7, j0:j0 + 7] = rng.uniform(235, 255, (7, 7))
    return np.clip(img, 0, 255).astype(np.uint8)


class RealAtlas:
    """Along-track Earth features sampled from NASA GIBS every 30 s over the real 30-day window.

    Produced in-browser by ``data/gibs_sampler.js`` (see paper Sec. IV-A): for each PHISAT-2
    sub-satellite point a 32x32-pixel (~313 km) quick-look block is cut from the global 4096x2048
    daily mosaics and summarised.
    """
    _cache: Dict[str, "RealAtlas"] = {}

    def __init__(self, path: str):
        import json as _json
        raw = open(path, "rb").read()
        self.header = _json.loads(raw[:4096].decode().strip())
        n = self.header["n"]
        o = 4096
        self.lat = np.frombuffer(raw, np.float32, n, o); o += 4 * n
        self.lon = np.frombuffer(raw, np.float32, n, o); o += 4 * n
        fields = ["H_tc", "H_bt", "land", "fire", "cloud_day", "cloud_night", "mean_tc"]
        for f in fields:
            setattr(self, f, np.frombuffer(raw, np.uint8, n, o).copy()); o += n
        self.n = n
        self.step = float(self.header["step_s"])
        self.days_done = int(self.header.get("days_done", 30))

    @classmethod
    def load(cls, cfg: SimConfig) -> "RealAtlas":
        path = cfg.atlas_path or os.path.join(DATA_DIR, "elotus_gibs_atlas.bin")
        if path not in cls._cache:
            cls._cache[path] = cls(path)
        return cls._cache[path]

    def nearest(self, lat: np.ndarray, lon: np.ndarray, day: np.ndarray, k: int = 24,
                radius_deg: float = 1.5) -> np.ndarray:
        """Index of the real NASA sample that best matches (lat, lon) on a what-if ground track.

        Among the k nearest real footprints within ``radius_deg``, the one closest in date wins;
        if none is that close, the geographically nearest sample is used.
        """
        from scipy.spatial import cKDTree
        limit = min(self.n, int(self.days_done * 86400 / self.step))
        if getattr(self, "_tree", None) is None:
            la, lo = np.radians(self.lat[:limit]), np.radians(self.lon[:limit])
            xyz = np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], axis=1)
            self._tree = cKDTree(xyz)
            self._day = (np.arange(limit) * self.step // 86400).astype(int)
        la, lo = np.radians(np.asarray(lat, float)), np.radians(np.asarray(lon, float))
        q = np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], axis=1)
        dist, idx = self._tree.query(q, k=k)
        chord = 2 * math.sin(math.radians(radius_deg) / 2)
        dday = np.abs(self._day[idx] - np.asarray(day)[:, None]).astype(float)
        dday[dist > chord] = 1e6
        best = np.argmin(dday + dist, axis=1)          # same-day wins; distance breaks ties
        return idx[np.arange(len(idx)), best]


def real_scene_label(land: float, cloud: float, alert: bool, dark: bool = False) -> str:
    if alert:
        return "fire"
    if dark:
        return "dark"
    if cloud >= 0.6:
        return "cloud"
    if land < 0.1:
        return "ocean"
    if land < 0.6:
        return "coast"
    return "land"


def generate_real_workload(cfg: SimConfig, eph: Ephemeris, n_slots: Optional[int] = None) -> List[List[Task]]:
    """Arrivals along the real PHISAT-2 ground track with features from real NASA imagery.

    * sunlit  -> optical quick-look entropy from VIIRS NOAA-20 corrected-reflectance true colour
    * eclipse -> thermal-IR quick-look entropy from VIIRS NOAA-20 I5 night brightness temperature
    * alert (priority 4) when the scene holds >= fire_trigger_px VIIRS 375 m thermal-anomaly pixels
    * hidden ground truth: v = 0.02 + 0.63 * land * (1 - cloud) (MODIS Aqua cloud fraction), alerts 3.0,
      0.02 for optical scenes in polar night (mean VIIRS luminance < 8)
    """
    A = RealAtlas.load(cfg)
    rng = np.random.default_rng(cfg.seed)
    n_slots = n_slots or cfg.n_slots
    off = int(round(cfg.start_day * 86400 / A.step))
    limit = min(A.n, int(A.days_done * 86400 / A.step))
    whatif = cfg.orbit_model != "sgp4"
    if whatif:   # what-if orbit: borrow the real NASA scene under each modelled footprint
        nn = A.nearest(eph.lat[:n_slots], eph.lon[:n_slots],
                       cfg.start_day + (np.arange(n_slots) * cfg.dt // 86400).astype(int))
    arrivals: List[List[Task]] = []
    tid = 0
    for k in range(n_slots):
        lam = cfg.load_scale * (cfg.lam_sunlit if eph.sunlit[k] else cfg.lam_eclipse)
        m = rng.poisson(lam * cfg.dt)
        slot: List[Task] = []
        for _ in range(m):
            t_gen = k * cfg.dt + rng.uniform(0, cfg.dt)
            i = int(nn[k]) if whatif else min(off + int(round(t_gen / A.step)), limit - 1)
            sun = bool(eph.sunlit[k])
            H = (A.H_tc[i] if sun else A.H_bt[i]) / 30.0
            cl = A.cloud_day[i] if sun else A.cloud_night[i]
            if cl == 255:
                cl = A.cloud_night[i] if sun else A.cloud_day[i]
            cloud = 0.5 if cl == 255 else cl / 100.0
            land = A.land[i] / 100.0
            alert = int(A.fire[i]) >= cfg.fire_trigger_px
            dark = sun and A.mean_tc[i] < 8          # optical scene in polar night: no usable content
            prio = 4 if alert else 1
            value = 3.0 if alert else (0.02 if dark else 0.02 + 0.63 * land * (1.0 - cloud))
            size = float(cfg.size_median_mb * math.exp(cfg.size_sigma * rng.standard_normal()))
            task = Task(task_id=tid, t_gen=t_gen, size_mb=size, gflops=size * cfg.gflop_per_mb, entropy=float(H),
                        priority=prio, aoi_deadline_s=cfg.deadline_alert_s if alert else cfg.deadline_routine_s,
                        scene=real_scene_label(land, cloud, alert, dark), true_value=value,
                        est_value=semantic_estimate(float(H), prio, land, sun, cfg.estimator))
            task.optical = sun
            task.lat, task.lon = ((float(eph.lat[k]), float(eph.lon[k])) if whatif
                                  else (float(A.lat[i]), float(A.lon[i])))
            task.land, task.cloud, task.fire_px = land, cloud, int(A.fire[i])
            slot.append(task)
            tid += 1
        arrivals.append(slot)
    return arrivals


def generate_workload(cfg: SimConfig, eph: Ephemeris, n_slots: Optional[int] = None) -> List[List[Task]]:
    """Policy-independent arrival stream: identical for every controller (same seed)."""
    if cfg.workload == "real":
        return generate_real_workload(cfg, eph, n_slots)
    return generate_synthetic_workload(cfg, eph, n_slots)


def generate_synthetic_workload(cfg: SimConfig, eph: Ephemeris, n_slots: Optional[int] = None) -> List[List[Task]]:
    """Procedural thumbnails (kept for comparison with the real-data workload)."""
    rng = np.random.default_rng(cfg.seed)
    n_slots = n_slots or cfg.n_slots
    names = list(SCENES.keys())
    probs = np.array([SCENES[s][0] for s in names])
    arrivals: List[List[Task]] = []
    tid = 0
    for k in range(n_slots):
        lam = cfg.load_scale * (cfg.lam_sunlit if eph.sunlit[k] else cfg.lam_eclipse)
        m = rng.poisson(lam * cfg.dt)
        slot: List[Task] = []
        for _ in range(m):
            scene = names[rng.choice(len(names), p=probs)]
            img = synth_thumbnail(scene, rng)
            H = shannon_entropy(img)
            hot = float((synth_tir(scene, rng) >= 235).mean())   # TIR hot-pixel trigger
            prio, value = 1, SCENES[scene][1]
            if hot > 0.02:
                prio = 4
            elif scene in ("land", "urban") and rng.random() < cfg.tasked_fraction:
                prio, value = 2, 2.0 * value            # customer-tasked acquisition
            deadline = {4: cfg.deadline_alert_s, 2: cfg.deadline_tasked_s}.get(prio, cfg.deadline_routine_s)
            size = float(cfg.size_median_mb * math.exp(cfg.size_sigma * rng.standard_normal()))
            t_gen = k * cfg.dt + rng.uniform(0, cfg.dt)
            slot.append(Task(task_id=tid, t_gen=t_gen, size_mb=size, gflops=size * cfg.gflop_per_mb,
                             entropy=H, priority=prio, aoi_deadline_s=deadline, scene=scene,
                             true_value=value, est_value=semantic_value(H, prio)))
            tid += 1
        arrivals.append(slot)
    return arrivals

