"""
ISO 5167-5 / ASME MFC-7M
V-Cone and Venturi meter sizing.
"""

import math


def size_v_cone(
    nps: int,
    q_max_Sm3h: float,
    q_min_Sm3h: float,
    P_oper_bar: float,
    T_oper_C: float,
    rho_kg_m3: float,
    mu_Pa_s: float,
    rho_std_kg_m3: float,
    is_gas: bool = True,
) -> dict:
    from metering_designer.piping import pipe_id_mm
    id_mm = pipe_id_mm(nps)
    id_m = id_mm / 1000
    A_pipe = math.pi * (id_m / 2) ** 2

    if is_gas:
        q_act_max = q_max_Sm3h * rho_std_kg_m3 / rho_kg_m3 / 3600
    else:
        q_act_max = q_max_Sm3h / 3600

    v_pipe = q_act_max / A_pipe if A_pipe > 0 else 0
    Re = rho_kg_m3 * v_pipe * id_m / mu_Pa_s if mu_Pa_s > 0 else 1e6

    # Beta ratio: V-Cone typically 0.45-0.85
    beta = _estimate_vcone_beta(q_act_max, id_mm, rho_kg_m3)
    beta = max(0.45, min(beta, 0.85))

    # Discharge coefficient for V-Cone
    Cd = _vcone_cd(beta, Re)
    eps = _vcone_expansibility(beta, P_oper_bar) if is_gas else 1.0

    # Annular flow area between cone and pipe wall = A_pipe·β².
    # The cone body diameter that produces this annulus is D·√(1−β²); reporting
    # β·D (an "equivalent diameter") has no physical meaning.
    At = A_pipe * beta ** 2
    d_cone_mm = id_mm * math.sqrt(1 - beta ** 2)
    E = 1.0 / math.sqrt(1 - beta ** 4)
    dp_Pa = (q_act_max * rho_kg_m3) ** 2 / (2 * rho_kg_m3 * (Cd * eps * E * At) ** 2) if At > 0 else 25000
    dp_mbar = dp_Pa / 100

    # Permanent pressure loss (V-Cone: much lower than orifice)
    pl_factor = (1 - beta ** 2) * 0.3
    dp_perm_mbar = dp_mbar * pl_factor

    # Turndown
    td = q_max_Sm3h / q_min_Sm3h if q_min_Sm3h > 0 else 1
    td_ok = td <= 10

    # Uncertainty
    base_unc = 0.5 if beta <= 0.6 else 1.0

    return {
        "meter_type": "V-Cone",
        "nps": nps, "id_mm": round(id_mm, 1),
        "beta": round(beta, 4), "d_cone_mm": round(d_cone_mm, 2),
        "Cd": round(Cd, 5), "eps": round(eps, 5),
        "Re": round(Re, 0), "Re_ok": Re > 8000,
        "v_pipe_ms": round(v_pipe, 2),
        "dp_mbar": round(dp_mbar, 1),
        "dp_perm_mbar": round(dp_perm_mbar, 1),
        "turndown_actual": round(td, 1), "turndown_max": 10,
        "turndown_ok": td_ok, "base_uncertainty_pct": base_unc,
        "straight_upstream_D": 3, "straight_downstream_D": 2,
        "notes": _vcone_notes(beta, td_ok, Re),
    }


def size_v_cone_with_fluid(
    nps: int,
    q_max_Sm3h: float,
    q_min_Sm3h: float,
    fluid: "Fluid",
    is_gas: bool = True,
    P_oper_bar: float = 40.0,
    T_oper_C: float = 20.0,
) -> dict:
    """Wrapper around size_v_cone that accepts Fluid object.

    Args:
        nps: nominal pipe size
        q_max_Sm3h: maximum flow rate [Sm³/h]
        q_min_Sm3h: minimum flow rate [Sm³/h]
        fluid: Fluid dataclass instance
        is_gas: True for gas, False for liquid
        P_oper_bar: operating pressure [bar]
        T_oper_C: operating temperature [°C]
    """
    from metering_designer.fluids.fluid import Fluid

    rho = fluid.rho_oper_kg_m3
    mu = fluid.mu_dynamic_Pa_s
    rho_std = fluid.rho_std_kg_m3

    return size_v_cone(
        nps, q_max_Sm3h, q_min_Sm3h, P_oper_bar, T_oper_C,
        rho, mu, rho_std, is_gas=is_gas,
    )


def size_venturi(
    nps: int,
    q_max_Sm3h: float,
    q_min_Sm3h: float,
    P_oper_bar: float,
    T_oper_C: float,
    rho_kg_m3: float,
    mu_Pa_s: float,
    rho_std_kg_m3: float,
) -> dict:
    """ISO 5167-4 classical Venturi (machined convergent section) sizing.

    - Cd = 0.995 for 0.3 ≤ β ≤ 0.75, 2·10^5 ≤ Re ≤ 10^6 (uncalibrated).
    - Expansibility ε per ISO 5167-1 §5.3.2.2 with the real p1 (absolute).
    - β is sized to a typical design Δp ≈ 250 mbar at maximum flow.
    - Permanent loss of a classical Venturi is only ~10–17% of Δp.
    """
    from metering_designer.piping import pipe_id_mm

    id_mm = pipe_id_mm(nps)
    id_m = id_mm / 1000
    A_pipe = math.pi * (id_m / 2) ** 2
    qm_max = q_max_Sm3h * rho_std_kg_m3 / 3600 if rho_std_kg_m3 > 0 else 0
    q_act_max = qm_max / rho_kg_m3 if rho_kg_m3 > 0 else 0
    v_pipe = q_act_max / A_pipe if A_pipe > 0 else 0
    Re = rho_kg_m3 * v_pipe * id_m / mu_Pa_s if mu_Pa_s > 0 else 1e6

    Cd = 0.995
    kappa = 1.3  # isentropic exponent for natural gas
    p1_Pa = P_oper_bar * 1e5
    dp_target_Pa = 25000  # typical design Δp for a venturi, 250 mbar

    beta = _size_venturi_beta(qm_max, id_mm, rho_kg_m3, Cd, p1_Pa, dp_target_Pa, kappa)
    beta = max(0.3, min(beta, 0.75))
    d_throat_mm = beta * id_mm
    At = A_pipe * beta ** 2
    E = 1.0 / math.sqrt(1 - beta ** 4)
    eps = _venturi_expansibility(beta, dp_target_Pa, p1_Pa, kappa)

    dp_Pa = (qm_max / (Cd * eps * E * At)) ** 2 / (2 * rho_kg_m3) if At > 0 and rho_kg_m3 > 0 else dp_target_Pa
    dp_mbar = dp_Pa / 100
    # Classical venturi permanent loss ≈ 10–17% of Δp (ISO 5167-4).
    dp_perm_mbar = dp_mbar * 0.15

    td = q_max_Sm3h / q_min_Sm3h if q_min_Sm3h > 0 else 1
    unc = 0.7

    return {
        "meter_type": "Venturi (klasik)",
        "nps": nps, "id_mm": round(id_mm, 1),
        "beta": round(beta, 4), "d_throat_mm": round(d_throat_mm, 1),
        "Cd": Cd, "eps": round(eps, 5),
        "Re": round(Re, 0), "Re_ok": Re > 2e5,
        "v_pipe_ms": round(v_pipe, 2),
        "dp_mbar": round(dp_mbar, 1),
        "dp_perm_mbar": round(dp_perm_mbar, 1),
        "turndown_actual": round(td, 1), "turndown_max": 8,
        "turndown_ok": td <= 8, "base_uncertainty_pct": unc,
        "straight_upstream_D": 8, "straight_downstream_D": 5,
        "notes": "ISO 5167-4 machined convergent, Cd=0.995, 0.3≤β≤0.75, Re≥2·10^5.",
    }


def size_venturi_with_fluid(
    nps: int,
    q_max_Sm3h: float,
    q_min_Sm3h: float,
    fluid: "Fluid",
    P_oper_bar: float = 40.0,
    T_oper_C: float = 20.0,
) -> dict:
    """Wrapper around size_venturi that accepts Fluid object.

    Args:
        nps: nominal pipe size
        q_max_Sm3h: maximum flow rate [Sm³/h]
        q_min_Sm3h: minimum flow rate [Sm³/h]
        fluid: Fluid dataclass instance
        P_oper_bar: operating pressure [bar]
        T_oper_C: operating temperature [°C]
    """
    from metering_designer.fluids.fluid import Fluid

    rho = fluid.rho_oper_kg_m3
    mu = fluid.mu_dynamic_Pa_s
    rho_std = fluid.rho_std_kg_m3

    return size_venturi(
        nps, q_max_Sm3h, q_min_Sm3h, P_oper_bar, T_oper_C,
        rho, mu, rho_std,
    )


def _estimate_vcone_beta(q_m3s: float, id_mm: float, rho: float) -> float:
    if q_m3s <= 0 or id_mm <= 0:
        return 0.65
    target_beta = 0.05 * (q_m3s * rho) ** 0.3 + 0.45
    return min(max(target_beta, 0.45), 0.85)


def _vcone_cd(beta: float, Re: float) -> float:
    return 0.82 + 0.01 * beta - 0.0001 * beta * (Re / 1e6)


def _vcone_expansibility(beta: float, P_bar: float) -> float:
    if P_bar <= 0:
        return 1.0
    return 1 - (0.41 + 0.35 * beta ** 4) * 0.3 / (1.3 * P_bar)


def _size_venturi_beta(qm_kg_s: float, id_mm: float, rho: float,
                       Cd: float, p1_Pa: float, dp_target_Pa: float,
                       kappa: float = 1.3) -> float:
    """Iteratively size the Venturi β to reach dp_target at qm_max."""
    if qm_kg_s <= 0 or id_mm <= 0 or rho <= 0:
        return 0.5
    D_m = id_mm / 1000
    A_pipe = math.pi * (D_m / 2) ** 2
    beta = 0.5
    for _ in range(30):
        At = A_pipe * beta ** 2
        eps = _venturi_expansibility(beta, dp_target_Pa, p1_Pa, kappa)
        qm_calc = Cd * eps * At * math.sqrt(2 * rho * dp_target_Pa) / math.sqrt(1 - beta ** 4)
        if qm_calc <= 0:
            break
        factor = qm_kg_s / qm_calc
        beta_new = beta * factor ** 0.25
        if abs(beta_new - beta) < 1e-5:
            beta = beta_new
            break
        beta = beta_new
    return beta


def _venturi_expansibility(beta: float, dp_Pa: float, p1_Pa: float,
                           kappa: float = 1.3) -> float:
    """Expansibility factor for a Venturi per ISO 5167-1 §5.3.2.2."""
    if p1_Pa <= 0:
        return 1.0
    tau = 1 - dp_Pa / p1_Pa
    if tau <= 0:
        return 1.0
    k = kappa
    b4 = beta ** 4
    t2k = tau ** (2 / k)
    return math.sqrt(
        (k * t2k / (k - 1))
        * ((1 - b4) / (1 - b4 * t2k))
        * ((1 - tau ** ((k - 1) / k)) / (1 - tau))
    )


def _vcone_notes(beta: float, td_ok: bool, Re: float) -> str:
    n = []
    if beta < 0.45:
        n.append("β < 0.45, düşük sinyal")
    if not td_ok:
        n.append("Turndown > 10:1")
    if Re < 8000:
        n.append("Re < 8000, Cd değişken")
    return "; ".join(n) if n else "Tasarım sınırlar içinde"


def _nps_to_od(nps: int) -> float:
    m = {2: 60.3, 3: 88.9, 4: 114.3, 6: 168.3, 8: 219.1,
         10: 273.1, 12: 323.8, 16: 406.4, 20: 508.0, 24: 609.6}
    return m.get(nps, nps * 25.4)
