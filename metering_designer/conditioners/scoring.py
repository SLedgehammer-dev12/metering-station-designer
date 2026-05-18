"""
Flow conditioner multi-criteria scoring engine.
"""

import json
import os

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "knowledge")


def load_conditioner_data() -> dict:
    path = os.path.join(KNOWLEDGE_DIR, "meter_specs.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("flow_conditioners", {})


def score_all_conditioners(
    meter_key: str,
    nps: int,
    upstream_config: str = "single_bend_90",
    site_length_limit_m: float = 0.0,
    straight_required_m: float = 0.0,
) -> list[dict]:
    conditioners = load_conditioner_data()
    results = []

    for ckey, cdata in conditioners.items():
        scores = {}

        # K-factor (pressure loss) - weight 30%
        k_factor = cdata.get("k_factor", 4.0)
        scores["pressure_loss"] = max(1.0, min(10.0, 10.0 * (1.0 - k_factor / 10.0)))

        # Straight pipe reduction - weight 25%
        reduction = cdata.get("straight_pipe_reduction_pct", 0.5)
        scores["straight_pipe_reduction"] = reduction * 10.0

        # ISO compliance - weight 20%
        iso_comp = cdata.get("iso_compliant", False)
        scores["iso_compliance"] = 10.0 if iso_comp else 3.0

        # Maintenance + fouling - weight 10%
        maint = cdata.get("maintenance_score", 5.0)
        scores["maintenance"] = maint

        # Cost - weight 10%
        capex_f = cdata.get("capex_factor", 2.0)
        scores["cost"] = max(1.0, min(10.0, 10.0 / capex_f))

        # Installation complexity - weight 5%
        inst = cdata.get("installation_complexity", 5.0)
        scores["installation"] = inst

        # Weighted total
        weights = {"pressure_loss": 0.30, "straight_pipe_reduction": 0.25,
                    "iso_compliance": 0.20, "maintenance": 0.10,
                    "cost": 0.10, "installation": 0.05}

        total = sum(scores[k] * weights[k] for k in weights) * 10  # 0-100 scale

        # Effective straight pipe length with this conditioner
        up_d = cdata.get("min_upstream_l_d_required", 2) + cdata.get("typical_downstream_l_d", 8)
        od_m = nps * 0.0254 if nps <= 48 else 0.3
        effective_l = up_d * od_m + 5 * od_m  # + 5D downstream of meter

        fits_site = effective_l <= site_length_limit_m if site_length_limit_m > 0 else True

        results.append({
            "key": ckey,
            "name_tr": cdata.get("name_tr", ckey),
            "name_en": cdata.get("name_en", ckey),
            "total_score": round(total, 1),
            "k_factor": k_factor,
            "reduction_pct": round(reduction * 100, 0),
            "iso_compliant": iso_comp,
            "effective_length_m": round(effective_l, 2),
            "fits_site": fits_site,
            "sub_scores": scores,
        })

    results.sort(key=lambda r: -r["total_score"])
    return results


def recommend_conditioner(results: list[dict]) -> dict:
    if not results:
        return {}
    site_fits = [r for r in results if r.get("fits_site", True)]
    candidates = site_fits if site_fits else results
    return candidates[0]
