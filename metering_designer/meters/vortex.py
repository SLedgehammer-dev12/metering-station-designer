"""
ISO 17089-2 / VDI/VDE 2644
Vortex meter sizing for gas and liquid applications.
"""

import math


def size_vortex(
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
    id_mm = od_mm * 0.87
    id_m = id_mm / 1000
    A = math.pi * (id_m / 2) ** 2

    if is_gas:
        q_act_max_m3h = q_max_Sm3h * rho_std_kg_m3 / rho_kg_m3 if rho_kg_m3 > 0 else 0
        q_act_min_m3h = q_min_Sm3h * rho_std_kg_m3 / rho_kg_m3 if rho_kg_m3 > 0 else 0
    else:
        q_act_max_m3h = q_max_Sm3h
        q_act_min_m3h = q_min_Sm3h

    v_max = q_act_max_m3h / 3600 / A if A > 0 else 0
    v_min = q_act_min_m3h / 3600 / A if A > 0 else 0
    Re = rho_kg_m3 * v_max * id_m / mu_Pa_s if mu_Pa_s > 0 else 0

    # Vortex meter velocity limits
    v_min_limit = _calc_v_min_limit(rho_kg_m3, mu_Pa_s, id_m) if not is_gas else 0.5
    v_max_limit = 75 if is_gas else 9

    v_ok = v_min_limit <= v_max <= v_max_limit
    v_min_ok = v_min >= v_min_limit

    # Strouhal number and frequency
    St = 0.20
    bluff_body_width = id_mm * 0.26
    f_max_hz = St * v_max / (bluff_body_width / 1000) if bluff_body_width > 0 else 0
    f_min_hz = St * v_min / (bluff_body_width / 1000) if bluff_body_width > 0 else 0

    f_ok = f_min_hz >= 1.0 if not is_gas else f_min_hz >= 0.5

    # K-factor
    K_pulses_per_m3 = St / (math.pi * (bluff_body_width / 1000) ** 2 / 4) * (A / (bluff_body_width * 0.26 / 1000))
    K_pulses_per_m3 = _estimate_vortex_k_factor(nps)

    # Pressure loss
    dp_mbar = _vortex_pressure_loss(v_max, rho_kg_m3, id_mm)

    # Turndown
    turndown = q_act_max_m3h / q_act_min_m3h if q_act_min_m3h > 0 else float("inf")
    td_max = 20 if is_gas else 10
    turndown_ok = turndown <= td_max

    # Uncertainty
    base_uncertainty = 1.0 if is_gas else 0.75

    return {
        "nps": nps,
        "id_mm": round(id_mm, 1),
        "v_max_ms": round(v_max, 2),
        "v_min_ms": round(v_min, 3),
        "v_min_limit_ms": round(v_min_limit, 3),
        "velocity_ok": v_ok,
        "v_min_ok": v_min_ok,
        "Re": round(Re, 0),
        "Re_ok": Re > 20000 if not is_gas else Re > 15000,
        "f_max_hz": round(f_max_hz, 1),
        "f_min_hz": round(f_min_hz, 2),
        "frequency_ok": f_ok,
        "K_factor_pulses_per_m3": int(K_pulses_per_m3),
        "dp_mbar": round(dp_mbar, 2),
        "turndown_actual": round(turndown, 1),
        "turndown_max": td_max,
        "turndown_ok": turndown_ok,
        "base_uncertainty_pct": base_uncertainty,
        "straight_upstream_D": 15,
        "straight_downstream_D": 5,
        "notes": _vortex_notes(v_ok, f_ok, turndown_ok, Re),
    }


def _calc_v_min_limit(rho: float, mu: float, D_m: float) -> float:
    if rho <= 0 or D_m <= 0:
        return 0.3
    Re_min = 20000
    return Re_min * mu / (rho * D_m)


def _estimate_vortex_k_factor(nps: int) -> float:
    return {2: 18000, 3: 7000, 4: 3000, 6: 1200, 8: 550, 10: 250, 12: 120, 16: 40}.get(nps, 10000 / nps)


def _vortex_pressure_loss(v_ms: float, rho_kg_m3: float, id_mm: float) -> float:
    Cd_bluff = 1.2
    return 0.5 * rho_kg_m3 * v_ms ** 2 * Cd_bluff * 0.1 / 100


def _vortex_notes(v_ok: bool, f_ok: bool, td_ok: bool, Re: float) -> str:
    notes = []
    if not v_ok:
        notes.append("Hız vortex sınırları dışında")
    if not f_ok:
        notes.append("Frekans çok düşük, sinyal kaybı riski")
    if not td_ok:
        notes.append("Turndown sınırı aşıldı")
    if Re < 10000:
        notes.append("Düşük Re, ölçüm kararsız olabilir")
    return "; ".join(notes) if notes else "Tasarım sınırlar içinde"


def _nps_to_od(nps: int) -> float:
    mapping = {2: 60.3, 3: 88.9, 4: 114.3, 6: 168.3, 8: 219.1,
               10: 273.1, 12: 323.8, 16: 406.4}
    return mapping.get(nps, nps * 25.4)
