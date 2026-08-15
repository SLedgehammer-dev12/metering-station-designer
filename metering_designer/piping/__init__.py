"""Centralized pipe dimension utilities (ASME B36.10M)."""
import json
import os

_KNOWLEDGE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "knowledge"
)

_B3610M_CACHE = None


def _load_b3610m():
    global _B3610M_CACHE
    if _B3610M_CACHE is None:
        path = os.path.join(_KNOWLEDGE_DIR, "asme_b313_stress.json")
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        _B3610M_CACHE = raw.get("schedule_data", {}).get("schedules", {})
    return _B3610M_CACHE


_KEY_MAP = {
    2: "2_inch", 3: "3_inch", 4: "4_inch", 6: "6_inch",
    8: "8_inch", 10: "10_inch", 12: "12_inch", 14: "14_inch",
    16: "16_inch", 18: "18_inch", 20: "20_inch", 22: "22_inch",
    24: "24_inch",
}

# ASME B36.10M OD fallback for NPS not in JSON schedule data
_FALLBACK_OD_MM = {
    2: 60.3, 3: 88.9, 4: 114.3, 6: 168.3,
    8: 219.1, 10: 273.1, 12: 323.8, 14: 355.6,
    16: 406.4, 18: 457.2, 20: 508.0, 22: 558.8,
    24: 609.6,
}


def nps_to_od_mm(nps: int) -> float:
    """ASME B36.10M: convert Nominal Pipe Size to actual Outside Diameter in mm."""
    if nps in _FALLBACK_OD_MM:
        return _FALLBACK_OD_MM[nps]
    _warn_unknown_nps(nps)
    return float(nps) * 25.4


_warnings_issued = set()

def _warn_unknown_nps(nps: int) -> None:
    if nps not in _warnings_issued:
        _warnings_issued.add(nps)
        import warnings
        warnings.warn(f"NPS {nps} not in ASME B36.10M table; using approximate NPS×25.4 = {nps*25.4:.1f} mm")


def nps_to_od_m(nps: int) -> float:
    return nps_to_od_mm(nps) / 1000.0


def get_schedule_wall_mm(nps: int, schedule: str) -> float:
    """Return ASME B36.10M nominal wall thickness in mm for given NPS and schedule."""
    schedules = _load_b3610m()
    key = _KEY_MAP.get(nps)
    if key is None:
        _warn_unknown_nps(nps)
        return 0.0
    entry = schedules.get(key, {})
    if not entry:
        return 0.0
    for pattern in [f"sch_{schedule}_wall", f"{schedule}_wall",
                    f"sch_{schedule}_wall".replace("sch_sch_", "sch_")]:
        if pattern in entry:
            return float(entry[pattern])
    import warnings
    warnings.warn(f"Schedule {schedule} not found for NPS {nps}")
    return 0.0


def find_schedule_for_thickness(nps: int, t_required_mm: float) -> str | None:
    """Find the lightest ASME B36.10M schedule that meets t_required."""
    schedules = _load_b3610m()
    key = _KEY_MAP.get(nps)
    if key is None:
        return None
    entry = schedules.get(key, {})
    candidates = []
    for sch_key, wall in entry.items():
        if sch_key.endswith("_wall") and sch_key != "od_mm":
            sch_name = sch_key.replace("_wall", "").replace("sch_", "")
            if wall >= t_required_mm:
                candidates.append((wall, sch_name.upper()))
    candidates.sort()
    return candidates[0][1] if candidates else None


def get_od_mm_for_nps(nps: int) -> float:
    """Alias for nps_to_od_mm."""
    return nps_to_od_mm(nps)
