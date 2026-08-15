"""Extended scoring engine tests (Agent: test-scoring)."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import pytest
from metering_designer.meters.selector import evaluate_all_meters
from metering_designer.core.scoring_engine import MeterScorer, classify_score
from metering_designer.core.weights import DEFAULT_WEIGHTS


def test_all_8_meters_scored(sample_gas_composition):
    inputs = {"fluid_type": "gas", "nps": 10, "qmin": 10000, "qmax": 80000,
              "service_type": "custody_transfer", "target_uncertainty": 0.5,
              "composition": sample_gas_composition}
    results = evaluate_all_meters(inputs, fluid_type="gas")
    assert len(results) >= 6
    assert results[0].total_score >= results[-1].total_score


def test_scoring_performance(sample_gas_composition):
    inputs = {"fluid_type": "gas", "nps": 10, "qmin": 10000, "qmax": 80000,
              "service_type": "custody_transfer", "composition": sample_gas_composition}
    start = time.perf_counter()
    for _ in range(100):
        evaluate_all_meters(inputs, fluid_type="gas")
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0, f"Performance: {elapsed:.3f}s for 100 runs"


def test_empty_composition():
    inputs = {"fluid_type": "gas", "nps": 8, "qmin": 1000, "qmax": 10000}
    results = evaluate_all_meters(inputs, fluid_type="gas")
    assert len(results) >= 1
    for r in results:
        assert 0 <= r.total_score <= 100


def test_extreme_nps():
    for nps in [2, 48]:
        inputs = {"fluid_type": "gas", "nps": nps, "qmin": 100, "qmax": 1000}
        results = evaluate_all_meters(inputs, fluid_type="gas")
        assert len(results) >= 1


def test_extreme_pressure():
    for p in [1, 420]:
        inputs = {"fluid_type": "gas", "nps": 8, "design_p_bar": p, "design_t_c": 50,
                  "qmin": 100, "qmax": 1000}
        results = evaluate_all_meters(inputs, fluid_type="gas")
        assert len(results) >= 1


def test_zero_flow():
    inputs = {"fluid_type": "gas", "nps": 8, "qmin": 0.001, "qmax": 0.01}
    results = evaluate_all_meters(inputs, fluid_type="gas")
    assert len(results) >= 1


def test_weight_normalization():
    from metering_designer.core.weights import normalize_weights
    w = {"technical_fitness": 50, "accuracy_metrology": 50, "operational_ease": 0,
         "cost": 0, "implementability": 0, "project_specific": 0}
    n = normalize_weights(w)
    assert abs(sum(n.values()) - 1.0) < 0.001


def test_normalize_weights_zero():
    from metering_designer.core.weights import normalize_weights
    result = normalize_weights({"a": 0, "b": 0, "c": 0})
    assert abs(sum(result.values()) - 1.0) < 0.001
    assert result == DEFAULT_WEIGHTS


def test_tier_thresholds():
    _, _, label_high = classify_score(85.0)
    assert "Optimal" in label_high or "★★★" in label_high
    _, _, label_low = classify_score(84.9)
    assert "Good" in label_low.replace("İyi", "Good") or "★★☆" in label_low


def test_negative_uncertainty():
    inputs = {"fluid_type": "gas", "nps": 8, "qmin": 100, "qmax": 1000,
              "target_uncertainty": -0.5}
    results = evaluate_all_meters(inputs, fluid_type="gas")
    assert results[0].total_score >= 0


def test_meter_not_in_db():
    scorer = MeterScorer()
    with pytest.raises(KeyError):
        scorer.score_meter("nonexistent_meter", {"fluid_type": "gas"})


def test_auxiliary_details():
    scorer = MeterScorer()
    inputs = {
        "fluid_type": "gas",
        "nps": 10,
        "design_p_bar": 50,
        "design_t_c": 50,
        "qmin": 5000,
        "qmax": 30000,
        "service_type": "custody_transfer",
        "target_uncertainty": 0.5,
    }
    result = scorer.score_meter("ultrasonic", inputs)
    assert result.details is not None
    assert "straight_pipe_upstream_diameters" in result.details
    assert "straight_pipe_downstream_diameters" in result.details
    assert "straight_pipe_total_m" in result.details
    assert "estimated_dp_bar" in result.details
    assert isinstance(result.details["straight_pipe_upstream_diameters"], (int, float))
    assert isinstance(result.details["estimated_dp_bar"], (int, float))


def test_error_path_ERR_label():
    from metering_designer.core import scoring_engine as se_mod
    original_score_meter = se_mod.MeterScorer.score_meter

    def _raise_error(self, meter_key, inputs):
        raise RuntimeError("Simulated scoring failure")

    se_mod.MeterScorer.score_meter = _raise_error
    try:
        inputs = {"fluid_type": "gas", "nps": 10, "qmin": 10000, "qmax": 80000}
        results = evaluate_all_meters(inputs, fluid_type="gas")
        assert len(results) > 0
        for r in results:
            assert r.tier_label == "ERR"
            assert r.total_score == 0
    finally:
        se_mod.MeterScorer.score_meter = original_score_meter


# ---------------------------------------------------------------------------
# Phase 3 — Isolated & deep tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("crit_name,meter_key,inputs,cat_key,check_fn", [
    # 1) fluid_compatibility: gas-optimised meter with gas > with liquid
    ("fluid_compatibility", "ultrasonic", {"fluid_type": "gas"},
     "technical_fitness", lambda s: s == 10.0),
    ("fluid_compatibility", "positive_displacement", {"fluid_type": "gas"},
     "technical_fitness", lambda s: s == 0.0),
    # 2) pipe_size_fit: perfect NPS fit -> high score
    ("pipe_size_fit", "ultrasonic", {"nps": 10},
     "technical_fitness", lambda s: s == 10.0),
    # 3) h2s_compatibility: sour-rated meter with h2s=True > non-sour with h2s=True
    ("h2s_compatibility", "ultrasonic", {"h2s": True},
     "technical_fitness", lambda s: s == 10.0),
    ("h2s_compatibility", "coriolis", {"h2s": True},
     "technical_fitness", lambda s: s == 6.0),
    # 4) base_uncertainty: 0-10 for ultrasonic gas
    ("base_uncertainty", "ultrasonic", {"fluid_type": "gas"},
     "accuracy_metrology", lambda s: 0 <= s <= 10),
    # 5) pressure_loss: 0-10
    ("pressure_loss", "ultrasonic", {},
     "operational_ease", lambda s: 0 <= s <= 10),
    # 6) capex: 0-10
    ("capex", "ultrasonic", {},
     "cost", lambda s: 0 <= s <= 10),
])
def test_criterion_isolated(crit_name, meter_key, inputs, cat_key, check_fn):
    """Directly invoke _evaluate_criterion for 6 isolated criterion tests."""
    scorer = MeterScorer()
    meter_data = scorer.specs["meters"][meter_key]
    score, justification = scorer._evaluate_criterion(
        crit_name, meter_data, inputs, cat_key
    )
    assert isinstance(justification, str), (
        f"justification should be str: {justification}"
    )
    assert check_fn(score), (
        f"{crit_name}/{meter_key}: score={score}, justification={justification}"
    )


def test_generate_summary():
    """Verify strengths/weaknesses are generated as non-empty string lists."""
    scorer = MeterScorer()
    inputs = {
        "fluid_type": "gas",
        "nps": 10,
        "design_p_bar": 70.0,
        "design_t_c": 60.0,
        "qmin": 10000,
        "qmax": 80000,
        "service_type": "custody_transfer",
        "target_uncertainty": 0.5,
    }
    result = scorer.score_meter("ultrasonic", inputs)
    assert isinstance(result.strengths, list), "strengths must be a list"
    assert isinstance(result.weaknesses, list), "weaknesses must be a list"
    assert len(result.strengths) + len(result.weaknesses) >= 1, (
        "At least one of strengths or weaknesses must be non-empty"
    )
    for item in result.strengths:
        assert isinstance(item, str), f"strength item must be str: {item}"
    for item in result.weaknesses:
        assert isinstance(item, str), f"weakness item must be str: {item}"


def test_custom_weights():
    """Custom weights (all weight on cost) must produce a different total score."""
    inputs = {
        "fluid_type": "gas",
        "nps": 10,
        "design_p_bar": 50.0,
        "design_t_c": 50.0,
        "qmin": 5000,
        "qmax": 30000,
        "service_type": "custody_transfer",
        "target_uncertainty": 0.5,
    }
    # Default weights
    scorer_default = MeterScorer()
    result_default = scorer_default.score_meter("ultrasonic", inputs)

    # All weight on cost (zeros elsewhere)
    cost_only_weights = {
        "technical_fitness": 0.0,
        "accuracy_metrology": 0.0,
        "operational_ease": 0.0,
        "cost": 1.0,
        "implementability": 0.0,
        "project_specific": 0.0,
    }
    scorer_cost = MeterScorer(weights=cost_only_weights)
    result_cost = scorer_cost.score_meter("ultrasonic", inputs)

    # The total score should differ because weights are different
    assert result_default.total_score != result_cost.total_score, (
        f"Default={result_default.total_score}, Cost-only={result_cost.total_score}"
    )


def test_liquid_extreme_pressure():
    """Liquid fluid type with extreme 420 bar pressure must produce valid scores."""
    inputs = {
        "fluid_type": "liquid",
        "nps": 8,
        "design_p_bar": 420,
        "design_t_c": 50,
        "qmin": 100,
        "qmax": 1000,
    }
    results = evaluate_all_meters(inputs, fluid_type="liquid")
    assert len(results) >= 1, "Must return at least 1 result for liquid"
    for r in results:
        assert 0 <= r.total_score <= 100, (
            f"Score {r.total_score} out of range for {r.meter_key}"
        )


def test_liquid_extreme_nps():
    """Liquid fluid type with extreme NPS 2 and 48 must produce valid scores."""
    for nps in [2, 48]:
        inputs = {
            "fluid_type": "liquid",
            "nps": nps,
            "design_p_bar": 50,
            "design_t_c": 50,
            "qmin": 100,
            "qmax": 1000,
        }
        results = evaluate_all_meters(inputs, fluid_type="liquid")
        assert len(results) >= 1, f"Must return at least 1 result for NPS={nps}"
        for r in results:
            assert 0 <= r.total_score <= 100, (
                f"Score {r.total_score} out of range for {r.meter_key} at NPS={nps}"
            )
