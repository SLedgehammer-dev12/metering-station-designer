"""Deep inspection tests (Agent: test-inspection)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from metering_designer.inspection.builder import build_inspection_checklist, evaluate_report
from metering_designer.inspection.tolerance_engine import compute_tolerance
from metering_designer.inspection.uncertainty_impact import compute_geometric_uncertainty
from metering_designer.inspection.compliance_report import generate_compliance_report, HAS_OPENPYXL


ALL_COMBOS = [
    ("orifice", "zanker"), ("ultrasonic", "cpa_50e"), ("turbine", None),
    ("coriolis", None), ("vcone", None), ("venturi", None),
]


def test_all_equipment_types():
    for meter, cond in ALL_COMBOS:
        rep = build_inspection_checklist(meter, cond, 8, 0.6, 200)
        assert len(rep.components) >= 1
        assert rep.total_params > 0


def test_tolerance_percentage():
    t = compute_tolerance({"type": "percentage", "value": 0.3, "base_param": "D"}, {"D": 200})
    assert abs(t["upper"] - 200.6) < 0.1
    assert abs(t["nominal"] - 200) < 0.1


def test_tolerance_absolute():
    t = compute_tolerance({"type": "percentage_or_absolute", "percentage": 0.05, "absolute_mm": 0.01, "base_param": "d", "use": "larger"}, {"d": 10})
    assert abs(t["upper"] - 10.01) < 0.01


def test_tolerance_conditional():
    t1 = compute_tolerance({"type": "conditional_max", "conditions": [{"if": {"param": "beta", "op": ">", "value": 0.6}, "max": 0.4}]}, {"beta": 0.65})
    assert t1["upper"] == 0.4
    t2 = compute_tolerance({"type": "conditional_max", "conditions": [{"if": {"param": "beta", "op": "<=", "value": 0.6}, "max": 0.8}]}, {"beta": 0.5})
    assert t2["upper"] == 0.8


def test_tolerance_range_from_D():
    t = compute_tolerance({"type": "range_from_D", "min_factor": 0.005, "max_factor": 0.02}, {"D": 200})
    assert abs(t["lower"] - 1.0) < 0.01
    assert abs(t["upper"] - 4.0) < 0.01


def test_enum_qualitative():
    from metering_designer.inspection.models import InspectionParameter
    p = InspectionParameter(key="test", label="Test", unit="qualitative",
                            options=[{"value": "sharp", "status": "PASS"}, {"value": "rounded", "status": "FAIL"}])
    p.qualitative_value = "sharp"
    assert p.overall_status == "PASS"
    p.qualitative_value = "rounded"
    assert p.overall_status == "FAIL"


def test_inspection_all_nominal_pass():
    rep = build_inspection_checklist("orifice", None, 8, 0.65, 202.7)
    for comp in rep.components:
        for param in comp.parameters:
            if not param.is_qualitative:
                for pt in param.points:
                    pt.measured = pt.nominal
    evaluate_report(rep)
    assert rep.overall_status.startswith("PASS")


def test_inspection_critical_failure():
    rep = build_inspection_checklist("orifice", None, 8, 0.65, 202.7)
    for comp in rep.components:
        for param in comp.parameters:
            if not param.is_qualitative:
                for pt in param.points:
                    pt.measured = pt.nominal
    for comp in rep.components:
        for param in comp.parameters:
            if param.key == "e_edge_thickness":
                param.points[0].measured = 0.1
    evaluate_report(rep)
    assert "FAIL" in rep.overall_status


def test_uncertainty_chain():
    rep = build_inspection_checklist("orifice", None, 8, 0.65, 202.7)
    for comp in rep.components:
        for param in comp.parameters:
            if not param.is_qualitative:
                for pt in param.points:
                    pt.measured = pt.nominal * 0.99
    evaluate_report(rep)
    geo = compute_geometric_uncertainty(rep)
    assert geo >= 0


def test_compliance_excel():
    if not HAS_OPENPYXL:
        return
    rep = build_inspection_checklist("orifice", None, 8, 0.65, 202.7)
    buf = generate_compliance_report(rep)
    assert len(buf.getvalue()) > 1000
