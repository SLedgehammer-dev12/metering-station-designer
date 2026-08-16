"""Design-standard registry and standard-aware meter sizing tests."""

import pytest

from metering_designer.standards.design_standards import (
    METER_STANDARDS,
    default_standard,
    get_standard,
    list_standards,
)
from metering_designer.meters.orifice import (
    calc_beta_ratio,
    generate_design_advisories,
    size_orifice_for_flow,
)
from metering_designer.meters.ultrasonic import size_ultrasonic


# --------------------------------------------------------------------- registry

def test_registry_has_orifice_profiles():
    assert set(METER_STANDARDS["orifice"]) == {"iso5167_2", "aga3"}


def test_list_standards_orifice():
    opts = list_standards("orifice")
    assert len(opts) >= 2
    names = {o["name"] for o in opts}
    assert "ISO 5167-2:2022" in names
    assert any("AGA Report No.3" in n for n in names)


def test_list_standards_other_meters_empty():
    # Framework is staged: unimplemented meter types expose no profiles.
    assert list_standards("coriolis") == []
    assert list_standards("turbine") == []
    assert list_standards("v_cone") == []


def test_default_standard():
    assert default_standard("orifice") == "iso5167_2"
    assert default_standard("ultrasonic") == "aga9"
    assert default_standard("coriolis") is None


def test_get_standard_and_fallback():
    iso = get_standard("orifice", "iso5167_2")
    assert iso["default_tap"] == "corner"
    aga = get_standard("orifice", "aga3")
    assert aga["default_tap"] == "flange"
    # Unknown id falls back to the default profile.
    assert get_standard("orifice", "nope")["name"] == iso["name"]
    assert get_standard("coriolis", "anything") is None


# --------------------------------------------------------------- orifice sizing

def test_orifice_standard_fields_present():
    res = calc_beta_ratio(10.0, 100.0, 50.0, 1.2e-5, 25000, p1_Pa=45e5)
    assert res["standard"] == "iso5167_2"
    assert res["standard_ref"] == "ISO 5167-2:2022"
    assert res["tap_type"] == "corner"


def test_orifice_aga_defaults_to_flange_taps():
    res = calc_beta_ratio(10.0, 100.0, 50.0, 1.2e-5, 25000, p1_Pa=45e5, tap_type=None, standard="aga3")
    assert res["standard"] == "aga3"
    assert res["tap_type"] == "flange"
    assert "AGA Report No.3" in res["standard_name"]


def test_orifice_explicit_tap_overrides_standard_default():
    res = calc_beta_ratio(10.0, 100.0, 50.0, 1.2e-5, 25000, p1_Pa=45e5, tap_type="D_D", standard="aga3")
    assert res["tap_type"] == "D_D"


def test_orifice_invalid_keyword_standard_falls_back():
    res = calc_beta_ratio(10.0, 100.0, 50.0, 1.2e-5, 25000, p1_Pa=45e5, standard="garbage")
    assert res["standard"] == "iso5167_2"


def test_orifice_invalid_explicit_tap_raises():
    with pytest.raises(ValueError):
        calc_beta_ratio(10.0, 100.0, 50.0, 1.2e-5, 25000, p1_Pa=45e5, tap_type="nonsense")


def test_dp_design_mbar_drives_beta_monotonically():
    base = size_orifice_for_flow(30000, 5000, 202.7, 45, 40, 40, 1.2e-5, 0.91, 0.75,
                                 dp_design_mbar=250)
    higher_dp = size_orifice_for_flow(30000, 5000, 202.7, 45, 40, 40, 1.2e-5, 0.91, 0.75,
                                      dp_design_mbar=500)
    assert base["dp_design_mbar"] == 250.0
    assert higher_dp["dp_design_mbar"] == 500.0
    # Higher ΔP at fixed flow -> smaller β (smaller bore handles more dP).
    assert higher_dp["beta"] < base["beta"]
    # And ΔP@Qmin scales quadratically with flow ratio.
    assert base["dp_at_qmin_mbar"] > 0
    assert base["dp_at_qmin_mbar"] < base["dp_at_qmax_mbar"]


def test_dp_design_default_keeps_250():
    res = size_orifice_for_flow(30000, 5000, 202.7, 45, 40, 40, 1.2e-5, 0.91, 0.75)
    assert res["dp_design_mbar"] == 250.0
    assert res["standard"] == "iso5167_2"


def test_orifice_aga3_via_size_with_default_tap():
    res = size_orifice_for_flow(30000, 5000, 202.7, 45, 40, 40, 1.2e-5, 0.91, 0.75,
                                standard="aga3")
    assert res["tap_type"] == "flange"
    assert res["standard"] == "aga3"


# --------------------------------------------------------------- advisory notes

def test_advisories_beta_in_recommended_band():
    adv = generate_design_advisories(0.45, 80.0, 250)
    levels = [a["level"] for a in adv]
    assert "warning" not in levels
    assert any(a["key"] == "std_adv_beta_ok" for a in adv)


def test_advisories_warn_high_beta():
    adv = generate_design_advisories(0.70, 80.0, 250)
    keys = [a["key"] for a in adv]
    assert "std_adv_beta_high" in keys


def test_advisories_warn_low_beta():
    adv = generate_design_advisories(0.15, 80.0, 250)
    keys = [a["key"] for a in adv]
    assert "std_adv_beta_low" in keys


def test_advisories_warn_out_of_limits():
    adv = generate_design_advisories(0.02, 80.0, 250)
    keys = [a["key"] for a in adv]
    assert "std_adv_beta_out_of_limits" in keys


def test_advisories_warn_low_qmin_dp():
    adv = generate_design_advisories(0.45, 5.0, 250)
    keys = [a["key"] for a in adv]
    assert "std_adv_dp_low" in keys


def test_advisories_always_report_design_dp():
    adv = generate_design_advisories(0.45, 80.0, 500)
    assert any(a["key"] == "std_adv_dp_design" and a["values"]["dp"] == 500 for a in adv)


# --------------------------------------------------------------- ultrasonic

def test_usm_default_standard_aga9():
    res = size_ultrasonic(8, 30000, 3000, 45, 40, 40, 1.2e-5, 0.75)
    assert res["standard"] == "aga9"
    assert res["standard_name"] == "AGA Report No.9"


def test_usm_iso17089_standard():
    res = size_ultrasonic(8, 30000, 3000, 45, 40, 40, 1.2e-5, 0.75, standard="iso17089")
    assert res["standard"] == "iso17089"
    assert res["standard_ref"] == "ISO 17089-1"


def test_usm_invalid_standard_falls_back_aga9():
    res = size_ultrasonic(8, 30000, 3000, 45, 40, 40, 1.2e-5, 0.75, standard="garbage")
    assert res["standard"] == "aga9"


def test_usm_velocity_limits_applied():
    res = size_ultrasonic(8, 30000, 3000, 45, 40, 40, 1.2e-5, 0.75)
    assert isinstance(res["velocity_ok"], bool)
    assert "velocity" in res["sizing_note"].lower() or res["velocity_ok"]


# ------------------------------------------------------------------------- UI

def test_engineering_page_renders_standard_selector_and_dp_input():
    """The engineering page must show the standard selector and design-ΔP box."""
    import copy
    import os

    from metering_designer.core.scoring_engine import ScoredMeter
    from streamlit.testing.v1 import AppTest

    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base = {
        "page": "engineering", "lang": "tr",
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
        "weights": None, "results": None,
        "selected_meter": ScoredMeter(
            meter_key="orifice", name_tr="Orifis Plakası", name_en="Orifice Plate",
            total_score=85.0, tier_label="Tier 1", tier_color="green",
            strengths=["güçlü"], weaknesses=["zayıf"],
        ),
        "engineering": {},
    }
    at = AppTest.from_file(os.path.join(ROOT, "streamlit_app", "app.py"), default_timeout=90)
    for k, v in base.items():
        at.session_state[k] = copy.deepcopy(v)
    at.run()
    assert not at.exception, [str(e) for e in at.exception]

    selectbox_ids = [sb.key for sb in at.selectbox if sb.key]
    assert any("std_select_orifice" in k for k in selectbox_ids)
    number_keys = [n.key for n in at.number_input if n.key]
    assert "dp_design_mbar_input" in number_keys


def test_engineering_standard_switch_updates_orifice_tap_metric(monkeypatch):
    """Switching orifice standard to AGA-3 must surface flange taps in results."""
    import copy
    import os

    from metering_designer.core.scoring_engine import ScoredMeter
    from streamlit.testing.v1 import AppTest

    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base = {
        "page": "engineering", "lang": "tr",
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
        "weights": None, "results": None,
        "selected_meter": ScoredMeter(
            meter_key="orifice", name_tr="Orifis Plakası", name_en="Orifice Plate",
            total_score=85.0, tier_label="Tier 1", tier_color="green",
            strengths=["güçlü"], weaknesses=["zayıf"],
        ),
        "engineering": {},
    }
    at = AppTest.from_file(os.path.join(ROOT, "streamlit_app", "app.py"), default_timeout=90)
    for k, v in base.items():
        at.session_state[k] = copy.deepcopy(v)
    at.run()
    assert not at.exception
    # Flip the standard selector to AGA-3 and rerun.
    for sb in at.selectbox:
        if sb.key == "std_select_orifice":
            sb.select("aga3")
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    metrics = [m.value for m in at.metric]
    assert any("Flange" in v for v in metrics)