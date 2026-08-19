"""Cross-validation regression tests derived from the 15-scenario calc audit.

Locks in the physical-correctness findings: ideal-gas density law, Z bounds,
Wobbe ordering, speed of sound, orifice round-trip / saturation / DP-beta
monotonicity, Venturi permanent loss, erosional C factors, pipe-ID monotonicity.
(Agent: test-sizing / test-backend.)
"""
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import pytest
from metering_designer.fluids import gas
from metering_designer.meters.orifice import size_orifice_for_flow
from metering_designer.meters.vcone import size_venturi
from metering_designer.auxiliaries.erosional_velocity import check_erosional_velocity
from metering_designer.piping import pipe_id_mm

R = 8.314462618
PIPELINE = {"C1": 0.9137, "C2": 0.0406, "C3": 0.0152, "N2": 0.0102, "CO2": 0.0203}
RICH = {"C1": 0.80, "C2": 0.09, "C3": 0.05, "iC4": 0.01, "nC4": 0.01, "N2": 0.02, "CO2": 0.02}
LEAN = {"C1": 0.97, "C2": 0.01, "N2": 0.02}


def _get_z(res):
    return res.get("Z_oper") or res.get("Z") or res.get("z_factor")


def test_gas_density_matches_ideal_gas_law():
    """rho = P_abs * M / (Z*R*T); calc_gas_properties treats P_oper_bar as ABSOLUTE."""
    gp = gas.calc_gas_properties(PIPELINE, P_oper_bar=45.0, T_oper_C=20.0)
    rho, z, M = gp["rho_oper_kg_m3"], _get_z(gp), gp["M_mix"]
    rho_ind = 45.0e5 * (M / 1000.0) / (z * R * (20 + 273.15))
    assert abs(100.0 * (rho - rho_ind) / rho_ind) <= 2.0


def test_gas_z_low_pressure_near_unity():
    gp = gas.calc_gas_properties(PIPELINE, P_oper_bar=1.01325, T_oper_C=20.0)
    assert 0.985 <= _get_z(gp) <= 1.0


def test_gas_z_high_pressure_physical_band():
    gp = gas.calc_gas_properties(PIPELINE, P_oper_bar=45.0, T_oper_C=20.0)
    assert 0.80 < _get_z(gp) < 0.97


def test_wobbe_rich_gas_higher():
    wr = gas.calc_gas_properties(RICH, 30, 15)["Wobbe_MJ_m3"]
    wl = gas.calc_gas_properties(LEAN, 30, 15)["Wobbe_MJ_m3"]
    assert 30 < wr < 60
    assert wr > wl


def test_speed_of_sound_methane_sane():
    sos = gas.calc_speed_of_sound(15 + 273.15, 16.043, 1.30, 0.678, Z=1.0)
    assert 380 <= sos <= 470


def test_orifice_round_trip_mass_flow():
    """Sized d + actual dp must reproduce the input q_max via ISO 5167 flow eq."""
    o = size_orifice_for_flow(30000, 3000, pipe_id_mm(6), 45, 40, 38, 1.5e-5, 0.85, 0.75,
                              standard="iso5167_2", dp_design_mbar=250)
    d_m, beta, Cd = o["d_mm"] / 1000.0, o["beta"], o["Cd"]
    dp = (o["dp_at_qmax_mbar"] or o["dp_actual_mbar"]) * 100.0
    qm = Cd / math.sqrt(1 - beta**4) * math.pi / 4 * d_m**2 * math.sqrt(2 * 38.0 * dp)
    qm_expected = 38.0 * (30000 / 3600.0) * (0.75 / 38.0)
    assert abs(100.0 * (qm - qm_expected) / qm_expected) <= 2.0


def test_orifice_saturation_reports_actual_dp():
    o = size_orifice_for_flow(30000, 3000, pipe_id_mm(3), 41, 40, 40, 1.5e-5, 0.9, 0.75,
                              standard="iso5167_2", dp_design_mbar=250)
    assert o["beta_saturated"] is True
    assert o["dp_attainable"] is False
    assert abs(o["beta"] - 0.75) < 0.001
    assert (o["dp_at_qmax_mbar"] or o["dp_actual_mbar"]) != 250


def test_orifice_dp_beta_monotonic():
    b250 = size_orifice_for_flow(20000, 2000, pipe_id_mm(6), 45, 40, 38, 1.5e-5, 0.85, 0.75,
                                 standard="iso5167_2", dp_design_mbar=250)["beta"]
    b1000 = size_orifice_for_flow(20000, 2000, pipe_id_mm(6), 45, 40, 38, 1.5e-5, 0.85, 0.75,
                                  standard="iso5167_2", dp_design_mbar=1000)["beta"]
    assert b1000 < b250


def test_venturi_permanent_loss_about_15pct():
    ve = size_venturi(8, 80000, 8000, 55, 45, 45, 1.5e-6, 0.75)
    perm_pct = 100.0 * ve["dp_perm_mbar"] / ve["dp_mbar"]
    assert abs(perm_pct - 15.0) <= 2.0


def test_erosional_velocity_c_factors():
    er = check_erosional_velocity(12.0, 45, service_type="continuous")
    er2 = check_erosional_velocity(30.0, 45, service_type="intermittent")
    assert er["C_factor"] == 122 and er["ok"] is True
    assert er2["C_factor"] == 152.5 and er2["C_factor"] > er["C_factor"]
    # unphysical high velocity must be rejected
    assert check_erosional_velocity(400.0, 45, service_type="continuous")["ok"] is False


def test_pipe_id_monotonic():
    ids = {n: pipe_id_mm(n) for n in (3, 4, 6, 8, 10)}
    order = sorted(ids)
    for i in range(len(order) - 1):
        assert ids[order[i]] < ids[order[i + 1]]
    assert 0.7 * 25.4 * 6 < ids[6] < 0.95 * 25.4 * 7


def test_coriolis_zero_stability_scales_with_size():
    """Zero stability must scale with meter capacity (not a fixed constant)."""
    from metering_designer.meters.coriolis import size_coriolis
    small = size_coriolis(2, 500, 50, 30, 30, 20, 1.5e-6, 0.75)
    large = size_coriolis(6, 40000, 5000, 30, 30, 20, 1.5e-6, 0.75)
    assert large["zero_stability_kg_s"] > small["zero_stability_kg_s"]
    # borderline case from audit (1.5", qmin 500 Sm3/h) now comfortably under 5%
    case = size_coriolis(4, 5000, 500, 30, 30, 20, 1.5e-6, 0.75)
    assert case["zero_effect_at_qmin_pct"] < 5.0
    assert case["zero_effect_at_qmin_pct"] > 0


def test_coriolis_oversized_meter_flags_qmin():
    """A large meter with a tiny Qmin must be flagged via the %5 threshold."""
    from metering_designer.meters.coriolis import size_coriolis
    big = size_coriolis(8, 40000, 40, 30, 30, 20, 1.5e-6, 0.75)
    assert big["zero_effect_at_qmin_pct"] > 5.0
    assert "Sıfır kayması %5 aştı" in big["notes"]