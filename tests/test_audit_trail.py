"""
Audit trail and data provenance tests (Phase E5).

Tests cover:
- Result dataclass provenance field and add_provenance() method
- Provenance merging across Result objects
- calc_gas_properties_result provenance
- calc_beta_ratio_result provenance
- calc_orifice_pressure_loss_result provenance
- recompute_uncertainty_result provenance
"""

import sys
import os

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)

import pytest
from metering_designer.core.result import Result


# ---------------------------------------------------------------------------
# Result dataclass provenance
# ---------------------------------------------------------------------------


def test_provenance_added():
    r = Result(data={"value": 42})
    r.add_provenance("test_func", {"a": 1}, "ISO 5167-2:2003")
    assert len(r.provenance) == 1
    p = r.provenance[0]
    assert p["function"] == "test_func"
    assert p["parameters"] == {"a": 1}
    assert p["standard_ref"] == "ISO 5167-2:2003"
    assert "timestamp" in p


def test_provenance_default_parameters():
    r = Result(data={"x": 1})
    r.add_provenance("no_params")
    p = r.provenance[0]
    assert p["function"] == "no_params"
    assert p["parameters"] == {}
    assert p["standard_ref"] == ""
    assert "timestamp" in p


def test_provenance_multiple_entries():
    r = Result(data={"x": 1})
    r.add_provenance("func_a", {"p": "a"})
    r.add_provenance("func_b", {"p": "b"})
    assert len(r.provenance) == 2
    assert r.provenance[0]["function"] == "func_a"
    assert r.provenance[1]["function"] == "func_b"


def test_provenance_merged():
    r1 = Result(data={"x": 1})
    r1.add_provenance("func1", {"p1": "v1"})
    r2 = Result(data={"y": 2})
    r2.add_provenance("func2", {"p2": "v2"})
    merged = r1.merge(r2)
    assert len(merged.provenance) == 2
    assert merged.provenance[0]["function"] == "func1"
    assert merged.provenance[1]["function"] == "func2"
    assert merged.data["x"] == 1
    assert merged.data["y"] == 2


def test_provenance_merge_errors_and_warnings():
    r1 = Result(errors=["err1"], warnings=["warn1"])
    r2 = Result(errors=["err2"], warnings=["warn2"])
    merged = r1.merge(r2)
    assert merged.errors == ["err1", "err2"]
    assert merged.warnings == ["warn1", "warn2"]
    assert merged.ok is False


def test_result_ok_property():
    r = Result(data={"x": 1})
    assert r.ok is True
    r.errors.append("something wrong")
    assert r.ok is False


def test_result_from_value():
    r = Result.from_value("key1", 42.0)
    assert r.data == {"key1": 42.0}
    assert r.ok is True


# ---------------------------------------------------------------------------
# calc_gas_properties_result provenance
# ---------------------------------------------------------------------------


def test_gas_properties_with_provenance():
    from metering_designer.fluids.gas import calc_gas_properties_result

    comp = {"C1": 0.9, "C2": 0.05, "C3": 0.02, "N2": 0.02, "CO2": 0.01}
    result = calc_gas_properties_result(comp, 40.0, 20.0)
    assert result.ok, f"Errors: {result.errors}"
    assert len(result.provenance) >= 1
    assert result.provenance[0]["function"] == "calc_gas_properties"
    assert (
        result.provenance[0]["standard_ref"]
        == "AGA 8:1994 (GERG-2008 extension)"
    )
    # Should have kappa and speed_of_sound in data
    assert "kappa" in result.data
    assert "speed_of_sound_ms" in result.data


def test_gas_properties_data_contents():
    from metering_designer.fluids.gas import calc_gas_properties_result

    comp = {"C1": 0.95, "N2": 0.03, "CO2": 0.02}
    result = calc_gas_properties_result(comp, 50.0, 25.0)
    assert result.ok
    d = result.data
    assert d.get("Z_oper", 0) > 0.5
    assert d.get("M_mix", 0) > 10
    assert d.get("rho_oper_kg_m3", 0) > 0
    assert d.get("kappa", 0) > 1.0
    assert d.get("backend_used", "") != ""


# ---------------------------------------------------------------------------
# calc_beta_ratio_result provenance
# ---------------------------------------------------------------------------


def test_orifice_with_provenance():
    from metering_designer.meters.orifice import calc_beta_ratio_result

    result = calc_beta_ratio_result(
        10.0, 100.0, 50.0, 1.2e-5, 25000, tap_type="flange"
    )
    assert result.ok, f"Errors: {result.errors}"
    assert len(result.provenance) >= 1
    p = result.provenance[0]
    assert p["function"] == "calc_beta_ratio"
    assert p["standard_ref"] == "ISO 5167-2:2003"


def test_orifice_beta_data():
    from metering_designer.meters.orifice import calc_beta_ratio_result

    result = calc_beta_ratio_result(10.0, 100.0, 50.0, 1.2e-5, 25000)
    assert result.ok
    d = result.data
    assert "beta" in d
    assert "Cd" in d
    assert "dp_orifice_Pa" in d
    assert 0.1 <= d["beta"] <= 0.75


# ---------------------------------------------------------------------------
# calc_orifice_pressure_loss_result provenance
# ---------------------------------------------------------------------------


def test_pressure_loss_with_provenance():
    from metering_designer.auxiliaries.pressure_loss import (
        calc_orifice_pressure_loss_result,
    )

    result = calc_orifice_pressure_loss_result(beta=0.5, dp_orifice_Pa=25000)
    assert result.ok, f"Errors: {result.errors}"
    assert len(result.provenance) >= 1
    assert result.provenance[0]["function"] == "calc_orifice_pressure_loss"
    assert result.provenance[0]["standard_ref"] == "ISO 5167-2:2003 §6.3"


def test_pressure_loss_data():
    from metering_designer.auxiliaries.pressure_loss import (
        calc_orifice_pressure_loss_result,
    )

    result = calc_orifice_pressure_loss_result(beta=0.6, dp_orifice_Pa=50000)
    assert result.ok
    d = result.data
    assert "dp_permanent_Pa" in d
    assert "dp_permanent_mbar" in d
    assert d["dp_permanent_Pa"] < d["dp_orifice_Pa"]  # loss < total dp


# ---------------------------------------------------------------------------
# recompute_uncertainty_result provenance
# ---------------------------------------------------------------------------


def test_uncertainty_with_provenance():
    from metering_designer.inspection.uncertainty_impact import (
        recompute_uncertainty_result,
    )

    result = recompute_uncertainty_result(1.0, 0.5)
    assert result.ok, f"Errors: {result.errors}"
    assert len(result.provenance) >= 1
    p = result.provenance[0]
    assert p["function"] == "recompute_uncertainty"
    assert p["standard_ref"] == "ISO 5168:2023 (GUM methodology)"
    assert "base_uncertainty_pct" in p["parameters"]
    assert "geometric_contribution_pct" in p["parameters"]


def test_uncertainty_data():
    from metering_designer.inspection.uncertainty_impact import (
        recompute_uncertainty_result,
    )

    result = recompute_uncertainty_result(1.0, 0.5)
    assert result.ok
    d = result.data
    assert "base_uncertainty_pct" in d
    assert "combined_uncertainty_pct" in d
    assert "expanded_k2_pct" in d
    assert d["combined_uncertainty_pct"] > d["base_uncertainty_pct"]


# ---------------------------------------------------------------------------
# calc_z_factor_result provenance
# ---------------------------------------------------------------------------


def test_backend_z_factor_with_provenance():
    from metering_designer.core.backends import calc_z_factor_result

    comp = {"C1": 0.9, "C2": 0.05, "C3": 0.02, "N2": 0.02, "CO2": 0.01}
    result = calc_z_factor_result(40.0, 20.0, comp)
    assert result.ok, f"Errors: {result.errors}"
    assert len(result.provenance) >= 1
    assert result.provenance[0]["function"] == "calc_z_factor"
    assert "AGA 8:1994" in result.provenance[0]["standard_ref"]
    assert "Z" in result.data
    assert 0.5 < result.data["Z"] < 1.5


# ---------------------------------------------------------------------------
# DATASET_VERSION in backends
# ---------------------------------------------------------------------------


def test_dataset_version():
    from metering_designer.core.backends import DATASET_VERSION

    assert DATASET_VERSION == "1.0"
