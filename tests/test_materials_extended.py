"""Extended materials tests (Agent: test-materials)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from metering_designer.piping.wall_thickness import calc_min_wall_thickness, calc_flange_min_class
from metering_designer.piping.materials import select_material
from metering_designer.piping.schedule import recommend_schedule
from metering_designer.safety.ex_classification import classify_ex, _detect_t_class_from_composition


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


def test_api5l_temp_derating(all_api5l_grades):
    pipe_ambient = calc_min_wall_thickness(50, 40, 273.1, "API_5L_X65")
    pipe_hot = calc_min_wall_thickness(50, 350, 273.1, "API_5L_X65")
    if "error" not in pipe_hot:
        assert pipe_hot["allowable_stress_MPa"] < pipe_ambient["allowable_stress_MPa"]


def test_material_temp_limit():
    pipe = calc_min_wall_thickness(50, 500, 219.1, "A106_GrB")
    assert "error" in pipe


def test_material_burst_pressure():
    pipe = calc_min_wall_thickness(70, 60, 273.1, "API_5L_X65")
    if "error" not in pipe:
        bp = pipe.get("burst_pressure_bar", 0)
        assert bp > 70  # burst > design pressure


def test_flange_class_70bar_cs():
    flange = calc_flange_min_class(70, 60, "carbon_steel")
    assert "error" not in flange
    assert flange["flange_class"] >= 300


def test_schedule_nps10():
    s = recommend_schedule(10, 11.5)
    assert s.get("recommended") is not None
    assert "SCH 80" in s["recommended"]["schedule_name"]


def test_ex_t_class_auto():
    comp = {"C1": 0.85, "nC5": 0.05, "C6": 0.03, "N2": 0.04, "CO2": 0.03}
    t_class = _detect_t_class_from_composition(comp)
    assert t_class in ("T1", "T2", "T3")


def test_ex_methane_only():
    t_class = _detect_t_class_from_composition({"C1": 1.0})
    assert t_class == "T1"


def test_ex_with_h2s():
    t_class = _detect_t_class_from_composition({"C1": 0.90, "H2S": 0.05, "N2": 0.05})
    assert t_class in ("T2", "T3")
