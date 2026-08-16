"""
AGA Report No. 9 / ISO 17089
Ultrasonic meter sizing and path configuration.
"""

import math


def _standard_profile(standard: str | None) -> dict:
    """Resolve the USM design standard profile (velocity limits, references)."""
    from metering_designer.standards.design_standards import get_standard

    profile = get_standard("ultrasonic", standard) or {}
    std_id = (standard or "aga9").lower()
    if std_id not in ("aga9", "iso17089"):
        std_id = "aga9"
    return {
        "standard": std_id,
        "standard_name": profile.get("name", "AGA Report No.9"),
        "standard_ref": profile.get("standard_ref", "AGA Report No.9"),
        "velocity_range": profile.get("velocity_range", (0.3, 30.0)),
    }


def size_ultrasonic(
    nps: int,
    q_max_Sm3h: float,
    q_min_Sm3h: float,
    P_oper_bar: float,
    T_oper_C: float,
    rho_kg_m3: float,
    mu_Pa_s: float,
    rho_std_kg_m3: float,
    standard: str | None = None,
) -> dict:
    std = _standard_profile(standard)
    v_lo, v_hi = std["velocity_range"]
    od_mm = _nps_to_od(nps)
    from metering_designer.piping import pipe_id_mm
    id_mm = pipe_id_mm(nps)
    id_m = id_mm / 1000
    A = math.pi * (id_m / 2) ** 2

    qm_max = q_max_Sm3h * rho_std_kg_m3 / 3600
    qm_min = q_min_Sm3h * rho_std_kg_m3 / 3600

    qv_max_m3h = qm_max / rho_kg_m3 * 3600 if rho_kg_m3 > 0 else 0
    v_max = qv_max_m3h / 3600 / A if A > 0 else 0
    v_min = q_min_Sm3h * rho_std_kg_m3 / rho_kg_m3 / 3600 / A if rho_kg_m3 > 0 and A > 0 else 0
    Re = rho_kg_m3 * v_max * id_m / mu_Pa_s if mu_Pa_s > 0 else 0
    turndown = q_max_Sm3h / q_min_Sm3h if q_min_Sm3h > 0 else float("inf")

    velocity_ok = v_lo <= v_max <= v_hi

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
    if v_lo <= v_max <= v_hi * 0.85:
        meter_size = nps
        sizing_note = f"{std['standard_name']} için aynı çapta metre uygun"
    elif v_max < v_lo:
        meter_size = max(nps - 2, 2)
        sizing_note = f"Düşük hız, daha küçük metre (NPS {meter_size}) önerilir"
    elif v_max > v_hi:
        meter_size = nps + 2
        sizing_note = f"Yüksek hız, daha büyük metre (NPS {meter_size}) düşünülmeli"
    else:
        meter_size = nps
        sizing_note = f"Hız {std['standard_name']} sınırları içinde, kabul edilebilir"

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
        "standard": std["standard"],
        "standard_name": std["standard_name"],
        "standard_ref": std["standard_ref"],
        "notes": _generate_usm_notes(v_max, velocity_ok, turndown, std),
    }


def size_ultrasonic_with_fluid(
    nps: int,
    q_max_Sm3h: float,
    q_min_Sm3h: float,
    fluid: "Fluid",
    P_oper_bar: float = 40.0,
    T_oper_C: float = 20.0,
    standard: str | None = None,
) -> dict:
    """Wrapper around size_ultrasonic that accepts Fluid object.

    Args:
        nps: nominal pipe size
        q_max_Sm3h: maximum flow rate [Sm³/h]
        q_min_Sm3h: minimum flow rate [Sm³/h]
        fluid: Fluid dataclass instance
        P_oper_bar: operating pressure [bar]
        T_oper_C: operating temperature [°C]
        standard: design standard id ('aga9' or 'iso17089')
    """
    from metering_designer.fluids.fluid import Fluid

    rho = fluid.rho_oper_kg_m3
    mu = fluid.mu_dynamic_Pa_s
    rho_std = fluid.rho_std_kg_m3

    return size_ultrasonic(
        nps, q_max_Sm3h, q_min_Sm3h, P_oper_bar, T_oper_C,
        rho, mu, rho_std, standard=standard,
    )


def _estimate_k_factor(paths: int, Re: float) -> float:
    base = {2: 1.005, 4: 1.002, 6: 1.001, 8: 1.0005}
    return base.get(paths, 1.003)


def _generate_usm_notes(v_max: float, v_ok: bool, turndown: float, std: dict | None = None) -> str:
    std = std or {}
    std_name = std.get("standard_name", "AGA 9")
    v_lo, v_hi = std.get("velocity_range", (0.3, 30.0))
    notes = []
    if not v_ok:
        notes.append(f"Hız {v_max:.1f} m/s {std_name} sınırları dışında ({v_lo}-{v_hi} m/s)")
    if turndown > 100:
        notes.append(f"Turndown {turndown}:1 {std_name} sınırını aşıyor (>100:1)")
    if turndown <= 50:
        notes.append("Turndown limit içinde, optimum çalışma")
    return "; ".join(notes) if notes else f"Hız ve turndown {std_name} sınırları içinde"


def _nps_to_od(nps: int) -> float:
    mapping = {2: 60.3, 3: 88.9, 4: 114.3, 6: 168.3, 8: 219.1,
               10: 273.1, 12: 323.8, 14: 355.6, 16: 406.4, 18: 457.2,
               20: 508.0, 24: 609.6, 30: 762.0, 36: 914.4, 42: 1066.8, 48: 1219.2}
    return mapping.get(nps, nps * 25.4)
