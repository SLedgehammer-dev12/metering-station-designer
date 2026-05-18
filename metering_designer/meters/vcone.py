"""
ISO 5167-5 / ASME MFC-7M
V-Cone and Venturi meter sizing.
"""

import math


def size_v_cone(
    nps: int,
    q_max_Sm3h: float,
    q_min_Sm3h: float,
    P_oper_bar: float,
    T_oper_C: float,
    rho_kg_m3: float,
    mu_Pa_s: float,
    rho_std_kg_m3: float,
    is_gas: bool = True,
) -> dict:
    od_mm = _nps_to_od(nps)
    id_mm = od_mm * 0.88
    id_m = id_mm / 1000
    A_pipe = math.pi * (id_m / 2) ** 2

    if is_gas:
        q_act_max = q_max_Sm3h * rho_std_kg_m3 / rho_kg_m3 / 3600
    else:
        q_act_max = q_max_Sm3h / 3600

    v_pipe = q_act_max / A_pipe if A_pipe > 0 else 0
    Re = rho_kg_m3 * v_pipe * id_m / mu_Pa_s if mu_Pa_s > 0 else 1e6

    # Beta ratio: V-Cone typically 0.45-0.85
    beta = _estimate_vcone_beta(q_act_max, id_mm, rho_kg_m3)
    beta = max(0.45, min(beta, 0.85))
    d_vc_mm = beta * id_mm

    # Discharge coefficient for V-Cone
    Cd = _vcone_cd(beta, Re)
    eps = _vcone_expansibility(beta, P_oper_bar) if is_gas else 1.0

    # Differential pressure
    At = math.pi * (d_vc_mm / 2000) ** 2
    E = 1.0 / math.sqrt(1 - beta ** 4)
    dp_Pa = (q_act_max * rho_kg_m3) ** 2 / (2 * rho_kg_m3 * (Cd * eps * E * At) ** 2) if At > 0 else 25000
    dp_mbar = dp_Pa / 100

    # Permanent pressure loss (V-Cone: much lower than orifice)
    pl_factor = (1 - beta ** 2) * 0.3
    dp_perm_mbar = dp_mbar * pl_factor

    # Turndown
    td = q_max_Sm3h / q_min_Sm3h if q_min_Sm3h > 0 else 1
    td_ok = td <= 10

    # Uncertainty
    base_unc = 0.5 if beta <= 0.6 else 1.0

    return {
        "meter_type": "V-Cone",
        "nps": nps, "id_mm": round(id_mm, 1),
        "beta": round(beta, 4), "d_cone_mm": round(d_vc_mm, 2),
        "Cd": round(Cd, 5), "eps": round(eps, 5),
        "Re": round(Re, 0), "Re_ok": Re > 8000,
        "v_pipe_ms": round(v_pipe, 2),
        "dp_mbar": round(dp_mbar, 1),
        "dp_perm_mbar": round(dp_perm_mbar, 1),
        "turndown_actual": round(td, 1), "turndown_max": 10,
        "turndown_ok": td_ok, "base_uncertainty_pct": base_unc,
        "straight_upstream_D": 3, "straight_downstream_D": 2,
        "notes": _vcone_notes(beta, td_ok, Re),
    }


def size_venturi(
    nps: int,
    q_max_Sm3h: float,
    q_min_Sm3h: float,
    P_oper_bar: float,
    T_oper_C: float,
    rho_kg_m3: float,
    mu_Pa_s: float,
    rho_std_kg_m3: float,
) -> dict:
    od_mm = _nps_to_od(nps)
    id_mm = od_mm * 0.88
    id_m = id_mm / 1000
    A_pipe = math.pi * (id_m / 2) ** 2
    q_act_max = q_max_Sm3h * rho_std_kg_m3 / rho_kg_m3 / 3600 if rho_kg_m3 > 0 else 0
    v_pipe = q_act_max / A_pipe if A_pipe > 0 else 0
    Re = rho_kg_m3 * v_pipe * id_m / mu_Pa_s if mu_Pa_s > 0 else 1e6

    # Venturi: machined convergent section, fixed beta = 0.5 typical
    beta = 0.5
    d_throat_mm = beta * id_mm
    Cd = 0.995  # Venturi Cd ≈ 0.995
    eps = 1 - (0.41 + 0.35 * beta ** 4) * 0.3 / 1.3  # simplified

    At = math.pi * (d_throat_mm / 2000) ** 2
    dp_Pa = 25000
    dp_mbar = dp_Pa / 100
    dp_perm_mbar = dp_mbar * (1 - beta ** 2) * 0.15  # Venturi: very low perm loss

    td = q_max_Sm3h / q_min_Sm3h if q_min_Sm3h > 0 else 1
    unc = 0.7

    return {
        "meter_type": "Venturi (klasik)",
        "nps": nps, "id_mm": round(id_mm, 1),
        "beta": beta, "d_throat_mm": round(d_throat_mm, 1),
        "Cd": Cd, "eps": round(eps, 5),
        "Re": round(Re, 0), "Re_ok": Re > 2e5,
        "v_pipe_ms": round(v_pipe, 2),
        "dp_mbar": round(dp_mbar, 1),
        "dp_perm_mbar": round(dp_perm_mbar, 1),
        "turndown_actual": round(td, 1), "turndown_max": 8,
        "turndown_ok": td <= 8, "base_uncertainty_pct": unc,
        "straight_upstream_D": 8, "straight_downstream_D": 5,
        "notes": "Cd=0.995 sabit, β=0.5. ISO 5167-4 machined convergent.",
    }


def _estimate_vcone_beta(q_m3s: float, id_mm: float, rho: float) -> float:
    if q_m3s <= 0 or id_mm <= 0:
        return 0.65
    target_beta = 0.05 * (q_m3s * rho) ** 0.3 + 0.45
    return min(max(target_beta, 0.45), 0.85)


def _vcone_cd(beta: float, Re: float) -> float:
    return 0.82 + 0.01 * beta - 0.0001 * beta * (Re / 1e6)


def _vcone_expansibility(beta: float, P_bar: float) -> float:
    if P_bar <= 0:
        return 1.0
    return 1 - (0.41 + 0.35 * beta ** 4) * 0.3 / (1.3 * P_bar)


def _vcone_notes(beta: float, td_ok: bool, Re: float) -> str:
    n = []
    if beta < 0.45:
        n.append("β < 0.45, düşük sinyal")
    if not td_ok:
        n.append("Turndown > 10:1")
    if Re < 8000:
        n.append("Re < 8000, Cd değişken")
    return "; ".join(n) if n else "Tasarım sınırlar içinde"


def _nps_to_od(nps: int) -> float:
    m = {2: 60.3, 3: 88.9, 4: 114.3, 6: 168.3, 8: 219.1,
         10: 273.1, 12: 323.8, 16: 406.4, 20: 508.0, 24: 609.6}
    return m.get(nps, nps * 25.4)
