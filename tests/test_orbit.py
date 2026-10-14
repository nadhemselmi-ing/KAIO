"""The real orbit: SGP4 propagation of the Φsat-2 TLE, checked against an independent integrator."""
import numpy as np

from kaio import OrbitPropagator, R_EARTH, SimConfig, build_ephemeris, propagate_tle


def test_sgp4_and_rk4_j2_agree():
    cfg = SimConfig()
    jd0 = cfg.epoch_jd
    r, v = propagate_tle(cfg, np.array([jd0 + k * 10.0 / 86400 for k in range(int(6 * 360) + 1)]))
    st = OrbitPropagator.propagate(tuple(r[0]), tuple(v[0]), 10.0, len(r))
    err = np.linalg.norm(st[:, :3] - r, axis=1)
    assert err.max() < 25.0, f"RK4/J2 drifts {err.max():.1f} km from SGP4 in 6 h"


def test_orbit_geometry_is_plausible():
    cfg = SimConfig(duration_h=24.0)
    e = build_ephemeris(cfg, extra_h=0.0)
    alt = e.alt.mean()
    assert 450 < alt < 500                      # Φsat-2 flies at ~470 km
    asc = np.flatnonzero((e.lat[:-1] < 0) & (e.lat[1:] >= 0))
    period_min = np.median(np.diff(asc)) * cfg.dt / 60
    assert 93 < period_min < 96
    eclipse = 1 - e.sunlit.mean()
    assert 0.25 < eclipse < 0.45
    contact_min = e.contact.sum() * cfg.dt / 60
    assert 30 < contact_min < 150                # two high-latitude stations
    assert np.all(np.linalg.norm(e.r, axis=1) > R_EARTH)
