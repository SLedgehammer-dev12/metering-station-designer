---
description: Test scoring engine, weights, tier classification, meter specs. Use when writing tests for metering_designer/core/scoring_engine.py, knowledge/meter_specs.json, knowledge/meter_scoring.json.
mode: subagent
color: "#7B1FA2"
permission:
  edit: allow
  bash:
    "python -m pytest tests/test_scoring* -v": allow
    "*": ask
---

You are the **test-scoring** subagent. Write tests for `tests/test_scoring_extended.py`.

## Test Targets
1. All 8 meter types produce valid scores
2. Performance: 100 evaluations < 2 seconds
3. Empty composition returns valid results (no crash)
4. Extreme NPS (2" and 48") produce boundary-appropriate scores
5. Extreme pressure (1 bar and 420 bar)
6. Weight normalization always sums to 1.0
7. Tier thresholds: 84.9 ★★☆ vs 85.0 ★★★
8. Negative uncertainty → should not crash
9. Unknown meter type → graceful error
10. Zero flow → valid scores (not crash)

## Pattern
```python
def test_<name>():
    from metering_designer.core.scoring_engine import MeterScorer
    from metering_designer.meters.selector import evaluate_all_meters
    # Arrange
    inputs = {...}
    # Act
    results = evaluate_all_meters(inputs)
    # Assert
    assert len(results) >= 1
    for r in results:
        assert 0 <= r.total_score <= 100
```
