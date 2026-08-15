"""
Pipe schedule recommendation based on ASME B36.10M / B36.19M.

Uses the centralized pipe dimension cache and lookups from
``metering_designer.piping`` (avoiding duplicate JSON loading).
"""

from metering_designer.piping import _load_b3610m


def recommend_schedule(nps: int, t_required_mm: float) -> dict:
    sched_data = _load_b3610m()
    nps_key = f"{nps}_inch"
    if nps_key not in sched_data:
        return {"error": f"NPS {nps}\" schedule verisi bulunamadı"}

    info = sched_data[nps_key]
    od_mm = info.get("od_mm", nps * 25.4)

    available_scheds = []
    for key, wall in info.items():
        if key.endswith("_wall") and key != "od_mm":
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
