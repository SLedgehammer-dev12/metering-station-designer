import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from metering_designer.core.units import (
    safe_convert,
    Pressure, Temperature, MassFlowRate,
    Density, Viscosity, Length,
    validate_units, ureg, Q,
)


def test_safe_convert_bar_to_pa():
    result = safe_convert(40, "bar", "Pa")
    assert abs(result - 4_000_000) < 1.0


def test_safe_convert_degc_to_k():
    result = safe_convert(20, "degC", "K")
    assert abs(result - 293.15) < 0.1


def test_safe_convert_mm_to_m():
    result = safe_convert(100, "mm", "m")
    assert abs(result - 0.1) < 1e-6


def test_safe_convert_kg_m3():
    result = safe_convert(1.2, "kg/m^3", "kg/m^3")
    assert abs(result - 1.2) < 1e-6


def test_pressure_class():
    P = Pressure(40, "bar")
    assert abs(P.Pa - 4_000_000) < 1
    assert abs(P.bar - 40) < 0.1
    assert abs(P.MPa - 4.0) < 0.01
    assert abs(P.kPa - 4000) < 1


def test_temperature_class():
    T = Temperature(20, "degC")
    assert abs(T.degC - 20) < 0.1
    assert abs(T.K - 293.15) < 0.1


def test_mass_flow_rate_class():
    m = MassFlowRate(100, "kg/h")
    assert abs(m.kg_s - 100/3600) < 0.001
    assert abs(m.kg_h - 100) < 0.1


def test_density_class():
    d = Density(30, "kg/m^3")
    assert abs(d.kg_m3 - 30) < 0.1


def test_viscosity_class():
    v = Viscosity(1, "cP")
    assert abs(v.cP - 1) < 0.01
    assert v.Pa_s > 0


def test_length_class():
    L = Length(6, "inch")
    assert abs(L.mm - 152.4) < 0.5
    assert abs(L.inch - 6) < 0.1


def test_validate_units():
    q = Q(40, "bar")
    result = validate_units(q, ureg.pascal, "pressure")
    assert isinstance(result, Q)
    assert abs(result.magnitude - 4_000_000) < 1


def test_validate_units_incompatible():
    q = Q(20, "degC")
    with pytest.raises(Exception):
        validate_units(q, ureg.pascal, "bad")
