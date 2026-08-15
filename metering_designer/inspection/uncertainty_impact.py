"""
Geometric deviation → uncertainty impact calculation.
Computes additional measurement uncertainty from geometric non-conformances.
Supports GUM-compliant automatic error propagation via 'uncertainties' library.
"""

import math
from metering_designer.core.result import Result

try:
    from uncertainties import ufloat
    HAS_UNCERTAINTIES = True
except ImportError:
    HAS_UNCERTAINTIES = False


def compute_geometric_uncertainty(report) -> float:
    """
    Calculate additional measurement uncertainty contribution
    from geometric deviations per ISO 5168 methodology.
    """
    total_contribution_sq = 0.0

    for comp in report.components:
        for param in comp.parameters:
            if param.overall_status == "PASS" or param.overall_status == "PENDING":
                continue

            factor = param.uncertainty_factor
            if factor <= 0:
                continue

            if param.is_qualitative:
                if param.overall_status == "FAIL":
                    total_contribution_sq += (factor * 0.5) ** 2
                else:
                    total_contribution_sq += (factor * 0.2) ** 2
                continue

            for point in param.points:
                if point.measured is None or point.status == "PASS":
                    continue
                deviation_pct = abs(point.measured - point.nominal) / point.nominal * 100 if point.nominal > 0 else 0
                contribution = factor * deviation_pct
                total_contribution_sq += contribution ** 2

    return math.sqrt(total_contribution_sq)


def recompute_uncertainty(base_uncertainty_pct: float, geometric_contribution_pct: float) -> dict:
    combined = math.sqrt(base_uncertainty_pct ** 2 + geometric_contribution_pct ** 2)
    result = {
        "base_uncertainty_pct": round(base_uncertainty_pct, 4),
        "geometric_contribution_pct": round(geometric_contribution_pct, 4),
        "combined_uncertainty_pct": round(combined, 4),
        "expanded_k2_pct": round(combined * 2, 4),
    }
    if HAS_UNCERTAINTIES:
        u_base = ufloat(base_uncertainty_pct, base_uncertainty_pct * 0.05)
        u_geo = ufloat(geometric_contribution_pct, geometric_contribution_pct * 0.05)
        u_combined = (u_base ** 2 + u_geo ** 2) ** 0.5
        result["gum_combined"] = round(u_combined.nominal_value, 4)
        result["gum_std_uncertainty"] = round(u_combined.std_dev, 6)
        result["gum_k2"] = round(u_combined.nominal_value * 2, 4)
    return result


def recompute_uncertainty_result(
    base_uncertainty_pct: float,
    geometric_contribution_pct: float,
) -> Result:
    """Recompute uncertainty with provenance tracking."""
    result = Result()
    try:
        data = recompute_uncertainty(base_uncertainty_pct, geometric_contribution_pct)
        result.data = data
        result.add_provenance(
            function_name="recompute_uncertainty",
            parameters={
                "base_uncertainty_pct": base_uncertainty_pct,
                "geometric_contribution_pct": geometric_contribution_pct,
            },
            standard_ref="ISO 5168:2023 (GUM methodology)",
        )
    except Exception as e:
        result.errors.append(str(e))
    return result
