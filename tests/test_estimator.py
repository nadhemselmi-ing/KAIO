"""The onboard value estimator: cheap, uses only onboard information, and ranks clouds low."""
import numpy as np

from kaio import semantic_estimate, shannon_entropy


def test_entropy_limits():
    assert shannon_entropy(np.zeros((32, 32), np.uint8)) == 0.0
    img = np.arange(256, dtype=np.uint8).reshape(16, 16)
    assert abs(shannon_entropy(img) - 8.0) < 1e-9


def test_land_prior_beats_texture():
    # a very textured scene over open ocean (typical of clouds) must rank below a clear land scene
    cloud_like = semantic_estimate(entropy=7.0, priority=1, land_prior=0.0, optical=True)
    clear_land = semantic_estimate(entropy=6.3, priority=1, land_prior=1.0, optical=True)
    assert clear_land > 3 * cloud_like


def test_alerts_dominate():
    alert = semantic_estimate(entropy=5.0, priority=4, land_prior=0.5, optical=True)
    routine = semantic_estimate(entropy=5.0, priority=1, land_prior=0.5, optical=True)
    assert alert == 4 * routine


def test_raw_entropy_mode_ignores_land():
    a = semantic_estimate(6.0, 1, 0.0, True, estimator="entropy")
    b = semantic_estimate(6.0, 1, 1.0, True, estimator="entropy")
    assert a == b
