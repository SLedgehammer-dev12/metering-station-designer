"""Shared fixtures for all test modules."""
import pytest


@pytest.fixture
def sample_gas_composition():
    """Typical pipeline natural gas composition (mole fractions)."""
    return {"C1": 0.90, "C2": 0.04, "C3": 0.015, "iC4": 0.002, "nC4": 0.002,
            "N2": 0.01, "CO2": 0.02, "H2S": 0.001}


@pytest.fixture
def typical_meter_inputs():
    """Standard meter selection inputs for gas metering station."""
    return {
        "fluid_type": "gas", "nps": 10, "design_p_bar": 70.0, "design_t_c": 60.0,
        "oper_p_bar": 55.0, "oper_t_c": 45.0, "qmin": 10000, "qmax": 80000, "qnormal": 30000,
        "service_type": "custody_transfer", "target_uncertainty": 0.5,
        "composition": {"C1": 0.90, "C2": 0.04, "C3": 0.015, "N2": 0.01, "CO2": 0.02},
        "h2s": False, "upstream_config": "single_bend_90", "material": "A106_GrB",
    }


@pytest.fixture
def liquid_meter_inputs():
    """Meter selection inputs for crude oil / liquid metering station."""
    return {
        "fluid_type": "liquid", "nps": 8, "design_p_bar": 100.0, "design_t_c": 80.0,
        "oper_p_bar": 60.0, "oper_t_c": 50.0, "qmin": 500, "qmax": 5000, "qnormal": 2000,
        "service_type": "custody_transfer", "target_uncertainty": 0.3,
        "fluid_name": "crude_oil", "density_kg_m3": 850.0, "viscosity_cp": 12.0,
        "h2s": True, "h2s_ppm": 5000, "has_chlorides": True, "chloride_ppm": 30000,
        "offshore": True, "upstream_config": "double_bend_out_of_plane",
        "material": "Duplex_2205",
    }


@pytest.fixture
def sour_gas_composition():
    """Sour natural gas composition with 1% H2S (mole fractions)."""
    return {"C1": 0.85, "C2": 0.05, "C3": 0.02, "iC4": 0.005, "nC4": 0.005,
            "N2": 0.02, "CO2": 0.03, "H2S": 0.01}


@pytest.fixture
def venturi_inputs():
    """Inputs suitable for classical venturi meter sizing."""
    return {
        "fluid_type": "gas", "nps": 12, "design_p_bar": 100.0, "design_t_c": 80.0,
        "oper_p_bar": 70.0, "oper_t_c": 55.0, "qmin": 20000, "qmax": 150000, "qnormal": 60000,
        "beta": 0.55, "service_type": "custody_transfer", "target_uncertainty": 0.75,
        "composition": {"C1": 0.88, "C2": 0.06, "C3": 0.02, "N2": 0.02, "CO2": 0.02},
        "h2s": False, "upstream_config": "straight_pipe", "material": "API_5L_X52",
    }


@pytest.fixture
def all_api5l_grades():
    return ["API_5L_B", "API_5L_X42", "API_5L_X46", "API_5L_X52", "API_5L_X56",
            "API_5L_X60", "API_5L_X65", "API_5L_X70", "API_5L_X80"]
