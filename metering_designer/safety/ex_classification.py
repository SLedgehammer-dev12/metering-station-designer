"""
IEC 60079-10-1 hazardous area classification for natural gas / petroleum.
Simplified zone determination based on fluid properties.
"""

from metering_designer.meters.specs import normalize_fluid_type

# IEC 60079-10-1: max surface temperature = 0.8 × AIT (safety factor)
SAFETY_FACTOR = 0.8

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
    if normalize_fluid_type(fluid_type) == "gas":
        if h2s and h2s_ppm > 100:
            fluid_key = "h2s"
        else:
            fluid_key = "natural_gas"
    else:
        fluid_key = "crude_oil"

    gas = GAS_GROUPS.get(fluid_key, GAS_GROUPS["natural_gas"])

    # Map legacy ventilation parameter to detailed parameters
    if ventilation == "natural":
        vent_type = "natural"
        vent_rate = "medium"
    else:
        vent_type = "forced"
        vent_rate = "high"

    zone = classify_zone_detailed(
        is_enclosed=is_enclosed,
        ventilation_type=vent_type,
        ventilation_rate=vent_rate,
        has_gas_detection=has_gas_detection,
        release_grade="secondary",
    )

    # Zone descriptions (backward-compatible)
    if zone == "Zone 0":
        zone_description = "Sürekli patlayıcı ortam"
    elif zone == "Zone 1":
        if is_enclosed and ventilation == "natural":
            zone_description = "Sürekli sızdırmazlık arızası ihtimali, doğal havalandırma yetersiz"
        elif is_enclosed:
            zone_description = "Kapalı alan, yetersiz havalandırma"
        elif not has_gas_detection:
            zone_description = "Açık alan, gaz dedektörü yok"
        else:
            zone_description = "Patlayıcı ortam oluşma ihtimali"
    elif zone == "Zone 2":
        if is_enclosed and ventilation != "natural":
            zone_description = "Mekanik havalandırmalı kapalı alan"
        elif not is_enclosed and has_gas_detection:
            zone_description = "Açık alan + gaz dedektörü - normalde patlayıcı ortam beklenmez"
        else:
            zone_description = "Nadir durumlarda patlayıcı ortam"
    else:  # Non-hazardous
        zone_description = "Patlayıcı ortam beklenmez"

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
        "recommended_ip": "IP66" if is_enclosed or normalize_fluid_type(fluid_type) == "gas" else "IP65",
    }


def _recommend_protection(zone: str, gas_group: str) -> list[str]:
    if zone == "Zone 0":
        # Ex d (flameproof) is NOT permitted in Zone 0 — an explosive atmosphere
        # is continuously present, so only intrinsically-safe (Ex ia), Ex ma or
        # special protection (Ex s) are allowed per IEC 60079-14.
        return ["Ex ia (Intrinsic Safety)", "Ex s (Special protection)"]
    elif zone == "Zone 1":
        return ["Ex d (Flameproof)", "Ex ia (Intrinsic Safety)", "Ex e (Increased Safety)"]
    elif zone == "Zone 2":
        return ["Ex nA (Non-sparking)", "Ex ec (Increased Safety)", "Ex nC (Enclosed break)"]
    return ["No special requirement"]


def classify_zone_detailed(
    is_enclosed: bool,
    ventilation_type: str = "natural",
    ventilation_rate: str = "high",
    has_gas_detection: bool = False,
    release_grade: str = "secondary",
) -> str:
    """Detailed zone classification per IEC 60079-10-1.

    Parameters
    ----------
    is_enclosed : bool
        Whether the area is enclosed.
    ventilation_type : str
        Type of ventilation: natural, forced, or artificial.
    ventilation_rate : str
        Rate of ventilation: high, medium, or low.
    has_gas_detection : bool
        Whether gas detection is installed.
    release_grade : str
        Grade of release: primary, secondary, or continuous.

    Returns
    -------
    str
        Zone classification: "Zone 0", "Zone 1", "Zone 2", or "Non-hazardous".
    """
    # Release grade has highest priority
    if release_grade == "continuous":
        return "Zone 0"  # Zone 0 cannot be reduced by gas detection

    if release_grade == "primary":
        base = "Zone 1"
    else:  # secondary
        if is_enclosed:
            # Enclosed space with forced+high ventilation + gas detection → Zone 2
            if ventilation_type == "forced" and ventilation_rate == "high" and has_gas_detection:
                base = "Zone 2"
            else:
                base = "Zone 1"
        else:
            # Open area
            if ventilation_rate == "high":
                base = "Zone 2"
            else:
                base = "Zone 1"

    # Gas detection mitigation (open areas): a detector justifies Zone 2 over
    # Zone 1 in marginal cases, but IEC 60079-10-1 does not allow it to erase
    # the zone entirely — a secondary release still produces a Zone 2, never a
    # "Non-hazardous" area.
    if has_gas_detection and not is_enclosed:
        if base == "Zone 1":
            base = "Zone 2"

    return base


def _detect_t_class_from_composition(composition: dict) -> str:
    """Determine temperature class from gas composition by finding the component with lowest AIT."""
    COMPONENT_AIT = {
        "C1": 595, "C2": 472, "C3": 470, "iC4": 460, "nC4": 405,
        "iC5": 420, "nC5": 260, "C6": 225, "C6plus": 220,
        "N2": 9999, "CO2": 9999, "H2S": 260, "H2": 560, "CO": 609,
        "C2H2": 305,
    }
    lowest_ait = 9999
    lowest_comp = None
    for comp, mol in composition.items():
        ait = COMPONENT_AIT.get(comp, 9999)
        if mol > 0.005 and ait < lowest_ait:
            lowest_ait = ait
            lowest_comp = comp

    # Apply safety factor per IEC 60079-10-1
    max_surface_temp = lowest_ait * SAFETY_FACTOR

    if max_surface_temp >= 450: return "T1"
    if max_surface_temp >= 300: return "T2"
    if max_surface_temp >= 200: return "T3"
    if max_surface_temp >= 135: return "T4"
    if max_surface_temp >= 100: return "T5"
    return "T6"
