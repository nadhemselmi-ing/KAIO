"""The SafetyGuard vetoes jobs that would break the battery floor or the thermal limit."""
from kaio import ELotusEngine, KELVIN, SafetyGuard, Simulation


def _sim(day0):
    cfg, eph, arr = day0
    sim = Simulation(cfg, ELotusEngine(), eph, arr)
    sim.k, sim.t = 0, 0.0
    return sim, arr


def _first_task(arr, priority=1):
    return next(t for slot in arr for t in slot if t.priority == priority)


def test_allows_normal_job(day0):
    sim, arr = _sim(day0)
    ok, why = SafetyGuard().check(sim, "gpu", _first_task(arr))
    assert ok and why == ""


def test_blocks_on_low_battery(day0):
    sim, arr = _sim(day0)
    sim.node.E = float(sim.e_survive[0]) + 0.1
    ok, why = SafetyGuard().check(sim, "gpu", _first_task(arr))
    assert not ok and "battery" in why


def test_blocks_on_heat(day0):
    sim, arr = _sim(day0)
    sim.node.T = sim.cfg.t_safe_c + KELVIN - 0.2
    ok, why = SafetyGuard().check(sim, "gpu", _first_task(arr))
    assert not ok and "°C" in why
    # the relaxed mode only protects the hard limit
    ok, _ = SafetyGuard(thermal_limit="max").check(sim, "gpu", _first_task(arr))
    assert ok


def test_fire_alerts_may_use_the_thermal_margin(day0):
    from dataclasses import replace
    sim, arr = _sim(day0)
    alert = replace(_first_task(arr), priority=4)
    sim.node.T = sim.cfg.t_safe_c + KELVIN - 0.2
    assert SafetyGuard().check(sim, "gpu", alert)[0]
    assert not SafetyGuard(alert_override=False).check(sim, "gpu", alert)[0]
