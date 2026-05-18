"""
Pipe schedule recommendation based on ASME B36.10M / B36.19M.
"""

import json
import os

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "knowledge")


def recommend_schedule(nps: int, t_required_mm: float) -> dict:
    path = os.path.join(KNOWLEDGE_DIR, "asme_b313_stress.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sched_data = data.get("schedule_data", {}).get("schedules", {})
    nps_key = f"{nps}_inch"
    if nps_key not in sched_data:
        return {"error": f"NPS {nps}\" schedule verisi bulunamadı"}

    info = sched_data[nps_key]
    od_mm = info.get("od_mm", nps * 25.4)

    available_scheds = []
    for key, wall in info.items():
        if key.startswith("sch_") or key.startswith("sch_"):
            sch_name = key.replace("_", " ").upper()
            available_scheds.append((sch_name, float(wall)))

    available_scheds.sort(key=lambda x: x[1])

    recommended = None
    for sch_name, wall in available_scheds:
        if wall >= t_required_mm:
            recommended = {"schedule_name": sch_name, "wall_mm": wall}
            break

    return {
        "nps": nps,
        "od_mm": od_mm,
        "t_required_mm": round(t_required_mm, 3),
        "recommended": recommended,
        "available_schedules": [{"name": n, "wall": w} for n, w in available_scheds],
        "notes": "ASME B36.10M standard schedule selection" if recommended else "Gerekli kalınlık mevcut schedule'ların üstünde, özel imalat gerekebilir",
    }
