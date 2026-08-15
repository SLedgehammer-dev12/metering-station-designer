"""
Pint-based unit safety layer (Phase C3).
Provides unit-aware wrappers for common metering calculations.

Usage:
    from metering_designer.core.units import Q, ureg, Pressure, Temperature
    
    P = Pressure(40, "bar")    # wraps Quantity with validation
    T = Temperature(20, "degC")
    
    # Convert to SI for calculation
    P_si = P.to("Pa")          # 4e6 Pa
    T_si = T.to("K")           # 293.15 K
"""

import pint

# Global unit registry (singleton)
ureg = pint.UnitRegistry()
Q = ureg.Quantity

# Shortcuts for common metering units
BAR = ureg.bar
PASCAL = ureg.pascal
KPA = ureg.kilopascal
MPA = ureg.megapascal
DEGC = ureg.degC
KELVIN = ureg.kelvin
KG_M3 = ureg.kilogram / ureg.meter ** 3
# Standard cubic meter for gas metering (Sm³ ≡ m³ at reference conditions)
ureg.define("standard_cubic_meter = meter**3")
ureg.define("Sm3 = standard_cubic_meter")
ureg.define("sm3 = Sm3")
SM3 = ureg.standard_cubic_meter
SM3_H = ureg.standard_cubic_meter / ureg.hour
MM = ureg.millimeter
M = ureg.meter
PA_S = ureg.pascal * ureg.second
CP = ureg.centipoise


class UnitError(ValueError):
    """Raised when a unit mismatch is detected."""
    pass


def validate_units(value, expected_unit, name=""):
    """Validate that a quantity has the expected units.
    
    Args:
        value: pint Quantity or plain number (assumed SI if plain)
        expected_unit: pint Unit
        name: optional name for error messages
    
    Returns:
        Quantity converted to expected unit
    
    Raises:
        UnitError if units are incompatible
    """
    if not isinstance(value, pint.Quantity):
        # Assume plain number is already in expected unit
        return value * expected_unit
    
    try:
        return value.to(expected_unit)
    except pint.errors.DimensionalityError as e:
        raise UnitError(f"{name}: {e}") from e


def safe_convert(
    value,
    from_unit: str,
    to_unit: str,
) -> float:
    """Safely convert a numeric value between units.
    
    Args:
        value: numeric value
        from_unit: source unit string (e.g., "bar", "degC", "kg/m^3")
        to_unit: target unit string (e.g., "Pa", "K", "kg/m^3")
    
    Returns:
        Converted numeric value
    
    Examples:
        >>> safe_convert(40, "bar", "Pa")
        4000000.0
        >>> safe_convert(20, "degC", "K")
        293.15
    """
    q = Q(value, from_unit)
    return q.to(to_unit).magnitude


def safe_mul(a, b):
    """Multiply two quantities and return the product quantity."""
    if isinstance(a, pint.Quantity) or isinstance(b, pint.Quantity):
        return a * b
    return a * b


def safe_div(a, b):
    """Divide two quantities and return the result quantity."""
    if b == 0:
        return float("inf")
    return a / b


# Convenience classes for common metering physical quantities

class Pressure:
    def __init__(self, value, unit="bar"):
        self._q = Q(value, unit)
    
    @property
    def bar(self) -> float:
        return self._q.to("bar").magnitude
    
    @property
    def Pa(self) -> float:
        return self._q.to("Pa").magnitude
    
    @property
    def kPa(self) -> float:
        return self._q.to("kPa").magnitude
    
    @property
    def MPa(self) -> float:
        return self._q.to("MPa").magnitude
    
    def to(self, unit: str) -> float:
        return self._q.to(unit).magnitude
    
    def __repr__(self) -> str:
        return f"Pressure({self._q})"


class Temperature:
    def __init__(self, value, unit="degC"):
        self._q = Q(value, unit)
    
    @property
    def degC(self) -> float:
        return self._q.to("degC").magnitude
    
    @property
    def K(self) -> float:
        return self._q.to("K").magnitude
    
    def to(self, unit: str) -> float:
        return self._q.to(unit).magnitude
    
    def __repr__(self) -> str:
        return f"Temperature({self._q})"


class MassFlowRate:
    def __init__(self, value, unit="kg/s"):
        self._q = Q(value, unit)
    
    @property
    def kg_s(self) -> float:
        return self._q.to("kg/s").magnitude
    
    @property
    def kg_h(self) -> float:
        return self._q.to("kg/h").magnitude
    
    def to(self, unit: str) -> float:
        return self._q.to(unit).magnitude

    def __repr__(self) -> str:
        return f"MassFlowRate({self._q})"


class Density:
    def __init__(self, value, unit="kg/m^3"):
        self._q = Q(value, unit)
    
    @property
    def kg_m3(self) -> float:
        return self._q.to("kg/m^3").magnitude
    
    def to(self, unit: str) -> float:
        return self._q.to(unit).magnitude

    def __repr__(self) -> str:
        return f"Density({self._q})"


class Viscosity:
    def __init__(self, value, unit="Pa*s"):
        self._q = Q(value, unit)
    
    @property
    def Pa_s(self) -> float:
        return self._q.to("Pa*s").magnitude
    
    @property
    def cP(self) -> float:
        return self._q.to("cP").magnitude
    
    def to(self, unit: str) -> float:
        return self._q.to(unit).magnitude

    def __repr__(self) -> str:
        return f"Viscosity({self._q})"


class Length:
    def __init__(self, value, unit="mm"):
        self._q = Q(value, unit)
    
    @property
    def mm(self) -> float:
        return self._q.to("mm").magnitude
    
    @property
    def m(self) -> float:
        return self._q.to("m").magnitude
    
    @property
    def inch(self) -> float:
        return self._q.to("inch").magnitude
    
    def to(self, unit: str) -> float:
        return self._q.to(unit).magnitude

    def __repr__(self) -> str:
        return f"Length({self._q})"
