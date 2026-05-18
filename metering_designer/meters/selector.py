"""
Multi-meter evaluator: runs the scoring engine for all applicable meter types
and returns a ranked list.
"""

from metering_designer.core.scoring_engine import MeterScorer, ScoredMeter
from metering_designer.meters.specs import get_meter_keys


def evaluate_all_meters(
    inputs: dict,
    weights: dict = None,
    fluid_type: str = "gas",
) -> list[ScoredMeter]:
    scorer = MeterScorer(weights=weights)

    meter_keys = get_meter_keys(fluid_type=fluid_type)
    results: list[ScoredMeter] = []

    for meter_key in meter_keys:
        try:
            scored = scorer.score_meter(meter_key, inputs)
            results.append(scored)
        except Exception as e:
            results.append(ScoredMeter(
                meter_key=meter_key,
                name_tr=meter_key,
                name_en=meter_key,
                total_score=0,
                tier_label="ERR",
                tier_color="gray",
            ))

    results.sort(key=lambda r: -r.total_score)
    return results
