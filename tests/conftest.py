import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kaio import SimConfig, build_ephemeris, generate_workload  # noqa: E402


@pytest.fixture(scope="session")
def day0():
    """6 hours of the first real day: real orbit + real NASA scenes."""
    cfg = SimConfig(seed=11, start_day=0, duration_h=6.0)
    eph = build_ephemeris(cfg)
    return cfg, eph, generate_workload(cfg, eph)
