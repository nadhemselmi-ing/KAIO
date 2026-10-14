"""Simulator bookkeeping and the headline safety properties."""
from kaio import ELotusEngine, GreedyProcess, RuleBased, Simulation


def test_every_image_is_accounted_for(day0):
    cfg, eph, arr = day0
    sim = Simulation(cfg, ELotusEngine(), eph, arr)
    sim.run()
    c = sim.cnt
    in_flight = len(sim.raw_q) + len(sim.prod_q) + sum(j is not None for j in sim.jobs.values()) + len(sim.pending_nb)
    assert c["generated"] == c["delivered"] + c["overflow"] + c["expired"] + in_flight


def test_elotus_is_safe_and_competitive(day0):
    cfg, eph, arr = day0
    m = Simulation(cfg, ELotusEngine(), eph, arr).run().metrics
    rb = Simulation(cfg, RuleBased(), eph, arr).run().metrics
    assert m["shed_pct"] == 0.0 and m["throttled_pct"] == 0.0
    assert m["temp_max_c"] < cfg.t_max_c
    assert m["value"] >= 0.95 * rb["value"]


def test_greedy_shows_the_problem(day0):
    cfg, eph, arr = day0
    g = Simulation(cfg, GreedyProcess(), eph, arr).run().metrics
    assert g["temp_max_c"] > cfg.t_safe_c       # processing everything overheats
