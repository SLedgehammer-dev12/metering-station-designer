from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MeterInputs:
    fluid_type: str = "gas"
    qmin: float = 0.0
    qmax: float = 100.0
    qnormal: float = 50.0
    nps: int = 6
    od_mm: float = 168.3
    design_p_bar: float = 50.0
    design_t_C: float = 50.0
    oper_p_bar: float = 40.0
    oper_t_C: float = 40.0
    h2s: bool = False
    h2s_ppm: float = 0.0
    service_type: str = "process"
    ex_zone: str = "zone_2"
    target_uncertainty: float = 1.0
    upstream_config: str = "single_bend"
    viscosity_cp: float = 1.0
    composition: dict[str, float] = field(default_factory=lambda: {"C1": 1.0})
    location: str = "turkey"
    ambient_min_C: float = -10.0
    ambient_max_C: float = 40.0
    power_source: str = "grid"
    communication: str = "cable"
    site_length_limit_m: float = 0.0


class BaseMeter:
    key: str = ""

    @classmethod
    def recompute_details(cls, inputs: MeterInputs) -> dict:
        return {}
