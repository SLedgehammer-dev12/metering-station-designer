"""Fluid dataclass — typed container for gas/liquid properties."""
from dataclasses import dataclass, field


@dataclass
class Fluid:
    composition: dict[str, float] = field(default_factory=dict)
    M_mix: float = 0.0
    Z_oper: float = 1.0
    Z_design: float = 1.0
    rho_oper_kg_m3: float = 0.0
    rho_std_kg_m3: float = 0.0
    rho_design_kg_m3: float = 0.0
    mu_dynamic_Pa_s: float = 0.0
    nu_kinematic_m2_s: float = 0.0
    gross_CV_MJ_m3: float = 0.0
    net_CV_MJ_m3: float = 0.0
    Wobbe_MJ_m3: float = 0.0
    relative_density: float = 0.0
    kappa: float = 1.3
    speed_of_sound_ms: float = 0.0
    backend_used: str = ""
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "Fluid":
        return cls(
            composition=d.get("composition", {}),
            M_mix=d.get("M_mix", 0.0),
            Z_oper=d.get("Z_oper", 1.0),
            Z_design=d.get("Z_design", 1.0),
            rho_oper_kg_m3=d.get("rho_oper_kg_m3", 0.0),
            rho_std_kg_m3=d.get("rho_std_kg_m3", 0.0),
            rho_design_kg_m3=d.get("rho_design_kg_m3", 0.0),
            mu_dynamic_Pa_s=d.get("mu_dynamic_Pa_s", 0.0),
            nu_kinematic_m2_s=d.get("nu_kinematic_m2_s", 0.0),
            gross_CV_MJ_m3=d.get("gross_CV_MJ_m3", 0.0),
            net_CV_MJ_m3=d.get("net_CV_MJ_m3", 0.0),
            Wobbe_MJ_m3=d.get("Wobbe_MJ_m3", 0.0),
            relative_density=d.get("relative_density", 0.0),
            kappa=d.get("kappa", 1.3),
            speed_of_sound_ms=d.get("speed_of_sound_ms", 0.0),
            backend_used=d.get("backend_used", ""),
            warnings=d.get("warnings", []),
        )

    @property
    def is_gas(self) -> bool:
        return self.rho_std_kg_m3 < 100

    @property
    def error(self) -> str | None:
        return None
