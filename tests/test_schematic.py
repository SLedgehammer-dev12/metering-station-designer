"""Tests for the single-line flow schematic renderer (Adım D)."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest


from metering_designer.instruments.schematic import (
    render_schematic,
    render_schematic_png_bytes,
    condenser_label,
)


def test_figure_generated_for_all_meter_types():
    for meter_key in ["orifice", "ultrasonic", "turbine", "coriolis",
                      "v_cone", "venturi", "vortex", "positive_displacement"]:
        fig = render_schematic(meter_key, nps=8, upstream_config="double_bend_out_of_plane")
        assert fig is not None
        assert hasattr(fig, "savefig")


def test_png_bytes_generated():
    data = render_schematic_png_bytes("orifice", nps=8, conditioner_key="zanker",
                                      lang="tr")
    assert isinstance(data, bytes)
    assert len(data) > 1000
    assert data[:8].hex().startswith("89504e47")  # PNG magic


def test_png_en_works():
    data = render_schematic_png_bytes("turbine", nps=12, lang="en")
    assert len(data) > 1000


def test_with_straight_pipe_and_tolerances():
    sp = {"upstream_required_diameters": 18, "downstream_required_diameters": 5}
    tols = {"d (Delik Çapı)": "±0.05% / ±0.01mm", "E (Plaka Kalınlığı)": "0.005D–0.02D"}
    data = render_schematic_png_bytes("orifice", nps=8, straight_pipe=sp,
                                      tolerances=tols, lang="tr")
    assert len(data) > 1000


def test_condenser_labels():
    assert condenser_label("zanker", "tr") == "Zanker"
    assert condenser_label("tube_bundle_19", "en") == "19-Tube Bundle"