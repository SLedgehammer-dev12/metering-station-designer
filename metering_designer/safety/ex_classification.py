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
