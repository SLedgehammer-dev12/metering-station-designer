"""
ISO 5167-2 / AGA Report No. 3
Orifice plate sizing and flow calculation.
"""

import math


def calc_beta_ratio(
    qm_kg_s: float,
    D_mm: float,
    rho_kg_m3: float,
    mu_Pa_s: float,
    dp_target_Pa: float = 25000,
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
    D_m = D_mm / 1000
    A_pipe = math.pi * (D_m / 2) ** 2
    v_m_s = qm_kg_s / (rho_kg_m3 * A_pipe) if rho_kg_m3 > 0 and A_pipe > 0 else 0
    Re = rho_kg_m3 * v_m_s * D_m / mu_Pa_s if mu_Pa_s > 0 else 1e6

    # Initial estimate: β from simplified ΔP equation
    # ΔP ∝ qm² / (β² * ...)
    beta = 0.6
    for i in range(30):
        eps = _expansibility_factor(beta, dp_target_Pa, 4.5e6)
        Cd = _discharge_coefficient_rhg(beta, Re, D_mm)
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
    Cd = _discharge_coefficient_rhg(beta, Re, D_mm)
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
        "notes": _generate_notes(beta, beta_ok),
    }


def _discharge_coefficient_rhg(beta: float, Re: float, D_mm: float) -> float:
    """Reader-Harris/Gallagher discharge coefficient (ISO 5167-2:2003)."""
    if Re < 100:
        return 0.6
    D_m = D_mm / 1000

    L1 = 0.0
    L2 = 0.0

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
) -> dict:
    """Size orifice meter for given gas flow range."""
    qm_max = q_max_Sm3h * rho_std_kg_m3 / 3600
    qm_min = q_min_Sm3h * rho_std_kg_m3 / 3600
    dp_max_Pa = 25000

    result = calc_beta_ratio(qm_max, D_mm, rho_kg_m3, mu_Pa_s, dp_max_Pa)

    D_m = D_mm / 1000
    A_pipe = math.pi * (D_m / 2) ** 2
    dp_min = dp_max_Pa * (qm_min / qm_max) ** 2 if qm_max > 0 else 0
    turndown_actual = q_max_Sm3h / q_min_Sm3h if q_min_Sm3h > 0 else float("inf")

    result["turndown_actual"] = round(turndown_actual, 2)
    result["dp_at_qmin_mbar"] = round(dp_min / 100, 2)
    result["dp_at_qmax_mbar"] = round(dp_max_Pa / 100, 1)
    result["velocity_ms"] = round(qm_max / (rho_kg_m3 * A_pipe), 2) if rho_kg_m3 > 0 and A_pipe > 0 else 0

    return result
