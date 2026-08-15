"""
Instrument layout calculation for a metering run.

Determines the count, tag, and location of pressure/temperature/differential
pressure transmitters around a selected meter per relevant standards
(ISO 5167, AGA 7/9/11, API MPMS). Positions are expressed in pipe diameters
(D), with upstream as negative and downstream as positive; 0 is the meter.
"""

import json
import os

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "knowledge")

INSTRUMENT_JSON = "instrument_placements.json"

INSTRUMENT_TYPE_LABELS_TR = {
    "pressure": "Basınç Transmiteri (PT)",
    "temperature": "Sıcaklık Transmiteri (TT)",
    "differential_pressure": "Diferansiyel Basınç Transmiteri (FT/dP)",
}

INSTRUMENT_TYPE_LABELS_EN = {
    "pressure": "Pressure Transmitter (PT)",
    "temperature": "Temperature Transmitter (TT)",
    "differential_pressure": "Differential Pressure Transmitter (FT/dP)",
}

# DEFAULT_COUNTS used when a meter type has no explicit layout entry.
DEFAULT_LAYOUT = {
    "instruments": [
        {"type": "pressure", "count": 1, "position_D": -1.0, "side": "upstream",
         "standard": "Generic", "auto_tag": "PT",
         "note_tr": "Statik basınç transmiteri", "note_en": "Static pressure transmitter"},
        {"type": "temperature", "count": 1, "position_D": 5.0, "side": "downstream",
         "standard": "Generic", "auto_tag": "TT",
         "note_tr": "Sıcaklık transmiteri", "note_en": "Temperature transmitter"},
    ]
}


def _load_placements() -> dict:
    path = os.path.join(KNOWLEDGE_DIR, INSTRUMENT_JSON)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_meter_key(meter_key: str) -> str:
    k = meter_key.lower()
    if "positive_displacement" in k or "pd_meter" in k or "pd" == k:
        return "positive_displacement"
    if "ultrasonic" in k:
        return "ultrasonic"
    if "turbine" in k:
        return "turbine"
    if "coriolis" in k:
        return "coriolis"
    if "vorton" in k or "vortex" in k:
        return "vortex"
    if "v_cone" in k or "vcone" in k:
        return "v_cone"
    if "venturi" in k:
        return "venturi"
    if "orifice" in k:
        return "orifice"
    return k


def compute_instrument_layout(
    meter_key: str,
    nps: int = 8,
    conditioner_key: str | None = None,
    tags_start: int = 1001,
) -> dict:
    """Compute instrument count, tags, and placement for a meter run.

    Returns:
        {
          "meter_key": str,
          "instruments": [ {type, count, auto_tag, position_D, side, standard,
                            note_tr, note_en, tag_list:[str], position_m:float} ],
          "conditioner_key": str | None,
          "notes": [str],
          "nps": int,
          "od_m": float,
          "counts": {"pressure": n, "temperature": n, "differential_pressure": n}
        }
    """
    placements = _load_placements()
    mkey = _normalize_meter_key(meter_key)
    entry = placements.get("layouts", {}).get(mkey, DEFAULT_LAYOUT)
    inst_specs = list(entry.get("instruments", []))
    od_m = (nps * 25.4) / 1000.0 if 2 <= nps <= 48 else 0.3

    # If a conditioner is upstream, add a dedicated PT immediately before it
    # so the conditioner pressure drop is monitored.
    if conditioner_key:
        inst_specs = list(inst_specs)
        inst_specs.insert(0, {
            "type": "pressure", "count": 1, "position_D": -2.0, "side": "upstream",
            "standard": "ISO 5167-1 Table 4 (conditioner upstream PT)",
            "auto_tag": "PT",
            "note_tr": "Statik basınç transmiteri — akış düzenleyici öncesi",
            "note_en": "Static pressure transmitter — upstream of conditioner",
        })

    instruments = []
    counts = {"pressure": 0, "temperature": 0, "differential_pressure": 0}
    tag_no = tags_start

    for spec in inst_specs:
        itype = spec.get("type", "pressure")
        count = int(spec.get("count", 1))
        auto_tag = spec.get("auto_tag", {"pressure": "PT", "temperature": "TT",
                                          "differential_pressure": "FT"}.get(itype, "TX"))
        position_D = float(spec.get("position_D", 0.0))
        tag_list = ["-".join([auto_tag, str(tag_no + i)]) for i in range(count)]
        tag_no += count

        instruments.append({
            "type": itype,
            "count": count,
            "auto_tag": auto_tag,
            "position_D": position_D,
            "side": spec.get("side", "upstream"),
            "standard": spec.get("standard", ""),
            "note_tr": spec.get("note_tr", ""),
            "note_en": spec.get("note_en", ""),
            "tag_list": tag_list,
            "position_m": round(position_D * od_m, 3),
        })
        counts[itype] = counts.get(itype, 0) + count

    return {
        "meter_key": mkey,
        "instruments": instruments,
        "conditioner_key": conditioner_key,
        "notes": list(entry.get("notes", [])),
        "nps": nps,
        "od_m": round(od_m, 4),
        "counts": counts,
    }


def summarize_layout(layout: dict) -> list[dict]:
    """Rows for easy display: instrument type label, count, tags, location."""
    rows = []
    for inst in layout.get("instruments", []):
        rows.append({
            "type": inst["type"],
            "count": inst["count"],
            "tag_list": ", ".join(inst["tag_list"]),
            "position_D": inst["position_D"],
            "position_m": inst["position_m"],
            "side": inst["side"],
            "standard": inst["standard"],
        })
    return rows