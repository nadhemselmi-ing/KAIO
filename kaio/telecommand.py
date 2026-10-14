"""Authenticated telecommands: how the ground changes the engine's settings safely.

A telecommand (TC) is a small JSON packet signed by the ground segment with HMAC-SHA256 and a
secret key that only the ground and the satellite know (the idea of CCSDS SDLS authentication).
The satellite applies a TC only if all three checks pass:

1. the signature is valid           -> the packet was not forged or modified;
2. the sequence number is new        -> an old packet recorded by an attacker cannot be replayed;
3. the value is inside safe limits   -> even a valid operator cannot push the spacecraft out of bounds.

Standard library only (hmac, hashlib, json), so it runs unchanged on the onboard computer / Raspberry Pi.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Dict, Tuple

# parameter -> (min, max, description). Anything else is rejected.
LIMITS: Dict[str, Tuple[float, float, str]] = {
    "V": (0.01, 10.0, "engine trade-off knob (Lyapunov V)"),
    "energy_margin_wh": (0.0, 20.0, "battery reserve above the eclipse-survival floor [Wh]"),
    "thermal_margin_k": (0.0, 15.0, "extra margin below the 45 C limit [K]"),
    "alert_override": (0.0, 1.0, "fire alerts may run up to the 60 C hardware limit (0/1)"),
    "use_isl": (0.0, 1.0, "laser offload to neighbours allowed (0/1)"),
}
BOOL_PARAMS = {"alert_override", "use_isl"}


def _body(seq: int, param: str, value: float, ts: int) -> bytes:
    return json.dumps({"seq": seq, "param": param, "value": value, "ts": ts},
                      sort_keys=True, separators=(",", ":")).encode()


def sign(key: bytes, seq: int, param: str, value: float, ts: int | None = None) -> dict:
    """Ground side: build a signed telecommand packet."""
    ts = int(time.time()) if ts is None else ts
    mac = hmac.new(key, _body(seq, param, value, ts), hashlib.sha256).hexdigest()
    return {"seq": seq, "param": param, "value": value, "ts": ts, "mac": mac}


@dataclass
class TCVerifier:
    """Satellite side: checks and applies telecommands."""
    key: bytes
    last_seq: int = 0

    def check(self, pkt: dict) -> Tuple[bool, str]:
        try:
            seq, param, value, ts, mac = int(pkt["seq"]), str(pkt["param"]), float(pkt["value"]), int(pkt["ts"]), str(pkt["mac"])
        except (KeyError, TypeError, ValueError):
            return False, "malformed packet"
        good = hmac.new(self.key, _body(seq, param, value, ts), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(good, mac):
            return False, "bad signature"
        if seq <= self.last_seq:
            return False, f"replayed or old sequence number ({seq} <= {self.last_seq})"
        if param not in LIMITS:
            return False, f"unknown parameter '{param}'"
        lo, hi, _ = LIMITS[param]
        if not lo <= value <= hi or (param in BOOL_PARAMS and value not in (0.0, 1.0)):
            return False, f"{param}={value:g} outside safe limits [{lo:g}, {hi:g}]"
        return True, "accepted"

    def apply(self, pkt: dict, engine) -> Tuple[bool, str]:
        ok, why = self.check(pkt)
        if not ok:
            return False, why
        self.last_seq = int(pkt["seq"])
        p, v = pkt["param"], float(pkt["value"])
        if p == "V":
            engine.V = v
        elif p == "use_isl":
            engine.use_isl = bool(v)
        elif p == "alert_override":
            engine.guard.alert_override = bool(v)
        else:
            setattr(engine.guard, p, v)
        return True, f"TC #{pkt['seq']} accepted: {p} = {v:g}"
