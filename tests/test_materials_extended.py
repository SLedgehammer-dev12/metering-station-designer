"""Extended materials tests (Agent: test-materials)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from metering_designer.piping.wall_thickness import calc_min_wall_thickness, calc_flange_min_class
from metering_designer.piping.materials import select_material
from metering_designer.piping.schedule import recommend_schedule
from metering_designer.piping.materials import MATERIAL_RECOMMENDATIONS
from metering_designer.safety.ex_classification import classify_ex, _detect_t_class_from_composition, classify_zone_detailed, SAFETY_FACTOR


def test_all_9_api5l_grades(all_api5l_grades):
    for grade in all_api5l_grades:
        pipe = calc_min_wall_thickness(70, 60, 273.1, grade)
        assert "error" not in pipe, f"{grade}: {pipe.get('error','')}"
        assert pipe["t_min_pressure_mm"] > 0, f"{grade}: t_min=0"


def test_api5l_sour_matrix():
    b = select_material(h2s=True, h2s_ppm=0)
    assert b["key"] in ("api_5l_b_sweet", "carbon_steel_sour", "carbon_steel_low_temp")

    x52 = select_material(h2s=True, h2s_ppm=5000, high_pressure=True)
    assert "X52" in x52.get("name", "") or "A106" in x52.get("name", "")

    x80 = select_material(h2s=True, h2s_ppm=5000, high_pressure=True)
    assert "X80" not in x80.get("name", "")

    # X70: restricted per ISO 15156-2
    x70_mat = MATERIAL_RECOMMENDATIONS["api_5l_x70"]
    assert "restricted" in x70_mat.get("nace_standard", "").lower()

    # X52: SSC test required
    x52_mat = MATERIAL_RECOMMENDATIONS["api_5l_x52_sour"]
    assert "SSC" in x52_mat.get("notes", "") or "SSC" in x52_mat.get("name", "")


def test_api5l_temp_derating(all_api5l_grades):
    pipe_ambient = calc_min_wall_thickness(50, 40, 273.1, "API_5L_X65")
    pipe_hot = calc_min_wall_thickness(50, 350, 273.1, "API_5L_X65")
    if "error" not in pipe_hot:
        S_ambient = pipe_ambient["allowable_stress_MPa"]
        S_hot = pipe_hot["allowable_stress_MPa"]
        assert S_hot < S_ambient
        ratio = S_hot / S_ambient
        assert 0.45 < ratio < 0.65  # ~55% at 350°C


def test_material_temp_limit():
    pipe = calc_min_wall_thickness(50, 500, 219.1, "A106_GrB")
    assert "error" in pipe


def test_material_burst_pressure():
    design_p = 70
    pipe = calc_min_wall_thickness(design_p, 60, 273.1, "API_5L_X65")
    if "error" not in pipe:
        assert "burst_pressure_bar" in pipe
        assert pipe["burst_pressure_bar"] > design_p  # burst > design pressure


def test_flange_class_70bar_cs():
    flange = calc_flange_min_class(70, 60, "carbon_steel")
    assert "error" not in flange
    assert flange["flange_class"] == 600


def test_schedule_nps10():
    s = recommend_schedule(10, 11.5)
    assert s.get("recommended") is not None
    assert "SCH 80" in s["recommended"]["schedule_name"]


def test_ex_t_class_auto():
    comp = {"C1": 0.85, "nC5": 0.05, "C6": 0.03, "N2": 0.04, "CO2": 0.03}
    t_class = _detect_t_class_from_composition(comp)
    # Lowest AIT = C6 (225°C). With SF 0.8: 225*0.8=180 → T4
    assert t_class == "T4"


def test_ex_methane_only():
    t_class = _detect_t_class_from_composition({"C1": 1.0})
    assert t_class == "T1"


def test_ex_with_h2s():
    t_class = _detect_t_class_from_composition({"C1": 0.90, "H2S": 0.05, "N2": 0.05})
    assert t_class in ("T2", "T3")


def test_classify_ex_zone_enclosed():
    result = classify_ex(fluid_type="gas", is_enclosed=True, ventilation="natural")
    assert result["zone"] == "Zone 1"


def test_schedule_exceeds_max():
    s = recommend_schedule(10, 50.0)
    assert s.get("recommended") is None


# ---------------------------------------------------------------------------
# 3.12: Material selection for sweet gas
# ---------------------------------------------------------------------------

def test_select_material_sweet_gas():
    """Sweet gas only: carbon steel materials appear, Duplex/2507 do NOT."""
    result = select_material(h2s=False, h2s_ppm=0)
    assert result is not None
    assert "name" in result
    name = result["name"]
    # Must be a carbon steel or sweet-rated material
    assert any(kw in name.lower() for kw in ["karbon", "carbon", "a106", "a333", "api 5l"]), \
        f"expected carbon steel, got: {name}"
    # Must NOT be Duplex or Super Duplex
    assert "duplex" not in name.lower(), f"sweet gas should not select Duplex: {name}"
    assert "2507" not in name, f"sweet gas should not select 2507: {name}"
    assert "2205" not in name, f"sweet gas should not select 2205: {name}"


# ---------------------------------------------------------------------------
# Phase E2: ATEX classification with safety factor and ventilation detail
# ---------------------------------------------------------------------------

def test_ex_t_class_safety_factor():
    """Safety factor 0.8 is applied to AIT for T-class determination.
    Acetylene AIT=305°C → max_surface_temp=305*0.8=244°C → T3 (200 ≤ 244 < 300).
    Without safety factor, 305 ≥ 300 would give T2.
    """
    # Acetylene composition — lowest AIT = 305°C (C2H2)
    comp = {"C2H2": 1.0}
    t_class = _detect_t_class_from_composition(comp)
    # With SF=0.8: 305*0.8 = 244 → T3 (200..300)
    assert t_class == "T3", f"Expected T3 with safety factor, got {t_class}"

    # Verify the safety factor constant exists and is in range
    assert SAFETY_FACTOR == 0.8
    assert 0 < SAFETY_FACTOR < 1.0


def test_classify_zone_detailed():
    """Test various ventilation/release scenarios for zone classification."""
    # 1. Open area + high ventilation + secondary release → Zone 2
    assert classify_zone_detailed(
        is_enclosed=False, ventilation_type="natural",
        ventilation_rate="high", has_gas_detection=False,
        release_grade="secondary",
    ) == "Zone 2"

    # 2. Enclosed + natural/low ventilation + secondary → Zone 1
    assert classify_zone_detailed(
        is_enclosed=True, ventilation_type="natural",
        ventilation_rate="low", has_gas_detection=False,
        release_grade="secondary",
    ) == "Zone 1"

    # 3. Enclosed + forced/high + gas detection + secondary → Zone 2
    assert classify_zone_detailed(
        is_enclosed=True, ventilation_type="forced",
        ventilation_rate="high", has_gas_detection=True,
        release_grade="secondary",
    ) == "Zone 2"

    # 4. Continuous release → Zone 0 (ignores ventilation/enclosure)
    assert classify_zone_detailed(
        is_enclosed=False, ventilation_type="natural",
        ventilation_rate="high", has_gas_detection=False,
        release_grade="continuous",
    ) == "Zone 0"

    # 5. Primary release → Zone 1
    assert classify_zone_detailed(
        is_enclosed=False, ventilation_type="natural",
        ventilation_rate="high", has_gas_detection=False,
        release_grade="primary",
    ) == "Zone 1"

    # 6. Open + medium ventilation + gas detection → Zone 2 (reduced from 1)
    assert classify_zone_detailed(
        is_enclosed=False, ventilation_type="natural",
        ventilation_rate="medium", has_gas_detection=True,
        release_grade="secondary",
    ) == "Zone 2"

    # 7. Open + medium ventilation + no gas detection → Zone 1
    assert classify_zone_detailed(
        is_enclosed=False, ventilation_type="natural",
        ventilation_rate="medium", has_gas_detection=False,
        release_grade="secondary",
    ) == "Zone 1"

    # 8. Enclosed + forced/high + no gas detection → Zone 1 (gd required for Z2)
    assert classify_zone_detailed(
        is_enclosed=True, ventilation_type="forced",
        ventilation_rate="high", has_gas_detection=False,
        release_grade="secondary",
    ) == "Zone 1"

    # 9. Open + high ventilation + gas detection + secondary → Non-hazardous
    assert classify_zone_detailed(
        is_enclosed=False, ventilation_type="natural",
        ventilation_rate="high", has_gas_detection=True,
        release_grade="secondary",
    ) == "Non-hazardous"
