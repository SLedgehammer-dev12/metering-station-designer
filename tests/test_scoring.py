"""Basic scoring engine sanity tests"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from metering_designer.core.scoring_engine import MeterScorer, classify_score


def test_classify_score():
    tier, color, label = classify_score(90)
    assert tier == "★★★"
    assert color == "green"

    tier, color, label = classify_score(75)
    assert "★" in tier
    assert color == "blue"

    tier, color, label = classify_score(60)
    assert "★" in tier
    assert color == "orange"

    tier, color, label = classify_score(30)
    assert "—" in tier or "–" in tier
    assert color == "red"


def test_scoring_gas():
    scorer = MeterScorer()
    inputs = {
        "fluid_type": "gas",
        "nps": 8,
        "design_p_bar": 50,
        "design_t_c": 50,
        "oper_p_bar": 40,
        "oper_t_c": 40,
        "qmin": 5000,
        "qmax": 30000,
        "qnormal": 10000,
        "h2s": False,
        "service_type": "custody_transfer",
        "target_uncertainty": 0.5,
    }
    result = scorer.score_meter("ultrasonic", inputs)
    assert result.total_score > 0
    assert result.total_score <= 100
    assert len(result.strengths) > 0 or len(result.weaknesses) > 0
    print(f"\nUSM Gas Score: {result.total_score}")
    for cat_name, cat in result.categories.items():
        print(f"  {cat_name}: {cat.score:.2f}")


def test_scoring_liquid():
    scorer = MeterScorer()
    inputs = {
        "fluid_type": "liquid",
        "nps": 6,
        "design_p_bar": 20,
        "design_t_c": 30,
        "oper_p_bar": 15,
        "oper_t_c": 25,
        "qmin": 100,
        "qmax": 1000,
        "qnormal": 500,
        "h2s": True,
        "h2s_ppm": 500,
        "service_type": "custody_transfer",
        "target_uncertainty": 0.2,
    }
    result = scorer.score_meter("positive_displacement", inputs)
    assert result.total_score > 0
    print(f"\nPD Liquid H2S Score: {result.total_score}")


def test_all_meters_gas():
    from metering_designer.meters.selector import evaluate_all_meters
    inputs = {
        "fluid_type": "gas",
        "nps": 10,
        "design_p_bar": 70,
        "design_t_c": 60,
        "oper_p_bar": 55,
        "oper_t_c": 45,
        "qmin": 10000,
        "qmax": 80000,
        "qnormal": 30000,
        "h2s": False,
        "service_type": "custody_transfer",
        "target_uncertainty": 0.5,
        "location": "turkey",
    }
    results = evaluate_all_meters(inputs, fluid_type="gas")
    assert len(results) > 0
    assert results[0].total_score >= results[-1].total_score
    print(f"\nGas Ranking ({len(results)} meters):")
    for r in results:
        print(f"  {r.name_tr}: {r.total_score:.1f} ({r.tier_label})")


if __name__ == "__main__":
    test_classify_score()
    test_scoring_gas()
    test_scoring_liquid()
    test_all_meters_gas()
    print("\nAll tests passed!")
