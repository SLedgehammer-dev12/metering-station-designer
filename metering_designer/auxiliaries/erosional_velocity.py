"""
API RP 14E — Erosional velocity limit check for piping.
v_e = C / sqrt(rho_kg_m3) with SI-unit constants:
    C = 122  (continuous service)
    C = 152.5 (intermittent service)
(US-unit constants 100/125 apply when density is in lb/ft³; with SI density in
kg/m³ the standard recommends 122/152.5.)
"""

import math


def check_erosional_velocity(
    velocity_m_s: float,
    rho_kg_m3: float,
    service_type: str = "continuous",
) -> dict:
    if rho_kg_m3 <= 0:
        return {"error": "Density must be > 0"}

    C = 122 if service_type == "continuous" else 152.5
    v_erosional = C / math.sqrt(rho_kg_m3)

    ok = velocity_m_s <= v_erosional
    margin_pct = (v_erosional - velocity_m_s) / v_erosional * 100 if v_erosional > 0 else 0

    return {
        "velocity_m_s": round(velocity_m_s, 2),
        "rho_kg_m3": round(rho_kg_m3, 2),
        "v_erosional_m_s": round(v_erosional, 2),
        "C_factor": C,
        "service_type": service_type,
        "ok": ok,
        "margin_pct": round(margin_pct, 1),
        "warning": None if ok else f"Hız ({velocity_m_s:.1f} m/s) erozyonel limiti ({v_erosional:.1f} m/s) aşıyor! Boru erozyonu riski.",
        "standard": "API RP 14E",
    }
