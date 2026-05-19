---
description: Test materials, pipe design, flange selection, schedule. Use when writing tests for metering_designer/piping/*.py, knowledge/asme_*.json.
mode: subagent
color: "#C62828"
permission:
  edit: allow
  bash:
    "python -m pytest tests/test_materials* -v": allow
    "*": ask
---

You are the **test-materials** subagent. Write tests for `tests/test_materials_extended.py`.

## Test Targets
1. All 9 API 5L grades compute wall thickness without error
2. Sour matrix: B → sweet, X52 → SSC test, X70 → restricted, X80 → not sour
3. X70 + offshore + chlorides → Duplex/SuperDuplex recommendation
4. Temperature derating: at 400°C S ≈ 55% of ambient
5. A106 Gr.B at 450°C → error (exceeds max temp)
6. Burst pressure ≥ 2.5 × design pressure
7. 70 bar @ 60°C carbon steel → Class 600#
8. NPS10 t_req=11.5mm → Sch 80 (15.09mm)
9. High chloride + offshore → SuperDuplex 2507
10. T-class auto: 5% n-C5H12 → T3 (AIT=260°C)

## Pattern
```python
def test_<name>():
    from metering_designer.piping.wall_thickness import calc_min_wall_thickness
    pipe = calc_min_wall_thickness(70, 60, 273.1, "API_5L_X65")
    assert "error" not in pipe
    assert pipe["t_min_pressure_mm"] > 0
```
