"""
AGA Report No. 9 / ISO 17089
Ultrasonic meter sizing and path configuration.
"""

import math


def size_ultrasonic(
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
    A = math.pi * (id_m / 2) ** 2

    qm_max = q_max_Sm3h * rho_std_kg_m3 / 3600
    qm_min = q_min_Sm3h * rho_std_kg_m3 / 3600

    qv_max_m3h = qm_max / rho_kg_m3 * 3600 if rho_kg_m3 > 0 else 0
    v_max = qv_max_m3h / 3600 / A if A > 0 else 0
    v_min = q_min_Sm3h * rho_std_kg_m3 / rho_kg_m3 / 3600 / A if rho_kg_m3 > 0 and A > 0 else 0
    Re = rho_kg_m3 * v_max * id_m / mu_Pa_s if mu_Pa_s > 0 else 0
    turndown = q_max_Sm3h / q_min_Sm3h if q_min_Sm3h > 0 else float("inf")

    velocity_ok = 0.3 <= v_max <= 30.0

    # Path configuration
    if nps <= 4:
        recommended_paths = 2
        path_option = "2-path (chordal)"
    elif nps <= 10:
        recommended_paths = 4
        path_option = "4-path (chordal) - standard custody transfer"
    elif nps <= 24:
        recommended_paths = 6
        path_option = "6-path (chordal) - custody transfer, high accuracy"
    else:
        recommended_paths = 8
        path_option = "8-path (chordal) - büyük çaplar"

    # Meter body sizing
    if 0.3 <= v_max <= 25:
        meter_size = nps
        sizing_note = "Aynı çapta metre uygun"
    elif v_max < 0.3:
        meter_size = max(nps - 2, 2)
        sizing_note = f"Düşük hız, daha küçük metre (NPS {meter_size}) önerilir"
    elif v_max > 30:
        meter_size = nps + 2
        sizing_note = f"Yüksek hız, daha büyük metre (NPS {meter_size}) düşünülmeli"
    else:
        meter_size = nps
        sizing_note = "Hız kabul edilebilir"

    # Profile correction factor (k-factor)
    k_factor = _estimate_k_factor(recommended_paths, Re)

    # Uncertainty estimate
    if recommended_paths >= 6:
        uncertainty_typical = 0.3
    elif recommended_paths >= 4:
        uncertainty_typical = 0.4
    else:
        uncertainty_typical = 0.5

    # Straight pipe requirements
    straight_up = 10 if recommended_paths >= 4 else 15

    return {
        "nps": nps,
        "od_mm": od_mm,
        "id_mm": round(id_mm, 1),
        "flow_area_m2": round(A, 6),
        "v_max_ms": round(v_max, 2),
        "v_min_ms": round(v_min, 3),
        "Re": round(Re, 0),
        "velocity_ok": velocity_ok,
        "turndown_actual": round(turndown, 1),
        "turndown_ok": turndown <= 100,
        "recommended_paths": recommended_paths,
        "path_config": path_option,
        "meter_size_nps": meter_size,
        "sizing_note": sizing_note,
        "k_factor_estimated": round(k_factor, 4),
        "typical_uncertainty_pct": uncertainty_typical,
        "straight_upstream_D": straight_up,
        "straight_downstream_D": 5,
        "notes": _generate_usm_notes(v_max, velocity_ok, turndown),
    }


def _estimate_k_factor(paths: int, Re: float) -> float:
    base = {2: 1.005, 4: 1.002, 6: 1.001, 8: 1.0005}
    return base.get(paths, 1.003)


def _generate_usm_notes(v_max: float, v_ok: bool, turndown: float) -> str:
    notes = []
    if not v_ok:
        notes.append(f"Hız {v_max:.1f} m/s AGA 9 sınırları dışında (0.3-30 m/s)")
    if turndown > 100:
        notes.append(f"Turndown {turndown}:1 AGA 9 sınırını aşıyor (>100:1)")
    if turndown <= 50:
        notes.append("Turndown limit içinde, optimum çalışma")
    return "; ".join(notes) if notes else "Hız ve turndown AGA 9 sınırları içinde"


def _nps_to_od(nps: int) -> float:
    mapping = {2: 60.3, 3: 88.9, 4: 114.3, 6: 168.3, 8: 219.1,
               10: 273.1, 12: 323.8, 14: 355.6, 16: 406.4, 18: 457.2,
               20: 508.0, 24: 609.6, 30: 762.0, 36: 914.4, 42: 1066.8, 48: 1219.2}
    return mapping.get(nps, nps * 25.4)
