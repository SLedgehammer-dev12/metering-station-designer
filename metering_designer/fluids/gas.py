"""
Natural gas fluid properties module.
Calculates density, compressibility, viscosity, calorific value per ISO 6976.

Alias convention:
  calc_*(composition, P_bar, T_C, ...) -> dict     (legacy, backward compat)
  calc_*_result(composition, P_bar, T_C, ...) -> Result  (modern, error-aware)
"""

import math
from metering_designer.core.backends import calc_z_factor as backend_z_factor
from metering_designer.core.backends import calc_heating_value as backend_cv
from metering_designer.fluids.fluid import Fluid
from metering_designer.fluids.data import get_critical_props, get_cv_data
from metering_designer.core.result import Result

GAS_COMPONENT_NAMES = {
    "C1": "Methane",
    "C2": "Ethane",
    "C3": "Propane",
    "iC4": "i-Butane",
    "nC4": "n-Butane",
    "iC5": "i-Pentane",
    "nC5": "n-Pentane",
    "C6": "Hexane",
    "N2": "Nitrogen",
    "CO2": "Carbon Dioxide",
    "H2S": "Hydrogen Sulfide",
    "C6plus": "Hexane+",
}

STANDARD_T_K = 288.15
STANDARD_P_BAR = 1.01325


def calc_gas_properties(
    composition: dict[str, float],
    P_oper_bar: float,
    T_oper_C: float,
    P_design_bar: float = None,
    T_design_C: float = None,
) -> dict:
    T_oper_K = T_oper_C + 273.15
    T_design_K = (T_design_C + 273.15) if T_design_C is not None else T_oper_K
    P_design = P_design_bar if P_design_bar is not None else P_oper_bar

    comp_normalized = _normalize_comp(composition)
    if not comp_normalized:
        return {"error": "Kompozisyon boş veya geçersiz"}

    # Density using multi-backend fallback chain
    oper = backend_z_factor(P_oper_bar, T_oper_C, comp_normalized)
    design = backend_z_factor(P_design, T_design_C if T_design_C is not None else T_oper_C, comp_normalized)
    standard = backend_z_factor(STANDARD_P_BAR, 15.0, comp_normalized)

    M_mix = oper.get("M_mix", 20)
    Z_oper = oper.get("Z", 1.0)
    backend_used = oper.get("backend", "unknown")

    # Ideal gas density at standard conditions
    rho_std_ideal = (STANDARD_P_BAR * 1e5) * M_mix / (1000 * 8.314462618 * 288.15)
    rho_oper = oper.get("density_kg_m3", 0)

    # Kinematic viscosity estimate
    mu_gas = _calc_viscosity(M_mix, Z_oper, P_oper_bar, T_oper_K, comp_normalized)
    nu_gas = mu_gas / rho_oper if rho_oper > 0 else 1e-6

    # ISO 6976 calorific value with thermo fallback
    cv = backend_cv(comp_normalized)
    gross_CV = cv.get("gross_CV_MJ_m3", 0)
    net_CV = cv.get("net_CV_MJ_m3", 0)

    # Wobbe index
    rel_density = rho_std_ideal / 1.225 if rho_std_ideal > 0 else 0.6
    Wobbe = gross_CV / math.sqrt(rel_density) if rel_density > 0 else 0

    rho_std = rho_std_ideal

    # Isentropic exponent (kappa = Cp/Cv) and speed of sound
    kappa_val = compute_isentropic_kappa(comp_normalized, T_oper_C)
    sos_val = calc_speed_of_sound(T_oper_K, M_mix, kappa_val, rho_oper)

    return {
        "composition": comp_normalized,
        "M_mix": round(M_mix, 4),
        "Z_oper": round(Z_oper, 6),
        "Z_design": round(design.get("Z", 1.0), 6),
        "rho_oper_kg_m3": round(rho_oper, 4),
        "rho_std_kg_m3": round(rho_std, 4),
        "rho_design_kg_m3": round(design.get("density_kg_m3", 0), 4),
        "mu_dynamic_Pa_s": round(mu_gas, 8),
        "nu_kinematic_m2_s": round(nu_gas, 8),
        "gross_CV_MJ_m3": round(gross_CV, 4),
        "net_CV_MJ_m3": round(net_CV, 4),
        "Wobbe_MJ_m3": round(Wobbe, 4),
        "relative_density": round(rel_density, 4),
        "kappa": round(kappa_val, 4),
        "speed_of_sound_ms": round(sos_val, 4),
        "backend_used": backend_used,
    }


def _normalize_comp(comp: dict) -> dict[str, float]:
    valid = {k: max(0, v) for k, v in comp.items() if k in GAS_COMPONENT_NAMES and v > 0}
    total = sum(valid.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in valid.items()}


def _pseudo_critical(composition: dict[str, float]) -> tuple[float, float]:
    props = get_critical_props()
    Tc = sum(composition.get(c, 0) * props.get(c, {"Tc": 200})["Tc"]
             for c in composition)
    Pc = sum(composition.get(c, 0) * props.get(c, {"Pc": 50})["Pc"]
             for c in composition)
    total = sum(composition.values())
    if total > 0:
        Tc /= total
        Pc /= total
    return Tc or 200.0, Pc or 50.0


def _calc_viscosity(M: float, Z: float, P_bar: float, T_K: float,
                    composition: dict[str, float] = None) -> float:
    if composition:
        Tc, Pc_bar = _pseudo_critical(composition)
    else:
        Tc, Pc_bar = 200.0, 50.0

    P_Pa = P_bar * 1e5
    Tr = T_K / Tc if Tc > 0 else 1.0
    mu0 = 1e-6 * (0.807 * Tr ** 0.618 - 0.357 * math.exp(-0.449 * Tr) + 0.34)
    Pc_Pa = Pc_bar * 1e5
    return mu0 * (1 + 0.4 * P_Pa / Pc_Pa) if Pc_Pa > 0 else mu0


def _calc_calorific_values(comp: dict) -> tuple[float, float]:
    cv_data = get_cv_data()
    gross = sum(comp.get(c, 0) * v[0] for c, v in cv_data.items())
    net = sum(comp.get(c, 0) * v[1] for c, v in cv_data.items())
    return gross, net


def calc_fluid(composition, P_oper_bar, T_oper_C,
               P_design_bar=None, T_design_C=None) -> Fluid:
    d = calc_gas_properties(composition, P_oper_bar, T_oper_C,
                            P_design_bar, T_design_C)
    return Fluid.from_dict(d)


def estimate_velocity(q_act_m3h: float, pipe_id_m: float) -> float:
    if pipe_id_m <= 0 or q_act_m3h <= 0:
        return 0
    area = math.pi * (pipe_id_m / 2) ** 2
    return q_act_m3h / 3600 / area


def estimate_reynolds(rho_kg_m3: float, velocity_m_s: float, mu_Pa_s: float, pipe_id_m: float) -> float:
    return rho_kg_m3 * velocity_m_s * pipe_id_m / mu_Pa_s if mu_Pa_s > 0 else 0


# ── Isentropic exponent (kappa = Cp/Cv) and speed of sound ─────────

def calc_ideal_cp(composition: dict[str, float], T_K: float) -> float:
    """Ideal gas specific heat at constant pressure, J/(mol·K).

    Uses Shomate equation coefficients from NIST Chemistry WebBook (298–1500 K).
    """
    # Shomate coefficients: A, B, C, D, E  (kJ/mol·K basis → multiplied by 1000)
    CP_SHOMATE = {
        "C1":  [0.04088, 0.06635, -1.247e-5, -2.663e-8, 1.303e-4],
        "N2":  [0.03052, 0.03179, -1.135e-5, 2.420e-9, -5.548e-5],
        "CO2": [0.02480, 0.07370, -5.488e-5, 1.703e-8, -2.053e-5],
        "C2":  [0.05327, 0.14729, -5.072e-5, 7.628e-9, 1.382e-4],
        "C3":  [0.02430, 0.19988, -8.513e-5, 1.448e-8, -1.127e-4],
        "H2S": [0.03366, 0.02774, -4.086e-6, -3.863e-9, 4.535e-5],
    }
    t = T_K / 1000
    cp_mix = 0.0
    for c, x in composition.items():
        if x <= 0:
            continue
        shom = CP_SHOMATE.get(c)
        if shom is None:
            # Default Cp ~28 J/(mol·K) for heavy hydrocarbons
            cp_mix += x * 28.0
            continue
        cp = shom[0] + shom[1] * t + shom[2] * t**2 + shom[3] * t**3 + shom[4] / t**2
        cp_mix += x * cp * 1000  # kJ/(mol·K) → J/(mol·K)
    return cp_mix


def calc_ideal_cv(cp: float) -> float:
    """Ideal gas specific heat at constant volume, J/(mol·K)."""
    return cp - 8.314462618


def calc_kappa(cp: float, cv: float) -> float:
    """Isentropic exponent (ratio of specific heats Cp/Cv)."""
    return cp / cv if cv > 0 else 1.3


def calc_speed_of_sound(
    T_K: float, M_mix: float, kappa: float, rho_kg_m3: float
) -> float:
    """Speed of sound in an ideal gas, m/s.

    Uses c = sqrt(kappa * P / rho) with P from the ideal gas law.
    """
    R = 8.314462618
    P_Pa = (
        rho_kg_m3 * R * T_K / (M_mix / 1000)
        if rho_kg_m3 > 0
        else 101325
    )
    return math.sqrt(kappa * P_Pa / rho_kg_m3) if rho_kg_m3 > 0 else 0


def compute_isentropic_kappa(
    composition: dict[str, float],
    T_oper_C: float,
    M_mix: float = None,
    rho_kg_m3: float = None,
) -> float:
    """Compute isentropic exponent (kappa) from composition and temperature."""
    T_K = T_oper_C + 273.15
    cp = calc_ideal_cp(composition, T_K)
    cv = calc_ideal_cv(cp)
    kappa = calc_kappa(cp, cv)
    return round(kappa, 4)


def compute_speed_of_sound_value(
    composition: dict[str, float],
    T_oper_C: float,
    M_mix: float = None,
    rho_kg_m3: float = None,
) -> float:
    """Compute speed of sound for the gas mixture, m/s."""
    T_K = T_oper_C + 273.15
    kappa = compute_isentropic_kappa(composition, T_oper_C)
    if M_mix is None:
        from metering_designer.fluids.data import get_molar_masses
        masses = get_molar_masses()
        M_mix = sum(composition.get(c, 0) * masses.get(c, 20) for c in composition)
    if rho_kg_m3 is None:
        R = 8.314462618
        P_bar = 1.01325  # standard pressure
        rho_kg_m3 = (P_bar * 1e5) * M_mix / (1000 * R * T_K)
    return calc_speed_of_sound(T_K, M_mix, kappa, rho_kg_m3)


# ── Consistent API aliases (composition-first) ──────────────────────

def calc_z(composition: dict[str, float], P_bar: float, T_C: float) -> dict:
    return backend_z_factor(P_bar, T_C, composition)


def calc_cv(composition: dict[str, float]) -> dict:
    return backend_cv(composition)


def calc_z_result(composition: dict[str, float], P_bar: float, T_C: float) -> Result:
    try:
        raw = calc_z(composition, P_bar, T_C)
        return Result(data=raw)
    except Exception as e:
        return Result(errors=[str(e)])


def calc_props_result(
    composition: dict[str, float],
    P_oper_bar: float,
    T_oper_C: float,
    P_design_bar: float = None,
    T_design_C: float = None,
) -> Result:
    try:
        raw = calc_gas_properties(composition, P_oper_bar, T_oper_C, P_design_bar, T_design_C)
        if "error" in raw:
            return Result(errors=[raw["error"]])
        return Result(data=raw)
    except Exception as e:
        return Result(errors=[str(e)])


def calc_gas_properties_result(
    composition: dict[str, float],
    P_bar: float,
    T_C: float,
) -> Result:
    """Compute full gas properties with provenance tracking."""
    result = Result()

    inner = calc_gas_properties(composition, P_bar, T_C)
    result.data = inner

    result.add_provenance(
        function_name="calc_gas_properties",
        parameters={"P_bar": P_bar, "T_C": T_C},
        standard_ref="AGA 8:1994 (GERG-2008 extension)",
    )

    if "kappa" not in result.data:
        result.data["kappa"] = 1.3
        result.warnings.append("Kappa not available, using default 1.3")
    if "speed_of_sound_ms" not in result.data:
        result.data["speed_of_sound_ms"] = 0.0

    return result
