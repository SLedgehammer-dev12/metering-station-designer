"""Fluid dataclass integration tests (Phase C2)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from metering_designer.fluids.fluid import Fluid


@pytest.fixture
def sample_fluid():
    return Fluid(
        composition={"C1": 0.9, "C2": 0.05, "C3": 0.02, "N2": 0.02, "CO2": 0.01},
        M_mix=18.5,
        Z_oper=0.9,
        rho_oper_kg_m3=30.0,
        rho_std_kg_m3=0.8,
        mu_dynamic_Pa_s=1.2e-5,
        kappa=1.3,
        speed_of_sound_ms=400.0,
    )


def test_orifice_beta_with_fluid(sample_fluid):
    from metering_designer.meters.orifice import calc_beta_ratio_with_fluid
    result = calc_beta_ratio_with_fluid(10.0, 100.0, sample_fluid)
    assert 0.1 <= result["beta"] <= 0.75
    assert result["tap_type"] == "corner"


def test_orifice_beta_with_fluid_tap_type(sample_fluid):
    from metering_designer.meters.orifice import calc_beta_ratio_with_fluid
    result = calc_beta_ratio_with_fluid(10.0, 100.0, sample_fluid, tap_type="flange")
    assert result["tap_type"] == "flange"


def test_orifice_size_with_fluid(sample_fluid):
    from metering_designer.meters.orifice import size_orifice_for_flow_with_fluid
    result = size_orifice_for_flow_with_fluid(1000, 100, 100.0, sample_fluid)
    assert result["beta"] > 0


def test_ultrasonic_with_fluid(sample_fluid):
    from metering_designer.meters.ultrasonic import size_ultrasonic_with_fluid
    result = size_ultrasonic_with_fluid(6, 1000, 100, sample_fluid)
    assert result is not None


def test_turbine_with_fluid(sample_fluid):
    from metering_designer.meters.turbine import size_turbine_with_fluid
    result = size_turbine_with_fluid(6, 1000, 100, sample_fluid)
    assert result is not None


def test_coriolis_with_fluid(sample_fluid):
    from metering_designer.meters.coriolis import size_coriolis_with_fluid
    result = size_coriolis_with_fluid(6, 1000, 100, sample_fluid)
    assert result is not None


def test_pd_meter_with_fluid(sample_fluid):
    from metering_designer.meters.pd_meter import size_pd_meter_with_fluid
    result = size_pd_meter_with_fluid(6, 1000, 100, sample_fluid)
    assert result is not None


def test_vortex_with_fluid(sample_fluid):
    from metering_designer.meters.vortex import size_vortex_with_fluid
    result = size_vortex_with_fluid(6, 1000, 100, sample_fluid)
    assert result is not None


def test_vcone_with_fluid(sample_fluid):
    from metering_designer.meters.vcone import size_v_cone_with_fluid
    result = size_v_cone_with_fluid(6, 1000, 100, sample_fluid)
    assert result is not None


def test_venturi_with_fluid(sample_fluid):
    from metering_designer.meters.vcone import size_venturi_with_fluid
    result = size_venturi_with_fluid(6, 1000, 100, sample_fluid)
    assert result is not None
