"""
ISO 5167-2 / AGA Report No. 3
Orifice plate sizing and flow calculation.
"""

import math
from metering_designer.core.result import Result

TAP_TYPES = {
    "corner": {"description": "Corner taps (ISO 5167-2 §6.1.2)", "L1": 0.0, "L2": 0.0},
    "flange": {"description": "Flange taps (ISO 5167-2 §6.1.3)", "L1": None, "L2": None},  # L = 25.4/D_mm
    "D_D": {"description": "D-D/2 taps (ISO 5167-2 §6.1.4)", "L1": 1.0, "L2": 0.47},
    "2D": {"description": "2D and 2D taps", "L1": 2.0, "L2": 2.0},
}


def list_tap_types() -> list:
    """Return list of supported orifice tap types with descriptions."""
    return [
        {"name": name, "description": cfg["description"]}
        for name, cfg in TAP_TYPES.items()
    ]


def _standard_profile(tap_type: str | None, standard: str | None) -> dict:
    """Resolve the design standard profile and reconcile the tap default.

    Returns a merged dict with ``standard`` (id), ``standard_name``,
    ``standard_ref``, ``tap_type`` and the beta/advisory limits.
    """
    from metering_designer.standards.design_standards import get_standard

    profile = get_standard("orifice", standard) or {}
    std_id = (standard or "iso5167_2").lower()
    if std_id not in ("iso5167_2", "aga3"):
        std_id = "iso5167_2"

    # A standard with a mandated default tap wins only when the caller did not
    # pick one explicitly (tap_type defaults to the standard's default tap).
    resolved_tap = tap_type
    if resolved_tap is None:
        resolved_tap = profile.get("default_tap", "corner")
    if resolved_tap not in TAP_TYPES:
        resolved_tap = "corner"

    return {
        "standard": std_id,
        "standard_name": profile.get("name", "ISO 5167-2:2022"),
        "standard_ref": profile.get("standard_ref", "ISO 5167-2:2022"),
        "tap_type": resolved_tap,
        "tap_type_description": TAP_TYPES[resolved_tap]["description"],
        "beta_limits": profile.get("beta_limits", (0.1, 0.75)),
        "beta_recommended": profile.get("beta_recommended", (0.2, 0.65)),
        "D_min_mm": profile.get("D_min_mm", 50.0),
        "dp_recommended_mbar": profile.get("dp_recommended_mbar", 250),
        "dp_range_mbar": profile.get("dp_range_mbar", (20, 1000)),
        "cd_formula": profile.get("cd_formula", "Reader-Harris/Gallagher (1998)"),
    }


def calc_beta_ratio(
    qm_kg_s: float,
    D_mm: float,
    rho_kg_m3: float,
    mu_Pa_s: float,
    dp_target_Pa: float = 25000,
    p1_Pa: float = None,
    tap_type: str = "corner",
    standard: str | None = None,
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
        p1_Pa: upstream pressure [Pa ABSOLUTE]. Required — the expansibility
            factor ε depends on p1, and hardcoding a nominal 45 bar produced
            wrong results at low pressure (ε→1 at 5 bar vs 0.984 at 45 bar).
        tap_type: tap type; when None the selected standard's default is used
        standard: design standard id ('iso5167_2' or 'aga3')
    """
    if p1_Pa is None:
        raise ValueError("p1_Pa (upstream absolute pressure in Pa) is required")
    if tap_type is not None and tap_type not in TAP_TYPES:
        raise ValueError(
            f"Unknown tap_type '{tap_type}'. Available options: {', '.join(TAP_TYPES.keys())}"
        )
    std = _standard_profile(tap_type, standard)
    tap_type = std["tap_type"]
    beta_limit_lo, beta_limit_hi = std["beta_limits"]

    D_m = D_mm / 1000
    A_pipe = math.pi * (D_m / 2) ** 2
    v_m_s = qm_kg_s / (rho_kg_m3 * A_pipe) if rho_kg_m3 > 0 and A_pipe > 0 else 0
    Re = rho_kg_m3 * v_m_s * D_m / mu_Pa_s if mu_Pa_s > 0 else 1e6

    def _flow_at(beta: float, dp_Pa: float) -> float:
        """qm at given β and ΔP per ISO 5167-2 (Cd·ε·A_t·√(2ρΔP)/√(1−β⁴))."""
        if rho_kg_m3 <= 0 or A_pipe <= 0:
            return 0.0
        eps = _expansibility_factor(beta, dp_Pa, p1_Pa)
        Cd = _discharge_coefficient_rhg(beta, Re, D_mm, tap_type=tap_type)
        d_m = (beta * D_mm / 1000) / 2
        A_throat = math.pi * d_m ** 2
        return Cd * eps * A_throat * math.sqrt(2 * rho_kg_m3 * dp_Pa) / math.sqrt(1 - beta ** 4)

    # Solve for β that passes qm at the target ΔP. qm_calc increases
    # monotonically with β, so bisection within the standard's β limits is
    # exact. When the required β falls outside the limits the design is
    # saturated: the target ΔP is not achievable on this line/flow.
    beta = 0.6
    beta_saturated = False
    saturation_dir = None
    if qm_kg_s > 0 and rho_kg_m3 > 0 and A_pipe > 0:
        qm_hi = _flow_at(beta_limit_hi, dp_target_Pa)
        qm_lo = _flow_at(beta_limit_lo, dp_target_Pa)
        if qm_hi < qm_kg_s:
            # Even the largest bore passes too little flow at the target ΔP →
            # the requested ΔP is below what this line can achieve; β pins high.
            beta = beta_limit_hi
            beta_saturated = True
            saturation_dir = "low"
        elif qm_lo > qm_kg_s:
            # Even the smallest bore passes too much flow → ΔP target too high;
            # β pins low.
            beta = beta_limit_lo
            beta_saturated = True
            saturation_dir = "high"
        else:
            lo, hi = beta_limit_lo, beta_limit_hi
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                if _flow_at(mid, dp_target_Pa) < qm_kg_s:
                    lo = mid
                else:
                    hi = mid
                if (hi - lo) < 1e-7:
                    break
            beta = 0.5 * (lo + hi)

    d_mm = beta * D_mm
    Cd = _discharge_coefficient_rhg(beta, Re, D_mm, tap_type=tap_type)
    eps = _expansibility_factor(beta, dp_target_Pa, p1_Pa)

    # Achievable ΔP at the solved β (invert the flow equation). Relevant when
    # saturated: the plate can only deliver this ΔP at Qmax, not the target.
    dp_actual_Pa = dp_target_Pa
    if qm_kg_s > 0 and rho_kg_m3 > 0:
        d_m = d_mm / 1000
        A_throat = math.pi * (d_m / 2) ** 2
        if A_throat > 0:
            dp_actual_Pa = (qm_kg_s * math.sqrt(1 - beta ** 4) / (Cd * eps * A_throat)) ** 2 / (2 * rho_kg_m3)
            if dp_actual_Pa > 0:
                # Re-resolve ε at the achievable ΔP (one pass is sufficient).
                eps = _expansibility_factor(beta, dp_actual_Pa, p1_Pa)
                dp_actual_Pa = (qm_kg_s * math.sqrt(1 - beta ** 4) / (Cd * eps * A_throat)) ** 2 / (2 * rho_kg_m3)

    dp_attainable = not beta_saturated
    if dp_attainable:
        dp_attainable = abs(dp_actual_Pa - dp_target_Pa) / dp_target_Pa < 0.005

    # Permanent pressure loss from the ACTUAL ΔP of the designed plate.
    pl_ratio = 1.0 - (beta ** 1.9)
    dp_permanent_Pa = dp_actual_Pa * pl_ratio

    # Check β limits per selected standard
    beta_ok = beta_limit_lo <= beta <= beta_limit_hi
    re_limits_ok = _check_Re_limits(beta, Re, D_mm)

    return {
        "beta": round(beta, 5),
        "d_mm": round(d_mm, 3),
        "Cd": round(Cd, 5),
        "Cd_formula": std["cd_formula"],
        "expansibility_eps": round(eps, 5),
        "p1_Pa_abs": round(p1_Pa, 0),
        "Re": round(Re, 0),
        "dp_orifice_Pa": round(dp_target_Pa, 0),
        "dp_orifice_mbar": round(dp_target_Pa / 100, 1),
        "dp_actual_Pa": round(dp_actual_Pa, 0),
        "dp_actual_mbar": round(dp_actual_Pa / 100, 1),
        "dp_attainable": dp_attainable,
        "beta_saturated": beta_saturated,
        "saturation_dir": saturation_dir,
        "dp_permanent_Pa": round(dp_permanent_Pa, 0),
        "dp_permanent_mbar": round(dp_permanent_Pa / 100, 1),
        "beta_valid": beta_ok,
        "Re_valid": re_limits_ok,
        "tap_type": tap_type,
        "tap_type_description": std["tap_type_description"],
        "standard": std["standard"],
        "standard_name": std["standard_name"],
        "standard_ref": std["standard_ref"],
        "beta_limits": list(std["beta_limits"]),
        "beta_recommended": list(std["beta_recommended"]),
        "notes": _generate_notes(beta, beta_ok, std),
    }


def generate_design_advisories(beta: float, dp_at_qmin_mbar: float,
                               dp_design_mbar: float, standard: dict | None = None,
                               dp_attainable: bool = True,
                               dp_actual_mbar: float | None = None) -> list[dict]:
    """Produce structured advisory messages for the design dP and β choice.

    Each entry: {'level': 'info'|'warning', 'key': <i18n key>, 'values': {...}}.
    Used by the engineering UI to guide the user toward a well-conditioned
    orifice design per the selected standard.
    """
    from metering_designer.standards.design_standards import get_standard

    profile = standard or get_standard("orifice", "iso5167_2") or {}
    beta_rec_lo, beta_rec_hi = profile.get("beta_recommended", (0.2, 0.65))
    beta_lo, beta_hi = profile.get("beta_limits", (0.1, 0.75))

    advisories = []
    if beta_rec_lo <= beta <= beta_rec_hi:
        advisories.append({"level": "info", "key": "std_adv_beta_ok",
                           "values": {"lo": beta_rec_lo, "hi": beta_rec_hi}})
    elif beta > beta_hi or beta < beta_lo:
        advisories.append({"level": "warning", "key": "std_adv_beta_out_of_limits",
                           "values": {"lo": beta_lo, "hi": beta_hi}})
    elif beta > beta_rec_hi:
        advisories.append({"level": "warning", "key": "std_adv_beta_high",
                           "values": {"hi": beta_rec_hi}})
    elif beta < beta_rec_lo:
        advisories.append({"level": "warning", "key": "std_adv_beta_low",
                           "values": {"lo": beta_rec_lo}})

    if not dp_attainable:
        advisories.append({"level": "warning", "key": "std_adv_dp_not_attainable",
                           "values": {"target": dp_design_mbar,
                                      "actual": dp_actual_mbar or 0}})
    if dp_at_qmin_mbar < 10:
        advisories.append({"level": "warning", "key": "std_adv_dp_low",
                           "values": {"dp": dp_at_qmin_mbar}})
    advisories.append({"level": "info", "key": "std_adv_dp_design",
                       "values": {"dp": dp_actual_mbar if dp_actual_mbar else dp_design_mbar}})
    return advisories


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


def _generate_notes(beta: float, beta_ok: bool, std: dict | None = None) -> str:
    std = std or {}
    beta_rec_lo, beta_rec_hi = std.get("beta_recommended", (0.2, 0.65))
    notes = []
    if not beta_ok:
        notes.append("β seçilen standardın sınırları dışında")
    if beta > beta_rec_hi:
        notes.append(f"β > {beta_rec_hi}, belirsizlik artar; β < {beta_rec_hi} önerilir")
    if beta < beta_rec_lo:
        notes.append(f"β < {beta_rec_lo}, düşük duyarlılık; daha küçük DP aralığı düşünün")
    return "; ".join(notes) if notes else "β önerilen sınırlar içinde"


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
    tap_type: str | None = None,
    standard: str | None = None,
    dp_design_mbar: float | None = None,
) -> dict:
    """Size orifice meter for given gas flow range.

    design the plate for a user-selectable differential pressure at maximum
    flow and a user-selectable design standard.

    P_oper_bar must be the ABSOLUTE upstream operating pressure (bar); it is
    converted to Pa and used as p1 for the expansibility factor ε.
    """
    std = _standard_profile(tap_type, standard)
    resolved_tap = std["tap_type"]

    dp_max_Pa = (dp_design_mbar if dp_design_mbar else std["dp_recommended_mbar"]) * 100
    qm_max = q_max_Sm3h * rho_std_kg_m3 / 3600
    qm_min = q_min_Sm3h * rho_std_kg_m3 / 3600

    p1_Pa = P_oper_bar * 1e5
    result = calc_beta_ratio(qm_max, D_mm, rho_kg_m3, mu_Pa_s, dp_max_Pa,
                             p1_Pa=p1_Pa,
                             tap_type=resolved_tap, standard=std["standard"])

    D_m = D_mm / 1000
    A_pipe = math.pi * (D_m / 2) ** 2
    dp_actual_Pa = result.get("dp_actual_Pa", dp_max_Pa)
    # ΔP scales with the square of flow, so Qmin sees (qmin/qmax)² of the
    # achievable (not merely requested) Qmax ΔP.
    dp_min = dp_actual_Pa * (qm_min / qm_max) ** 2 if qm_max > 0 else 0
    turndown_actual = q_max_Sm3h / q_min_Sm3h if q_min_Sm3h > 0 else float("inf")

    result["turndown_actual"] = round(turndown_actual, 2)
    result["turndown_ok"] = turndown_actual >= 10
    result["dp_at_qmin_mbar"] = round(dp_min / 100, 2)
    result["dp_at_qmax_mbar"] = round(dp_actual_Pa / 100, 1)
    result["dp_design_mbar"] = round(dp_max_Pa / 100, 1)
    result["dp_attainable"] = bool(result.get("dp_attainable"))
    result["standard"] = std["standard"]
    result["standard_name"] = std["standard_name"]
    result["standard_ref"] = std["standard_ref"]
    result["velocity_ms"] = round(qm_max / (rho_kg_m3 * A_pipe), 2) if rho_kg_m3 > 0 and A_pipe > 0 else 0

    return result


def calc_beta_ratio_with_fluid(
    qm_kg_s: float,
    D_mm: float,
    fluid: "Fluid",
    dp_target_Pa: float = 25000,
    p1_Pa: float = 4.5e6,
    tap_type: str = "corner",
) -> dict:
    """Wrapper around calc_beta_ratio that extracts fluid props from Fluid object.

    Args:
        qm_kg_s: mass flow rate [kg/s]
        D_mm: pipe internal diameter [mm]
        fluid: Fluid dataclass instance with rho_oper_kg_m3, mu_dynamic_Pa_s
        dp_target_Pa: target differential pressure [Pa]
        p1_Pa: upstream absolute pressure [Pa] (Fluid carries no pressure field)
        tap_type: tap type ("corner", "flange", "D_D", "2D")
    """
    from metering_designer.fluids.fluid import Fluid

    rho = fluid.rho_oper_kg_m3 if hasattr(fluid, "rho_oper_kg_m3") else 0
    mu = fluid.mu_dynamic_Pa_s if hasattr(fluid, "mu_dynamic_Pa_s") else 1e-5

    return calc_beta_ratio(qm_kg_s, D_mm, rho, mu, dp_target_Pa, p1_Pa=p1_Pa,
                           tap_type=tap_type)


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
    p1_Pa: float = 4.5e6,
    tap_type: str = "corner",
    standard: str | None = None,
) -> Result:
    """Calculate orifice beta ratio with provenance tracking."""
    result = Result()
    try:
        data = calc_beta_ratio(qm_kg_s, D_mm, rho_kg_m3, mu_Pa_s, dp_target_Pa,
                               p1_Pa=p1_Pa,
                               tap_type=tap_type, standard=standard)
        result.data = data
        result.add_provenance(
            function_name="calc_beta_ratio",
            parameters={"tap_type": tap_type, "dp_target_Pa": dp_target_Pa,
                        "p1_Pa": p1_Pa,
                        "standard": data.get("standard", "iso5167_2")},
            standard_ref=data.get("standard_ref", "ISO 5167-2:2022"),
        )
        if not data.get("beta_valid", False):
            result.warnings.append("Beta ratio outside selected standard's β limits")
    except Exception as e:
        result.errors.append(str(e))
    return result
