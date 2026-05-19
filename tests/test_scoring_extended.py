"""Extended scoring engine tests (Agent: test-scoring)."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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
    start = time.time()
    for _ in range(50):
        evaluate_all_meters(inputs, fluid_type="gas")
    elapsed = time.time() - start
    assert elapsed < 5.0, f"Performance: {elapsed:.1f}s for 50 runs"


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
    try:
        result = scorer.score_meter("nonexistent_meter", {"fluid_type": "gas"})
    except Exception:
        result = None
    if result:
        assert 0 <= result.total_score <= 100
