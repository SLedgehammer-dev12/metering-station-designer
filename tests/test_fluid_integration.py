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


# ---------------------------------------------------------------------------
# Faz 1: real-gas thermodynamics (LGE viscosity, compressibility-aware SOS)
# ---------------------------------------------------------------------------

def test_lge_viscosity_increases_with_pressure():
    """LGE density-based viscosity rises with pressure (Pa·s)."""
    from metering_designer.fluids.gas import calc_gas_properties

    comp = {"C1": 0.90, "C2": 0.04, "C3": 0.015, "N2": 0.02, "CO2": 0.025}
    p1 = calc_gas_properties(comp, 45, 40)
    p2 = calc_gas_properties(comp, 120, 40)

    # Typical NG at 45 bar / 40 °C: mu ≈ 1.1e-5 – 1.4e-5 Pa·s
    assert 0.9e-5 < p1["mu_dynamic_Pa_s"] < 1.9e-5, (
        f"mu={p1['mu_dynamic_Pa_s']} outside LGE expected band"
    )
    # Density-based LGE must capture the viscosity rise with pressure
    assert p2["mu_dynamic_Pa_s"] > p1["mu_dynamic_Pa_s"], (
        "viscosity must increase with pressure"
    )


def test_real_gas_speed_of_sound():
    """Real-gas speed of sound for typical NG at 45 bar/40 °C ≈ 380–470 m/s."""
    from metering_designer.fluids.gas import calc_gas_properties

    comp = {"C1": 0.90, "C2": 0.04, "C3": 0.015, "N2": 0.02, "CO2": 0.025}
    props = calc_gas_properties(comp, 45, 40)
    sos = props["speed_of_sound_ms"]
    assert 380 < sos < 470, f"SOS={sos} outside expected 380–470 m/s band"
    assert props["Z_oper"] < 0.96, "Z should reflect real-gas compressibility"


def test_speed_of_sound_includes_compressibility():
    """c = sqrt(kappa·Z·R·T/M) drops as Z drops below 1."""
    from metering_designer.fluids.gas import calc_speed_of_sound

    c_ideal = calc_speed_of_sound(313.15, 17.7, 1.15, 33.0, Z=1.0)
    c_real = calc_speed_of_sound(313.15, 17.7, 1.15, 33.0, Z=0.90)
    assert c_real < c_ideal, "real-gas SOS must be lower than ideal-gas at Z<1"
    assert 0.85 * c_ideal < c_real < 0.98 * c_ideal
