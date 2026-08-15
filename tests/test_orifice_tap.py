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
    result = calc_beta_ratio(10.0, 100.0, 50.0, 1.2e-5, 25000)
    assert result["tap_type"] == "corner"


def test_different_tap_types():
    qm = 10.0
    D = 100.0
    rho = 50.0
    mu = 1.2e-5
    dp = 25000

    corner = calc_beta_ratio(qm, D, rho, mu, dp, tap_type="corner")
    flange = calc_beta_ratio(qm, D, rho, mu, dp, tap_type="flange")
    D_D = calc_beta_ratio(qm, D, rho, mu, dp, tap_type="D_D")
    two_D = calc_beta_ratio(qm, D, rho, mu, dp, tap_type="2D")

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


def test_invalid_tap_type():
    with pytest.raises(ValueError):
        calc_beta_ratio(10.0, 100.0, 50.0, 1.2e-5, 25000, tap_type="invalid")


def test_size_orifice_for_flow_tap():
    result = size_orifice_for_flow(
        1000, 100, 100.0, 40.0, 20.0, 20.0, 1.2e-5, 0.9, 0.8,
        tap_type="flange",
    )
    assert result["tap_type"] == "flange"
