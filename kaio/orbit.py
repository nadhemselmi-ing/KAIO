"""Orbit and geometry: real Φsat-2 TLE propagated with SGP4, an independent RK4 two-body + J2
integrator, sun/eclipse geometry, ground-station contacts and inter-satellite line of sight.

Everything here is policy-independent: every controller sees the same ``Ephemeris``.
"""
from __future__ import annotations

import math
import os
from typing import Dict, List, Optional, Tuple

import numpy as np

from dataclasses import dataclass

from .config import J2, MU_EARTH, R_EARTH, DATA_DIR, SimConfig

# ---------------------------------------------------------------------------
# Orbit propagation (RK4, two-body + J2)
# ---------------------------------------------------------------------------
def _accel(x: float, y: float, z: float) -> Tuple[float, float, float]:
    r2 = x * x + y * y + z * z
    r = math.sqrt(r2)
    k = -MU_EARTH / (r2 * r)
    f = 1.5 * J2 * MU_EARTH * R_EARTH * R_EARTH / (r2 * r2 * r)
    zz = 5.0 * z * z / r2
    return (k * x + f * x * (zz - 1.0),
            k * y + f * y * (zz - 1.0),
            k * z + f * z * (zz - 3.0))


class OrbitPropagator:
    """Fixed-step 4th-order Runge-Kutta integration of the J2-perturbed orbit."""

    @staticmethod
    def initial_state(a_km: float, inc_deg: float, raan_deg: float, u_deg: float = 0.0):
        i, O, u = map(math.radians, (inc_deg, raan_deg, u_deg))
        v = math.sqrt(MU_EARTH / a_km)
        cO, sO, ci, si, cu, su = math.cos(O), math.sin(O), math.cos(i), math.sin(i), math.cos(u), math.sin(u)
        r = (a_km * (cO * cu - sO * su * ci), a_km * (sO * cu + cO * su * ci), a_km * su * si)
        vv = (v * (-cO * su - sO * cu * ci), v * (-sO * su + cO * cu * ci), v * cu * si)
        return r, vv

    @staticmethod
    def propagate(r0, v0, dt: float, n: int) -> np.ndarray:
        out = np.empty((n, 6))
        x, y, z = r0
        vx, vy, vz = v0
        h = dt
        for k in range(n):
            out[k, 0] = x; out[k, 1] = y; out[k, 2] = z
            out[k, 3] = vx; out[k, 4] = vy; out[k, 5] = vz
            a1 = _accel(x, y, z)
            x2, y2, z2 = x + 0.5 * h * vx, y + 0.5 * h * vy, z + 0.5 * h * vz
            vx2, vy2, vz2 = vx + 0.5 * h * a1[0], vy + 0.5 * h * a1[1], vz + 0.5 * h * a1[2]
            a2 = _accel(x2, y2, z2)
            x3, y3, z3 = x + 0.5 * h * vx2, y + 0.5 * h * vy2, z + 0.5 * h * vz2
            vx3, vy3, vz3 = vx + 0.5 * h * a2[0], vy + 0.5 * h * a2[1], vz + 0.5 * h * a2[2]
            a3 = _accel(x3, y3, z3)
            x4, y4, z4 = x + h * vx3, y + h * vy3, z + h * vz3
            vx4, vy4, vz4 = vx + h * a3[0], vy + h * a3[1], vz + h * a3[2]
            a4 = _accel(x4, y4, z4)
            x += h / 6.0 * (vx + 2 * vx2 + 2 * vx3 + vx4)
            y += h / 6.0 * (vy + 2 * vy2 + 2 * vy3 + vy4)
            z += h / 6.0 * (vz + 2 * vz2 + 2 * vz3 + vz4)
            vx += h / 6.0 * (a1[0] + 2 * a2[0] + 2 * a3[0] + a4[0])
            vy += h / 6.0 * (a1[1] + 2 * a2[1] + 2 * a3[1] + a4[1])
            vz += h / 6.0 * (a1[2] + 2 * a2[2] + 2 * a3[2] + a4[2])
        return out


# ---------------------------------------------------------------------------
# Ephemeris (policy-independent geometry)
# ---------------------------------------------------------------------------
def sun_unit_vector(jd: np.ndarray) -> np.ndarray:
    """Low-precision solar ephemeris (Astronomical Almanac), ECI unit vectors."""
    n = jd - 2451545.0
    L = np.radians((280.460 + 0.9856474 * n) % 360.0)
    g = np.radians((357.528 + 0.9856003 * n) % 360.0)
    lam = L + np.radians(1.915) * np.sin(g) + np.radians(0.020) * np.sin(2 * g)
    eps = np.radians(23.439 - 4.0e-7 * n)
    return np.stack([np.cos(lam), np.cos(eps) * np.sin(lam), np.sin(eps) * np.sin(lam)], axis=-1)


def gmst_rad(jd: np.ndarray) -> np.ndarray:
    return np.radians((280.46061837 + 360.98564736629 * (jd - 2451545.0)) % 360.0)


def _in_shadow(r: np.ndarray, s: np.ndarray) -> np.ndarray:
    """Cylindrical Earth-shadow model."""
    proj = np.einsum("ij,ij->i", r, s)
    perp = r - proj[:, None] * s
    return (proj < 0.0) & (np.linalg.norm(perp, axis=1) < R_EARTH)


def _gs_visible(r: np.ndarray, theta: np.ndarray, lat_deg: float, lon_deg: float, mask_deg: float):
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    ang = lon + theta
    g = R_EARTH * np.stack([math.cos(lat) * np.cos(ang), math.cos(lat) * np.sin(ang),
                            np.full_like(ang, math.sin(lat))], axis=-1)
    rho = r - g
    up = g / R_EARTH
    sin_el = np.einsum("ij,ij->i", rho, up) / np.linalg.norm(rho, axis=1)
    el = np.degrees(np.arcsin(np.clip(sin_el, -1, 1)))
    return el >= mask_deg, el


def _next_true_wait(flag: np.ndarray, dt: float) -> np.ndarray:
    """Seconds from slot k until the next slot where flag is True (0 if already True)."""
    n = len(flag)
    idx = np.flatnonzero(flag)
    ar = np.arange(n)
    if idx.size == 0:
        return np.full(n, 1e9)
    pos = np.searchsorted(idx, ar)
    wait = np.full(n, 1e9)
    ok = pos < idx.size
    wait[ok] = (idx[pos[ok]] - ar[ok]) * dt
    return wait


def _segment_clear(r1: np.ndarray, r2: np.ndarray, rmin: float) -> np.ndarray:
    d = r2 - r1
    s = np.clip(-np.einsum("ij,ij->i", r1, d) / np.einsum("ij,ij->i", d, d), 0.0, 1.0)
    p = r1 + s[:, None] * d
    return np.linalg.norm(p, axis=1) > rmin


@dataclass
class Ephemeris:
    t: np.ndarray
    r: np.ndarray
    v: np.ndarray
    sun: np.ndarray
    sunlit: np.ndarray
    theta_deg: np.ndarray           # solar incidence angle on the zenith panel
    solar_factor: np.ndarray        # sum of max(0, n_i . s) over lit faces
    lat: np.ndarray
    lon: np.ndarray
    alt: np.ndarray
    contact: np.ndarray
    contact_station: np.ndarray     # index into station list, -1 if none
    wait_contact: np.ndarray
    nb_sunlit: Dict[str, np.ndarray]
    isl_los: Dict[str, np.ndarray]
    nb_wait_contact: Dict[str, np.ndarray]
    ecl_remaining_s: np.ndarray     # if in eclipse: time to exit
    t_to_eclipse_s: np.ndarray      # if sunlit: time to next eclipse entry
    next_ecl_dur_s: np.ndarray      # if sunlit: duration of next eclipse
    station_names: List[str]
    beta_deg: np.ndarray
    dt: float


def read_tle(cfg: SimConfig) -> Tuple[str, str, str]:
    path = cfg.tle_path or os.path.join(DATA_DIR, "phisat2_tle.txt")
    lines = [ln.rstrip() for ln in open(path) if ln.strip()]
    return lines[0], lines[1], lines[2]


def propagate_tle(cfg: SimConfig, jd: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """SGP4 propagation of the real TLE; TEME positions are rotated to Earth-fixed with GMST."""
    from sgp4.api import Satrec
    _, l1, l2 = read_tle(cfg)
    sat = Satrec.twoline2rv(l1, l2)
    whole = np.floor(jd - 0.5) + 0.5
    e, r, v = sat.sgp4_array(whole, jd - whole)
    if np.any(e != 0):
        raise RuntimeError(f"SGP4 error codes {set(e[e != 0].tolist())}")
    return r, v


def build_ephemeris(cfg: SimConfig, extra_h: float = 14.0) -> Ephemeris:
    """extra_h: look-ahead beyond the horizon (> longest AoI deadline) for contact/eclipse prediction."""
    n = int(round((cfg.duration_h + extra_h) * 3600.0 / cfg.dt))
    t = np.arange(n) * cfg.dt
    jd = cfg.epoch_jd + t / 86400.0
    sun = sun_unit_vector(jd)
    if cfg.orbit_model == "sgp4":
        r, v = propagate_tle(cfg, jd)
    else:
        ra_sun = math.degrees(math.atan2(sun[0, 1], sun[0, 0]))
        raan = (ra_sun + (cfg.ltan_h - 12.0) * 15.0) % 360.0
        a = R_EARTH + cfg.altitude_km
        r0, v0 = OrbitPropagator.initial_state(a, cfg.inclination_deg, raan, 0.0)
        st = OrbitPropagator.propagate(r0, v0, cfg.dt, n)
        r, v = st[:, :3], st[:, 3:]
    rn = np.linalg.norm(r, axis=1)
    rhat = r / rn[:, None]
    h = np.cross(r, v)
    hhat = h / np.linalg.norm(h, axis=1)[:, None]
    that = np.cross(hhat, rhat)                    # along-track (ram) direction
    shadow = _in_shadow(r, sun)
    sunlit = ~shadow
    cz = np.einsum("ij,ij->i", rhat, sun)
    ct = np.einsum("ij,ij->i", that, sun)
    solar_factor = (np.maximum(cz, 0) + np.maximum(ct, 0) + np.maximum(-ct, 0)) * sunlit
    theta = np.degrees(np.arccos(np.clip(cz, -1, 1)))
    beta = np.degrees(np.arcsin(np.clip(np.einsum("ij,ij->i", hhat, sun), -1, 1)))
    gm = gmst_rad(jd)
    lat = np.degrees(np.arcsin(r[:, 2] / rn))
    lon = (np.degrees(np.arctan2(r[:, 1], r[:, 0]) - gm) + 180.0) % 360.0 - 180.0
    alt = rn - R_EARTH

    names = list(cfg.ground_stations.keys())
    contact = np.zeros(n, bool)
    station = np.full(n, -1)
    for j, nm in enumerate(names):
        vis, _ = _gs_visible(r, gm, *cfg.ground_stations[nm], cfg.elevation_mask_deg)
        station[vis & ~contact] = j
        contact |= vis
    wait_contact = _next_true_wait(contact, cfg.dt)

    phi = math.radians(cfg.isl_phase_deg)
    hxr = np.cross(hhat, r)
    nb_pos = {"lead": r * math.cos(phi) + hxr * math.sin(phi),
              "trail": r * math.cos(phi) - hxr * math.sin(phi)}
    nb_sunlit, isl_los, nb_wait = {}, {}, {}
    for side, rp in nb_pos.items():
        nb_sunlit[side] = ~_in_shadow(rp, sun)
        isl_los[side] = _segment_clear(r, rp, R_EARTH + cfg.isl_graze_km)
        c = np.zeros(n, bool)
        for nm in names:
            vis, _ = _gs_visible(rp, gm, *cfg.ground_stations[nm], cfg.elevation_mask_deg)
            c |= vis
        nb_wait[side] = _next_true_wait(c, cfg.dt)

    # eclipse timing
    ecl_remaining = _next_true_wait(sunlit, cfg.dt) * shadow
    t_to_ecl = _next_true_wait(shadow, cfg.dt) * sunlit
    # beyond the end of the look-ahead window the wait is unknown: clip to one orbital period
    ecl_remaining = np.where(ecl_remaining > 1e8, 0.0, ecl_remaining)
    t_to_ecl = np.where(t_to_ecl > 1e8, 0.0, t_to_ecl)
    next_dur = np.zeros(n)
    # run-length of each eclipse
    edges = np.diff(np.concatenate([[0], shadow.astype(int), [0]]))
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    dur_at_start = np.zeros(n)
    for s_, e_ in zip(starts, ends):
        dur_at_start[s_] = (e_ - s_) * cfg.dt
    nxt = np.minimum(np.arange(n) + (t_to_ecl / cfg.dt).astype(int), n - 1)
    next_dur = np.where(sunlit, dur_at_start[nxt], 0.0)

    return Ephemeris(t=t, r=r, v=v, sun=sun, sunlit=sunlit, theta_deg=theta,
                     solar_factor=solar_factor, lat=lat, lon=lon, alt=alt,
                     contact=contact, contact_station=station, wait_contact=wait_contact,
                     nb_sunlit=nb_sunlit, isl_los=isl_los, nb_wait_contact=nb_wait,
                     ecl_remaining_s=ecl_remaining, t_to_eclipse_s=t_to_ecl,
                     next_ecl_dur_s=next_dur, station_names=names, beta_deg=beta, dt=cfg.dt)


def orbit_power_map(cfg: SimConfig, incs, ltans, hours: float = 24.0, dt: float = 30.0) -> Dict[str, np.ndarray]:
    """Geometry-only sweep for the orbit designer (circular orbit, J2 secular node drift).

    For every (inclination, LTAN) pair: eclipse share, solar-array energy available per day for the
    body-mounted zenith + ram/wake faces, mean beta angle and ground-contact minutes per day.
    Fast (vectorised); the full controller simulation is run separately for the chosen orbit.
    """
    n = int(round(hours * 3600.0 / dt))
    t = np.arange(n) * dt
    jd = cfg.epoch_jd + t / 86400.0
    sun = sun_unit_vector(jd)
    gm = gmst_rad(jd)
    a = R_EARTH + cfg.altitude_km
    nmot = math.sqrt(MU_EARTH / a ** 3)
    ra_sun = math.atan2(sun[0, 1], sun[0, 0])
    u = nmot * t
    cu, su = np.cos(u), np.sin(u)
    shape = (len(incs), len(ltans))
    out = {k: np.zeros(shape) for k in ("eclipse_pct", "solar_wh", "beta_deg", "contact_min")}
    for i, inc in enumerate(incs):
        ir = math.radians(inc)
        ci, si = math.cos(ir), math.sin(ir)
        draan = -1.5 * nmot * J2 * (R_EARTH / a) ** 2 * ci
        for j, lt in enumerate(ltans):
            O = ra_sun + math.radians((lt - 12.0) * 15.0) + draan * t
            cO, sO = np.cos(O), np.sin(O)
            rhat = np.stack([cO * cu - sO * su * ci, sO * cu + cO * su * ci, su * si], axis=1)
            that = np.stack([-cO * su - sO * cu * ci, -sO * su + cO * cu * ci, cu * si], axis=1)
            hhat = np.cross(rhat, that)
            r = a * rhat
            lit = ~_in_shadow(r, sun)
            cz = np.einsum("ij,ij->i", rhat, sun)
            ct = np.einsum("ij,ij->i", that, sun)
            sf = (np.maximum(cz, 0) + np.abs(ct)) * lit
            contact = np.zeros(n, bool)
            for nm in cfg.ground_stations:
                vis, _ = _gs_visible(r, gm, *cfg.ground_stations[nm], cfg.elevation_mask_deg)
                contact |= vis
            out["eclipse_pct"][i, j] = 100.0 * (1.0 - lit.mean())
            out["solar_wh"][i, j] = cfg.p_face_w * sf.sum() * dt / 3600.0 * 24.0 / hours
            out["beta_deg"][i, j] = float(np.degrees(np.arcsin(np.clip(np.einsum("ij,ij->i", hhat, sun), -1, 1))).mean())
            out["contact_min"][i, j] = contact.sum() * dt / 60.0 * 24.0 / hours
    return out

