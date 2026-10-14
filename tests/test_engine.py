"""E-LOTUS decisions: deterministic, explainable, and blind to the hidden ground truth."""
import random
from dataclasses import replace

from kaio import ELotusEngine, Simulation


def _events(day0, arrivals=None):
    cfg, eph, arr = day0
    r = Simulation(cfg, ELotusEngine(), eph, arrivals or arr).run()
    return [(e["t_h"], e["task_id"], e["action"]) for e in r.events if e["detail"] != "arrival"], r


def test_deterministic(day0):
    a, _ = _events(day0)
    b, _ = _events(day0)
    assert a == b


def test_never_reads_ground_truth(day0):
    """Shuffle the hidden scene labels and true values: the engine must make exactly the same decisions."""
    cfg, eph, arr = day0
    rng = random.Random(0)
    vals = [(t.true_value, t.scene) for s in arr for t in s]
    rng.shuffle(vals)
    it = iter(vals)
    scrambled = [[replace(t, true_value=v, scene=sc) for t, (v, sc) in zip(s, it)] for s in arr]
    a, _ = _events(day0)
    b, _ = _events(day0, scrambled)
    assert [x[1:] for x in a] == [x[1:] for x in b]


def test_every_started_job_is_explained(day0):
    _, r = _events(day0)
    started = [e for e in r.events if e["action"] in ("PROCESS", "TRANSMIT", "OFFLOAD_ISLL")]
    assert started, "the engine should do something in 6 hours"
    assert all(len(e["why"]) > 20 for e in started)
    assert not any(e["action"] == "VETO" for e in r.events)  # the engine already respects the guard
