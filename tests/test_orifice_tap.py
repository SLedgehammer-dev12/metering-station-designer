"""Orifice tap type selection tests (Phase E4)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from metering_designer.meters.orifice import (
    calc_beta_ratio,
    size_orifice_for_flow,
    _discharge_coefficient_rhg,
    TAP_TYPES,
    list_tap_types,
)


def test_tap_types_listed():
    types = list_tap_types()
    assert isinstance(types, list)
    names = [t["name"] for t in types]
    assert "corner" in names
    assert "flange" in names
    assert "D_D" in names
    assert "2D" in names


def test_corner_taps_default():
    result = calc_beta_ratio(10.0, 100.0, 50.0, 1.2e-5, 25000, p1_Pa=45e5)
    assert result["tap_type"] == "corner"


def test_different_tap_types():
    qm = 10.0
    D = 100.0
    rho = 50.0
    mu = 1.2e-5
    dp = 25000
    p1 = 45e5

    corner = calc_beta_ratio(qm, D, rho, mu, dp, p1_Pa=p1, tap_type="corner")
    flange = calc_beta_ratio(qm, D, rho, mu, dp, p1_Pa=p1, tap_type="flange")
    D_D = calc_beta_ratio(qm, D, rho, mu, dp, p1_Pa=p1, tap_type="D_D")
    two_D = calc_beta_ratio(qm, D, rho, mu, dp, p1_Pa=p1, tap_type="2D")

    assert corner["tap_type"] == "corner"
    assert flange["tap_type"] == "flange"
    assert D_D["tap_type"] == "D_D"
    assert two_D["tap_type"] == "2D"


def test_cd_varies_with_tap_type():
    beta = 0.6
    Re = 1e6
    D_mm = 100.0

    cd_corner = _discharge_coefficient_rhg(beta, Re, D_mm, tap_type="corner")
    cd_flange = _discharge_coefficient_rhg(beta, Re, D_mm, tap_type="flange")
    cd_D_D = _discharge_coefficient_rhg(beta, Re, D_mm, tap_type="D_D")
    cd_2D = _discharge_coefficient_rhg(beta, Re, D_mm, tap_type="2D")

    results = set(round(c, 6) for c in [cd_corner, cd_flange, cd_D_D, cd_2D])
    assert len(results) > 1, f"All tap types gave same Cd: {results}"


def test_dd_taps_l1_equals_one():
    """ISO 5167-2 §6.1.4: D and D/2 taps place the upstream tap 1·D upstream."""
    assert TAP_TYPES["D_D"]["L1"] == 1.0
    assert TAP_TYPES["D_D"]["L2"] == 0.47


def test_invalid_tap_type():
    with pytest.raises(ValueError):
        calc_beta_ratio(10.0, 100.0, 50.0, 1.2e-5, 25000, p1_Pa=45e5, tap_type="invalid")


def test_missing_p1_raises():
    """p1_Pa is mandatory — omitting it must raise, never silently hardcode."""
    with pytest.raises(ValueError):
        calc_beta_ratio(10.0, 100.0, 50.0, 1.2e-5, 25000)


def test_low_pressure_eps_drops():
    """ε at 5 bar must be meaningfully lower than at 45 bar (old hardcode hid this)."""
    hi = calc_beta_ratio(10.0, 100.0, 50.0, 1.2e-5, 25000, p1_Pa=45e5)
    lo = calc_beta_ratio(10.0, 100.0, 50.0, 1.2e-5, 25000, p1_Pa=6e5)
    assert hi["expansibility_eps"] > lo["expansibility_eps"]
    assert lo["expansibility_eps"] < 0.995
    assert lo["p1_Pa_abs"] == pytest.approx(6e5)


def test_size_orifice_for_flow_tap():
    result = size_orifice_for_flow(
        1000, 100, 100.0, 40.0, 20.0, 20.0, 1.2e-5, 0.9, 0.8,
        tap_type="flange",
    )
    assert result["tap_type"] == "flange"
