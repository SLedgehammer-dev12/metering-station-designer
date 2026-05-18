"""
ISO 5167 / AGA 3 / AGA 7 / AGA 9 straight pipe length requirements.
"""

STRAIGHT_LENGTH_TABLE = {
    "single_bend_90": {
        "description": "Tek 90° dirsek",
        "orifice": {"upstream": "14D - 24D", "value": 18},
        "turbine": {"upstream": "10D - 15D", "value": 12},
        "ultrasonic": {"upstream": "5D - 10D", "value": 10},
    },
    "double_bend_in_plane": {
        "description": "Çift dirsek (düzlem içi)",
        "orifice": {"upstream": "18D - 28D", "value": 22},
        "turbine": {"upstream": "12D - 20D", "value": 15},
        "ultrasonic": {"upstream": "10D - 15D", "value": 12},
    },
    "double_bend_out_of_plane": {
        "description": "Çift dirsek (düzlem dışı)",
        "orifice": {"upstream": "30D - 44D", "value": 35},
        "turbine": {"upstream": "15D - 25D", "value": 20},
        "ultrasonic": {"upstream": "15D - 20D", "value": 18},
    },
    "reducer_expander": {
        "description": "Redüksiyon / Genişletici",
        "orifice": {"upstream": "8D - 16D", "value": 12},
        "turbine": {"upstream": "8D - 12D", "value": 10},
        "ultrasonic": {"upstream": "5D - 10D", "value": 8},
    },
    "full_ball_valve": {
        "description": "Tam geçişli küresel vana",
        "orifice": {"upstream": "10D - 18D", "value": 14},
        "turbine": {"upstream": "10D - 15D", "value": 12},
        "ultrasonic": {"upstream": "5D - 10D", "value": 8},
    },
    "control_valve": {
        "description": "Regülatör / Kontrol vanası",
        "orifice": {"upstream": "20D - 40D", "value": 30},
        "turbine": {"upstream": "15D - 25D", "value": 20},
        "ultrasonic": {"upstream": "15D - 25D", "value": 20},
    },
    "two_or_more_bends": {
        "description": "İki veya daha fazla dirsek (3B)",
        "orifice": {"upstream": "30D - 44D", "value": 35},
        "turbine": {"upstream": "15D - 25D", "value": 20},
        "ultrasonic": {"upstream": "15D - 20D", "value": 18},
    },
}

FLOW_CONDITIONER_REDUCTION = {
    "tube_bundle_19": {"upstream": 20, "downstream": 6, "notes": "ISO 5167-2 Tablo B.1"},
    "zanker": {"upstream": 2, "downstream": 10, "notes": "ISO 5167-1 Tablo 4"},
    "cpa_50e": {"upstream": 2, "downstream": 6, "notes": "ISO 5167-1 Tablo 4"},
    "perforated": {"upstream": 2, "downstream": 8, "notes": "Generic, no ISO compliance"},
}


def calc_straight_pipe(
    meter_key: str,
    nps: int,
    upstream_config: str = "single_bend_90",
    with_conditioner: str = None,
    beta_ratio: float = 0.6,
) -> dict:
    od_m = nps * 0.0254 if nps <= 48 else nps * 25.4 / 1000

    meter_type = _map_meter_key(meter_key)
    config_data = STRAIGHT_LENGTH_TABLE.get(upstream_config)
    if not config_data:
        config_data = STRAIGHT_LENGTH_TABLE["single_bend_90"]

    entry = config_data.get(meter_type)
    if not entry:
        entry = config_data.get("orifice")

    upstream_D = entry.get("value", 15)
    downstream_D = 5

    if with_conditioner:
        cond = FLOW_CONDITIONER_REDUCTION.get(with_conditioner)
        if cond:
            upstream_D = cond["upstream"] + cond["downstream"]
            downstream_D = 5

    upstream_m = upstream_D * od_m
    downstream_m = downstream_D * od_m

    return {
        "upstream_required_diameters": upstream_D,
        "downstream_required_diameters": downstream_D,
        "upstream_required_m": round(upstream_m, 3),
        "downstream_required_m": round(downstream_m, 3),
        "total_required_m": round(upstream_m + downstream_m, 3),
        "meter_type": meter_type,
        "upstream_config": upstream_config,
    }


def _map_meter_key(key: str) -> str:
    if "orifice" in key:
        return "orifice"
    if "ultrasonic" in key:
        return "ultrasonic"
    if "turbine" in key:
        return "turbine"
    if "coriolis" in key:
        return "orifice"
    if "positive_displacement" in key or "pd" in key:
        return "orifice"
    return "orifice"
