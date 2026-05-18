"""
ASME B31.3/4/8 based pipe wall thickness calculation.
"""

import json
import os
import math

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "knowledge")


_NPS_TO_OD = {
    2: 60.3, 3: 88.9, 4: 114.3, 6: 168.3, 8: 219.1,
    10: 273.1, 12: 323.8, 14: 355.6, 16: 406.4, 18: 457.2,
    20: 508.0, 22: 558.8, 24: 609.6, 30: 762.0, 36: 914.4,
    42: 1066.8, 48: 1219.2,
}

_OD_TO_NPS = {v: k for k, v in _NPS_TO_OD.items()}


def load_stress_data():
    path = os.path.join(KNOWLEDGE_DIR, "asme_b313_stress.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_nps_from_od(od_mm: float) -> int:
    closest = min(_OD_TO_NPS.keys(), key=lambda x: abs(x - od_mm))
    return _OD_TO_NPS.get(closest, 0)


def get_od_from_nps(nps: int) -> float:
    return _NPS_TO_OD.get(nps, nps * 25.4)


def calc_min_wall_thickness(
    design_p_bar: float,
    design_t_C: float,
    od_mm: float,
    material: str,
    corrosion_mm: float = 3.0,
    joint_efficiency: float = 1.0,
    standard: str = "B31.3",
    y_factor: float = 0.4,
    mill_tolerance_pct: float = 12.5,
) -> dict:
    data = load_stress_data()
    mats = data.get("materials", {})

    material_key = material
    if material_key not in mats:
        for k in mats:
            if material.lower() in k.lower() or k.lower() in material.lower():
                material_key = k
                break
        else:
            return {"error": f"Malzeme {material} veritabanında bulunamadı"}

    mat = mats[material_key]
    stress_table = mat.get("allowable_stress", {})

    S = _interpolate_stress(stress_table, design_t_C)
    if S is None:
        return {"error": f"{material} için {design_t_C}°C'de gerilme değeri yok"}

    P_MPa = design_p_bar * 0.1  # bar → MPa (for ASME B31.3 S in MPa)
    D = od_mm
    E = joint_efficiency
    Y = y_factor
    CA = corrosion_mm
    W = 1.0  # weld joint strength reduction factor

    if standard in ("B31.3", "B31.4"):
        tm = P_MPa * D / (2 * (S * E * W + P_MPa * Y))
    elif standard == "B31.8":
        tm = P_MPa * D / (2 * S * E * W * 0.72)
    else:
        tm = P_MPa * D / (2 * S)

    t_required = tm + CA
    t_with_mill = t_required / (1 - mill_tolerance_pct / 100)

    return {
        "material": mat.get("name", material),
        "material_key": material_key,
        "standard": standard,
        "design_P_bar": design_p_bar,
        "design_T_C": design_t_C,
        "od_mm": D,
        "allowable_stress_MPa": round(S, 2),
        "t_min_pressure_mm": round(tm, 3),
        "corrosion_allowance_mm": CA,
        "t_required_mm": round(t_required, 3),
        "t_with_tolerance_mm": round(t_with_mill, 3),
        "joint_efficiency": E,
        "notes": "ASME B31.3 Eq. (3a): tm = P*D/(2*(S*E*W + P*Y))" if standard == "B31.3" else "",
    }


def calc_flange_min_class(
    design_p_bar: float,
    design_t_C: float,
    material_group: str = "carbon_steel",
) -> dict:
    path = os.path.join(KNOWLEDGE_DIR, "asme_b165_ratings.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    groups = data.get("material_groups", {})
    if material_group not in groups:
        return {"error": f"Malzeme grubu {material_group} bulunamadı"}

    group = groups[material_group]
    ratings = group.get("ratings", {})
    classes = sorted(ratings.keys(), key=lambda c: int(c.split("_")[1]))

    for cls in classes:
        pt_table = ratings[cls]
        max_p = _interpolate_stress(pt_table, design_t_C, temp_key_format="standard")
        if max_p is not None and design_p_bar <= max_p * 1.05:
            cls_num = int(cls.split("_")[1])
            return {
                "flange_class": cls_num,
                "max_p_at_T_bar": round(max_p, 1),
                "material_group": group.get("name", material_group),
                "notes": f"{cls_num}# flanş {design_p_bar} bar @ {design_t_C}°C için yeterli",
            }

    return {
        "error": f"{design_p_bar} bar @ {design_t_C}°C için uygun flanş bulunamadı (2500# üstü gerekebilir)"
    }


def _interpolate_stress(table: dict, temp_C: float, temp_key_format: str = "standard") -> float | None:
    if not table:
        return None

    temps = []
    values = []
    for k, v in table.items():
        try:
            if temp_key_format == "standard":
                t = float(k.replace("_", "-").split("_")[-1]) if "_" in k else float(k)
            else:
                t = float(k)
            temps.append(t)
            values.append(float(v))
        except (ValueError, TypeError):
            continue

    if not temps:
        return None

    sorted_pairs = sorted(zip(temps, values))
    temps_sorted, vals_sorted = zip(*sorted_pairs)

    if temp_C <= temps_sorted[0]:
        return vals_sorted[0]
    if temp_C >= temps_sorted[-1]:
        return vals_sorted[-1]

    for i in range(len(temps_sorted) - 1):
        if temps_sorted[i] <= temp_C <= temps_sorted[i + 1]:
            ratio = (temp_C - temps_sorted[i]) / (temps_sorted[i + 1] - temps_sorted[i])
            return vals_sorted[i] + ratio * (vals_sorted[i + 1] - vals_sorted[i])

    return vals_sorted[-1]
