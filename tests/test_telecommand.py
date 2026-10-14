"""Authenticated telecommands: forged, replayed or unsafe commands never reach the engine."""
from kaio import ELotusEngine
from kaio.telecommand import TCVerifier, sign

KEY = b"k" * 32


def test_valid_command_is_applied():
    eng, sat = ELotusEngine(), TCVerifier(KEY)
    ok, why = sat.apply(sign(KEY, 1, "V", 0.5), eng)
    assert ok and eng.V == 0.5 and sat.last_seq == 1


def test_tampered_or_wrong_key_is_rejected():
    eng, sat = ELotusEngine(), TCVerifier(KEY)
    pkt = sign(KEY, 1, "V", 0.5)
    pkt["value"] = 5.0                                   # attacker edits the value
    assert sat.apply(pkt, eng) == (False, "bad signature")
    assert sat.apply(sign(b"x" * 32, 1, "V", 0.5), eng)[1] == "bad signature"
    assert eng.V == ELotusEngine().V


def test_replay_is_rejected():
    eng, sat = ELotusEngine(), TCVerifier(KEY)
    pkt = sign(KEY, 1, "energy_margin_wh", 2.0)
    assert sat.apply(pkt, eng)[0]
    ok, why = sat.apply(pkt, eng)
    assert not ok and "replayed" in why


def test_out_of_range_and_unknown_are_rejected_even_when_signed():
    eng, sat = ELotusEngine(), TCVerifier(KEY)
    assert not sat.apply(sign(KEY, 1, "V", 99.0), eng)[0]
    assert not sat.apply(sign(KEY, 2, "use_isl", 0.5), eng)[0]
    assert not sat.apply(sign(KEY, 3, "battery_wh", 1.0), eng)[0]
    assert sat.last_seq == 0
