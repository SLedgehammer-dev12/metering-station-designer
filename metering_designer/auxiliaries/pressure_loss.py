"""
Permanent pressure loss estimation for different meter types.
"""


def estimate_permanent_pressure_loss(
    meter_key: str,
    oper_p_bar: float,
    beta_ratio: float = 0.6,
    diameter_mm: float = 100.0,
    velocity_m_s: float = 10.0,
    rho_kg_m3: float = 50.0,
) -> dict:
    if "orifice" in meter_key:
        dp_mbar, formula = _orifice_pressure_loss(oper_p_bar, beta_ratio)
    elif "ultrasonic" in meter_key:
        dp_mbar, formula = 0.5 * (velocity_m_s ** 2) * rho_kg_m3 / 100, "USM: negligible loss, estimate 10Pa"
        dp_mbar = round(dp_mbar, 3)
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


def _orifice_pressure_loss(oper_p_bar: float, beta: float) -> tuple:
    loss_coeff = 1 - beta ** 2
    dp_frac = loss_coeff * 0.6
    dp_mbar = dp_frac * oper_p_bar * 1000
    formula = f"ISO 5167: ΔP = (1-β²)×ΔPorifice, β={beta}"
    return dp_mbar, formula
