"""
IEC 61511 simplified SIL determination using risk graph method.
"""


def assess_sil(
    consequence: str = "serious",
    occupancy: str = "rare",
    avoidance: str = "possible",
    demand_rate: str = "low",
    environment: str = "onshore",
) -> dict:
    risk_scores = {
        "consequence": {"minor": 1, "serious": 2, "major": 3, "catastrophic": 4},
        "occupancy": {"rare": 1, "frequent": 2, "continuous": 3},
        "avoidance": {"possible": 1, "possible_limited": 2, "impossible": 3},
        "demand": {"low": 1, "medium": 2, "high": 3},
    }

    score = (
        risk_scores["consequence"].get(consequence, 2)
        * risk_scores["occupancy"].get(occupancy, 1)
        * risk_scores["avoidance"].get(avoidance, 1)
        * risk_scores["demand"].get(demand_rate, 1)
    )

    if score <= 4:
        sil = "No SIL required (a)"
        pfd = "< 10^-1"
        risk_reduction = "< 10"
    elif score <= 8:
        sil = "SIL 1"
        pfd = "10^-2 to 10^-1"
        risk_reduction = "10 to 100"
    elif score <= 16:
        sil = "SIL 2"
        pfd = "10^-3 to 10^-2"
        risk_reduction = "100 to 1000"
    elif score <= 32:
        sil = "SIL 3"
        pfd = "10^-4 to 10^-3"
        risk_reduction = "1000 to 10000"
    else:
        sil = "SIL 3 with redundancy"
        pfd = "< 10^-4"
        risk_reduction = "> 10000"

    return {
        "sil_rating": sil,
        "pfd_range": pfd,
        "risk_reduction_factor": risk_reduction,
        "raw_score": score,
        "notes": "IEC 61511 risk graph method - preliminary assessment, requires HAZOP validation",
    }
