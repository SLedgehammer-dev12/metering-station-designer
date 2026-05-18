"""
AGA Report No. 11 / ISO 10790
Coriolis mass flow meter sizing.
"""

import math


def size_coriolis(
    nps: int,
    q_max_Sm3h: float,
    q_min_Sm3h: float,
    P_oper_bar: float,
    T_oper_C: float,
    rho_kg_m3: float,
    mu_Pa_s: float,
    rho_std_kg_m3: float,
) -> dict:
    qm_max_kg_s = q_max_Sm3h * rho_std_kg_m3 / 3600
    qm_min_kg_s = q_min_Sm3h * rho_std_kg_m3 / 3600

    # Available Coriolis sizes and their max capacity
    av_sizes = [0.5, 1, 1.5, 2, 3, 4, 6, 8, 10, 12]
    max_flow_per_size_kg_s = {
        0.5: 0.2, 1: 1.0, 1.5: 2.5, 2: 5.0, 3: 12.0,
        4: 25.0, 6: 60.0, 8: 110.0, 10: 180.0, 12: 300.0,
    }

    # Select meter size
    meter_size = 0.5
    for sz in av_sizes:
        if max_flow_per_size_kg_s.get(sz, 0) >= qm_max_kg_s:
            meter_size = sz
            sizing_note = f"NPS {meter_size}\" seçildi, kapasite yeterli"
            break
    else:
        meter_size = max(av_sizes)
        if qm_max_kg_s > max_flow_per_size_kg_s.get(meter_size, 0):
            sizing_note = f"Birden fazla NPS {meter_size}\" metre gerekebilir"
        else:
            sizing_note = "En büyük standart boy kullanılıyor"

    capacity_pct = qm_max_kg_s / max_flow_per_size_kg_s.get(meter_size, 1) * 100

    # Zero drift effect
    zero_stability = 0.005  # kg/s typical for medium size
    zero_effect_at_qmin = zero_stability / qm_min_kg_s * 100 if qm_min_kg_s > 0 else 100

    # Pressure drop estimation
    id_coriolis_mm = meter_size * 20
    A = math.pi * (id_coriolis_mm / 2000) ** 2
    v_ms = qm_max_kg_s / (rho_kg_m3 * A) if rho_kg_m3 > 0 and A > 0 else 0
    dp_bar = _estimate_coriolis_dp(v_ms, rho_kg_m3, meter_size)

    # Viscosity effect on accuracy
    visc_effect = "None" if mu_Pa_s < 0.05 else "Minimal (<0.05%)" if mu_Pa_s < 0.2 else "Calibrate at operating viscosity"

    return {
        "nps": nps,
        "meter_size_inches": meter_size,
        "qm_max_kg_s": round(qm_max_kg_s, 3),
        "qm_min_kg_s": round(qm_min_kg_s, 4),
        "capacity_percent": round(capacity_pct, 1),
        "sizing_note": sizing_note,
        "zero_stability_kg_s": zero_stability,
        "zero_effect_at_qmin_pct": round(zero_effect_at_qmin, 4),
        "dp_estimate_bar": round(dp_bar, 4),
        "dp_estimate_mbar": round(dp_bar * 1000, 1),
        "viscosity_effect": visc_effect,
        "straight_upstream_D": 0,
        "straight_downstream_D": 0,
        "straight_pipe_note": "Coriolis metre düz boru gerektirmez",
        "notes": _coriolis_notes(capacity_pct, zero_effect_at_qmin),
    }


def _estimate_coriolis_dp(v_ms: float, rho_kg_m3: float, size_in: float) -> float:
    if v_ms <= 0 or rho_kg_m3 <= 0:
        return 0.2
    # Simplified: tube restriction loss + velocity head
    loss_coeff = 1.5 + 2.0 / max(size_in, 0.5)
    dp_pa = loss_coeff * 0.5 * rho_kg_m3 * v_ms ** 2
    return dp_pa / 1e5


def _coriolis_notes(cap_pct: float, zero_effect: float) -> str:
    notes = []
    if cap_pct < 10:
        notes.append("Düşük kapasite kullanımı (<%10), daha küçük boy düşünün")
    elif cap_pct > 95:
        notes.append("Kapasite sınırında, over-range riski var")
    if zero_effect > 0.5:
        notes.append(f"Sıfır kayması etkisi yüksek ({zero_effect:.2f}% @ Qmin)")
    return "; ".join(notes) if notes else "Boyutlandırma optimum"
