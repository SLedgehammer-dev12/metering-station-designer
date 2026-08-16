"""
ISO 5167 / AGA 3 / AGA 7 / AGA 9 straight pipe length requirements.
"""
from metering_designer.piping import nps_to_od_m

STRAIGHT_LENGTH_TABLE = {
    "single_bend_90": {
        "description": "Tek 90° dirsek",
        "orifice": {"upstream": "14D - 24D", "value": 18},
        "turbine": {"upstream": "10D - 15D", "value": 12},
        "ultrasonic": {"upstream": "5D - 10D", "value": 10},
        "vortex": {"upstream": "15D - 25D", "value": 15},
        "vcone": {"upstream": "3D - 5D", "value": 3},
        "venturi": {"upstream": "5D - 8D", "value": 5},
        "coriolis": {"upstream": "0D - 2D", "value": 2},
        "pd_meter": {"upstream": "0D - 2D", "value": 2},
    },
    "double_bend_in_plane": {
        "description": "Çift dirsek (düzlem içi)",
        "orifice": {"upstream": "18D - 28D", "value": 22},
        "turbine": {"upstream": "12D - 20D", "value": 15},
        "ultrasonic": {"upstream": "10D - 15D", "value": 12},
        "vortex": {"upstream": "18D - 30D", "value": 18},
        "vcone": {"upstream": "4D - 8D", "value": 4},
        "venturi": {"upstream": "8D - 12D", "value": 8},
        "coriolis": {"upstream": "0D - 2D", "value": 2},
        "pd_meter": {"upstream": "0D - 2D", "value": 2},
    },
    "double_bend_out_of_plane": {
        "description": "Çift dirsek (düzlem dışı)",
        "orifice": {"upstream": "30D - 44D", "value": 35},
        "turbine": {"upstream": "15D - 25D", "value": 20},
        "ultrasonic": {"upstream": "15D - 20D", "value": 18},
        "vortex": {"upstream": "25D - 40D", "value": 25},
        "vcone": {"upstream": "6D - 10D", "value": 6},
        "venturi": {"upstream": "10D - 15D", "value": 10},
        "coriolis": {"upstream": "0D - 2D", "value": 2},
        "pd_meter": {"upstream": "0D - 2D", "value": 2},
    },
    "reducer_expander": {
        "description": "Redüksiyon / Genişletici",
        "orifice": {"upstream": "8D - 16D", "value": 12},
        "turbine": {"upstream": "8D - 12D", "value": 10},
        "ultrasonic": {"upstream": "5D - 10D", "value": 8},
        "vortex": {"upstream": "12D - 20D", "value": 12},
        "vcone": {"upstream": "3D - 5D", "value": 3},
        "venturi": {"upstream": "5D - 8D", "value": 5},
        "coriolis": {"upstream": "0D - 2D", "value": 2},
        "pd_meter": {"upstream": "0D - 2D", "value": 2},
    },
    "full_ball_valve": {
        "description": "Tam geçişli küresel vana",
        "orifice": {"upstream": "10D - 18D", "value": 14},
        "turbine": {"upstream": "10D - 15D", "value": 12},
        "ultrasonic": {"upstream": "5D - 10D", "value": 8},
        "vortex": {"upstream": "12D - 20D", "value": 12},
        "vcone": {"upstream": "3D - 5D", "value": 3},
        "venturi": {"upstream": "5D - 8D", "value": 5},
        "coriolis": {"upstream": "0D - 2D", "value": 2},
        "pd_meter": {"upstream": "0D - 2D", "value": 2},
    },
    "control_valve": {
        "description": "Regülatör / Kontrol vanası",
        "orifice": {"upstream": "20D - 40D", "value": 30},
        "turbine": {"upstream": "15D - 25D", "value": 20},
        "ultrasonic": {"upstream": "15D - 25D", "value": 20},
        "vortex": {"upstream": "25D - 40D", "value": 25},
        "vcone": {"upstream": "6D - 10D", "value": 6},
        "venturi": {"upstream": "10D - 15D", "value": 10},
        "coriolis": {"upstream": "0D - 2D", "value": 2},
        "pd_meter": {"upstream": "0D - 2D", "value": 2},
    },
    "two_or_more_bends": {
        "description": "İki veya daha fazla dirsek (3B)",
        "orifice": {"upstream": "30D - 44D", "value": 35},
        "turbine": {"upstream": "15D - 25D", "value": 20},
        "ultrasonic": {"upstream": "15D - 20D", "value": 18},
        "vortex": {"upstream": "25D - 40D", "value": 25},
        "vcone": {"upstream": "6D - 10D", "value": 6},
        "venturi": {"upstream": "10D - 15D", "value": 10},
        "coriolis": {"upstream": "0D - 2D", "value": 2},
        "pd_meter": {"upstream": "0D - 2D", "value": 2},
    },
}

FLOW_CONDITIONER_REDUCTION = {
    "tube_bundle_19": {"upstream": 20, "downstream": 6, "notes": "ISO 5167-2 Tablo B.1"},
    "zanker": {"upstream": 2, "downstream": 10, "notes": "ISO 5167-1 Tablo 4"},
    "cpa_50e": {"upstream": 2, "downstream": 6, "notes": "ISO 5167-1 Tablo 4"},
    "perforated": {"upstream": 2, "downstream": 8, "notes": "Generic, no ISO compliance"},
    "gallagher": {"upstream": 2, "downstream": 5, "notes": "AGA 9 referenced"},
}


def calc_straight_pipe(
    meter_key: str,
    nps: int,
    upstream_config: str = "single_bend_90",
    with_conditioner: str = None,
    beta_ratio: float = 0.6,
) -> dict:
    od_m = nps_to_od_m(nps)

    meter_type = _map_meter_key(meter_key)
    config_data = STRAIGHT_LENGTH_TABLE.get(upstream_config)
    if not config_data:
        config_data = STRAIGHT_LENGTH_TABLE["single_bend_90"]

    entry = config_data.get(meter_type)
    if not entry:
        entry = config_data.get("orifice")

    upstream_D = entry.get("value", 15)
    # Coriolis and PD meters are not velocity-profile sensitive; V-Cone has a
    # short requirement. Others default to 5D downstream.
    downstream_D = {"vcone": 2, "coriolis": 1, "pd_meter": 1}.get(meter_type, 5)

    if with_conditioner:
        cond = FLOW_CONDITIONER_REDUCTION.get(with_conditioner)
        if cond:
            upstream_D = cond["upstream"] + cond["downstream"]
            downstream_D = 5
    elif meter_type == "orifice":
        upstream_D = _beta_adjusted_upstream(upstream_D, beta_ratio)

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
        "beta_ratio": beta_ratio if meter_type == "orifice" else None,
        "with_conditioner": with_conditioner,
        "conditioner_notes": FLOW_CONDITIONER_REDUCTION.get(with_conditioner, {}).get("notes", "")
        if with_conditioner else None,
    }


def _beta_adjusted_upstream(base_D: float, beta: float) -> float:
    if beta <= 0.3:
        return max(base_D * 0.6, 8)
    elif beta <= 0.5:
        return max(base_D * 0.8, 10)
    elif beta <= 0.65:
        return base_D
    elif beta <= 0.75:
        return base_D * 1.3
    else:
        return base_D * 1.6


def _map_meter_key(key: str) -> str:
    if "orifice" in key:
        return "orifice"
    if "ultrasonic" in key:
        return "ultrasonic"
    if "turbine" in key:
        return "turbine"
    if "vortex" in key:
        return "vortex"
    if "v_cone" in key or "vcone" in key:
        return "vcone"
    if "venturi" in key:
        return "venturi"
    if "coriolis" in key:
        return "coriolis"
    if "positive_displacement" in key or "pd" in key:
        return "pd_meter"
    return "orifice"
