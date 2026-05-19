"""
Dynamic inspection checklist builder.
Generates complete measurement forms based on meter type + conditioner selection.
"""

import json
import os

from metering_designer.inspection.models import (
    InspectionPoint, InspectionParameter, ComponentInspection, InspectionReport,
)
from metering_designer.inspection.tolerance_engine import compute_tolerance

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "knowledge")


def _load_json(filename: str) -> dict:
    path = os.path.join(KNOWLEDGE_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


COMPONENT_MAP = {
    "orifice":    [("inspection_orifice.json", "orifice_plate"), ("inspection_orifice.json", "meter_tube")],
    "ultrasonic": [("inspection_usm.json", "usm_body"), ("inspection_usm.json", "usm_transducers")],
    "turbine":    [("inspection_turbine.json", "turbine_body")],
    "coriolis":   [("inspection_coriolis.json", "coriolis_body")],
    "vcone":      [("inspection_vcone.json", "vcone_body")],
    "venturi":    [("inspection_venturi.json", "venturi_body")],
    "vortex":     [],
    "positive_displacement": [],
}

CONDITIONER_MAP = {
    "zanker":     ("inspection_conditioners.json", "conditioner_zanker"),
    "cpa_50e":    ("inspection_conditioners.json", "conditioner_cpa"),
    "tube_bundle_19": ("inspection_conditioners.json", "conditioner_tube_bundle"),
    "perforated":  ("inspection_conditioners.json", "conditioner_perforated"),
    "gallagher":   ("inspection_conditioners.json", "conditioner_perforated"),
}

PIPING_KEY = ("inspection_piping.json", "piping")

METER_LABELS_TR = {
    "orifice": "Orifis Plakası", "ultrasonic": "Ultrasonik (USM)",
    "turbine": "Türbin", "coriolis": "Coriolis",
    "vortex": "Vorteks", "positive_displacement": "PD Metre",
}
CONDITIONER_LABELS_TR = {
    "zanker": "Zanker Plakası", "cpa_50e": "CPA 50E",
    "tube_bundle_19": "19-Tüp Demeti", "perforated": "Perfore Plaka",
    "gallagher": "Gallagher Yarıklı",
}


def build_inspection_checklist(
    meter_type: str,
    conditioner_type: str | None = None,
    nps: int = 8,
    beta: float | None = None,
    D_mm: float | None = None,
    lang: str = "tr",
) -> InspectionReport:
    if D_mm is None:
        D_mm = _nps_to_od(nps) * 0.88  # approximate ID

    report = InspectionReport(
        meter_type=meter_type,
        conditioner_type=conditioner_type,
        nps=nps,
        beta=beta,
        D_mm=D_mm,
    )

    reference_values = {"D": D_mm, "beta": beta or 0.6, "nps": nps, "OD": _nps_to_od(nps), "d": (beta or 0.6) * D_mm}

    # Meter-specific components
    keys = COMPONENT_MAP.get(meter_type, [])
    for filename, comp_key in keys:
        data = _load_json(filename)
        comp_data = data["components"].get(comp_key)
        if comp_data:
            comp = _build_component(comp_data, reference_values, lang)
            report.components.append(comp)

    # Flow conditioner
    if conditioner_type and conditioner_type in CONDITIONER_MAP:
        filename, comp_key = CONDITIONER_MAP[conditioner_type]
        data = _load_json(filename)
        comp_data = data["components"].get(comp_key)
        if comp_data:
            comp = _build_component(comp_data, reference_values, lang)
            report.components.append(comp)

    # Always add piping for all meter types
    filename, comp_key = PIPING_KEY
    data = _load_json(filename)
    comp_data = data["components"].get(comp_key)
    if comp_data:
        comp = _build_component(comp_data, reference_values, lang)
        report.components.append(comp)

    return report


def _build_component(comp_data: dict, ref: dict, lang: str) -> ComponentInspection:
    label_key = "label_tr" if lang == "tr" else "label_en"
    name_key = "name_tr" if lang == "tr" else "name_en"

    comp = ComponentInspection(
        component_name=comp_data.get(name_key, ""),
        standard=comp_data.get("standard", ""),
    )

    for param_key, param_data in comp_data.get("parameters", {}).items():
        tol_result = compute_tolerance(param_data.get("tolerance", {}), ref)

        nominal_val = tol_result.get("nominal", ref.get("D", 200))

        points = []
        point_spec = param_data.get("points", {})
        n_points = point_spec.get("count", 1)

        if isinstance(n_points, str) and n_points == "*":
            n_points = 4

        labels = point_spec.get("labels", [])
        for i in range(min(n_points, 20)):
            lbl = labels[i] if i < len(labels) else f"#{i+1}"
            t_lower = tol_result.get("lower")
            t_upper = tol_result.get("upper")
            pt = InspectionPoint(
                position_label=lbl,
                nominal=nominal_val,
                tol_lower=t_lower,
                tol_upper=t_upper,
            )
            points.append(pt)

        param = InspectionParameter(
            key=param_key,
            label=param_data.get(label_key, param_key),
            unit=param_data.get("unit", "mm"),
            points=points,
            tolerance_spec=param_data.get("tolerance", {}),
            standard_clause=param_data.get("clause", ""),
            criticality=param_data.get("criticality", "MINOR"),
            uncertainty_factor=param_data.get("uncertainty_factor", 0),
            options=param_data.get("options", []),
        )
        if param.is_qualitative and param.options:
            param.qualitative_value = param.options[0]["value"]
        comp.parameters.append(param)

    return comp


def _nps_to_od(nps: int) -> float:
    mapping = {2: 60.3, 3: 88.9, 4: 114.3, 6: 168.3, 8: 219.1,
               10: 273.1, 12: 323.8, 14: 355.6, 16: 406.4, 18: 457.2,
               20: 508.0, 24: 609.6}
    return mapping.get(nps, nps * 25.4)


def evaluate_report(report: InspectionReport) -> InspectionReport:
    """
    Re-evaluates all statuses (after user fills in measurements).
    Also updates tolerance ranges based on actual measurements.
    """
    for comp in report.components:
        for param in comp.parameters:
            if not param.is_qualitative:
                for pt in param.points:
                    if pt.measured is not None and pt.nominal == 0:
                        pt.nominal = pt.measured
    return report
