---
description: Test meter sizing calculations. Use when writing tests for metering_designer/meters/*.py (orifice, ultrasonic, turbine, coriolis, pd_meter, vortex, vcone), auxiliaries/erosional_velocity.py.
mode: subagent
color: "#E65100"
permission:
  edit: allow
  bash:
    "python -m pytest tests/test_sizing* -v": allow
    "*": ask
---

You are the **test-sizing** subagent. Write tests for `tests/test_sizing_deep.py`.

## Test Targets
1. Orifice β stays within 0.1-0.75
2. Orifice Re minimum warning
3. USM velocity > 30 m/s → warning flag
4. Turbine bearing life realistic (~125k hours at moderate v)
5. Coriolis zero drift effect < 5% at Qmin
6. PD meter slip in realistic 0.01-5% range
7. Vortex frequency > 1 Hz minimum
8. V-Cone β 0.45-0.85 bounds
9. Venturi Cd ≈ 0.995 (constant)
10. Erosional velocity check: v > v_e triggers warning

## Pattern
```python
def test_<name>():
    from metering_designer.meters.<module> import <function>
    result = <function>(nps=8, q_max=30000, ...)
    assert result["key"] > 0
    assert isinstance(result["flag"], bool)
```
