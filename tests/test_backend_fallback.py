"""Backend fallback chain tests (Agent: test-backend)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from metering_designer.core.backends import calc_z_factor, get_backend_status, calc_heating_value
from metering_designer.fluids.gas import calc_gas_properties
from metering_designer.fluids.aga8 import calc_density as internal_calc


def test_pyaga8_z_reference():
    comp = {"C1": 0.9137, "C2": 0.0406, "C3": 0.0152, "N2": 0.0102, "CO2": 0.0203}
    r = calc_z_factor(45, 40, comp)
    assert 0.85 < r["Z"] < 1.00
    assert r["density_kg_m3"] > 10
    assert "backend_layer" in r


def test_internal_dak_z():
    r = internal_calc(45, 40, {"C1": 1.0})
    assert 0.85 < r["Z"] < 1.00


def test_dak_pure_methane():
    r = internal_calc(1, 15, {"C1": 1.0})
    assert 0.97 < r["Z"] < 1.01


def test_backend_consistency():
    comp = {"C1": 0.90, "C2": 0.04, "CO2": 0.02, "N2": 0.04}
    r = calc_z_factor(30, 30, comp)
    assert r["Z"] > 0.5
    assert r["density_kg_m3"] > 0


def test_mixture_molar_mass():
    comp = {"C1": 0.9137, "C2": 0.0406, "C3": 0.0152, "N2": 0.0102, "CO2": 0.0203}
    r = calc_z_factor(45, 40, comp)
    assert 16 < r["M_mix"] < 20


def test_heating_value():
    comp = {"C1": 90, "C2": 4, "C3": 1.5, "N2": 1.0, "CO2": 2.0}
    cv = calc_heating_value({k: v/100 for k, v in comp.items()})
    assert cv["gross_CV_MJ_m3"] > 35


def test_wobbe_index():
    comp = {"C1": 90, "C2": 4, "C3": 1.5, "N2": 1.0, "CO2": 2.0}
    gp = calc_gas_properties(comp, 45, 40)
    assert 40 < gp["Wobbe_MJ_m3"] < 60


def test_gas_properties_valid():
    comp = {"C1": 90, "C2": 4, "C3": 1.5, "N2": 1.0, "CO2": 2.0}
    gp = calc_gas_properties(comp, 10, 20)
    assert gp["Z_oper"] > 0.5
    assert gp["rho_oper_kg_m3"] > 0
    assert gp["gross_CV_MJ_m3"] > 0


def test_high_h2s():
    comp = {"C1": 0.85, "H2S": 0.10, "CO2": 0.03, "N2": 0.02}
    r = calc_z_factor(45, 40, comp)
    assert r["Z"] > 0.3


def test_high_co2():
    comp = {"C1": 0.75, "CO2": 0.20, "N2": 0.05}
    r = calc_z_factor(45, 40, comp)
    assert r["Z"] > 0.3
