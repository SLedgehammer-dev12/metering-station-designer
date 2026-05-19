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
def all_api5l_grades():
    return ["API_5L_B", "API_5L_X42", "API_5L_X46", "API_5L_X52", "API_5L_X56",
            "API_5L_X60", "API_5L_X65", "API_5L_X70", "API_5L_X80"]
