"""
ISO 5167-2 / AGA Report No. 3
Orifice plate sizing and flow calculation.
"""

import math
from metering_designer.core.result import Result

TAP_TYPES = {
    "corner": {"description": "Corner taps (ISO 5167-2 §6.1.2)", "L1": 0.0, "L2": 0.0},
    "flange": {"description": "Flange taps (ISO 5167-2 §6.1.3)", "L1": None, "L2": None},  # L = 25.4/D_mm
    "D_D": {"description": "D-D/2 taps (ISO 5167-2 §6.1.4)", "L1": 0.5, "L2": 0.47},
    "2D": {"description": "2D and 2D taps", "L1": 2.0, "L2": 2.0},
}


def list_tap_types() -> list:
    """Return list of supported orifice tap types with descriptions."""
    return [
        {"name": name, "description": cfg["description"]}
        for name, cfg in TAP_TYPES.items()
    ]


def calc_beta_ratio(
    qm_kg_s: float,
    D_mm: float,
    rho_kg_m3: float,
    mu_Pa_s: float,
    dp_target_Pa: float = 25000,
    tap_type: str = "corner",
) -> dict:
    """
    Calculate orifice beta ratio (d/D) for a given mass flow rate.
    Uses iterative approach per ISO 5167-2 / AGA 3.

    Args:
        qm_kg_s: mass flow rate [kg/s]
        D_mm: pipe internal diameter [mm]
        rho_kg_m3: fluid density [kg/m³]
        mu_Pa_s: dynamic viscosity [Pa·s]
        dp_target_Pa: target differential pressure [Pa] (default 250 mbar)
    """
    if tap_type not in TAP_TYPES:
        raise ValueError(
            f"Unknown tap_type '{tap_type}'. Available options: {', '.join(TAP_TYPES.keys())}"
        )

    D_m = D_mm / 1000
    A_pipe = math.pi * (D_m / 2) ** 2
    v_m_s = qm_kg_s / (rho_kg_m3 * A_pipe) if rho_kg_m3 > 0 and A_pipe > 0 else 0
    Re = rho_kg_m3 * v_m_s * D_m / mu_Pa_s if mu_Pa_s > 0 else 1e6

    # Initial estimate: β from simplified ΔP equation
    # ΔP ∝ qm² / (β² * ...)
    beta = 0.6
    for i in range(30):
        eps = _expansibility_factor(beta, dp_target_Pa, 4.5e6)
        Cd = _discharge_coefficient_rhg(beta, Re, D_mm, tap_type=tap_type)
        d_mm = beta * D_mm
        d_m = d_mm / 1000
        A_throat = math.pi * (d_m / 2) ** 2
        E = 1.0 / math.sqrt(1 - beta ** 4)

        # Flow equation: qm = Cd * eps * E * A_throat * sqrt(2*rho*ΔP) / sqrt(1-β⁴)
        # Rearranged for qm verification
        qm_calc = Cd * eps * A_throat * math.sqrt(2 * rho_kg_m3 * dp_target_Pa) / math.sqrt(1 - beta ** 4)

        # Refine β
        if qm_calc <= 0:
            beta = min(beta + 0.1, 0.75)
            continue

        factor = qm_kg_s / qm_calc
        target_factor = 1.0
        beta_new = beta * math.pow(factor, 0.25) if factor > 0 else beta

        if beta_new < 0.1:
            beta_new = 0.1
        elif beta_new > 0.75:
            beta_new = 0.75

        if abs(beta_new - beta) < 1e-5:
            beta = beta_new
            break
        beta = beta_new

    # Final Cd with converged β
    beta = max(0.1, min(beta, 0.75))
    d_mm = beta * D_mm
    Cd = _discharge_coefficient_rhg(beta, Re, D_mm, tap_type=tap_type)
    eps = _expansibility_factor(beta, dp_target_Pa, 4.5e6)
    d_m = d_mm / 1000
    A_throat = math.pi * (d_m / 2) ** 2

    # Permanent pressure loss
    pl_ratio = 1.0 - (beta ** 1.9)
    dp_permanent_Pa = dp_target_Pa * pl_ratio

    # Check β limits per ISO 5167-2
    beta_ok = 0.1 <= beta <= 0.75
    re_limits_ok = _check_Re_limits(beta, Re, D_mm)

    return {
        "beta": round(beta, 5),
        "d_mm": round(d_mm, 3),
        "Cd": round(Cd, 5),
        "Cd_formula": "Reader-Harris/Gallagher (1998)",
        "expansibility_eps": round(eps, 5),
        "Re": round(Re, 0),
        "dp_orifice_Pa": round(dp_target_Pa, 0),
        "dp_orifice_mbar": round(dp_target_Pa / 100, 1),
        "dp_permanent_Pa": round(dp_permanent_Pa, 0),
        "dp_permanent_mbar": round(dp_permanent_Pa / 100, 1),
        "beta_valid": beta_ok,
        "Re_valid": re_limits_ok,
        "tap_type": tap_type,
        "tap_type_description": TAP_TYPES.get(tap_type, {}).get("description", ""),
        "notes": _generate_notes(beta, beta_ok),
    }


def _discharge_coefficient_rhg(beta: float, Re: float, D_mm: float, tap_type: str = "corner") -> float:
    """Reader-Harris/Gallagher discharge coefficient (ISO 5167-2:2003)."""
    if Re < 100:
        return 0.6
    D_m = D_mm / 1000

    # Determine L1 and L2 based on tap type per ISO 5167-2 §6.1
    tap_type = tap_type or "corner"
    if tap_type not in TAP_TYPES:
        tap_type = "corner"

    L1_cfg = TAP_TYPES[tap_type]["L1"]
    L2_cfg = TAP_TYPES[tap_type]["L2"]

    if L1_cfg is None:  # flange taps: distance = 25.4 mm (1 inch)
        L1 = 25.4 / D_mm if D_mm > 0 else 0.0
        L2 = 25.4 / D_mm if D_mm > 0 else 0.0
    else:
        L1 = L1_cfg
        L2 = L2_cfg

    term1 = 0.5961 + 0.0261 * beta ** 2 - 0.216 * beta ** 8
    term2 = 0.000521 * (1e6 * beta / Re) ** 0.7
    term3 = (0.0188 + 0.0063 * _A(beta)) * beta ** 3.5 * (1e6 / Re) ** 0.3
    term4 = (0.043 + 0.080 * math.exp(-10 * L1) - 0.123 * math.exp(-7 * L1)) * (1 - 0.11 * _A(beta)) * (beta ** 4 / (1 - beta ** 4))
    term5 = -0.031 * (L2 - 0.8 * L2 ** 1.1) * beta ** 1.3

    if D_m < 0.07112:
        term6 = 0.011 * (0.75 - beta) * (2.8 - D_m / 0.0254)
    else:
        term6 = 0.0

    return term1 + term2 + term3 + term4 + term5 + term6


def _A(beta: float) -> float:
    return (19000 * beta / 1e6) ** 0.8


def _expansibility_factor(beta: float, dp_Pa: float, p1_Pa: float) -> float:
    """Expansibility factor for gases per ISO 5167-2."""
    if p1_Pa <= 0:
        return 1.0
    tau = 1 - dp_Pa / p1_Pa
    if tau < 0:
        tau = 0.01
    kappa = 1.3  # isentropic exponent for natural gas
    return 1 - (0.351 + 0.256 * beta ** 4 + 0.93 * beta ** 8) * (1 - tau ** (1.0 / kappa))


def _check_Re_limits(beta: float, Re: float, D_mm: float) -> bool:
    if beta <= 0.56:
        return Re >= 5000
    elif beta <= 0.75:
        return Re >= 10000
    return Re >= 20000


def _generate_notes(beta: float, beta_ok: bool) -> str:
    notes = []
    if not beta_ok:
        notes.append("β ISO 5167-2 sınırları dışında (0.1-0.75)")
    if beta > 0.6:
        notes.append("β > 0.6, belirsizlik artar; β < 0.6 önerilir")
    if beta < 0.2:
        notes.append("β < 0.2, düşük duyarlılık; daha küçük DP aralığı düşünün")
    return "; ".join(notes) if notes else "β sınırlar içinde"


def size_orifice_for_flow(
    q_max_Sm3h: float,
    q_min_Sm3h: float,
    D_mm: float,
    P_oper_bar: float,
    T_oper_C: float,
    rho_kg_m3: float,
    mu_Pa_s: float,
    Z: float,
    rho_std_kg_m3: float,
    tap_type: str = "corner",
) -> dict:
    """Size orifice meter for given gas flow range."""
    qm_max = q_max_Sm3h * rho_std_kg_m3 / 3600
    qm_min = q_min_Sm3h * rho_std_kg_m3 / 3600
    dp_max_Pa = 25000

    result = calc_beta_ratio(qm_max, D_mm, rho_kg_m3, mu_Pa_s, dp_max_Pa, tap_type=tap_type)

    D_m = D_mm / 1000
    A_pipe = math.pi * (D_m / 2) ** 2
    dp_min = dp_max_Pa * (qm_min / qm_max) ** 2 if qm_max > 0 else 0
    turndown_actual = q_max_Sm3h / q_min_Sm3h if q_min_Sm3h > 0 else float("inf")

    result["turndown_actual"] = round(turndown_actual, 2)
    result["turndown_ok"] = turndown_actual >= 10
    result["dp_at_qmin_mbar"] = round(dp_min / 100, 2)
    result["dp_at_qmax_mbar"] = round(dp_max_Pa / 100, 1)
    result["velocity_ms"] = round(qm_max / (rho_kg_m3 * A_pipe), 2) if rho_kg_m3 > 0 and A_pipe > 0 else 0

    return result


def calc_beta_ratio_with_fluid(
    qm_kg_s: float,
    D_mm: float,
    fluid: "Fluid",
    dp_target_Pa: float = 25000,
    tap_type: str = "corner",
) -> dict:
    """Wrapper around calc_beta_ratio that extracts fluid props from Fluid object.

    Args:
        qm_kg_s: mass flow rate [kg/s]
        D_mm: pipe internal diameter [mm]
        fluid: Fluid dataclass instance with rho_oper_kg_m3, mu_dynamic_Pa_s
        dp_target_Pa: target differential pressure [Pa]
        tap_type: tap type ("corner", "flange", "D_D", "2D")
    """
    from metering_designer.fluids.fluid import Fluid

    rho = fluid.rho_oper_kg_m3 if hasattr(fluid, "rho_oper_kg_m3") else 0
    mu = fluid.mu_dynamic_Pa_s if hasattr(fluid, "mu_dynamic_Pa_s") else 1e-5

    return calc_beta_ratio(qm_kg_s, D_mm, rho, mu, dp_target_Pa, tap_type=tap_type)


def size_orifice_for_flow_with_fluid(
    q_max_Sm3h: float,
    q_min_Sm3h: float,
    D_mm: float,
    fluid: "Fluid",
    P_oper_bar: float = 40.0,
    T_oper_C: float = 20.0,
    tap_type: str = "corner",
) -> dict:
    """Wrapper around size_orifice_for_flow that accepts Fluid.

    Args:
        q_max_Sm3h: maximum flow rate [Sm³/h]
        q_min_Sm3h: minimum flow rate [Sm³/h]
        D_mm: pipe internal diameter [mm]
        fluid: Fluid dataclass instance
        P_oper_bar: operating pressure [bar]
        T_oper_C: operating temperature [°C]
        tap_type: tap type ("corner", "flange", "D_D", "2D")
    """
    from metering_designer.fluids.fluid import Fluid

    rho = fluid.rho_oper_kg_m3
    mu = fluid.mu_dynamic_Pa_s
    rho_std = fluid.rho_std_kg_m3
    Z = fluid.Z_oper

    return size_orifice_for_flow(
        q_max_Sm3h, q_min_Sm3h, D_mm, P_oper_bar, T_oper_C,
        rho, mu, Z, rho_std, tap_type=tap_type,
    )


def calc_beta_ratio_result(
    qm_kg_s: float,
    D_mm: float,
    rho_kg_m3: float,
    mu_Pa_s: float,
    dp_target_Pa: float = 25000,
    tap_type: str = "corner",
) -> Result:
    """Calculate orifice beta ratio with provenance tracking."""
    result = Result()
    try:
        data = calc_beta_ratio(qm_kg_s, D_mm, rho_kg_m3, mu_Pa_s, dp_target_Pa, tap_type=tap_type)
        result.data = data
        result.add_provenance(
            function_name="calc_beta_ratio",
            parameters={"tap_type": tap_type, "dp_target_Pa": dp_target_Pa},
            standard_ref="ISO 5167-2:2003",
        )
        if not data.get("beta_valid", False):
            result.warnings.append("Beta ratio outside ISO 5167-2 recommended range (0.1-0.75)")
    except Exception as e:
        result.errors.append(str(e))
    return result
