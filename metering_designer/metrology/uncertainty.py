"""
ISO 5168 / ISO 61508 measurement uncertainty budget calculation.
"""

import math

try:
    from uncertainties import ufloat
    HAS_UNCERTAINTIES = True
except ImportError:
    HAS_UNCERTAINTIES = False


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


ADDITIONAL_UNCERTAINTY_TERMS = {
    "installation_effect": {"value": 0.10, "distribution": "rectangular", "description": "Installation effects (flow profile distortion)"},
    "pulsation": {"value": 0.05, "distribution": "rectangular", "description": "Pulsation effects from compressors/regulators"},
    "long_term_drift": {"value": 0.10, "distribution": "rectangular", "description": "Long-term drift/in-service degradation between calibrations"},
    "ambient_temperature": {"value": 0.05, "distribution": "rectangular", "description": "Ambient temperature effects on transmitter electronics"},
    "ad_conversion": {"value": 0.01, "distribution": "rectangular", "description": "A/D conversion resolution"},
}


def calc_uncertainty_budget_detailed(
    meter_key: str,
    pulsation_dampened: bool = False,
    flow_conditioner_installed: bool = False,
    geometric_contribution_pct: float = 0.0,
) -> dict:
    """
    Calculate an ISO 5168 uncertainty budget including additional
    uncertainty terms not covered by the basic budget:
      - Installation effects (flow profile distortion)
      - Pulsation effects
      - Long-term drift / in-service degradation
      - Ambient temperature effects on electronics
      - A/D conversion resolution

    Parameters
    ----------
    meter_key : str
        Meter type key (e.g. 'ultrasonic', 'orifice', 'turbine', ...).
    pulsation_dampened : bool
        If True, the pulsation term is reduced from 0.05 % to 0.02 %.
    flow_conditioner_installed : bool
        If True, the installation effect term is reduced from 0.10 % to 0.05 %.
    geometric_contribution_pct : float
        Additional standard uncertainty contribution from geometric
        non-conformances found during inspection (ISO 5168 re-verification).
        When > 0, it is RSS-combined into the budget and the GUM-compliant
        propagated uncertainty (uncertainties library) is reported.
        Default 0.0 keeps backward compatibility.

    Returns
    -------
    dict with keys:
        meter_type, components, combined_standard_uncertainty_pct,
        expanded_uncertainty_k2_95pct, expanded_uncertainty_k3_99pct,
        coverage_factor_comment, includes_additional_terms,
        geometric_contribution_pct, and (when geometric_contribution_pct > 0)
        gum_combined_standard_uncertainty_pct, gum_std_uncertainty, gum_expanded_k2_pct
    """
    # 1. Get the basic budget
    basic = calc_uncertainty_budget(meter_key)

    # 2. Build additional components
    extra_components = []
    sum_squares_extra = 0.0

    for name, spec in ADDITIONAL_UNCERTAINTY_TERMS.items():
        val = spec["value"]

        # Apply modifiers
        if name == "pulsation" and pulsation_dampened:
            val = 0.02
        if name == "installation_effect" and flow_conditioner_installed:
            val = 0.05

        # Convert rectangular to standard uncertainty
        k_div = 1.0
        if spec["distribution"] == "rectangular":
            std_val = val / math.sqrt(3)
        else:
            std_val = val

        extra_components.append({
            "name": name,
            "value_pct": val,
            "source": "additional",
            "type": "B",
            "distribution": spec["distribution"],
            "description": spec["description"],
            "standard_uncertainty_pct": round(std_val, 4),
        })
        sum_squares_extra += std_val ** 2

    # 2b. Geometric contribution from inspection non-conformances
    if geometric_contribution_pct and geometric_contribution_pct > 0:
        extra_components.append({
            "name": "geometric_deviation",
            "value_pct": round(geometric_contribution_pct, 4),
            "source": "inspection",
            "type": "A",
            "distribution": "normal",
            "description": "Geometric deviation contribution from inspection findings",
            "standard_uncertainty_pct": round(geometric_contribution_pct, 4),
        })
        sum_squares_extra += geometric_contribution_pct ** 2

    # 3. Combine: RSS of basic combined + extra terms
    combined_std = basic["combined_standard_uncertainty_pct"]
    combined_new = math.sqrt(combined_std ** 2 + sum_squares_extra)

    expanded_k2 = combined_new * 2
    expanded_k3 = combined_new * 3

    result = {
        "meter_type": meter_key,
        "components": basic["components"] + extra_components,
        "combined_standard_uncertainty_pct": round(combined_new, 4),
        "expanded_uncertainty_k2_95pct": round(expanded_k2, 4),
        "expanded_uncertainty_k3_99pct": round(expanded_k3, 4),
        "coverage_factor_comment": "k=2 for 95% confidence (ISO 5168); includes additional uncertainty terms",
        "includes_additional_terms": True,
        "pulsation_dampened": pulsation_dampened,
        "flow_conditioner_installed": flow_conditioner_installed,
        "geometric_contribution_pct": round(geometric_contribution_pct, 4),
    }

    # 4. GUM-compliant propagation: model the combined estimate with
    #    epistemic uncertainty (5% relative) when a geometric contribution
    #    is present, mirroring recompute_uncertainty() in the inspection module.
    #    NOTE: geometric_contribution_pct is already RSS-combined in
    #    combined_new above, so it must NOT be re-added here.
    if HAS_UNCERTAINTIES and geometric_contribution_pct > 0:
        u_combined = ufloat(combined_new, combined_new * 0.05)
        result["gum_combined_standard_uncertainty_pct"] = round(u_combined.nominal_value, 4)
        result["gum_std_uncertainty"] = round(u_combined.std_dev, 6)
        result["gum_expanded_k2_pct"] = round(u_combined.nominal_value * 2, 4)

    return result
