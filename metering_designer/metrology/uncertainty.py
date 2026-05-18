"""
ISO 5168 / ISO 61508 measurement uncertainty budget calculation.
"""

import math


UNCERTAINTY_FACTORS = {
    "ultrasonic": {
        "meter": {"value": 0.35, "type": "B", "distribution": "normal"},
        "calibration": {"value": 0.20, "type": "B", "distribution": "normal"},
        "flow_profile": {"value": 0.10, "type": "A", "distribution": "normal"},
        "gc_composition": {"value": 0.10, "type": "B", "distribution": "normal"},
        "pressure_transmitter": {"value": 0.05, "type": "B", "distribution": "rectangular"},
        "temperature_transmitter": {"value": 0.02, "type": "B", "distribution": "rectangular"},
        "flow_computer": {"value": 0.01, "type": "B", "distribution": "rectangular"},
    },
    "orifice": {
        "meter": {"value": 0.60, "type": "B", "distribution": "normal"},
        "calibration": {"value": 0.15, "type": "B", "distribution": "normal"},
        "dp_transmitter": {"value": 0.10, "type": "B", "distribution": "normal"},
        "gc_composition": {"value": 0.10, "type": "B", "distribution": "normal"},
        "gas_analysis": {"value": 0.10, "type": "B", "distribution": "normal"},
        "pressure_transmitter": {"value": 0.05, "type": "B", "distribution": "rectangular"},
        "temperature_transmitter": {"value": 0.02, "type": "B", "distribution": "rectangular"},
        "flow_computer": {"value": 0.01, "type": "B", "distribution": "rectangular"},
    },
    "turbine": {
        "meter": {"value": 0.50, "type": "B", "distribution": "normal"},
        "calibration": {"value": 0.15, "type": "B", "distribution": "normal"},
        "gc_composition": {"value": 0.10, "type": "B", "distribution": "normal"},
        "gas_analysis": {"value": 0.10, "type": "B", "distribution": "normal"},
        "pressure_transmitter": {"value": 0.05, "type": "B", "distribution": "rectangular"},
        "temperature_transmitter": {"value": 0.02, "type": "B", "distribution": "rectangular"},
        "flow_computer": {"value": 0.01, "type": "B", "distribution": "rectangular"},
    },
    "coriolis": {
        "meter": {"value": 0.15, "type": "B", "distribution": "normal"},
        "calibration": {"value": 0.10, "type": "B", "distribution": "normal"},
        "zero_drift": {"value": 0.05, "type": "A", "distribution": "normal"},
        "pressure_transmitter": {"value": 0.05, "type": "B", "distribution": "rectangular"},
        "flow_computer": {"value": 0.01, "type": "B", "distribution": "rectangular"},
    },
    "positive_displacement": {
        "meter": {"value": 0.15, "type": "B", "distribution": "normal"},
        "calibration": {"value": 0.10, "type": "B", "distribution": "normal"},
        "slip_correction": {"value": 0.05, "type": "A", "distribution": "normal"},
        "temperature_correction": {"value": 0.02, "type": "B", "distribution": "rectangular"},
        "pressure_transmitter": {"value": 0.05, "type": "B", "distribution": "rectangular"},
        "flow_computer": {"value": 0.01, "type": "B", "distribution": "rectangular"},
    },
    "vortex": {
        "meter": {"value": 0.75, "type": "B", "distribution": "normal"},
        "calibration": {"value": 0.20, "type": "B", "distribution": "normal"},
        "gc_composition": {"value": 0.15, "type": "B", "distribution": "normal"},
        "pressure_transmitter": {"value": 0.05, "type": "B", "distribution": "rectangular"},
        "temperature_transmitter": {"value": 0.02, "type": "B", "distribution": "rectangular"},
        "flow_computer": {"value": 0.01, "type": "B", "distribution": "rectangular"},
    },
    "vcone": {
        "meter": {"value": 0.50, "type": "B", "distribution": "normal"},
        "calibration": {"value": 0.15, "type": "B", "distribution": "normal"},
        "gc_composition": {"value": 0.10, "type": "B", "distribution": "normal"},
        "pressure_transmitter": {"value": 0.05, "type": "B", "distribution": "rectangular"},
        "temperature_transmitter": {"value": 0.02, "type": "B", "distribution": "rectangular"},
        "flow_computer": {"value": 0.01, "type": "B", "distribution": "rectangular"},
    },
}


def calc_uncertainty_budget(meter_key: str) -> dict:
    for full_key in UNCERTAINTY_FACTORS:
        if full_key in meter_key:
            factors = UNCERTAINTY_FACTORS[full_key]
            break
    else:
        factors = UNCERTAINTY_FACTORS.get(meter_key, UNCERTAINTY_FACTORS["orifice"])

    components = []
    sum_squares = 0.0

    for name, spec in factors.items():
        val = spec["value"]
        k_factor = 1.0
        if spec["distribution"] == "normal":
            k_factor = 1.0
        elif spec["distribution"] == "rectangular":
            val = val / math.sqrt(3)

        components.append({
            "name": name,
            "value_pct": spec["value"],
            "type": spec["type"],
            "distribution": spec["distribution"],
            "standard_uncertainty_pct": round(val, 4),
        })
        sum_squares += val ** 2

    combined = math.sqrt(sum_squares)
    expanded_k2 = combined * 2
    expanded_k3 = combined * 3

    return {
        "meter_type": meter_key,
        "components": components,
        "combined_standard_uncertainty_pct": round(combined, 4),
        "expanded_uncertainty_k2_95pct": round(expanded_k2, 4),
        "expanded_uncertainty_k3_99pct": round(expanded_k3, 4),
        "coverage_factor_comment": "k=2 for 95% confidence (ISO 5168)",
    }
