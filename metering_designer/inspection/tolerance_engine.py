"""
Tolerance computation engine. Always returns absolute bounds.
"""


def compute_tolerance(spec: dict, reference_values: dict) -> dict:
    t_type = spec.get("type", "max_value")

    if t_type == "percentage_or_absolute":
        base_val = reference_values.get(spec.get("base_param", "d"), 100)
        pct_tol = spec.get("percentage", 0.05) / 100 * base_val
        abs_tol = spec.get("absolute_mm", 0.01)
        tol = max(abs(pct_tol), abs_tol) if spec.get("use", "larger") == "larger" else abs(pct_tol)
        return {"lower": base_val - tol, "upper": base_val + tol, "nominal": base_val}

    elif t_type == "range_from_D":
        D = reference_values.get("D", 200)
        lo = spec.get("min_factor", 0.005) * D
        hi = spec.get("max_factor", 0.02) * D
        mid = (lo + hi) / 2
        return {"lower": lo, "upper": hi, "nominal": round(mid, 2)}

    elif t_type == "percentage":
        base_val = reference_values.get(spec.get("base_param", "D"), 200)
        pct = spec.get("value", 0.3) / 100 * base_val
        return {"lower": base_val - pct, "upper": base_val + pct, "nominal": base_val}

    elif t_type == "conditional_max":
        conditions = spec.get("conditions", [])
        for cond in conditions:
            param = cond["if"]["param"]
            op = cond["if"]["op"]
            threshold = cond["if"]["value"]
            actual = reference_values.get(param, 0)
            if _evaluate(actual, op, threshold):
                hi = cond["max"]
                return {"lower": None, "upper": hi, "nominal": round(hi * 0.75, 3)}
        return {"lower": None, "upper": None, "nominal": 0}

    elif t_type == "max_value":
        val = spec.get("value", 1.0)
        return {"lower": None, "upper": val, "nominal": round(val * 0.7, 3)}

    elif t_type == "min_value":
        val = spec.get("value", 1.0)
        if isinstance(val, str) and "t_min" in val:
            val = reference_values.get("t_min_mm", 3.0)
        return {"lower": val, "upper": None, "nominal": round(val * 1.5, 3)}

    elif t_type == "range":
        lo = spec.get("min", 0)
        hi = spec.get("max", 100)
        lo = float(lo) if not isinstance(lo, str) else 0.0
        hi = float(hi) if not isinstance(hi, str) else 100.0
        return {"lower": lo, "upper": hi, "nominal": round((lo + hi) / 2, 2)}

    elif t_type == "min_length_D":
        min_D = spec.get("min_factor", 10)
        D = reference_values.get("D", 200)
        min_val = min_D * D
        return {"lower": min_val, "upper": None, "nominal": round(min_val * 1.3, 1)}

    elif t_type == "enum":
        return {"lower": None, "upper": None, "nominal": 0}

    return {"lower": None, "upper": None, "nominal": 0}


def _evaluate(value: float, op: str, threshold: float) -> bool:
    ops = {">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
           "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
           "==": lambda a, b: a == b}
    return ops.get(op, lambda a, b: False)(value, threshold)
