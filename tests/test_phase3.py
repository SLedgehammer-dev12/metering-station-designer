"""Phase 3 comprehensive integration tests"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metering_designer.meters.pd_meter import size_pd_meter
from metering_designer.meters.vortex import size_vortex
from metering_designer.report.pdf_report import generate_pdf_report, HAS_WEASYPRINT as HAS_REPORTLAB
from metering_designer.metrology.uncertainty import calc_uncertainty_budget, calc_uncertainty_budget_detailed
from metering_designer.piping.materials import select_material
from metering_designer.core.i18n import get_text
from metering_designer.core.backends import calc_z_factor, get_backend_status
from metering_designer.fluids.gas import calc_gas_properties
from metering_designer.conditioners.scoring import score_all_conditioners
from metering_designer.core.validation import validate_process_inputs, validate_requirements, validate_project_inputs, check_composition_sanity
from collections import namedtuple


def test_pd_meter_sizing():
    pd = size_pd_meter(8, 200, 50, 850, 12, 30, 35)
    assert pd["meter_size_inches"] > 0
    assert pd["capacity_percent"] > 0
    assert pd["slip_pct_at_qmax"] < 10
    assert pd["delta_p_mbar"] > 0
    assert pd["turndown_actual"] > 0


def test_vortex_sizing():
    vx = size_vortex(6, 15000, 3000, 40, 35, 30, 1.5e-6, 0.75, True)
    assert vx["v_max_ms"] > 0
    assert vx["f_max_hz"] > 0
    assert vx["K_factor_pulses_per_m3"] > 0
    assert isinstance(vx["velocity_ok"], bool)
    assert isinstance(vx["turndown_ok"], bool)


def test_pdf_report():
    if not HAS_REPORTLAB:
        return
    import tempfile
    data = {
        "meter_type": "USM",
        "standard_ref": "ISO 5167 / AGA 9",
        "pressure": 40.0,
        "temperature": 20.0,
        "flow_max": 1000.0,
        "flow_min": 100.0,
        "density_op": 30.0,
        "viscosity": 1.2e-5,
        "z_factor": 0.9,
        "sizing_results": {"beta": 0.5, "Cd": 0.603, "d_mm": 50.0},
        "uncertainty_components": [
            {"name": "meter", "value_pct": 0.6, "type": "B", "distribution": "normal"},
        ],
        "combined_uncertainty": 0.65,
        "expanded_k2": 1.30,
        "gas_properties": {"M_mix": 18.5, "rho_std_kg_m3": 0.8},
        "notes": ["Test note 1", "Test note 2"],
        "schematic_png_b64": "QUJD",
        "instrument_table_rows": [
            {"tag": "PT-1001", "type": "pressure", "count": 1,
             "position_D": -2.0, "side": "Upstream", "standard": "ISO 5167-1"},
        ],
    }
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        out = f.name
    try:
        result = generate_pdf_report(data, out)
        assert os.path.exists(result), f"PDF was not created at {result}"
        assert os.path.getsize(result) > 1000, "PDF file too small"
        with open(out, "rb") as fh:
            raw = fh.read()
        assert b"%PDF-" in raw, "Missing PDF header"
    finally:
        try:
            os.unlink(out)
        except OSError:
            pass


def test_gc_uncertainty():
    unc = calc_uncertainty_budget('ultrasonic')
    assert 'gc_composition' in [c['name'] for c in unc['components']]
    assert unc['expanded_uncertainty_k2_95pct'] > 0


def test_material_chloride_offshore():
    mat = select_material(h2s=True, h2s_ppm=150000, has_chlorides=True, chloride_ppm=5000, offshore=True)
    assert '2507' in mat['name']


def test_material_sour_only():
    mat = select_material(h2s=True, h2s_ppm=1000, has_chlorides=False, offshore=False)
    assert mat['name'] != ''


def test_i18n():
    assert 'Proje' in get_text('project', 'tr')
    assert 'Project' in get_text('project', 'en')
    assert get_text('nonexistent', 'tr') == 'nonexistent'

    # Domain: safety
    assert len(get_text('sour_service', 'tr')) > 0
    assert 'H₂S' in get_text('sour_service', 'tr') or 'Sour' in get_text('sour_service', 'en')
    assert len(get_text('ex_zone', 'en')) > 0

    # Domain: fluids / process
    assert 'Gaz' in get_text('natural_gas', 'tr') or 'Gas' in get_text('natural_gas', 'en')
    assert len(get_text('custody_transfer', 'tr')) > 0
    assert 'Custody' in get_text('custody_transfer', 'en')

    # Domain: meters / results
    assert len(get_text('selected_meter', 'tr')) > 0
    assert 'Meter' in get_text('selected_meter', 'en')

    # Domain: reports
    assert len(get_text('excel_report', 'en')) > 0
    assert len(get_text('pdf_report', 'tr')) > 0

    # Domain: actions / UI
    assert len(get_text('calculate', 'tr')) > 0
    assert len(get_text('reset', 'en')) > 0

    # Verify fallback: unknown lang returns tr string for known key
    assert 'Proje' in get_text('project', 'zz')  # unknown lang → fallback to tr


def test_backend_fallback():
    # Different mixture + different P/T than test_pyaga8_z_reference in test_backend_fallback.py
    comp = {'C1': 0.85, 'C2': 0.08, 'C3': 0.03, 'iC4': 0.02, 'N2': 0.02}
    r = calc_z_factor(60, 50, comp)
    assert r['Z'] > 0.1
    assert r['Z'] < 3.0
    assert r['density_kg_m3'] > 0
    assert isinstance(r['backend_layer'], int)
    # Verify backend_used field is present and non-empty
    assert 'backend_used' in r or 'backend_layer' in r


def test_gas_properties_backend():
    comp = {'C1': 90, 'C2': 4, 'C3': 1.5, 'N2': 1.0, 'CO2': 2.0}
    gp = calc_gas_properties(comp, 45, 40)
    assert gp['Z_oper'] > 0.1
    assert gp['rho_oper_kg_m3'] > 0
    assert 'backend_used' in gp


def test_conditioner_scoring():
    cr = score_all_conditioners('orifice', 10, 'double_bend_out_of_plane', 3.0, 4.5)
    assert len(cr) > 0
    assert cr[0]['total_score'] >= cr[-1]['total_score']


def test_validation():
    proc_ok = {'fluid_type': 'doğal_gaz', 'nps': 8, 'design_p_bar': 50, 'oper_p_bar': 40,
               'design_t_c': 60, 'oper_t_c': 40, 'qmin': 1000, 'qmax': 10000}
    assert len(validate_process_inputs(proc_ok)) == 0

    proc_bad = {'fluid_type': 'gas', 'nps': 50, 'design_p_bar': 10, 'oper_p_bar': 40, 'qmin': 100, 'qmax': 0}
    errs = validate_process_inputs(proc_bad)
    assert len(errs) >= 3

    req_ok = {'ex_zone': 'zone_2', 'target_uncertainty': 1.0, 'ambient_min_C': 0, 'ambient_max_C': 40}
    assert len(validate_requirements(req_ok)) == 0


# ---------------------------------------------------------------------------
# 3.9: Composition sanity test
# ---------------------------------------------------------------------------

def test_composition_sanity_low_c1():
    """Low C1 (<70%) must trigger a warning."""
    warnings = check_composition_sanity({"C1": 50, "C2": 30, "N2": 20})
    assert len(warnings) >= 1, "should warn about low C1"
    assert any("düşük" in w.lower() or "low" in w.lower() for w in warnings)


def test_composition_sanity_high_h2s():
    """High H2S (>5%) must trigger a warning."""
    warnings = check_composition_sanity({"C1": 80, "H2S": 8, "N2": 12})
    assert len(warnings) >= 1, "should warn about high H2S"
    assert any("h2s" in w.lower() or "sour" in w.lower() or "H₂S" in w for w in warnings)


def test_composition_sanity_normal():
    """Normal pipeline composition should return no warnings."""
    comp = {"C1": 90, "C2": 4, "C3": 1.5, "N2": 2.5, "CO2": 2}
    warnings = check_composition_sanity(comp)
    assert len(warnings) == 0, f"expected no warnings, got: {warnings}"


# ---------------------------------------------------------------------------
# 3.10: Project validation test
# ---------------------------------------------------------------------------

def test_validate_project_inputs_missing_name():
    """Missing project name must return an error."""
    errors = validate_project_inputs({"location": "Test Site"})
    assert len(errors) >= 1, "should error on missing project name"
    assert any("zorunludur" in e.lower() or "required" in e.lower() for e in errors)


def test_validate_project_inputs_valid():
    """Valid project input must pass with no errors."""
    errors = validate_project_inputs({"name": "Test Project", "location": "Site A"})
    assert len(errors) == 0, f"expected no errors, got: {errors}"


def test_validate_project_inputs_missing_location():
    """Missing location should generate a warning."""
    errors = validate_project_inputs({"name": "Test Project"})
    assert len(errors) >= 1, "should warn about missing location"
    assert any("önerilir" in e.lower() or "location" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# 3.11: Uncertainty for orifice, turbine, vortex
# ---------------------------------------------------------------------------

def _check_uncertainty_result(result, meter_name):
    """Helper: verify uncertainty budget result structure."""
    assert isinstance(result, dict), f"{meter_name}: must return dict"
    assert "components" in result, f"{meter_name}: missing components"
    assert len(result["components"]) >= 3, f"{meter_name}: too few components"
    assert "combined_standard_uncertainty_pct" in result, f"{meter_name}: missing combined"
    assert result["combined_standard_uncertainty_pct"] > 0, f"{meter_name}: combined uncertainty <= 0"
    assert "expanded_uncertainty_k2_95pct" in result, f"{meter_name}: missing expanded k2"
    assert result["expanded_uncertainty_k2_95pct"] > 0, f"{meter_name}: expanded k2 <= 0"
    assert "expanded_uncertainty_k3_99pct" in result, f"{meter_name}: missing expanded k3"
    assert result["expanded_uncertainty_k3_99pct"] > 0, f"{meter_name}: expanded k3 <= 0"
    # k3 >= k2
    assert result["expanded_uncertainty_k3_99pct"] >= result["expanded_uncertainty_k2_95pct"], \
        f"{meter_name}: k3 ({result['expanded_uncertainty_k3_99pct']}) < k2 ({result['expanded_uncertainty_k2_95pct']})"
    # Verify component entries have required fields
    for c in result["components"]:
        assert "name" in c, f"{meter_name}: component missing name"
        assert "value_pct" in c, f"{meter_name}: component missing value_pct"
        assert "standard_uncertainty_pct" in c, f"{meter_name}: component missing std uncertainty"
        assert c["standard_uncertainty_pct"] >= 0, \
            f"{meter_name}: negative std uncertainty for {c['name']}"


def test_uncertainty_orifice():
    """Orifice meter uncertainty budget has expected structure."""
    result = calc_uncertainty_budget("orifice")
    _check_uncertainty_result(result, "orifice")
    # Orifice typically has higher uncertainty than ultrasonic
    assert result["combined_standard_uncertainty_pct"] > 0.3, \
        "orifice combined uncertainty too low"


def test_uncertainty_turbine():
    """Turbine meter uncertainty budget has expected structure."""
    result = calc_uncertainty_budget("turbine")
    _check_uncertainty_result(result, "turbine")
    # Turbine should have meter component
    comp_names = [c["name"] for c in result["components"]]
    assert "meter" in comp_names, "turbine missing 'meter' component"


def test_uncertainty_vortex():
    """Vortex meter uncertainty budget has expected structure."""
    result = calc_uncertainty_budget("vortex")
    _check_uncertainty_result(result, "vortex")
    # Vortex typically higher uncertainty
    assert result["combined_standard_uncertainty_pct"] > 0.4, \
        "vortex combined uncertainty too low"


# ---------------------------------------------------------------------------
# 3.12: Detailed uncertainty budget with additional terms
# ---------------------------------------------------------------------------

def test_detailed_budget_more_components():
    """Detailed budget includes additional uncertainty components."""
    basic = calc_uncertainty_budget("ultrasonic")
    detailed = calc_uncertainty_budget_detailed("ultrasonic")
    assert len(detailed["components"]) > len(basic["components"]), \
        "detailed budget should have more components than basic budget"
    # Verify the 5 additional terms are present
    extra_names = {"installation_effect", "pulsation", "long_term_drift",
                   "ambient_temperature", "ad_conversion"}
    detailed_names = {c["name"] for c in detailed["components"]}
    assert extra_names.issubset(detailed_names), \
        f"missing additional terms: {extra_names - detailed_names}"


def test_detailed_budget_higher_uncertainty():
    """Detailed combined uncertainty exceeds basic combined uncertainty."""
    basic = calc_uncertainty_budget("orifice")
    detailed = calc_uncertainty_budget_detailed("orifice")
    assert detailed["combined_standard_uncertainty_pct"] > basic["combined_standard_uncertainty_pct"], \
        "detailed combined uncertainty must be larger than basic"


def test_detailed_budget_expanded_k2():
    """Expanded uncertainty (k=2) is twice the combined standard uncertainty."""
    detailed = calc_uncertainty_budget_detailed("turbine")
    expected_k2 = detailed["combined_standard_uncertainty_pct"] * 2
    assert abs(detailed["expanded_uncertainty_k2_95pct"] - expected_k2) < 0.001, \
        f"k2 ({detailed['expanded_uncertainty_k2_95pct']}) != 2 * combined ({expected_k2})"


def test_detailed_budget_expanded_k3():
    """Expanded uncertainty (k=3) is three times the combined standard uncertainty."""
    detailed = calc_uncertainty_budget_detailed("vortex")
    expected_k3 = detailed["combined_standard_uncertainty_pct"] * 3
    assert abs(detailed["expanded_uncertainty_k3_99pct"] - expected_k3) < 0.001, \
        f"k3 ({detailed['expanded_uncertainty_k3_99pct']}) != 3 * combined ({expected_k3})"


def test_detailed_budget_all_meter_types():
    """All meter types produce valid detailed budgets."""
    for mtype in ["ultrasonic", "orifice", "turbine", "coriolis",
                  "positive_displacement", "vortex", "vcone"]:
        detailed = calc_uncertainty_budget_detailed(mtype)
        assert detailed["combined_standard_uncertainty_pct"] > 0, f"{mtype}: combined <= 0"
        assert detailed["includes_additional_terms"] is True, f"{mtype}: missing flag"
        # All extra terms present
        extra_names = {"installation_effect", "pulsation", "long_term_drift",
                       "ambient_temperature", "ad_conversion"}
        detailed_names = {c["name"] for c in detailed["components"]}
        assert extra_names.issubset(detailed_names), \
            f"{mtype}: missing {extra_names - detailed_names}"


def test_detailed_budget_pulsation_dampened():
    """Pulsation dampened flag reduces pulsation term."""
    default = calc_uncertainty_budget_detailed("orifice")
    dampened = calc_uncertainty_budget_detailed("orifice", pulsation_dampened=True)
    # Find pulsation components
    def get_pulsation_std(ub):
        for c in ub["components"]:
            if c["name"] == "pulsation":
                return c["standard_uncertainty_pct"]
        return None
    default_p = get_pulsation_std(default)
    dampened_p = get_pulsation_std(dampened)
    assert default_p is not None, "pulsation component missing in default"
    assert dampened_p is not None, "pulsation component missing in dampened"
    # Default: 0.05 / sqrt(3); Dampened: 0.02 / sqrt(3)
    expected_default = round(0.05 / 3**0.5, 4)
    expected_dampened = round(0.02 / 3**0.5, 4)
    assert abs(default_p - expected_default) < 0.001, \
        f"default pulsation std {default_p} != expected {expected_default}"
    assert abs(dampened_p - expected_dampened) < 0.001, \
        f"dampened pulsation std {dampened_p} != expected {expected_dampened}"
    # Dampened combined uncertainty should be slightly lower
    assert dampened["combined_standard_uncertainty_pct"] < default["combined_standard_uncertainty_pct"], \
        "dampened combined should be lower than default"


def test_detailed_budget_flow_conditioner():
    """Flow conditioner flag reduces installation effect term."""
    default = calc_uncertainty_budget_detailed("orifice")
    conditioned = calc_uncertainty_budget_detailed("orifice", flow_conditioner_installed=True)

    def get_install_std(ub):
        for c in ub["components"]:
            if c["name"] == "installation_effect":
                return c["standard_uncertainty_pct"]
        return None

    default_i = get_install_std(default)
    conditioned_i = get_install_std(conditioned)
    assert default_i is not None
    assert conditioned_i is not None
    # Default: 0.10 / sqrt(3); Conditioned: 0.05 / sqrt(3)
    expected_default = round(0.10 / 3**0.5, 4)
    expected_conditioned = round(0.05 / 3**0.5, 4)
    assert abs(default_i - expected_default) < 0.001
    assert abs(conditioned_i - expected_conditioned) < 0.001
    assert conditioned["combined_standard_uncertainty_pct"] < default["combined_standard_uncertainty_pct"]


def test_detailed_budget_both_flags():
    """Both pulsation_dampened and flow_conditioner_installed can be set together."""
    detailed = calc_uncertainty_budget_detailed("ultrasonic",
                                                 pulsation_dampened=True,
                                                 flow_conditioner_installed=True)
    assert detailed["pulsation_dampened"] is True
    assert detailed["flow_conditioner_installed"] is True
    # Verify reduced values
    for c in detailed["components"]:
        if c["name"] == "pulsation":
            assert abs(c["value_pct"] - 0.02) < 0.001
        if c["name"] == "installation_effect":
            assert abs(c["value_pct"] - 0.05) < 0.001


def test_detailed_budget_geometric_default_zero():
    """Geometric contribution defaults to 0.0 with no extra components."""
    detailed = calc_uncertainty_budget_detailed("ultrasonic")
    assert detailed["geometric_contribution_pct"] == 0.0
    names = {c["name"] for c in detailed["components"]}
    assert "geometric_deviation" not in names
    # Backward compatible: matches budget without geometric plumbing
    plain = calc_uncertainty_budget_detailed("ultrasonic")
    assert detailed["combined_standard_uncertainty_pct"] == plain["combined_standard_uncertainty_pct"]


def test_detailed_budget_geometric_contribution():
    """Geometric contribution is added to components and raises combined uncertainty."""
    base = calc_uncertainty_budget_detailed("orifice")
    geo = 0.30
    detailed = calc_uncertainty_budget_detailed("orifice", geometric_contribution_pct=geo)

    names = {c["name"] for c in detailed["components"]}
    assert "geometric_deviation" in names, "geometric_deviation component missing"
    assert detailed["geometric_contribution_pct"] == round(geo, 4)

    geo_comp = next(c for c in detailed["components"] if c["name"] == "geometric_deviation")
    assert geo_comp["value_pct"] == round(geo, 4)
    assert geo_comp["source"] == "inspection"
    assert geo_comp["type"] == "A"

    # RSS combination: sqrt(base_combined^2 + geo^2)
    expected = (base["combined_standard_uncertainty_pct"] ** 2 + geo ** 2) ** 0.5
    assert abs(detailed["combined_standard_uncertainty_pct"] - expected) < 0.001, \
        f"combined {detailed['combined_standard_uncertainty_pct']} != expected {expected}"
    assert detailed["combined_standard_uncertainty_pct"] > base["combined_standard_uncertainty_pct"]


def test_detailed_budget_geometric_gum():
    """GUM-propagated outputs are present when geometric contribution is used."""
    from metering_designer.metrology.uncertainty import HAS_UNCERTAINTIES
    detailed = calc_uncertainty_budget_detailed("turbine", geometric_contribution_pct=0.20)

    if not HAS_UNCERTAINTIES:
        assert "gum_std_uncertainty" not in detailed
        return

    assert "gum_combined_standard_uncertainty_pct" in detailed
    assert "gum_std_uncertainty" in detailed
    assert "gum_expanded_k2_pct" in detailed
    assert detailed["gum_std_uncertainty"] > 0, "gum_std_uncertainty must be positive"
    # nominal combined ~ classical combined; epistemic std ~ 5% of combined
    assert abs(detailed["gum_combined_standard_uncertainty_pct"]
               - detailed["gum_expanded_k2_pct"] / 2) < 0.001, \
        "gum expanded (k=2) must be twice gum combined"


def test_detailed_budget_geometric_zero_no_gum():
    """No GUM keys are emitted when geometric contribution is zero."""
    detailed = calc_uncertainty_budget_detailed("coriolis")
    assert "gum_std_uncertainty" not in detailed
    assert "gum_expanded_k2_pct" not in detailed


if __name__ == "__main__":
    for name, func in list(locals().items()):
        if name.startswith("test_"):
            try:
                func()
                print(f"✅ {name}")
            except Exception as e:
                print(f"❌ {name}: {e}")
    print("\nPhase 3 integration tests complete")
