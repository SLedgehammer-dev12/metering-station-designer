"""Expanded integration tests for v0.5.0"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metering_designer.meters.vcone import size_v_cone
from metering_designer.meters.pd_meter import size_pd_meter
from metering_designer.meters.vortex import size_vortex
from metering_designer.meters.orifice import size_orifice_for_flow
from metering_designer.meters.ultrasonic import size_ultrasonic
from metering_designer.meters.turbine import size_turbine
from metering_designer.meters.coriolis import size_coriolis
from metering_designer.inspection.builder import build_inspection_checklist, evaluate_report
from metering_designer.inspection.uncertainty_impact import compute_geometric_uncertainty
from metering_designer.inspection.tolerance_engine import compute_tolerance
from metering_designer.core.backends import calc_z_factor, get_backend_status
from metering_designer.core.validation import validate_process_inputs, validate_requirements
from metering_designer.core.scoring_engine import MeterScorer, classify_score
from metering_designer.meters.selector import evaluate_all_meters


def test_vcone_sizing():
    vc = size_v_cone(8, 50000, 5000, 45, 40, 35, 1.5e-6, 0.75)
    assert 0.45 < vc["beta"] < 0.85
    assert vc["Cd"] > 0.7
    assert vc["dp_mbar"] > 0


def test_vcone_edge_cases():
    vc = size_v_cone(2, 1000, 100, 10, 20, 10, 1e-5, 0.75)
    assert vc["beta"] >= 0.45
    vc2 = size_v_cone(24, 200000, 20000, 80, 50, 70, 1.5e-6, 0.75)
    assert vc2["beta"] <= 0.85


def test_pd_meter_edge():
    pd = size_pd_meter(4, 50, 10, 900, 50, 20, 30)
    assert pd["meter_size_inches"] > 0
    pd2 = size_pd_meter(12, 900, 100, 800, 1, 30, 35)
    assert pd2["delta_p_mbar"] > 0


def test_all_meters_scored():
    inputs = {"fluid_type": "gas", "nps": 10, "qmin": 10000, "qmax": 80000, "service_type": "custody_transfer",
              "target_uncertainty": 0.5, "composition": {"C1": 0.9, "C2": 0.04, "CO2": 0.02, "N2": 0.04}}
    results = evaluate_all_meters(inputs, fluid_type="gas")
    assert len(results) >= 5
    for r in results:
        assert 0 <= r.total_score <= 100


def test_all_liquid_meters():
    inputs = {"fluid_type": "liquid", "nps": 6, "qmin": 100, "qmax": 1000, "service_type": "custody_transfer"}
    results = evaluate_all_meters(inputs, fluid_type="liquid")
    assert len(results) >= 3
    keys = [r.meter_key for r in results]
    assert "positive_displacement" in keys


def test_inspection_all_combos():
    combos = [("orifice", "zanker"), ("ultrasonic", "cpa_50e"), ("turbine", None),
              ("coriolis", None), ("vortex", None)]
    for meter, cond in combos:
        rep = build_inspection_checklist(meter, cond, 8, 0.6, 200)
        assert len(rep.components) >= 1
        assert rep.total_params > 0


def test_inspection_fill_and_eval():
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
    # Force a critical failure
    for comp in rep.components:
        for param in comp.parameters:
            if param.key == "e_edge_thickness":
                param.points[0].measured = 0.1
    evaluate_report(rep)
    assert "FAIL" in rep.overall_status


def test_tolerance_engine():
    # percentage_or_absolute
    t = compute_tolerance({"type": "percentage_or_absolute", "percentage": 0.05, "absolute_mm": 0.01, "base_param": "d"}, {"d": 100})
    assert abs(t["upper"] - 100.05) < 0.01

    # range_from_D
    t = compute_tolerance({"type": "range_from_D", "min_factor": 0.005, "max_factor": 0.02}, {"D": 200})
    assert abs(t["lower"] - 1.0) < 0.01
    assert abs(t["upper"] - 4.0) < 0.01

    # max_value
    t = compute_tolerance({"type": "max_value", "value": 2.0}, {})
    assert t["upper"] == 2.0

    # conditional_max
    t = compute_tolerance({"type": "conditional_max", "conditions": [{"if": {"param": "beta", "op": ">", "value": 0.6}, "max": 0.4}]}, {"beta": 0.65})
    assert t["upper"] == 0.4


def test_backend_fallback_all():
    st = get_backend_status()
    comp = {"C1": 0.9, "C2": 0.04, "CO2": 0.02, "N2": 0.04}
    for p in [1, 30, 60]:
        r = calc_z_factor(p, 20, comp)
        assert r["Z"] > 0.3
        assert r["density_kg_m3"] > 0


def test_validation_edge_cases():
    # Negative flow - should be caught
    errs = validate_process_inputs({"fluid_type": "gas", "nps": 8, "design_p_bar": 50, "oper_p_bar": 40,
                                     "qmin": -1, "qmax": 100, "design_t_c": 60, "oper_t_c": 40})
    assert len(errs) >= 1  # catches negative qmin

    # Too high pressure
    errs = validate_process_inputs({"fluid_type": "gas", "nps": 8, "design_p_bar": 500, "oper_p_bar": 400,
                                     "qmin": 1, "qmax": 100, "design_t_c": 60, "oper_t_c": 40})
    assert len(errs) > 0  # >420 bar

    # Valid req
    e = validate_requirements({"ex_zone": "zone_2", "target_uncertainty": 1.0, "ambient_min_C": 0, "ambient_max_C": 40})
    assert len(e) == 0


def test_classify_scores():
    for s, e in [(90, "★★★"), (75, "★★☆"), (60, "★☆☆"), (30, "—–")]:
        t, c, _ = classify_score(s)
        assert t == e


if __name__ == "__main__":
    for name, func in list(locals().items()):
        if name.startswith("test_"):
            try:
                func()
                print(f"✅ {name}")
            except Exception as e:
                print(f"❌ {name}: {e}")
    print(f"\nTotal: {sum(1 for n in locals() if n.startswith('test_'))} tests")
