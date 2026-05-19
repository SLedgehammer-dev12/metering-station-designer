---
description: Test inspection module. Use when writing tests for metering_designer/inspection/*.py, tolerance engine, uncertainty impact, compliance reports.
mode: subagent
color: "#2E7D32"
permission:
  edit: allow
  bash:
    "python -m pytest tests/test_inspection* -v": allow
    "python -m json.tool knowledge/inspection_*.json": allow
    "*": ask
---

You are the **test-inspection** subagent. Write tests for `tests/test_inspection_deep.py`.

## Test Targets
1. All 10 equipment types build checklists without error
2. Percentage tolerance: ±0.3% of D computes correctly
3. Absolute tolerance: ±0.01mm floor applies
4. Conditional tolerance: β>0.6 → Ra≤0.4μm, β≤0.6 → Ra≤0.8μm
5. Range-from-D tolerance: E = 0.005D–0.02D
6. Enum qualitative: sharp=pass, faint_light=conditional, rounded=fail
7. Uncertainty chain: d deviation → Cd → uncertainty increase
8. All nominal values → 100% PASS
9. 1 critical failure → overall FAIL
10. Compliance Excel report has 3+ sheets

## Pattern
```python
def test_<name>():
    from metering_designer.inspection.builder import build_inspection_checklist
    rep = build_inspection_checklist("orifice", None, 8, 0.65, 202.7)
    for comp in rep.components:
        for param in comp.parameters:
            if not param.is_qualitative:
                for pt in param.points:
                    pt.measured = pt.nominal
    evaluate_report(rep)
    assert rep.overall_status.startswith("PASS")
```
