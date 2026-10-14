"""Battery and thermal model sanity."""
from kaio import KELVIN, SatelliteNode, SimConfig, build_ephemeris


def test_battery_stays_in_bounds_and_charges_in_sun():
    cfg = SimConfig(duration_h=3.0, soc0=0.5)
    eph = build_ephemeris(cfg, extra_h=0.0)
    node = SatelliteNode(cfg, eph)
    for k in range(cfg.n_slots):
        e0 = node.E
        node.step(k, cfg.p_bus_w, cfg.dt)
        assert 0.0 <= node.E <= cfg.battery_wh
        if eph.sunlit[k] and node.p_solar_series[k] > cfg.p_bus_w + 1 and e0 < 0.85 * cfg.battery_wh:
            assert node.E > e0


def test_thermal_relaxes_towards_radiative_equilibrium():
    cfg = SimConfig(duration_h=24.0)
    eph = build_ephemeris(cfg, extra_h=0.0)
    node = SatelliteNode(cfg, eph)
    for k in range(cfg.n_slots):
        node.step(k, 20.0, cfg.dt)       # 20 W constant load
    # equilibrium with the sun-averaged environment load: eps*sigma*A*T^4 = P + Q_env
    q_env = cfg.q_earth_ir_w + cfg.q_sun_w * eph.sunlit.mean()
    t_eq = ((20.0 + q_env) / cfg.rad_coeff) ** 0.25
    assert abs(node.T - t_eq) < 12.0
    assert node.T - KELVIN < 100
