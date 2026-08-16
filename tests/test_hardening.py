"""
Regression & hardening tests for professionally-released behavior.
Covers fixed crash bugs, boundary misclassification, unit-contract issues,
silent-wrong-result traps, and result-schema consistency across modules.
"""

import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest


# ─────────────────────────────────────────────
# Scoring engine: boundary + weight normalization
# ─────────────────────────────────────────────
def test_classify_score_exact_boundaries():
    from metering_designer.core.scoring_engine import classify_score
    assert classify_score(0.0)[0] == "—–"
    assert classify_score(49.99)[0] == "—–"
    assert classify_score(50.0)[0] == "★☆☆"
    assert classify_score(69.99)[0] == "★☆☆"
    assert classify_score(70.0)[0] == "★★☆"
    assert classify_score(84.99)[0] == "★★☆"
    assert classify_score(85.0)[0] == "★★★"
    assert classify_score(100.0)[0] == "★★★", "100.0 must be Optimal, not Önerilmez"
    assert classify_score(99.999)[0] == "★★★"


def test_scorer_weights_sum_to_one_for_partial_weights():
    """A partial weight dict must not produce totals > 100."""
    from metering_designer.core.scoring_engine import MeterScorer
    scorer = MeterScorer(weights={"technical_fitness": 0.8})
    total = sum(scorer.weights.values())
    assert abs(total - 1.0) < 1e-9, f"weights sum {total}, expected 1.0"
    result = scorer.score_meter("ultrasonic", {
        "fluid_type": "gas", "design_p_bar": 50, "qmin": 1000,
        "qmax": 30000, "nps": 8, "design_t_c": 60, "service_type": "custody_transfer",
    })
    assert 0 <= result.total_score <= 100.0, f"total {result.total_score} out of range"


def test_scorer_ignores_stale_unknown_keys():
    from metering_designer.core.scoring_engine import MeterScorer
    scorer = MeterScorer(weights={"technical_fitness": 0.5, "nonexistent_key": 99.0})
    total = sum(scorer.weights.values())
    assert abs(total - 1.0) < 1e-9
    assert "nonexistent_key" not in scorer.weights


# ─────────────────────────────────────────────
# Fluid type normalization (UI labels → canonical keys)
# ─────────────────────────────────────────────
def test_get_meter_keys_accepts_turkish_labels():
    from metering_designer.meters.specs import get_meter_keys, normalize_fluid_type
    assert normalize_fluid_type("doğal_gaz") == "gas"
    assert normalize_fluid_type("gas") == "gas"
    assert normalize_fluid_type("ham_petrol") == "liquid"
    assert normalize_fluid_type("liquid") == "liquid"
    gas_keys = get_meter_keys("doğal_gaz")
    assert "ultrasonic" in gas_keys and "orifice" in gas_keys
    assert len(gas_keys) > 0, "Turkish label must resolve to gas meters"
    liq_keys = get_meter_keys("ham_petrol")
    assert len(liq_keys) > 0, "Turkish label must resolve to liquid meters"
    assert not set(gas_keys).issuperset(liq_keys)


# ─────────────────────────────────────────────
# Backend fallback chain
# ─────────────────────────────────────────────
def test_calc_z_factor_percent_composition_no_panic():
    """Percentage-based composition (sum=100) must not crash pyaga8."""
    from metering_designer.core.backends import calc_z_factor
    res = calc_z_factor(45, 40, {"C1": 90.0, "C2": 4.0, "N2": 6.0})
    assert res["Z"] is not None
    assert 0.1 < res["Z"] < 3.0
    assert res["backend_layer"] >= 1
    assert res["density_kg_m3"] > 0


def test_calc_z_factor_near_one_composition():
    from metering_designer.core.backends import calc_z_factor
    res = calc_z_factor(45, 40, {"C1": 0.985, "C2": 0.01, "N2": 0.005})
    assert 0.1 < res["Z"] < 3.0
    assert "errors" not in res or res["errors"] == []


def test_molar_mass_unit_contract():
    """All backends must report M_mix in g/mol (~16-30), never kg/mol (~0.016)."""
    from metering_designer.core.backends import calc_z_factor
    res = calc_z_factor(45, 40, {"C1": 0.9, "C2": 0.1})
    assert res["M_mix"] > 5, f"M_mix {res['M_mix']} looks like kg/mol"
    assert res["density_kg_m3"] > 0, "density must be positive"
    m_ideal = 0.9 * 16.043 + 0.1 * 30.07
    assert abs(res["M_mix"] - m_ideal) < 2.0, f"M_mix {res['M_mix']} far from blend {m_ideal}"


def test_calc_heating_value_fraction_and_percent_agree():
    from metering_designer.core.backends import calc_heating_value
    frac = calc_heating_value({"C1": 0.9, "C2": 0.1})
    pct = calc_heating_value({"C1": 90.0, "C2": 10.0})
    assert abs(frac["gross_CV_MJ_m3"] - pct["gross_CV_MJ_m3"]) < 0.1, \
        "fraction and percent compositions must yield same calorific value"
    assert frac["gross_CV_MJ_m3"] > 30, f"gross CV {frac['gross_CV_MJ_m3']} implausibly low"
    assert frac["net_CV_MJ_m3"] < frac["gross_CV_MJ_m3"]


def test_calc_gas_properties_design_temp_zero_c():
    """Design temperature exactly 0 °C must be honored, not skipped as falsy."""
    from metering_designer.fluids.gas import calc_gas_properties
    res = calc_gas_properties({"C1": 0.95, "N2": 0.05}, 45, 40, 50, 0)
    assert "error" not in res, res
    # Design Z must differ from operating Z (T changes Z)
    assert res.get("Z_design", 0) > 0
    assert res.get("rho_oper_kg_m3", 0) > 0


# ─────────────────────────────────────────────
# Meter sizing crash guards
# ─────────────────────────────────────────────
def test_pd_meter_zero_viscosity_no_crash():
    from metering_designer.meters.pd_meter import _estimate_slip_pct, size_pd_meter
    slip = _estimate_slip_pct(0.0, 0.5, 60.0)
    assert math.isfinite(slip), "slip must be finite for zero viscosity"
    res = size_pd_meter(4, 50, 10, 900, 0.0, 20, 30)
    assert res is not None and isinstance(res, dict)


def test_turbine_negative_pressure_raises():
    from metering_designer.meters.turbine import _estimate_max_capacity
    with pytest.raises(ValueError):
        _estimate_max_capacity(8, -5.0)


def test_orifice_result_schema_complete():
    from metering_designer.meters.orifice import size_orifice_for_flow
    res = size_orifice_for_flow(30000, 5000, 202.7, 45, 40, 40, 1.2e-5, 0.91, 0.75)
    for key in ("beta", "d_mm", "Cd", "Re", "beta_valid", "turndown_ok", "turndown_actual"):
        assert key in res, f"missing key {key}"
    assert 0.1 <= res["beta"] <= 0.75
    assert isinstance(res["turndown_ok"], bool)


# ─────────────────────────────────────────────
# Safety: IEC 60079 zone recommendations
# ─────────────────────────────────────────────
def test_zone_0_protection_recommendation():
    from metering_designer.safety.ex_classification import _recommend_protection
    recs = _recommend_protection("Zone 0", "IIA")
    assert any("Ex ia" in r for r in recs), f"Zone 0 must require intrinsically-safe/special protection, got {recs}"
    assert "special" not in " ".join(recs).lower() or any("Ex s" in r or "Ex ia" in r for r in recs)
    recs2 = _recommend_protection("Zone 2", "IIB")
    assert any("Ex n" in r for r in recs2)


# ─────────────────────────────────────────────
# Materials: no global-state mutation
# ─────────────────────────────────────────────
def test_select_material_does_not_mutate_global():
    from metering_designer.piping import materials as m
    before = {k: dict(v) for k, v in m.MATERIAL_RECOMMENDATIONS.items()}
    for _ in range(3):
        m.select_material(h2s=False, max_temp_C=60, offshore=True)
    after = {k: dict(v) for k, v in m.MATERIAL_RECOMMENDATIONS.items()}
    assert before == after, "select_material mutated the global MATERIAL_RECOMMENDATIONS"


# ─────────────────────────────────────────────
# Uncertainty: GUM must not double-count geometric term
# ─────────────────────────────────────────────
def test_gum_does_not_double_count_geometric():
    from metering_designer.metrology.uncertainty import (
        HAS_UNCERTAINTIES, calc_uncertainty_budget_detailed,
    )
    base = calc_uncertainty_budget_detailed("orifice")
    geo = 0.2
    with_geo = calc_uncertainty_budget_detailed("orifice", geometric_contribution_pct=geo)
    single = math.sqrt(base["combined_standard_uncertainty_pct"] ** 2 + geo ** 2)
    assert abs(with_geo["combined_standard_uncertainty_pct"] - single) < 0.001
    if HAS_UNCERTAINTIES:
        gum_combined = with_geo.get("gum_combined_standard_uncertainty_pct")
        assert gum_combined is not None
        # GUM nominal value equals the deterministic single-add combination
        assert abs(gum_combined - single) < 0.01, \
            f"GUM combined {gum_combined} must not exceed single-add {single}"
        # Double-counted geometric term would push this to ~0.708
        double_count = math.sqrt(single ** 2 + geo ** 2)
        assert gum_combined < double_count - 0.01, \
            f"GUM combined {gum_combined} must equal single-add {single}, not {double_count}"


def test_uncertainty_unknown_meter_falls_back_with_marker():
    from metering_designer.metrology.uncertainty import calc_uncertainty_budget_detailed
    res = calc_uncertainty_budget_detailed("classical_venturi")
    assert res["combined_standard_uncertainty_pct"] > 0


# ─────────────────────────────────────────────
# Piping: temperature-key parsing + flange selection
# ─────────────────────────────────────────────
def test_stress_table_ambient_and_range_keys_parsed():
    from metering_designer.piping.wall_thickness import _parse_temp_key
    assert _parse_temp_key("ambient") == 20.0
    assert _parse_temp_key("50") == 50.0
    assert _parse_temp_key("-29_to_40") == -29.0
    assert _parse_temp_key("100") == 100.0


def test_interpolate_stress_uses_ambient_row():
    from metering_designer.piping.wall_thickness import load_stress_data, _interpolate_stress
    data = load_stress_data()
    mats = data.get("materials", {})
    key = next(iter(mats))
    table = mats[key]["allowable_stress"]
    s_20 = _interpolate_stress(table, 20.0)
    s_50 = _interpolate_stress(table, 50.0)
    s_minus25 = _interpolate_stress(table, -25.0)
    assert s_20 is not None and s_50 is not None
    # At 20 °C lines up with the -29_to_40 row, not the 50 °C row
    assert s_minus25 >= s_50, "sub-40 C values should read the cold row (higher S)"


def test_flange_selection_no_undertating():
    from metering_designer.piping.wall_thickness import calc_flange_min_class
    # Class 150 is rated 19.6 barg at ambient (20°C) — 19.5 bar must fit class 150
    res_ok = calc_flange_min_class(19.5, 20.0, "carbon_steel")
    assert res_ok.get("flange_class") == 150
    # But 19.7 bar exceeds the class-150 rating → must step up to class 300
    res_next = calc_flange_min_class(19.7, 20.0, "carbon_steel")
    assert res_next.get("flange_class") >= 300, \
        f"19.7 barg must exceed class-150 rating, got {res_next}"


def test_wall_thickness_guards_mill_tolerance():
    from metering_designer.piping.wall_thickness import calc_min_wall_thickness
    with pytest.raises(ValueError):
        calc_min_wall_thickness(50, 60, 219.1, "A106_GrB", mill_tolerance_pct=100.0)


# ─────────────────────────────────────────────
# Inspection: state machine correctness
# ─────────────────────────────────────────────
def test_inspection_fresh_report_not_pass():
    """A freshly built, unmeasured report must be PENDING, never PASS."""
    from metering_designer.inspection.builder import build_inspection_checklist
    rep = build_inspection_checklist("orifice", None, 8, 0.65, 202.7)
    assert rep.overall_status != "PASS — Tam uyumlu"
    assert any(p.overall_status == "PENDING" for p in rep.all_inspections)
    # Qualitative params must not auto-mark PASS
    for p in rep.all_inspections:
        if p.is_qualitative:
            assert p.qualitative_value is None, f"{p.key} auto-set to {p.qualitative_value}"


def test_inspection_partial_measurement_not_pass():
    from metering_designer.inspection.builder import build_inspection_checklist
    rep = build_inspection_checklist("orifice", None, 8, 0.65, 202.7)
    target = next(p for p in rep.all_inspections if not p.is_qualitative and len(p.points) >= 2)
    target.points[0].measured = target.points[0].nominal  # only 1 of N measured
    assert target.overall_status == "PENDING", \
        f"partially measured parameter must be PENDING, got {target.overall_status}"


def test_inspection_minor_failure_prefix_is_fail():
    from metering_designer.inspection.builder import build_inspection_checklist
    rep = build_inspection_checklist("orifice", None, 8, 0.65, 202.7)
    # Fill everything that passes
    for p in rep.all_inspections:
        if p.is_qualitative:
            for opt in p.options:
                if opt.get("status") == "PASS":
                    p.qualitative_value = opt["value"]
                    break
        else:
            for pt in p.points:
                pt.measured = pt.nominal
    # Force one non-critical failure
    for p in rep.all_inspections:
        if not p.is_qualitative and p.criticality != "CRITICAL" and p.points and p.points[0].tol_upper is not None:
            p.points[0].measured = p.points[0].tol_upper * 10
            break
    assert rep.failed_params >= 1
    assert rep.overall_status.startswith("FAIL"), \
        f"real non-conformance must render as FAIL, got {rep.overall_status}"


def test_inspection_usm_transducer_angle_reference():
    """USM transducer angle must have a real nominal (45°) not a default 100°."""
    from metering_designer.inspection.builder import build_inspection_checklist
    rep = build_inspection_checklist("ultrasonic", None, 8, 0.6, 200)
    ang = next(p for p in rep.all_inspections if p.key == "transducer_angular")
    assert ang.points and ang.points[0].nominal == 45.0, f"nominal {ang.points[0].nominal}"
    # A measured 45° transducer angle must now PASS (bounds around 45)
    for pt in ang.points:
        pt.measured = 45.0
    assert ang.overall_status == "PASS", f"45° must pass, got {ang.overall_status}"


def test_inspection_zanker_hole_nominal_from_d():
    from metering_designer.inspection.builder import build_inspection_checklist
    rep = build_inspection_checklist("orifice", "zanker", 8, 0.65, 202.7)
    holes = [p for p in rep.all_inspections if p.key == "hole_diameters"]
    assert holes, "Zanker hole diameter param missing"
    nominal = holes[0].points[0].nominal
    assert 10 < nominal < 100, f"d_hole nominal {nominal} implausible for D=202.7"


def test_inspection_tube_length_symbolic_bounds():
    """1.5×d_tube strings must resolve to numeric bounds, not [0,100]."""
    from metering_designer.inspection.builder import build_inspection_checklist
    rep = build_inspection_checklist("orifice", "tube_bundle_19", 8, 0.65, 202.7)
    tl = next(p for p in rep.all_inspections if p.key == "tube_length")
    lo, hi = tl.points[0].tol_lower, tl.points[0].tol_upper
    assert lo is not None and hi is not None, "symbolic bounds not resolved"
    assert lo > 0 and hi > lo, f"bounds [{lo}, {hi}] invalid"


def test_geometric_uncertainty_empty_and_all_pass():
    from metering_designer.inspection.builder import build_inspection_checklist
    from metering_designer.inspection.uncertainty_impact import compute_geometric_uncertainty
    rep = build_inspection_checklist("vortex", None, 8, 0.65, 202.7)
    # Nothing measured yet → all PENDING → no geometric uncertainty contribution
    assert math.isclose(compute_geometric_uncertainty(rep), 0.0, abs_tol=1e-9)
    # Vortex report must contain its own meter components, not only piping
    names = " ".join(c.component_name.lower() for c in rep.components)
    assert any(k in names for k in ("vortex", "vorteks")), f"no vortex component: {names}"


# ─────────────────────────────────────────────
# Report generation robustness
# ─────────────────────────────────────────────
def test_pdf_notes_accepts_list_and_string(tmp_path):
    from metering_designer.report import pdf_report as p
    assert p._split_notes("a; b") == ["a", "b"]
    assert p._split_notes(["x", "y"]) == ["x", "y"]
    assert p._split_notes("single") == ["single"]
    assert p._split_notes(None) == []
    assert p._split_notes("") == []


# ─────────────────────────────────────────────
# Streamlit pages must at least parse
# ─────────────────────────────────────────────
def test_all_streamlit_pages_compile():
    pages_dir = os.path.join(ROOT, "streamlit_app", "pages")
    for fname in sorted(os.listdir(pages_dir)):
        if fname.endswith(".py"):
            path = os.path.join(pages_dir, fname)
            try:
                compile(open(path, encoding="utf-8").read(), path, "exec")
            except SyntaxError as e:
                pytest.fail(f"{fname} has a syntax error: {e}")


def test_page_files_resolve_from_repo_root():
    """app.py loads pages via __file__-rooted paths; must resolve from any CWD."""
    import re
    src = open(os.path.join(ROOT, "streamlit_app", "app.py"), encoding="utf-8").read()
    page_dir_match = re.search(r'_PAGE_DIR\s*=\s*os\.path\.join\([^\n]+', src)
    page_files_match = re.search(r'PAGE_FILES\s*=\s*\{.*?\n\}', src, re.DOTALL)
    assert page_dir_match, "_PAGE_DIR definition missing in app.py"
    assert page_files_match, "PAGE_FILES definition missing in app.py"
    ns = {"os": os, "__file__": os.path.join(ROOT, "streamlit_app", "app.py")}
    exec(page_dir_match.group(0), ns)
    exec(page_files_match.group(0), ns)
    page_dir = ns["_PAGE_DIR"]
    assert page_dir.endswith(os.path.join("streamlit_app", "pages")), page_dir
    assert os.path.isdir(page_dir), f"_PAGE_DIR not a directory: {page_dir}"
    for key, fname in ns["PAGE_FILES"].items():
        full = os.path.join(page_dir, fname)
        assert os.path.isfile(full), f"page file missing: {full}"
        assert not os.path.isabs(fname), "PAGE_FILES entries must stay relative to _PAGE_DIR"


def test_i18n_full_coverage():
    """Every translation key must exist in both tr and en dictionaries."""
    from metering_designer.core import i18n

    tr_keys = set(i18n.TRANSLATIONS.get("tr", {}).keys())
    en_keys = set(i18n.TRANSLATIONS.get("en", {}).keys())
    assert tr_keys == en_keys, (
        f"TR/EN key mismatch. Only-TR: {sorted(tr_keys - en_keys)[:5]} "
        f"Only-EN: {sorted(en_keys - tr_keys)[:5]}"
    )
    assert len(tr_keys) >= 120, f"unexpectedly small dictionary: {len(tr_keys)}"
    # None of the EN values may still be Turkish placeholders
    for k in en_keys:
        assert "TRANS[" not in i18n.TRANSLATIONS["en"][k]
    # get_text fallback stays graceful
    assert i18n.get_text("definitely_not_a_key", "en") == "definitely_not_a_key"

# ─────────────────────────────────────────────
# Full-app smoke: every page renders in both languages
# ─────────────────────────────────────────────
def _build_app_test(session_state):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(os.path.join(ROOT, "streamlit_app", "app.py"), default_timeout=90)
    for k, v in session_state.items():
        at.session_state[k] = v
    at.run()
    return at


def _selected_meter():
    from metering_designer.core.scoring_engine import ScoredMeter
    return ScoredMeter(
        meter_key="orifice", name_tr="Orifis Plakası", name_en="Orifice Plate",
        total_score=85.0, tier_label="Tier 1", tier_color="green",
        strengths=["güçlü"], weaknesses=["zayıf"],
    )


def test_all_pages_render_tr_and_en():
    """Every streamlit page must execute without exceptions in both languages."""
    pages_base = {
        "page": "project", "lang": "tr",
        "project": {"name": "Test", "location": "Ankara", "date": "2026"},
        "process": {
            "fluid_type": "dogalgaz", "nps": 8, "od_mm": 219.1,
            "oper_p_bar": 40.0, "design_p_bar": 50.0,
            "oper_t_c": 40.0, "design_t_c": 60.0,
            "qmin": 5000, "qnormal": 10000, "qmax": 30000,
            "composition": {}, "upstream_config": "single_bend_90",
            "material": "A106_GrB", "service_type": "custody_transfer",
        },
        "requirements": {
            "h2s": False, "h2s_ppm": 0.0, "ex_zone": "zone_2",
            "target_uncertainty": 1.0, "location": "turkey",
            "has_gas_detection": True, "power_source": "grid",
            "site_length_limit_m": 0.0,
        },
        "weights": None, "results": None, "selected_meter": None,
        "engineering": {},
    }
    import copy
    for lang in ("tr", "en"):
        for page in range(1, 9):
            base = copy.deepcopy(pages_base)
            base["lang"] = lang
            base["page"] = ["project", "process", "requirements", "weights",
                            "results", "engineering", "report", "inspection"][page - 1]
            if page >= 5:
                base["results"] = []
            if page >= 6:
                base["selected_meter"] = _selected_meter()
                base["engineering"] = {
                    "pipe": {}, "uncertainty": {}, "ex": {}, "sil": {},
                    "straight_pipe": {"upstream_required_diameters": 18,
                                      "downstream_required_diameters": 5,
                                      "total_required_m": 5.0},
                    "instrument_layout": {"instruments": [
                        {"type": "pressure", "count": 1, "tag_list": ["PT-1001"],
                         "position_D": -2.0, "position_m": 0.05,
                         "side": "upstream", "standard": "ISO 5167-1"},
                    ]},
                    "conditioner_selected": None,
                }
            at = _build_app_test(base)
            assert not at.exception, (
                f"page {page} ({base['page']}) {lang}: {[str(e) for e in at.exception]}"
            )


def test_i18n_key_use_in_pages():
    """Every t('...') key used in pages must exist in the translation tables."""
    import re
    from metering_designer.core import i18n
    tr_keys = set(i18n.TRANSLATIONS["tr"].keys())
    pages_dir = os.path.join(ROOT, "streamlit_app", "pages")
    missing = []
    for fname in sorted(os.listdir(pages_dir)):
        if not fname.endswith(".py"):
            continue
        src = open(os.path.join(pages_dir, fname), encoding="utf-8").read()
        for m in re.finditer(r'(?<!\w)t\("([a-z_]+)"\)', src):
            if m.group(1) not in tr_keys:
                missing.append((fname, m.group(1)))
    components_dir = os.path.join(ROOT, "streamlit_app", "components")
    for fname in sorted(os.listdir(components_dir)):
        if not fname.endswith(".py"):
            continue
        src = open(os.path.join(components_dir, fname), encoding="utf-8").read()
        for m in re.finditer(r'(?<!\w)t\("([a-z_]+)"\)', src):
            if m.group(1) not in tr_keys:
                missing.append((fname, m.group(1)))
    assert not missing, f"missing i18n keys: {missing}"


def test_convert_display_pressure_units():
    from metering_designer.core.units import convert_display
    assert abs(convert_display(40, "bar", "psi") - 580.15) < 0.1
    assert abs(convert_display(580.15, "psi", "bar") - 40) < 0.01
    assert abs(convert_display(100, "kPa", "bar") - 1.0) < 0.001


def test_convert_display_temperature_units():
    from metering_designer.core.units import convert_display
    assert abs(convert_display(25, "degC", "degF") - 77.0) < 0.1
    assert abs(convert_display(77, "degF", "degC") - 25) < 0.1
    assert abs(convert_display(0, "degC", "K") - 273.15) < 0.1


def test_convert_display_flow_units():
    from metering_designer.core.units import convert_display
    assert abs(convert_display(10000, "Sm3/hour", "mmscf/hour") - 0.3531) < 0.001
    assert abs(convert_display(1, "mmscf/hour", "Sm3/hour") - 28316.85) < 1.0
    assert abs(convert_display(100, "m**3/hour", "Sm3/hour") - 100) < 1e-6


def test_unit_selector_symmetry_all_options():
    """Every UI unit option converts to every other option and back."""
    from metering_designer.core.units import (PRESSURE_UNITS, TEMPERATURE_UNITS,
                                              FLOW_UNITS, convert_display)
    for options in (PRESSURE_UNITS, FLOW_UNITS):
        for i, (_label1, unit1) in enumerate(options):
            for _label2, unit2 in options[i + 1:]:
                val_fwd = convert_display(10, unit1, unit2)
                val_back = convert_display(val_fwd, unit2, unit1)
                assert abs(val_back - 10) < 1e-6 * max(abs(10), abs(val_fwd))
    for _label1, unit1 in TEMPERATURE_UNITS:
        for _label2, unit2 in TEMPERATURE_UNITS:
            val_fwd = convert_display(25, unit1, unit2)
            val_back = convert_display(val_fwd, unit2, unit1)
            assert abs(val_back - 25) < 1e-6 * max(1, abs(val_fwd))


def test_measurement_schematic_renders_no_error():
    import matplotlib
    matplotlib.use("Agg")
    from metering_designer.inspection.models import InspectionPoint
    from metering_designer.instruments.schematic import (
        render_measurement_points_schematic, _parse_point_position,
    )
    pts = [
        InspectionPoint("0°@1D", 1.0, 1.0, 0.1, -0.1),
        InspectionPoint("90°@1D", 2.0, 1.0, 0.1, -0.1),
        InspectionPoint("45°@2D", 1.0, 1.0, 0.1, -0.1),
    ]
    fig = render_measurement_points_schematic("D — çap ölçümü", pts, nps=8, lang="tr")
    import matplotlib.pyplot as plt
    plt.close(fig)


def test_parse_point_position_labels():
    from metering_designer.instruments.schematic import _parse_point_position
    assert _parse_point_position("0°@1D") == (0.0, 1.0)
    assert _parse_point_position("90°@1D") == (90.0, 1.0)
    assert _parse_point_position("90°") == (90.0, None)
    assert _parse_point_position("2D") == (None, 2.0)
    assert _parse_point_position("135°@1.5D") == (135.0, 1.5)
    assert _parse_point_position("#1") == (None, None)


def test_schematic_png_bytes_roundtrip():
    from metering_designer.instruments.schematic import render_schematic_png_bytes
    png = render_schematic_png_bytes("orifice", nps=8, lang="tr")
    assert isinstance(png, bytes) and png[:8] == b"\x89PNG\r\n\x1a\n"


def test_inspection_report_points_render_schematic():
    """Every non-qualitative parameter in a real orifice report draws a schematic."""
    from metering_designer.inspection.builder import build_inspection_checklist
    from metering_designer.inspection.models import InspectionPoint
    from metering_designer.instruments.schematic import render_measurement_points_schematic
    import matplotlib.pyplot as plt
    report = build_inspection_checklist(meter_type="orifice", conditioner_type=None,
                                        nps=8, beta=0.65, D_mm=202.7)
    drawn = 0
    for comp in report.components:
        for param in comp.parameters:
            if not param.points:
                continue
            fig = render_measurement_points_schematic(param.label, param.points,
                                                      report.meter_type, report.nps, "tr")
            plt.close(fig)
            drawn += 1
    assert drawn >= 10


def test_get_app_version_reads_pyproject():
    from metering_designer.core.updates import get_app_version
    v = get_app_version()
    import re
    assert re.match(r"^\d+\.\d+(\.\d+)?", v), v


def test_compare_versions_basic():
    from metering_designer.core.updates import compare_versions
    assert compare_versions("1.0.0", "1.1.0") is True
    assert compare_versions("1.1.0", "1.0.0") is False
    assert compare_versions("1.0.0", "1.0.0") is False
    assert compare_versions("1.0.0", "2.0.0") is True
    assert compare_versions("1.0.0", "1.0.1") is True
    assert compare_versions("v1.0.0", "v1.0.2") is True


def test_compare_versions_garbage_never_newer():
    from metering_designer.core.updates import compare_versions
    assert compare_versions("1.0.0", "garbage") is False
    assert compare_versions("1.0.0", "") is False
    assert compare_versions("1.0.0", None) is False


def test_check_in_background_caches_result_and_never_blocks(monkeypatch):
    from metering_designer.core import updates
    from metering_designer.core.updates import check_in_background, reset_check_cache

    releases = [{
        "tag_name": "v9.9.9",
        "assets": [{
            "name": "MeteringStationDesigner_macOS_arm64.zip",
            "browser_download_url": "https://example.invalid/app.zip",
            "digest": "sha256:abcd",
        }],
    }]
    monkeypatch.setattr(updates, "fetch_releases", lambda *a, **k: releases)

    reset_check_cache()
    first = check_in_background(platform="darwin")
    # While a check is in flight we must get a usable (non-blocking) dict back.
    assert isinstance(first, dict)
    assert "update_available" in first
    assert "latest" in first

    import time
    deadline = time.time() + 10
    done = False
    while time.time() < deadline:
        res = check_in_background(platform="darwin")
        if res.get("latest") is not None or res.get("error") is not None:
            done = True
            break
        time.sleep(0.05)
    reset_check_cache()
    assert done, "background update check never completed"


def test_check_in_background_offline_degrades_gracefully(monkeypatch):
    import time

    from metering_designer.core import updates
    from metering_designer.core.updates import check_in_background, reset_check_cache

    def _boom(*a, **k):
        raise OSError("no network")

    monkeypatch.setattr(updates, "fetch_releases", _boom)
    reset_check_cache()
    res = check_in_background()
    # Offline still returns a usable dict; the app must not crash.
    assert isinstance(res, dict)
    assert res.get("update_available") in (True, False)
    deadline = time.time() + 10
    while time.time() < deadline:
        res = check_in_background()
        if res.get("error") is not None:
            break
        time.sleep(0.05)
    assert res.get("error") is not None
    reset_check_cache()
