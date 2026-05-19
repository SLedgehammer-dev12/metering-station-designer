"""
IEC 60079-10-1 hazardous area classification for natural gas / petroleum.
Simplified zone determination based on fluid properties.
"""

GAS_GROUPS = {
    "methane": {"group": "IIA", "temperature_class": "T1", "auto_ignition_C": 595},
    "natural_gas": {"group": "IIA", "temperature_class": "T1", "auto_ignition_C": 482},
    "propane": {"group": "IIA", "temperature_class": "T1", "auto_ignition_C": 470},
    "butane": {"group": "IIA", "temperature_class": "T2", "auto_ignition_C": 365},
    "pentane": {"group": "IIA", "temperature_class": "T3", "auto_ignition_C": 260},
    "hexane": {"group": "IIA", "temperature_class": "T3", "auto_ignition_C": 225},
    "hydrogen": {"group": "IIC", "temperature_class": "T1", "auto_ignition_C": 560},
    "h2s": {"group": "IIB", "temperature_class": "T2", "auto_ignition_C": 260},
    "ethylene": {"group": "IIB", "temperature_class": "T2", "auto_ignition_C": 425},
    "acetylene": {"group": "IIC", "temperature_class": "T2", "auto_ignition_C": 305},
    "crude_oil": {"group": "IIA", "temperature_class": "T3", "auto_ignition_C": 260},
}

TEMPERATURE_CLASS_LIMITS = {
    "T1": {"max_surface_C": 450},
    "T2": {"max_surface_C": 300},
    "T3": {"max_surface_C": 200},
    "T4": {"max_surface_C": 135},
    "T5": {"max_surface_C": 100},
    "T6": {"max_surface_C": 85},
}


def classify_ex(
    fluid_type: str = "gas",
    h2s: bool = False,
    h2s_ppm: float = 0.0,
    is_enclosed: bool = False,
    ventilation: str = "natural",
    has_gas_detection: bool = True,
    composition: dict = None,
) -> dict:
    if fluid_type.startswith("gas"):
        if h2s and h2s_ppm > 100:
            fluid_key = "h2s"
        else:
            fluid_key = "natural_gas"
    else:
        fluid_key = "crude_oil"

    gas = GAS_GROUPS.get(fluid_key, GAS_GROUPS["natural_gas"])

    if is_enclosed:
        if ventilation == "natural":
            zone = "Zone 1"
            zone_description = "Sürekli sızdırmazlık arızası ihtimali, doğal havalandırma yetersiz"
        else:
            zone = "Zone 2"
            zone_description = "Mekanik havalandırmalı kapalı alan"
    else:
        if has_gas_detection:
            zone = "Zone 2"
            zone_description = "Açık alan + gaz dedektörü - normalde patlayıcı ortam beklenmez"
        else:
            zone = "Zone 1"
            zone_description = "Açık alan, gaz dedektörü yok"

    temp_class = gas.get("temperature_class", "T1")
    max_surface = TEMPERATURE_CLASS_LIMITS.get(temp_class, {}).get("max_surface_C", 450)

    # Auto-detect T-class from gas composition
    if composition:
        comp_t_class = _detect_t_class_from_composition(composition)
        if comp_t_class:
            temp_class = comp_t_class
            max_surface = TEMPERATURE_CLASS_LIMITS.get(temp_class, {}).get("max_surface_C", 450)

    return {
        "gas_group": gas["group"],
        "temperature_class": temp_class,
        "auto_ignition_C": gas["auto_ignition_C"],
        "zone": zone,
        "zone_description": zone_description,
        "max_surface_temperature_C": max_surface,
        "recommended_protection": _recommend_protection(zone, gas["group"]),
        "recommended_ip": "IP66" if is_enclosed or fluid_type.startswith("gas") else "IP65",
    }


def _recommend_protection(zone: str, gas_group: str) -> list[str]:
    if zone == "Zone 1":
        return ["Ex d (Flameproof)", "Ex ia (Intrinsic Safety)", "Ex e (Increased Safety)"]
    elif zone == "Zone 2":
        return ["Ex nA (Non-sparking)", "Ex ec (Increased Safety)", "Ex nC (Enclosed break)"]
    return ["No special requirement"]


def _detect_t_class_from_composition(composition: dict) -> str:
    """Determine temperature class from gas composition by finding the component with lowest AIT."""
    COMPONENT_AIT = {
        "C1": 595, "C2": 472, "C3": 470, "iC4": 460, "nC4": 405,
        "iC5": 420, "nC5": 260, "C6": 225, "C6plus": 220,
        "N2": 9999, "CO2": 9999, "H2S": 260, "H2": 560, "CO": 609,
    }
    lowest_ait = 9999
    lowest_comp = None
    for comp, mol in composition.items():
        ait = COMPONENT_AIT.get(comp, 9999)
        if mol > 0.5 and ait < lowest_ait:
            lowest_ait = ait
            lowest_comp = comp

    if lowest_ait >= 450: return "T1"
    if lowest_ait >= 300: return "T2"
    if lowest_ait >= 200: return "T3"
    if lowest_ait >= 135: return "T4"
    if lowest_ait >= 100: return "T5"
    return "T6"
