"""
Natural gas fluid properties module.
Calculates density, compressibility, viscosity, calorific value per ISO 6976.
"""

import math
from metering_designer.core.backends import calc_z_factor as backend_z_factor
from metering_designer.core.backends import calc_heating_value as backend_cv

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
    design = backend_z_factor(P_design, T_design_C if T_design_C else T_oper_C, comp_normalized)
    standard = backend_z_factor(STANDARD_P_BAR, 15.0, comp_normalized)

    M_mix = oper.get("M_mix", 20)
    Z_oper = oper.get("Z", 1.0)
    backend_used = oper.get("backend", "unknown")

    # Ideal gas density at standard conditions
    rho_std_ideal = (STANDARD_P_BAR * 1e5) * M_mix / (1000 * 8.314462618 * 288.15)
    rho_oper = oper.get("density_kg_m3", 0)

    # Kinematic viscosity estimate
    mu_gas = _calc_viscosity(M_mix, Z_oper, P_oper_bar, T_oper_K)
    nu_gas = mu_gas / rho_oper if rho_oper > 0 else 1e-6

    # ISO 6976 calorific value with thermo fallback
    cv = backend_cv(comp_normalized)
    gross_CV = cv.get("gross_CV_MJ_m3", 0)
    net_CV = cv.get("net_CV_MJ_m3", 0)

    # Wobbe index
    rel_density = rho_std_ideal / 1.225 if rho_std_ideal > 0 else 0.6
    Wobbe = gross_CV / math.sqrt(rel_density) if rel_density > 0 else 0

    rho_std = rho_std_ideal

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
        "backend_used": backend_used,
    }


def _normalize_comp(comp: dict) -> dict[str, float]:
    valid = {k: max(0, v) for k, v in comp.items() if k in GAS_COMPONENT_NAMES and v > 0}
    total = sum(valid.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in valid.items()}


def _calc_viscosity(M: float, Z: float, P_bar: float, T_K: float) -> float:
    P_Pa = P_bar * 1e5
    Tc = 200
    Pc = 50

    Tr = T_K / Tc if Tc > 0 else 1.0
    mu0 = 1e-6 * (0.807 * Tr ** 0.618 - 0.357 * math.exp(-0.449 * Tr) + 0.34)
    return mu0 * (1 + 0.4 * P_Pa / (Pc * 1e5)) if Pc > 0 else mu0


def _calc_calorific_values(comp: dict) -> tuple[float, float]:
    cv_data = {
        "C1": [39.84, 35.88],
        "C2": [70.29, 64.35],
        "C3": [101.2, 93.18],
        "iC4": [133.0, 122.8],
        "nC4": [133.0, 122.8],
        "iC5": [163.5, 151.3],
        "nC5": [163.5, 151.3],
        "C6": [194.0, 179.8],
        "C6plus": [210.0, 195.0],
        "H2S": [25.33, 23.33],
        "N2": [0, 0],
        "CO2": [0, 0],
    }
    gross = sum(comp.get(c, 0) * v[0] for c, v in cv_data.items())
    net = sum(comp.get(c, 0) * v[1] for c, v in cv_data.items())
    return gross, net


def estimate_velocity(q_act_m3h: float, pipe_id_m: float) -> float:
    if pipe_id_m <= 0 or q_act_m3h <= 0:
        return 0
    area = math.pi * (pipe_id_m / 2) ** 2
    return q_act_m3h / 3600 / area


def estimate_reynolds(rho_kg_m3: float, velocity_m_s: float, mu_Pa_s: float, pipe_id_m: float) -> float:
    return rho_kg_m3 * velocity_m_s * pipe_id_m / mu_Pa_s if mu_Pa_s > 0 else 0
