"""Deep meter sizing tests (Agent: test-sizing)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from metering_designer.meters.orifice import size_orifice_for_flow
from metering_designer.meters.ultrasonic import size_ultrasonic
from metering_designer.meters.turbine import size_turbine
from metering_designer.meters.coriolis import size_coriolis
from metering_designer.meters.pd_meter import size_pd_meter
from metering_designer.meters.vortex import size_vortex
from metering_designer.meters.vcone import size_v_cone
from metering_designer.auxiliaries.erosional_velocity import check_erosional_velocity


def test_orifice_beta_bounds():
    o = size_orifice_for_flow(50000, 10000, 200, 45, 40, 35, 1.5e-6, 0.9, 0.75)
    assert 0.1 <= o["beta"] <= 0.75


def test_orifice_cd_positive():
    o = size_orifice_for_flow(30000, 5000, 150, 30, 30, 20, 1e-5, 0.95, 0.7)
    assert o["Cd"] > 0.5


def test_usm_velocity_in_range():
    u = size_ultrasonic(10, 80000, 10000, 55, 45, 45, 1.5e-6, 0.75)
    assert 0.3 <= u["v_max_ms"] <= 35


def test_usm_path_config():
    u4 = size_ultrasonic(6, 30000, 5000, 40, 35, 30, 1.5e-6, 0.75)
    assert u4["recommended_paths"] >= 2
    u10 = size_ultrasonic(10, 80000, 10000, 55, 45, 45, 1.5e-6, 0.75)
    assert u10["recommended_paths"] >= 4


def test_turbine_k_factor():
    t = size_turbine(8, 30000, 5000, 40, 35, 30, 1.5e-6, 0.75)
    assert t["K_factor_pulses_per_m3"] > 0


def test_turbine_bearing_life_positive():
    t = size_turbine(8, 30000, 5000, 40, 35, 30, 1.5e-6, 0.75)
    assert t["estimated_bearing_life_h"] > 1000


def test_coriolis_size_within_range():
    c = size_coriolis(6, 30000, 10000, 40, 35, 35, 1.5e-6, 0.75)
    assert 0.5 <= c["meter_size_inches"] <= 12


def test_pd_meter_slip_realistic():
    pd = size_pd_meter(8, 200, 50, 850, 12, 30, 35)
    assert 0 <= pd["slip_pct_at_qmax"] <= 10


def test_vortex_frequency_min():
    vx = size_vortex(6, 15000, 3000, 40, 35, 30, 1.5e-6, 0.75, True)
    assert vx["f_max_hz"] > 0


def test_vcone_beta_bounds():
    vc = size_v_cone(8, 50000, 5000, 45, 40, 35, 1.5e-6, 0.75)
    assert 0.45 <= vc["beta"] <= 0.85


def test_erosional_velocity_check():
    e = check_erosional_velocity(10, 50)
    assert e["v_erosional_m_s"] > 0
    assert isinstance(e["ok"], bool)
    # Very fast flow in light gas should trigger warning
    e2 = check_erosional_velocity(100, 5)
    assert e2["ok"] == False or "warning" in e2
