"""Tests for straight-pipe requirements incl. flow-conditioner reduction."""
import pytest

from metering_designer.auxiliaries.straight_pipe import (
    calc_straight_pipe,
    FLOW_CONDITIONER_REDUCTION,
)


def test_baseline_no_conditioner():
    r = calc_straight_pipe("orifice", 8, "single_bend_90")
    assert r["upstream_required_diameters"] == 18
    assert r["downstream_required_diameters"] == 5
    assert r["with_conditioner"] is None
    assert r["conditioner_notes"] is None


def test_unknown_config_falls_back_single_bend():
    r = calc_straight_pipe("orifice", 8, "not_a_real_config")
    assert r["upstream_config"] == "not_a_real_config"
    assert r["upstream_required_diameters"] == 18


def test_gallagher_reduces_upstream():
    base = calc_straight_pipe("orifice", 8, "single_bend_90")
    r = calc_straight_pipe("orifice", 8, "single_bend_90", with_conditioner="gallagher")
    assert r["with_conditioner"] == "gallagher"
    assert r["upstream_required_diameters"] < base["upstream_required_diameters"]
    assert r["downstream_required_diameters"] == 5
    assert "AGA 9" in r["conditioner_notes"]


def test_each_conditioner_in_lookup():
    for key, spec in FLOW_CONDITIONER_REDUCTION.items():
        r = calc_straight_pipe("orifice", 8, "single_bend_90", with_conditioner=key)
        expected = spec["upstream"] + spec["downstream"]
        assert r["upstream_required_diameters"] == expected, key
        assert r["conditioner_notes"] == spec["notes"], key


def test_total_length_scales_with_nps():
    small = calc_straight_pipe("orifice", 4, "single_bend_90")
    big = calc_straight_pipe("orifice", 16, "single_bend_90")
    assert big["total_required_m"] > small["total_required_m"]


def test_beta_adjustment_applied_for_orifice():
    low_beta = calc_straight_pipe("orifice", 8, "single_bend_90", beta_ratio=0.2)
    high_beta = calc_straight_pipe("orifice", 8, "single_bend_90", beta_ratio=0.8)
    assert low_beta["upstream_required_diameters"] <= high_beta["upstream_required_diameters"]


def test_ultrasonic_mapping():
    r = calc_straight_pipe("ultrasonic", 8, "single_bend_90")
    assert r["meter_type"] == "ultrasonic"
    assert r["upstream_required_diameters"] == 10


def test_coriolis_maps_to_orifice_defaults():
    r = calc_straight_pipe("coriolis_e_mass", 8, "single_bend_90")
    assert r["meter_type"] == "orifice"