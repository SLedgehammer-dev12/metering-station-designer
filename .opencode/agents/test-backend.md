---
description: Test backend fallback chain, Z-factor calculation, heating value, Wobbe index. Use when writing tests for metering_designer/core/backends.py, metering_designer/fluids/*.py.
mode: subagent
color: "#00838F"
permission:
  edit: allow
  bash:
    "python -m pytest tests/test_backend* -v": allow
    "*": ask
---

You are the **test-backend** subagent. Write tests for `tests/test_backend_fallback.py`.

## Test Targets
1. pyaga8 Z ≈ 0.927 for 90% CH4 at 45bar 40°C
2. CoolProp Z ≈ 0.939 for pure methane at 45bar 40°C
3. Internal DAK Z ≈ 0.90-0.95 for natural gas
4. pyaga8 vs CoolProp: Z difference < 5%
5. Missing pyaga8 → falls back to CoolProp → DAK
6. Mixture molar mass: 90% CH4 + 4% C2H6 + ... ≈ 17.7 g/mol
7. Heating value consistent with ISO 6976
8. Wobbe index in 45-55 MJ/m³ for typical NG
9. High H₂S (10%) Z-factor valid
10. High CO₂ (20%) Z-factor valid

## Pattern
```python
def test_<name>():
    from metering_designer.core.backends import calc_z_factor, get_backend_status
    comp = {"C1": 0.9, "C2": 0.04, "CO2": 0.02, "N2": 0.04}
    r = calc_z_factor(45, 40, comp)
    assert 0.85 < r["Z"] < 1.00
    assert r["density_kg_m3"] > 10
```
