"""
API MPMS Chapter 4 / OIML R 117
Positive Displacement (PD) meter sizing for liquid hydrocarbons.
"""

import math


def size_pd_meter(
    nps: int,
    q_max_m3h: float,
    q_min_m3h: float,
    rho_kg_m3: float,
    visc_cp: float,
    P_oper_bar: float,
    T_oper_C: float,
) -> dict:
    od_mm = _nps_to_od(nps)
    id_mm = od_mm * 0.82
    id_m = id_mm / 1000

    qm_max_kg_s = q_max_m3h * rho_kg_m3 / 3600
    qm_min_kg_s = q_min_m3h * rho_kg_m3 / 3600

    # PD meter sizes and max flow capacity
    pd_sizes = {
        2: 10, 3: 25, 4: 60, 6: 150, 8: 300,
        10: 500, 12: 800, 16: 1500,
    }

    meter_size = nps
    max_cap = pd_sizes.get(nps, 200)
    for sz, cap in sorted(pd_sizes.items()):
        if cap >= q_max_m3h:
            meter_size = sz
            max_cap = cap
            break
    else:
        meter_size = max(pd_sizes.keys())
        max_cap = pd_sizes[meter_size]

    capacity_pct = q_max_m3h / max_cap * 100 if max_cap > 0 else 0

    # Pressure loss
    delta_p_bar = _estimate_pd_pressure_loss(visc_cp, meter_size, q_max_m3h, max_cap)

    # Slip flow estimation (heuristic based on typical PD specs)
    slip_pct_at_qmax = _estimate_slip_pct(visc_cp, delta_p_bar, capacity_pct)
    slip_flow_m3h = slip_pct_at_qmax / 100 * q_max_m3h
    slip_at_qmin_pct = slip_flow_m3h / q_min_m3h * 100 if q_min_m3h > 0 else 100

    # K-factor
    K_pulses_per_m3 = _estimate_pd_k_factor(meter_size)

    # Viscosity effect on accuracy
    if visc_cp < 1:
        visc_note = "Düşük viskozite (<1cP) - slip artabilir"
        visc_accuracy_effect = 0.2
    elif visc_cp < 50:
        visc_note = f"Orta viskozite ({visc_cp:.1f}cP) - optimum aralık"
        visc_accuracy_effect = 0.05
    elif visc_cp < 200:
        visc_note = f"Yüksek viskozite ({visc_cp:.1f}cP) - basınç kaybı artar"
        visc_accuracy_effect = 0.1
    else:
        visc_note = f"Çok yüksek viskozite ({visc_cp:.1f}cP) - özel PD gerekebilir"
        visc_accuracy_effect = 0.3

    turndown = q_max_m3h / q_min_m3h if q_min_m3h > 0 else float("inf")
    turndown_ok = turndown <= 20

    return {
        "nps": nps,
        "meter_size_inches": meter_size,
        "q_max_m3h": round(q_max_m3h, 1),
        "q_min_m3h": round(q_min_m3h, 1),
        "max_capacity_m3h": max_cap,
        "capacity_percent": round(capacity_pct, 1),
        "sizing_note": _pd_sizing_note(capacity_pct, meter_size, nps),
        "K_factor_pulses_per_m3": int(K_pulses_per_m3),
        "delta_p_bar": round(delta_p_bar, 4),
        "delta_p_mbar": round(delta_p_bar * 1000, 1),
        "slip_flow_m3h": round(slip_flow_m3h, 4),
        "slip_pct_at_qmax": round(slip_pct_at_qmax, 4),
        "slip_pct_at_qmin": round(slip_at_qmin_pct, 4),
        "viscosity_cp": visc_cp,
        "viscosity_effect": visc_note,
        "viscosity_accuracy_effect_pct": visc_accuracy_effect,
        "turndown_actual": round(turndown, 1),
        "turndown_ok": turndown_ok,
        "straight_upstream_D": 3,
        "straight_downstream_D": 2,
        "notes": _generate_pd_notes(turndown_ok, slip_at_qmin_pct, capacity_pct),
    }


def _estimate_slip_pct(visc_cp: float, dp_bar: float, cap_pct: float) -> float:
    base_slip = max(0.05, 2.0 / visc_cp)
    dp_factor = (dp_bar / 0.3) ** 0.5
    cap_factor = 1.0 / max(cap_pct / 50.0, 0.5)
    return base_slip * dp_factor * cap_factor


def _estimate_pd_pressure_loss(visc_cp: float, size_in: float, q_m3h: float, max_cap: float) -> float:
    base_loss = 0.1 * (visc_cp / 10) ** 0.5
    flow_factor = (q_m3h / max_cap) ** 1.5 if max_cap > 0 else 1.0
    return base_loss * flow_factor


def _estimate_pd_k_factor(size_in: float) -> float:
    return int({2: 2500, 3: 1000, 4: 450, 6: 200, 8: 100, 10: 50, 12: 25, 16: 10}.get(size_in, 500 / size_in))


def _pd_sizing_note(cap_pct: float, meter_size: float, nps: float) -> str:
    if cap_pct > 95:
        return f"Kapasite sınırında (%{cap_pct:.0f}); NPS {meter_size} yetersiz olabilir"
    if cap_pct < 10:
        return f"Düşük kapasite (%{cap_pct:.0f}); daha küçük NPS {meter_size} düşünülebilir"
    if meter_size != nps:
        return f"NPS {meter_size}\" seçildi (hat NPS{nps}\")"
    return f"NPS {nps}\" uygun, yaklaşık %{cap_pct:.0f} kapasite"


def _generate_pd_notes(td_ok: bool, slip_qmin: float, cap_pct: float) -> str:
    notes = []
    if not td_ok:
        notes.append("Turndown 1:20 sınırını aşıyor")
    if slip_qmin > 5:
        notes.append(f"Qmin'de slip etkisi yüksek (%{slip_qmin:.1f})")
    if cap_pct > 90:
        notes.append("Over-range koruması önerilir")
    if cap_pct > 5 and not notes:
        notes.append("Tasarım sınırlar içinde")
    return "; ".join(notes) if notes else "Optimum"


def _nps_to_od(nps: int) -> float:
    mapping = {2: 60.3, 3: 88.9, 4: 114.3, 6: 168.3, 8: 219.1,
               10: 273.1, 12: 323.8, 14: 355.6, 16: 406.4}
    return mapping.get(nps, nps * 25.4)
