"""Deep meter sizing tests (Agent: test-sizing)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import pytest
from metering_designer.meters.orifice import size_orifice_for_flow
from metering_designer.meters.ultrasonic import size_ultrasonic
from metering_designer.meters.turbine import size_turbine
from metering_designer.meters.coriolis import size_coriolis
from metering_designer.meters.pd_meter import size_pd_meter
from metering_designer.meters.vortex import size_vortex
from metering_designer.meters.vcone import size_v_cone, size_venturi
from metering_designer.auxiliaries.erosional_velocity import check_erosional_velocity


def test_orifice_beta_bounds():
    o = size_orifice_for_flow(50000, 10000, 200, 45, 40, 35, 1.5e-6, 0.9, 0.75)
    assert 0.1 <= o["beta"] <= 0.75


def test_orifice_cd_positive():
    o = size_orifice_for_flow(30000, 5000, 150, 30, 30, 20, 1e-5, 0.95, 0.7)
    assert o["Cd"] > 0.5


def test_usm_velocity_in_range():
    u = size_ultrasonic(10, 80000, 10000, 55, 45, 45, 1.5e-6, 0.75)
    assert 0.3 <= u["v_max_ms"] <= 30
    assert isinstance(u["velocity_ok"], bool)


def test_usm_path_config():
    u4 = size_ultrasonic(6, 30000, 5000, 40, 35, 30, 1.5e-6, 0.75)
    assert u4["recommended_paths"] >= 2
    u10 = size_ultrasonic(10, 80000, 10000, 55, 45, 45, 1.5e-6, 0.75)
    assert u10["recommended_paths"] >= 4


def test_turbine_k_factor_and_bearing():
    t = size_turbine(8, 30000, 5000, 40, 35, 30, 1.5e-6, 0.75)
    assert t["K_factor_pulses_per_m3"] > 0
    assert t["estimated_bearing_life_h"] > 10000


def test_coriolis_size_within_range():
    c = size_coriolis(6, 30000, 10000, 40, 35, 35, 1.5e-6, 0.75)
    assert 0.5 <= c["meter_size_inches"] <= 12
    # Tight check: zero drift effect at Qmin must be under 5%
    c2 = size_coriolis(4, 5000, 500, 30, 30, 20, 1.5e-6, 0.75)
    assert "zero_effect_at_qmin_pct" in c2
    assert c2["zero_effect_at_qmin_pct"] < 5.0


def test_pd_meter_slip_realistic():
    pd = size_pd_meter(8, 200, 50, 850, 12, 30, 35)
    assert 0 <= pd["slip_pct_at_qmax"] <= 10


def test_vortex_frequency_min():
    vx = size_vortex(6, 15000, 3000, 40, 35, 30, 1.5e-6, 0.75, True)
    assert vx["f_max_hz"] > 0


def test_vcone_beta_bounds():
    vc = size_v_cone(8, 50000, 5000, 45, 40, 35, 1.5e-6, 0.75)
    assert 0.45 <= vc["beta"] <= 0.85


def test_vcone_cone_diameter_is_physical():
    """Reported cone diameter must be D·√(1−β²), not the β·D 'equivalent'."""
    vc = size_v_cone(8, 50000, 5000, 45, 40, 35, 1.5e-6, 0.75)
    id_mm = vc["id_mm"]
    beta = vc["beta"]
    expected = id_mm * (1 - beta ** 2) ** 0.5
    assert vc["d_cone_mm"] == pytest.approx(expected, rel=0.001)
    # And the annulus area A_pipe·β² is used for Δp, so β·D would be smaller.
    assert vc["d_cone_mm"] < id_mm


def test_erosional_velocity_check():
    e = check_erosional_velocity(10, 50)
    assert e["v_erosional_m_s"] > 0
    assert isinstance(e["ok"], bool)
    # Very fast flow in light gas should trigger warning
    e2 = check_erosional_velocity(100, 5)
    assert e2["ok"] is False or "warning" in e2


def test_venturi_basic_sizing():
    """Classical Venturi basic sizing with typical gas parameters."""
    v = size_venturi(
        nps=8, q_max_Sm3h=50000, q_min_Sm3h=5000,
        P_oper_bar=35, T_oper_C=40,
        rho_kg_m3=25, mu_Pa_s=1.5e-6, rho_std_kg_m3=0.75,
    )
    assert isinstance(v, dict)
    assert v["Cd"] >= 0.98
    assert v["beta"] > 0
    assert v["dp_mbar"] > 0
    assert v["meter_type"] == "Venturi (klasik)"
    assert v["Re_ok"] is True or isinstance(v["Re_ok"], bool)
    assert v["turndown_ok"] is True or isinstance(v["turndown_ok"], bool)


def test_venturi_cd_near_0995():
    """Classical Venturi Cd must be ≈ 0.995 per ISO 5167-4."""
    v = size_venturi(
        nps=8, q_max_Sm3h=50000, q_min_Sm3h=5000,
        P_oper_bar=35, T_oper_C=40,
        rho_kg_m3=25, mu_Pa_s=1.5e-6, rho_std_kg_m3=0.75,
    )
    assert 0.98 <= v["Cd"] <= 1.0
    # Cd should be very close to 0.995
    assert abs(v["Cd"] - 0.995) < 0.02


def test_venturi_eps_iso5167_formula():
    """Venturi expansibility uses the ISO 5167-1 ε formula with real p1."""
    v = size_venturi(
        nps=8, q_max_Sm3h=50000, q_min_Sm3h=5000,
        P_oper_bar=35, T_oper_C=40,
        rho_kg_m3=25, mu_Pa_s=1.5e-6, rho_std_kg_m3=0.75,
    )
    # At 35 bar (35e5 Pa) with Δp ≈ 250 mbar, ε ≈ 0.997–1.0
    assert 0.990 < v["eps"] <= 1.0
    # Low-pressure venturi must show a measurably lower ε
    v_low = size_venturi(
        nps=8, q_max_Sm3h=50000, q_min_Sm3h=5000,
        P_oper_bar=2.5, T_oper_C=40,
        rho_kg_m3=5, mu_Pa_s=1.5e-6, rho_std_kg_m3=0.75,
    )
    assert v_low["eps"] < v["eps"]


def test_venturi_dp_scales_with_flow():
    """Venturi is sized to ~250 mbar at Qmax; higher flow ⇒ bigger β, same Δp."""
    small = size_venturi(8, 20000, 2000, 35, 40, 25, 1.5e-6, 0.75)
    big = size_venturi(8, 60000, 6000, 35, 40, 25, 1.5e-6, 0.75)
    # Fixed design Δp means the throat (β) must grow with flow.
    assert big["beta"] > small["beta"]
    for v in (small, big):
        assert v["dp_mbar"] == pytest.approx(250.0, rel=0.15)
        assert v["dp_perm_mbar"] == pytest.approx(v["dp_mbar"] * 0.15, rel=0.01)


def test_venturi_edge_cases():
    """Classical Venturi handles small (NPS 4) and large (NPS 16) pipes."""
    # Small pipe
    v_small = size_venturi(
        nps=4, q_max_Sm3h=5000, q_min_Sm3h=500,
        P_oper_bar=20, T_oper_C=30,
        rho_kg_m3=15, mu_Pa_s=1.5e-6, rho_std_kg_m3=0.75,
    )
    assert isinstance(v_small, dict)
    assert v_small["beta"] > 0
    assert v_small["d_throat_mm"] > 0
    assert v_small["dp_mbar"] > 0

    # Large pipe
    v_large = size_venturi(
        nps=16, q_max_Sm3h=200000, q_min_Sm3h=20000,
        P_oper_bar=50, T_oper_C=50,
        rho_kg_m3=35, mu_Pa_s=1.5e-6, rho_std_kg_m3=0.75,
    )
    assert isinstance(v_large, dict)
    assert v_large["beta"] > 0
    assert v_large["d_throat_mm"] > 0
    assert v_large["dp_mbar"] > 0
    assert v_large["nps"] == 16


def test_vortex_liquid_mode():
    """Vortex meter in liquid mode: lower velocity limit, tighter turndown."""
    vx = size_vortex(
        nps=6, q_max_Sm3h=200, q_min_Sm3h=20,
        P_oper_bar=10, T_oper_C=25,
        rho_kg_m3=850, mu_Pa_s=0.001, rho_std_kg_m3=850,
        is_gas=False,
    )
    assert vx["v_max_ms"] <= 9
    assert isinstance(vx["turndown_ok"], bool)
    assert isinstance(vx["frequency_ok"], bool)
    assert vx["turndown_max"] == 10


def test_orifice_re_warning():
    """Orifice sizing with very low flow checks Re_valid key exists as bool."""
    o = size_orifice_for_flow(
        q_max_Sm3h=100, q_min_Sm3h=10,
        D_mm=50,
        P_oper_bar=20, T_oper_C=25,
        rho_kg_m3=15, mu_Pa_s=1.5e-6,
        Z=0.9, rho_std_kg_m3=0.75,
    )
    assert "Re_valid" in o
    assert isinstance(o["Re_valid"], bool)


def test_vcone_liquid_mode():
    """V-Cone meter in liquid mode: expansibility = 1, beta in 0.45-0.85."""
    vc = size_v_cone(
        nps=8, q_max_Sm3h=500, q_min_Sm3h=50,
        P_oper_bar=10, T_oper_C=25,
        rho_kg_m3=850, mu_Pa_s=0.001,
        rho_std_kg_m3=850,
        is_gas=False,
    )
    assert vc["eps"] == 1.0
    assert 0.45 <= vc["beta"] <= 0.85
    assert vc["dp_mbar"] > 0
    assert vc["meter_type"] == "V-Cone"


def test_coriolis_edge_cases():
    """Coriolis handles edge cases: small NPS + high flow, large NPS + low flow, extreme viscosity."""
    # Small NPS (2) with very high flow
    c_small = size_coriolis(
        nps=2, q_max_Sm3h=30000, q_min_Sm3h=1000,
        P_oper_bar=40, T_oper_C=35,
        rho_kg_m3=35, mu_Pa_s=1.5e-6, rho_std_kg_m3=0.75,
    )
    assert 0.5 <= c_small["meter_size_inches"] <= 12

    # Large NPS (12) with low flow
    c_large = size_coriolis(
        nps=12, q_max_Sm3h=200, q_min_Sm3h=20,
        P_oper_bar=20, T_oper_C=30,
        rho_kg_m3=25, mu_Pa_s=1.5e-6, rho_std_kg_m3=0.75,
    )
    assert 0.5 <= c_large["meter_size_inches"] <= 12

    # Extreme viscosity (100 cP = 0.1 Pa·s)
    c_visc = size_coriolis(
        nps=6, q_max_Sm3h=10000, q_min_Sm3h=1000,
        P_oper_bar=30, T_oper_C=30,
        rho_kg_m3=30, mu_Pa_s=0.1, rho_std_kg_m3=0.75,
    )
    assert 0.5 <= c_visc["meter_size_inches"] <= 12
    assert isinstance(c_visc["viscosity_effect"], str)


def test_erosional_intermittent():
    """Erosional velocity: intermittent service C=152.5 gives higher threshold than continuous C=122 (SI units)."""
    e_int = check_erosional_velocity(10, 50, service_type="intermittent")
    assert e_int["v_erosional_m_s"] > 0
    assert isinstance(e_int["ok"], bool)
    assert e_int["C_factor"] == 152.5

    # Compare with continuous: intermittent should have higher threshold
    e_cont = check_erosional_velocity(10, 50, service_type="continuous")
    assert e_cont["C_factor"] == 122
    assert e_int["v_erosional_m_s"] > e_cont["v_erosional_m_s"]


def test_orifice_dp_converges_to_target():
    """Orifice sizing must converge: achievable ΔP ≈ requested ΔP in a normal design."""
    from metering_designer.piping import pipe_id_mm
    D = pipe_id_mm(4)
    for dp in (250, 500, 1000):
        r = size_orifice_for_flow(15000, 1500, D, 41.0, 40, 40, 1.5e-5, 0.9, 0.75,
                                  standard="iso5167_2", dp_design_mbar=dp)
        assert r["dp_attainable"] is True, f"dp={dp}: expected attainable"
        assert r["dp_at_qmax_mbar"] == pytest.approx(dp, abs=3), \
            f"dp={dp}: achievable {r['dp_at_qmax_mbar']} != target"


def test_orifice_beta_moves_with_dp_when_attainable():
    """Higher target ΔP → smaller β (physical, in a non-saturated design)."""
    from metering_designer.piping import pipe_id_mm
    D = pipe_id_mm(4)
    r250 = size_orifice_for_flow(15000, 1500, D, 41.0, 40, 40, 1.5e-5, 0.9, 0.75,
                                 standard="iso5167_2", dp_design_mbar=250)
    r1000 = size_orifice_for_flow(15000, 1500, D, 41.0, 40, 40, 1.5e-5, 0.9, 0.75,
                                  standard="iso5167_2", dp_design_mbar=1000)
    assert r250["dp_attainable"] and r1000["dp_attainable"]
    assert r1000["beta"] < r250["beta"], "β must shrink as ΔP target grows"


def test_orifice_dp_saturation_reported():
    """When the target ΔP is unachievable within β limits, the result must say so
    and report the achievable ΔP instead of echoing the target."""
    from metering_designer.piping import pipe_id_mm
    D = pipe_id_mm(3)
    r = size_orifice_for_flow(30000, 3000, D, 41.0, 40, 40, 1.5e-5, 0.9, 0.75,
                              standard="iso5167_2", dp_design_mbar=250)
    assert r["beta_saturated"] is True
    assert r["saturation_dir"] == "low"
    assert r["dp_attainable"] is False
    assert r["beta"] == 0.75  # pinned at the upper standard limit
    assert r["dp_at_qmax_mbar"] != 250, "must not echo an unachievable target"
    assert r["dp_at_qmax_mbar"] > 250, "pinned-upper-β plate produces MORE ΔP than the low target"
    assert r["dp_actual_mbar"] == pytest.approx(r["dp_at_qmax_mbar"], rel=0.02)


def test_orifice_dp_saturation_sweep_constant_beta():
    """Sweeping ΔP in a saturated design leaves β/d/Cd pinned but flags it."""
    from metering_designer.piping import pipe_id_mm
    D = pipe_id_mm(3)
    betas = set()
    attainable_any = False
    for dp in (100, 250, 500, 1000):
        r = size_orifice_for_flow(30000, 3000, D, 41.0, 40, 40, 1.5e-5, 0.9, 0.75,
                                  standard="iso5167_2", dp_design_mbar=dp)
        betas.add(round(r["beta"], 4))
        if r["dp_attainable"]:
            attainable_any = True
    assert betas == {0.75}, f"β must stay pinned at 0.75, got {betas}"
    assert attainable_any is False, "no ΔP in the sweep may be attainable"


def test_orifice_dp_not_attainable_advisory():
    """The saturation state must surface as a design advisory."""
    from metering_designer.meters.orifice import generate_design_advisories
    adv = generate_design_advisories(0.75, 13.3, 250, dp_attainable=False, dp_actual_mbar=1332)
    keys = [a["key"] for a in adv]
    assert "std_adv_dp_not_attainable" in keys
    msg = next(a for a in adv if a["key"] == "std_adv_dp_not_attainable")
    assert msg["values"]["target"] == 250
    assert msg["values"]["actual"] == 1332
