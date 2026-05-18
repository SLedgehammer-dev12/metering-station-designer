"""
AGA Report No. 7 / ISO 9951
Turbine meter sizing.
"""

import math


def size_turbine(
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
    id_mm = od_mm * 0.85
    id_m = id_mm / 1000
    A = math.pi * (id_m / 2) ** 2

    qv_act_max = q_max_Sm3h * rho_std_kg_m3 / rho_kg_m3 if rho_kg_m3 > 0 else 0
    v_max = qv_act_max / 3600 / A if A > 0 else 0

    Re = rho_kg_m3 * v_max * id_m / mu_Pa_s if mu_Pa_s > 0 else 0
    turndown = q_max_Sm3h / q_min_Sm3h if q_min_Sm3h > 0 else float("inf")
    turndown_ok = turndown <= 25

    # Meter size check
    max_q_capacity = _estimate_max_capacity(nps, P_oper_bar)
    meter_size = nps
    if qv_act_max > max_q_capacity * 1.1:
        meter_size = nps + 2
        sizing_note = f"Kapasite aşımı, NPS {meter_size} önerilir"
    elif qv_act_max < max_q_capacity * 0.1:
        meter_size = max(nps - 2, 2)
        sizing_note = f"Düşük kapasite kullanımı, NPS {meter_size} yeterli olabilir"
    else:
        sizing_note = "Kapasite uygun"

    # K-factor (pulses per m³)
    K_typical = _estimate_k_factor_for_size(nps)

    # Over-range protection
    over_range_factor = 1.25
    q_over_range = max_q_capacity * over_range_factor
    over_range_ok = qv_act_max <= q_over_range

    # Bearing life estimate
    bearing_hours = _estimate_bearing_life(v_max, nps)

    # Pressure loss
    dp_mbar = _estimate_turbine_dp(v_max, rho_kg_m3)

    return {
        "nps": nps,
        "id_mm": round(id_mm, 1),
        "v_max_ms": round(v_max, 2),
        "Re": round(Re, 0),
        "turndown_actual": round(turndown, 1),
        "turndown_ok": turndown_ok,
        "q_act_max_m3h": round(qv_act_max, 1),
        "meter_size_nps": meter_size,
        "sizing_note": sizing_note,
        "K_factor_pulses_per_m3": int(K_typical),
        "over_range_factor": over_range_factor,
        "over_range_protection_ok": over_range_ok,
        "estimated_bearing_life_h": round(bearing_hours, 0),
        "dp_estimate_mbar": round(dp_mbar, 2),
        "straight_upstream_D": 10,
        "straight_downstream_D": 5,
        "notes": _generate_turbine_notes(v_max, turndown_ok, over_range_ok),
    }


def _estimate_max_capacity(nps: int, P_bar: float) -> float:
    base = {2: 40, 3: 100, 4: 160, 6: 400, 8: 650, 10: 1000, 12: 1600, 16: 2500}
    return base.get(nps, nps ** 2 * 10) * (P_bar / 10) ** 0.5


def _estimate_k_factor_for_size(nps: int) -> float:
    return {2: 35000, 3: 12000, 4: 6000, 6: 2200, 8: 1000, 10: 500, 12: 250, 16: 100}.get(nps, 5000 / nps)


def _estimate_bearing_life(v_ms: float, nps: int) -> float:
    base_life = 50000
    if v_ms <= 0:
        return base_life
    return base_life * (20 / v_ms) ** 2


def _estimate_turbine_dp(v_ms: float, rho_kg_m3: float) -> float:
    return 0.5 * rho_kg_m3 * v_ms ** 2 * 0.15 / 100


def _generate_turbine_notes(v_max, td_ok, over_ok) -> str:
    notes = []
    if not td_ok:
        notes.append("Turndown sınırı aşıldı (>1:25)")
    if not over_ok:
        notes.append("Over-range koruması yetersiz olabilir")
    if v_max > 25:
        notes.append(f"Hız {v_max:.1f} m/s yüksek - rotor ömrü kısalabilir")
    return "; ".join(notes) if notes else "Tasarım parametreleri sınırlar içinde"


def _nps_to_od(nps: int) -> float:
    mapping = {2: 60.3, 3: 88.9, 4: 114.3, 6: 168.3, 8: 219.1,
               10: 273.1, 12: 323.8, 14: 355.6, 16: 406.4, 18: 457.2,
               20: 508.0, 24: 609.6}
    return mapping.get(nps, nps * 25.4)
