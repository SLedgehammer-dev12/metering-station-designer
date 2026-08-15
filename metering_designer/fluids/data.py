"""Shared component property data — single source of truth loaded from JSON."""
import json
import os

_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "knowledge"
)

_COMP_CACHE = None


def _load_components():
    global _COMP_CACHE
    if _COMP_CACHE is None:
        path = os.path.join(_DATA_DIR, "gas_components.json")
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        _COMP_CACHE = raw.get("components", {})
    return _COMP_CACHE


def get_critical_props() -> dict:
    """Return dict of component → {Tc_K, Pc_bar, Mw_gmol}."""
    comps = _load_components()
    result = {}
    for key, c in comps.items():
        result[key] = {
            "Tc": c.get("critical_temp", 200),
            "Pc": c.get("critical_pressure", 5.0) * 10.0,  # MPa → bar
            "Mw": c.get("molar_mass", 20),
        }
    return result


def get_cv_data() -> dict:
    """Return dict of component → [gross_CV_MJ_m3, net_CV_MJ_m3]."""
    comps = _load_components()
    result = {}
    for key, c in comps.items():
        result[key] = [
            c.get("ideal_gross_cv_MJ_m3", 0),
            c.get("ideal_net_cv_MJ_m3", 0),
        ]
    return result


def get_molar_masses() -> dict:
    """Return dict of component → molar_mass_gmol."""
    comps = _load_components()
    return {k: c.get("molar_mass", 20) for k, c in comps.items()}
