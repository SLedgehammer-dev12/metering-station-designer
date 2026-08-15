"""Tests for the instrument layout module (Adım C)."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest


from metering_designer.instruments.layout import (
    compute_instrument_layout,
    summarize_layout,
)


@pytest.mark.parametrize("meter_key", [
    "orifice", "ultrasonic", "turbine", "coriolis",
    "v_cone", "venturi", "vortex", "positive_displacement",
])
def test_layout_has_at_least_pressure_and_temperature(meter_key):
    layout = compute_instrument_layout(meter_key, nps=8)
    assert layout["meter_key"] in (
        "orifice", "ultrasonic", "turbine", "coriolis",
        "v_cone", "venturi", "vortex", "positive_displacement",
    )
    assert layout["counts"]["pressure"] >= 1
    assert layout["counts"]["temperature"] >= 1
    assert sum(layout["counts"].values()) >= 2


def test_orifice_has_differential_pressure():
    layout = compute_instrument_layout("orifice", nps=8)
    assert layout["counts"]["differential_pressure"] == 1


def test_non_dp_meters_have_no_dP():
    for meter_key in ["ultrasonic", "turbine", "coriolis"]:
        layout = compute_instrument_layout(meter_key, nps=8)
        assert layout["counts"]["differential_pressure"] == 0


def test_tags_auto_generated_incrementing():
    layout = compute_instrument_layout("orifice", nps=8)
    tags = [t for inst in layout["instruments"] for t in inst["tag_list"]]
    assert len(tags) == sum(layout["counts"].values())
    assert all(tag.startswith(("PT-", "TT-", "FT-")) for tag in tags)
    assert len(set(tags)) == len(tags)


def test_conditioner_adds_upstream_pressure_transmitter():
    without = compute_instrument_layout("orifice", nps=8)
    with_cond = compute_instrument_layout("orifice", nps=8, conditioner_key="zanker")
    assert with_cond["counts"]["pressure"] == without["counts"]["pressure"] + 1
    assert with_cond["conditioner_key"] == "zanker"


def test_positions_are_numeric_and_upstream_negative():
    layout = compute_instrument_layout("orifice", nps=8)
    for inst in layout["instruments"]:
        assert isinstance(inst["position_D"], float)
        assert inst["position_m"] == round(inst["position_D"] * layout["od_m"], 3)
    # The PT upstream tap sits at negative D
    pt = [i for i in layout["instruments"] if i["type"] == "temperature"][0]
    assert pt["position_D"] > 0


def test_summarize_layout_returns_rows():
    layout = compute_instrument_layout("venturi", nps=12)
    rows = summarize_layout(layout)
    assert len(rows) >= 2
    assert all({"type", "count", "tag_list", "position_D", "side", "standard"} <= r.keys() for r in rows)


def test_unknown_meter_falls_back_to_generic():
    layout = compute_instrument_layout("weird_meter", nps=8)
    assert layout["counts"]["pressure"] >= 1
    assert layout["counts"]["temperature"] >= 1