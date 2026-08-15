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
    assert geo > 0.01, f"Expected geo > 0.01 but got {geo}"


def test_compliance_excel():
    if not HAS_OPENPYXL:
        return
    rep = build_inspection_checklist("orifice", None, 8, 0.65, 202.7)
    buf = generate_compliance_report(rep)
    assert len(buf.getvalue()) > 1000


def test_evaluate_report_behavior():
    """Verify evaluate_report updates report state correctly."""
    rep = build_inspection_checklist("orifice", None, 8, 0.65, 202.7)

    # Before evaluation, non-qualitative points should be PENDING (no measurements)
    pending_count = 0
    for comp in rep.components:
        for param in comp.parameters:
            if not param.is_qualitative:
                for pt in param.points:
                    if pt.status == "PENDING":
                        pending_count += 1
    assert pending_count > 0, "Expected some PENDING points before filling measurements"

    # overall_status is a string; qualitative params default to first option (PASS)
    assert isinstance(rep.overall_status, str)
    assert "PASS" in rep.overall_status or "PENDING" in rep.overall_status

    # Now set all non-qualitative measurements to nominal, then evaluate
    for comp in rep.components:
        for param in comp.parameters:
            if not param.is_qualitative:
                for pt in param.points:
                    pt.measured = pt.nominal
    evaluate_report(rep)

    # After setting all nominals, everything should be PASS
    assert rep.overall_status.startswith("PASS"), f"Expected PASS, got {rep.overall_status}"

    # Verify that at least some InspectionPoints changed from PENDING to PASS/FAIL
    evaluated_count = 0
    for comp in rep.components:
        for param in comp.parameters:
            if not param.is_qualitative:
                for pt in param.points:
                    if pt.status != "PENDING":
                        evaluated_count += 1
    assert evaluated_count > 0, "No points were evaluated after setting measurements"


def test_recompute_uncertainty():
    """Test combined and expanded uncertainty calculation."""
    from metering_designer.inspection.uncertainty_impact import recompute_uncertainty
    result = recompute_uncertainty(base_uncertainty_pct=0.5, geometric_contribution_pct=0.3)
    # sqrt(0.5² + 0.3²) = sqrt(0.25 + 0.09) = sqrt(0.34) ≈ 0.583
    assert abs(result["combined_uncertainty_pct"] - 0.5831) < 0.001, \
        f"Expected combined ≈ 0.583, got {result['combined_uncertainty_pct']}"
    # expanded = combined * 2 ≈ 1.166
    assert abs(result["expanded_k2_pct"] - 1.1662) < 0.002, \
        f"Expected expanded ≈ 1.166, got {result['expanded_k2_pct']}"


def test_multi_point_variance():
    """A single FAIL measurement on a parameter causes the parameter to FAIL."""
    rep = build_inspection_checklist("orifice", None, 8, 0.65, 202.7)

    # Set all non-qualitative points to nominal values (should all PASS)
    for comp in rep.components:
        for param in comp.parameters:
            if not param.is_qualitative:
                for pt in param.points:
                    pt.measured = pt.nominal

    # Find a multi-point parameter and make ONE point fail
    target_param = None
    for comp in rep.components:
        for param in comp.parameters:
            if not param.is_qualitative and len(param.points) >= 4:
                target_param = param
                break
        if target_param:
            break

    assert target_param is not None, "No multi-point parameter found"
    assert len(target_param.points) >= 4

    # All points should be PASS initially
    for pt in target_param.points:
        assert pt.status == "PASS", f"Expected PASS, got {pt.status}"

    # Set ONE point to a value far outside tolerance → FAIL
    pt_fail = target_param.points[0]
    if pt_fail.tol_upper is not None:
        pt_fail.measured = pt_fail.tol_upper * 10
    elif pt_fail.tol_lower is not None:
        pt_fail.measured = pt_fail.tol_lower * 0.1
    else:
        pt_fail.measured = pt_fail.nominal * 0.01

    assert pt_fail.status == "FAIL", f"Expected FAIL, got {pt_fail.status}"

    # The parameter should now be FAIL because one point failed
    assert target_param.overall_status == "FAIL", \
        f"Expected parameter FAIL, got {target_param.overall_status}"


def test_tolerance_min_value():
    """Test min_value tolerance type — only lower bound enforced."""
    # Compute tolerance bounds
    t = compute_tolerance(
        {"type": "min_value", "value": 0.2, "unit": "mm"}, {"D": 200}
    )
    assert t["lower"] == 0.2, f"Expected lower=0.2, got {t['lower']}"
    assert t["upper"] is None, f"Expected upper=None, got {t['upper']}"
    assert t["nominal"] == round(0.2 * 1.5, 3), f"Unexpected nominal: {t['nominal']}"

    # Verify status via InspectionPoint: measured below lower → FAIL
    from metering_designer.inspection.models import InspectionPoint
    pt = InspectionPoint(
        position_label="test", nominal=t["nominal"],
        tol_lower=t["lower"], tol_upper=t["upper"],
    )
    pt.measured = 0.1
    assert pt.status == "FAIL", f"Expected FAIL for measured=0.1, got {pt.status}"
    pt.measured = 0.2
    assert pt.status == "PASS", f"Expected PASS for measured=0.2, got {pt.status}"
    pt.measured = 0.5
    assert pt.status == "PASS", f"Expected PASS for measured=0.5, got {pt.status}"


def test_tolerance_range():
    """Test range tolerance type with min and max bounds."""
    t = compute_tolerance(
        {"type": "range", "min": 5, "max": 10, "unit": "mm"}, {"D": 200}
    )
    assert t["lower"] == 5, f"Expected lower=5, got {t['lower']}"
    assert t["upper"] == 10, f"Expected upper=10, got {t['upper']}"
    assert t["nominal"] == 7.5, f"Expected nominal=7.5, got {t['nominal']}"

    # Verify status via InspectionPoint
    from metering_designer.inspection.models import InspectionPoint
    pt = InspectionPoint(
        position_label="test", nominal=t["nominal"],
        tol_lower=t["lower"], tol_upper=t["upper"],
    )
    pt.measured = 7
    assert pt.status == "PASS", f"Expected PASS for measured=7, got {pt.status}"
    pt.measured = 3
    assert pt.status == "FAIL", f"Expected FAIL for measured=3 (below min), got {pt.status}"
    pt.measured = 12
    assert pt.status == "FAIL", f"Expected FAIL for measured=12 (above max), got {pt.status}"


def test_tolerance_min_length_D():
    """Test min_length_D tolerance — lower bound = min_factor * D."""
    t = compute_tolerance(
        {"type": "min_length_D", "min_factor": 2.0, "unit": "mm"}, {"D": 200}
    )
    expected_lower = 2.0 * 200  # 400
    expected_nominal = round(expected_lower * 1.3, 1)  # 520.0
    assert t["lower"] == expected_lower, f"Expected lower=400, got {t['lower']}"
    assert t["upper"] is None, f"Expected upper=None, got {t['upper']}"
    assert t["nominal"] == expected_nominal, f"Expected nominal={expected_nominal}, got {t['nominal']}"

    # Verify status via InspectionPoint
    from metering_designer.inspection.models import InspectionPoint
    pt = InspectionPoint(
        position_label="test", nominal=t["nominal"],
        tol_lower=t["lower"], tol_upper=t["upper"],
    )
    pt.measured = 500
    assert pt.status == "PASS", f"Expected PASS for measured=500, got {pt.status}"
    pt.measured = 300
    assert pt.status == "FAIL", f"Expected FAIL for measured=300 (below min), got {pt.status}"


# ============================================================
# Phase 3 deep tests: pass-rate counters, USM transducer,
# conditioner subtypes, boundary conditions
# ============================================================


def test_pass_rate_counters():
    """3.17: Verify InspectionReport pass/fail counters and overall_status
    reflect a mixed (pass + fail) state after evaluation."""
    rep = build_inspection_checklist("orifice", None, 8, 0.65, 202.7)

    # Set all non-qualitative points to nominal → all PASS
    for comp in rep.components:
        for param in comp.parameters:
            if not param.is_qualitative:
                for pt in param.points:
                    pt.measured = pt.nominal
            else:
                # Qualitatively: pick the option that carries a PASS status
                for opt in param.options:
                    if opt.get("status") == "PASS":
                        param.qualitative_value = opt["value"]
                        break
    evaluate_report(rep)

    # At this point everything should PASS
    assert rep.passed_params > 0, "Expected at least one passed parameter"
    assert rep.failed_params == 0, "No failed parameters expected initially"
    assert rep.pass_rate == 100.0, f"Expected 100% pass rate, got {rep.pass_rate:.1f}%"
    assert rep.overall_status.startswith("PASS"), f"Expected PASS status, got {rep.overall_status}"

    # Now deliberately make one non-critical parameter fail
    for comp in rep.components:
        for param in comp.parameters:
            if not param.is_qualitative and param.criticality != "CRITICAL":
                if param.points and param.points[0].tol_upper is not None:
                    param.points[0].measured = param.points[0].tol_upper * 10
                    break
        else:
            continue
        break

    evaluate_report(rep)

    # Now we should have at least one failure and some passes
    assert rep.failed_params >= 1, f"Expected ≥1 failed, got {rep.failed_params}"
    assert rep.passed_params >= 1, f"Expected ≥1 passed, got {rep.passed_params}"
    assert rep.pass_rate < 100.0, f"Expected pass rate < 100%, got {rep.pass_rate:.1f}%"
    assert "CONDITIONAL" in rep.overall_status or "FAIL" in rep.overall_status, \
        f"Expected CONDITIONAL or FAIL status, got {rep.overall_status}"

    # Verify total_params matches passed + failed + conditional
    assert rep.total_params == rep.passed_params + rep.failed_params + rep.conditional_params, \
        f"Sum mismatch: {rep.total_params} != {rep.passed_params}+{rep.failed_params}+{rep.conditional_params}"


def test_usm_transducer_tolerance():
    """3.18: Ultrasonic checklist must include transducer parameters
    (angular, axial, protrusion) with valid tolerance bounds."""
    rep = build_inspection_checklist("ultrasonic", None, 8, 0.6, 200)

    # Collect all parameter keys across all components
    all_keys = {p.key for comp in rep.components for p in comp.parameters}

    required_transducer_keys = ["transducer_angular", "transducer_axial", "transducer_protrusion"]
    for key in required_transducer_keys:
        assert key in all_keys, f"Missing transducer parameter: {key}"

    # Verify each transducer parameter has at least one point with valid tolerance
    for comp in rep.components:
        for param in comp.parameters:
            if param.key in required_transducer_keys:
                assert len(param.points) > 0, \
                    f"Parameter {param.key} has no inspection points"
                for pt in param.points:
                    both_none = (pt.tol_lower is None and pt.tol_upper is None)
                    assert not both_none, \
                        f"Parameter {param.key} point {pt.position_label} has no tolerance bounds"
                # At least one point must have a defined tolerance
                any_tol = any(
                    pt.tol_lower is not None or pt.tol_upper is not None
                    for pt in param.points
                )
                assert any_tol, f"Parameter {param.key} has no tolerance defined"


def test_conditioner_subtypes():
    """3.19: Each conditioner subtype produces a valid report with
    conditioner-specific parameters (not just piping)."""
    subtypes = ["zanker", "cpa_50e", "tube_bundle_19", "perforated", "gallagher"]

    # Parameters that are conditioner-specific (not piping)
    conditioner_param_keys = {
        "zanker": ["hole_diameters", "hole_positions", "plate_thickness",
                    "open_area_ratio", "plate_flatness", "plate_alignment", "hole_chamfers"],
        "cpa_50e": ["hole_diameters", "hole_positions", "plate_thickness", "center_hole"],
        "tube_bundle_19": ["tube_diameters", "tube_length", "tube_parallelism", "tube_positions"],
        "perforated": ["hole_diameters", "open_area_ratio", "plate_thickness"],
        "gallagher": ["vane_thickness", "vane_count", "concentricity", "surface_finish", "slot_width", "open_area_ratio"],
    }

    for subtype in subtypes:
        rep = build_inspection_checklist("orifice", subtype, 8, 0.6, 200)
        assert len(rep.components) >= 2, \
            f"Subtype {subtype}: expected ≥2 components, got {len(rep.components)}"
        assert rep.total_params > 0, \
            f"Subtype {subtype}: no parameters found"

        # Collect all parameter keys
        all_keys = {p.key for comp in rep.components for p in comp.parameters}

        # Check at least some conditioner-specific keys exist
        expected_keys = conditioner_param_keys.get(subtype, [])
        found_expected = [k for k in expected_keys if k in all_keys]
        msg = (f"Subtype {subtype}: expected ≥2 conditioner-specific params "
               f"from {expected_keys}, found {found_expected} among {all_keys}")
        assert len(found_expected) >= 2, msg

        # Verify the report has a valid overall_status (string with recognizable state)
        assert isinstance(rep.overall_status, str)
        assert len(rep.overall_status) > 0

        # Verify each component has a name and at least one parameter
        for comp in rep.components:
            assert len(comp.component_name) > 0
            assert len(comp.parameters) >= 1


def test_english_labels():
    """3.21: Build inspection checklist with lang='en' and verify English labels
    differ from Turkish defaults."""
    rep_tr = build_inspection_checklist("orifice", None, 8, 0.65, 202.7, lang="tr")
    rep_en = build_inspection_checklist("orifice", None, 8, 0.65, 202.7, lang="en")

    # Check component names differ
    tr_names = {c.component_name for c in rep_tr.components}
    en_names = {c.component_name for c in rep_en.components}
    assert tr_names != en_names, "English and Turkish component names should differ"
    assert "Orifice Plate" in en_names or "Piping" in en_names, \
        f"Expected English component names, got: {en_names}"

    # Collect all parameter labels
    tr_labels = {p.label for comp in rep_tr.components for p in comp.parameters}
    en_labels = {p.label for comp in rep_en.components for p in comp.parameters}
    assert tr_labels != en_labels, "English and Turkish parameter labels should differ"

    # Verify some English-specific labels exist
    english_indicators = [lbl for lbl in en_labels
                          if any(w in lbl.lower() for w in ['diameter', 'thickness', 'roughness', 'flatness', 'edge'])]
    assert len(english_indicators) >= 3, \
        f"Expected ≥3 English-labeled params, found {len(english_indicators)}: {english_indicators}"

    # Verify Turkish labels contain Turkish characters/words
    turkish_indicators = [lbl for lbl in tr_labels
                          if any(w in lbl.lower() for w in ['çap', 'kalınlık', 'yüzey', 'kenar', 'düzlem', 'pah'])]
    assert len(turkish_indicators) >= 3, \
        f"Expected ≥3 Turkish-labeled params, found {len(turkish_indicators)}: {turkish_indicators}"

    # Both reports should have the same structure (same number of components/params)
    assert rep_en.total_params == rep_tr.total_params, \
        f"Param count mismatch: en={rep_en.total_params} vs tr={rep_tr.total_params}"


def test_tolerance_boundary_exact():
    """Tolerance bounds are inclusive — measured value exactly at
    the boundary should PASS."""
    from metering_designer.inspection.models import InspectionPoint

    # Test lower boundary inclusive: measured == tol_lower → PASS
    pt_lower = InspectionPoint(
        position_label="lower_bound",
        nominal=7.5,
        tol_lower=5.0,
        tol_upper=10.0,
    )
    pt_lower.measured = 5.0
    assert pt_lower.status == "PASS", \
        f"Expected PASS at lower boundary (measured=5==tol_lower), got {pt_lower.status}"

    # Test upper boundary inclusive: measured == tol_upper → PASS
    pt_upper = InspectionPoint(
        position_label="upper_bound",
        nominal=7.5,
        tol_lower=5.0,
        tol_upper=10.0,
    )
    pt_upper.measured = 10.0
    assert pt_upper.status == "PASS", \
        f"Expected PASS at upper boundary (measured=10==tol_upper), got {pt_upper.status}"

    # Sanity: just below lower → FAIL
    pt_lower.measured = 4.999
    assert pt_lower.status == "FAIL", \
        f"Expected FAIL just below lower boundary (measured=4.999), got {pt_lower.status}"

    # Sanity: just above upper → FAIL
    pt_upper.measured = 10.001
    assert pt_upper.status == "FAIL", \
        f"Expected FAIL just above upper boundary (measured=10.001), got {pt_upper.status}"

    # Edge case: tol_lower is None (only upper bound enforced)
    pt_upper_only = InspectionPoint(
        position_label="upper_only",
        nominal=5.0,
        tol_lower=None,
        tol_upper=10.0,
    )
    pt_upper_only.measured = 0.0  # below None lower → still PASS (lower not enforced)
    assert pt_upper_only.status == "PASS", \
        f"Expected PASS when tol_lower=None and measured=0, got {pt_upper_only.status}"
    pt_upper_only.measured = 10.001
    assert pt_upper_only.status == "FAIL", \
        f"Expected FAIL above upper when tol_lower=None, got {pt_upper_only.status}"

    # Edge case: tol_upper is None (only lower bound enforced)
    pt_lower_only = InspectionPoint(
        position_label="lower_only",
        nominal=10.0,
        tol_lower=5.0,
        tol_upper=None,
    )
    pt_lower_only.measured = 100.0  # above None upper → still PASS (upper not enforced)
    assert pt_lower_only.status == "PASS", \
        f"Expected PASS when tol_upper=None and measured=100, got {pt_lower_only.status}"
    pt_lower_only.measured = 4.999
    assert pt_lower_only.status == "FAIL", \
        f"Expected FAIL below lower when tol_upper=None, got {pt_lower_only.status}"
