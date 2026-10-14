"""KAIO: onboard "process, store, transmit or offload?" decisions for an Earth-observation satellite.

Package map
-----------
config     every numeric assumption (SimConfig) and physical constants
orbit      real Φsat-2 orbit (SGP4) + RK4/J2 check, eclipses, ground contacts, laser-link geometry
estimator  onboard value estimate from quick-look entropy + land mask (runs on the spacecraft)
workload   instrument data stream sampled from real NASA imagery (hidden ground truth for scoring)
physics    battery and radiative thermal model (RK4)
safety     SafetyGuard: independent hard-limit veto layer
engine     E-LOTUS decision engine (+ one-line explanation of every decision)
baselines  Always-Transmit, Greedy-Process, Store-and-Forward, Rule-Based, Bandwidth-Rules
simulator  slotted mission simulation, telemetry and metrics
scenarios  named stress scenarios used by the benchmark
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .config import (ACTION_CODE, ACTIONS, DATA_DIR, GROUND_STATIONS, J2, KELVIN, MU_EARTH, R_EARTH,
                     RESOURCE_ACTION, ROOT_DIR, SCENES, SIGMA_SB, SimConfig)
from .orbit import (Ephemeris, OrbitPropagator, build_ephemeris, gmst_rad, orbit_power_map, propagate_tle,
                    read_tle, sun_unit_vector)
from .estimator import semantic_estimate, semantic_value, shannon_entropy
from .workload import (RealAtlas, Task, generate_real_workload, generate_synthetic_workload, generate_workload,
                       real_scene_label, synth_thumbnail, synth_tir)
from .physics import SatelliteNode
from .safety import SafetyGuard
from .engine import ELotusEngine, Policy
from .baselines import AlwaysTransmit, BandwidthRules, GreedyProcess, RuleBased, StoreAndForward
from .simulator import SimResult, Simulation
from .scenarios import SCENARIOS

__version__ = "1.0.0"


def make_policies(V: float = 0.3, include_ablations: bool = False) -> List[Policy]:
    pols: List[Policy] = [ELotusEngine(V=V), AlwaysTransmit(), GreedyProcess(), StoreAndForward(), RuleBased(),
                          BandwidthRules()]
    if include_ablations:
        pols += [ELotusEngine(V=V, use_isl=False, label="E-LOTUS w/o ISLL"),
                 ELotusEngine(V=V, use_entropy=False, label="E-LOTUS w/o entropy"),
                 ELotusEngine(V=V, eclipse_aware=False, label="E-LOTUS static E_min"),
                 ELotusEngine(V=V, estimator="entropy", label="E-LOTUS raw entropy")]
    return pols


def run_simulation(cfg: SimConfig, policy: Policy, eph: Optional[Ephemeris] = None,
                   arrivals=None, progress=None) -> SimResult:
    """Run one controller over cfg.duration_h hours and return telemetry, events and metrics."""
    eph = eph if eph is not None else build_ephemeris(cfg)
    arrivals = arrivals if arrivals is not None else generate_workload(cfg, eph)
    return Simulation(cfg, policy, eph, arrivals).run(progress)


def run_comparison(cfg: SimConfig, policies: List[Policy]) -> Dict[str, SimResult]:
    """Run several controllers on the same orbit and the same data stream."""
    eph = build_ephemeris(cfg)
    arrivals = generate_workload(cfg, eph)
    return {p.name: Simulation(cfg, p, eph, arrivals).run() for p in policies}
