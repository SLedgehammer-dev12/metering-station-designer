"""
Permanent pressure loss estimation for different meter types.
ISO 5167-2 / AGA standards compliant.
"""

import math
from metering_designer.core.result import Result


def estimate_permanent_pressure_loss(
    meter_key: str,
    oper_p_bar: float,
    beta_ratio: float = 0.6,
    diameter_mm: float = 100.0,
    velocity_m_s: float = 10.0,
    rho_kg_m3: float = 50.0,
    dp_orifice_mbar: float = None,
) -> dict:
    if "orifice" in meter_key:
        dp_mbar, formula = _orifice_pressure_loss(beta_ratio, dp_orifice_mbar)
    elif "venturi" in meter_key or "v_cone" in meter_key or "vcone" in meter_key:
        dp_mbar, formula = _orifice_pressure_loss(beta_ratio, dp_orifice_mbar)
    elif "ultrasonic" in meter_key:
        dp_mbar = 0.5 * (velocity_m_s ** 2) * rho_kg_m3 / 100
        formula = "USM: negligible loss, ~dynamic pressure fraction"
    elif "turbine" in meter_key:
        dp_mbar = 50 + 0.02 * (velocity_m_s ** 2) * rho_kg_m3 / 100
        formula = "Turbine: bearing + friction loss"
    elif "coriolis" in meter_key:
        dp_mbar = 200 + 0.5 * (velocity_m_s ** 2) * rho_kg_m3 / 100
        formula = "Coriolis: tube restriction loss"
    elif "positive_displacement" in meter_key or "pd" in meter_key:
        dp_mbar = 200 + 100 * (velocity_m_s / 10)
        formula = "PD meter: mechanical friction + seal loss"
    elif "vortex" in meter_key:
        dp_mbar = 150 * (velocity_m_s / 10) ** 1.5
        formula = "Vortex: bluff body loss"
    else:
        dp_mbar = 50
        formula = "Generic estimate"

    dp_bar = dp_mbar / 1000
    dp_percent = (dp_bar / oper_p_bar * 100) if oper_p_bar > 0 else 0

    return {
        "dp_mbar": round(dp_mbar, 1),
        "dp_bar": round(dp_bar, 4),
        "dp_pct_of_oper_p": round(dp_percent, 3),
        "velocity_m_s": velocity_m_s,
        "formula": formula,
    }


def _orifice_pressure_loss(beta: float, dp_orifice_mbar: float = None) -> tuple:
    if dp_orifice_mbar is None:
        dp_orifice_mbar = 250.0

    b2 = beta ** 2
    b4 = beta ** 4
    b8 = beta ** 8

    C = 0.5961 + 0.0261 * b2 - 0.216 * b8
    C = max(C, 0.55)

    numerator = math.sqrt(1 - b4 * (1 - C ** 2)) - C * b2
    denominator = math.sqrt(1 - b4 * (1 - C ** 2)) + C * b2
    loss_fraction = numerator / denominator if denominator > 0 else 0.0

    dp_perm_mbar = loss_fraction * dp_orifice_mbar
    formula = (
        f"ISO 5167-2 permanent loss: Δω/Δp={loss_fraction:.3f}, "
        f"β={beta:.3f}, Δp_orifice={dp_orifice_mbar:.0f} mbar"
    )
    return dp_perm_mbar, formula


def calc_orifice_pressure_loss_result(
    beta: float = 0.5,
    dp_orifice_Pa: float = 25000,
) -> Result:
    """Calculate orifice permanent pressure loss with provenance tracking."""
    result = Result()
    try:
        dp_orifice_mbar = dp_orifice_Pa / 100
        dp_perm_mbar, formula = _orifice_pressure_loss(beta, dp_orifice_mbar)
        result.data = {
            "dp_permanent_Pa": round(dp_perm_mbar * 100, 1),
            "dp_permanent_mbar": round(dp_perm_mbar, 1),
            "dp_orifice_Pa": round(dp_orifice_Pa, 0),
            "dp_orifice_mbar": round(dp_orifice_mbar, 1),
            "formula": formula,
            "beta": beta,
        }
        result.add_provenance(
            function_name="calc_orifice_pressure_loss",
            parameters={"beta": beta, "dp_orifice_Pa": dp_orifice_Pa},
            standard_ref="ISO 5167-2:2003 §6.3",
        )
    except Exception as e:
        result.errors.append(str(e))
    return result
