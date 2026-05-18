import json
import os
import math
from dataclasses import dataclass, field
from typing import Optional

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "knowledge")


@dataclass
class CriteriaScore:
    name: str
    score: float
    weight: float
    description: str
    raw_input: Optional[float] = None
    justification: str = ""


@dataclass
class CategoryScore:
    name: str
    score: float
    weight: float
    criteria: list[CriteriaScore] = field(default_factory=list)

    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class ScoredMeter:
    meter_key: str
    name_tr: str
    name_en: str
    total_score: float
    tier_label: str
    tier_color: str
    categories: dict[str, CategoryScore] = field(default_factory=dict)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


def load_json(filename: str) -> dict:
    path = os.path.join(KNOWLEDGE_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


TIER_THRESHOLDS = [
    (85, 100, "★★★", "green", "Optimal - En iyi tercih"),
    (70, 85, "★★☆", "blue", "İyi alternatif"),
    (50, 70, "★☆☆", "orange", "Değerlendirilebilir"),
    (0, 50, "—–", "red", "Önerilmez"),
]


def classify_score(score: float) -> tuple[str, str, str]:
    for lo, hi, tier, color, label in TIER_THRESHOLDS:
        if lo <= score < hi:
            return tier, color, label
    return "—–", "red", "Önerilmez"


class MeterScorer:
    def __init__(self, weights: Optional[dict] = None):
        self.specs = load_json("meter_specs.json")
        self.scoring_cfg = load_json("meter_scoring.json")
        self.default_weights = dict(self.scoring_cfg["default_weights"])
        self.weights = weights if weights else dict(self.default_weights)

        cat_cfg = self.scoring_cfg["categories"]
        normalizer = sum(self.weights.get(k, v["weight"]) for k, v in cat_cfg.items())
        for key in self.weights:
            self.weights[key] /= normalizer

    def score_meter(self, meter_key: str, inputs: dict) -> ScoredMeter:
        cfg = self.scoring_cfg
        meter_data = self.specs["meters"][meter_key]
        categories: dict[str, CategoryScore] = {}
        all_strengths: list[str] = []
        all_weaknesses: list[str] = []

        for cat_key, cat_cfg in cfg["categories"].items():
            cat_weight = self.weights.get(cat_key, cat_cfg["weight"])
            criterion_scores: list[CriteriaScore] = []
            for crit_key, crit_cfg in cat_cfg["criteria"].items():
                score, justification = self._evaluate_criterion(
                    crit_key, meter_data, inputs, cat_key
                )
                criterion_scores.append(CriteriaScore(
                    name=crit_key,
                    score=score,
                    weight=crit_cfg["weight"],
                    description=crit_cfg["description"],
                    justification=justification,
                ))
            cat_score = sum(cs.score * cs.weight for cs in criterion_scores)
            categories[cat_key] = CategoryScore(
                name=cat_key,
                score=cat_score,
                weight=cat_weight,
                criteria=criterion_scores,
            )

        total = sum(cat.score * cat.weight for cat in categories.values()) * 10

        tier_label, tier_color, _ = classify_score(total)

        strengths, weaknesses = self._generate_summary(meter_key, categories, inputs)

        details = self._compute_auxiliary_details(meter_key, inputs)

        return ScoredMeter(
            meter_key=meter_key,
            name_tr=meter_data.get("name_tr", meter_key),
            name_en=meter_data.get("name_en", meter_key),
            total_score=round(total, 1),
            tier_label=tier_label,
            tier_color=tier_color,
            categories=categories,
            strengths=strengths,
            weaknesses=weaknesses,
            details=details,
        )

    def _evaluate_criterion(
        self, crit_key: str, meter_data: dict, inputs: dict, cat_key: str
    ) -> tuple[float, str]:
        fluid = inputs.get("fluid_type", "gas")
        is_gas = fluid.startswith("gas")
        design_p = inputs.get("design_p_bar", 50.0)
        qmin = inputs.get("qmin", 0)
        qmax = inputs.get("qmax", 100)
        nps = inputs.get("nps", 6)
        design_t = inputs.get("design_t_c", 50.0)
        h2s = inputs.get("h2s", False)
        service_type = inputs.get("service_type", "process")
        target_uncertainty = inputs.get("target_uncertainty", 2.0)

        def _to_10(val, inverse=False):
            if inverse:
                return max(0.0, min(10.0, 10.0 - val * 10.0))
            return max(0.0, min(10.0, val * 10.0))

        if cat_key == "technical_fitness":
            if crit_key == "fluid_compatibility":
                if is_gas and "gas" in meter_data.get("fluids", []):
                    return 10.0, "Gaz ölçümü için uygun tasarlanmış"
                if not is_gas and "liquid" in meter_data.get("fluids", []):
                    return 10.0, "Sıvı ölçümü için uygun tasarlanmış"
                if not is_gas and is_gas:
                    return 5.0, "Alternatif uygulama, orta derece uygun"
                return 0.0, "Bu akışkan tipi için uygun değil"

            if crit_key == "turndown_coverage":
                if qmin <= 0 or qmax <= 0:
                    return 7.0, "Turndown bilgisi eksik, varsayılan"
                required = qmax / qmin
                max_td = meter_data.get("max_turndown", 10)
                ratio = max_td / required if required > 0 else max_td
                score = min(10.0, ratio * 10.0)
                just = f"İstenen turndown 1:{int(required)}, metre kapasitesi 1:{max_td}"
                return min(10.0, score), just

            if crit_key == "pipe_size_fit":
                meter_min = meter_data.get("min_nps", 1)
                meter_max = meter_data.get("max_nps", 48)
                if meter_min <= nps <= meter_max:
                    return 10.0, f"NPS {nps} metre boyut aralığı içinde"
                middle = (meter_min + meter_max) / 2.0
                if nps < meter_min:
                    score = max(0, 10 - (meter_min - nps) * 3)
                    return score, f"NPS {nps} minimum {meter_min}\" altında"
                if nps > meter_max:
                    score = max(0, 10 - (nps - meter_max) * 2)
                    return score, f"NPS {nps} maksimum {meter_max}\" üstünde"
                return 5.0, "Sınır aralığında"

            if crit_key == "flow_velocity_fit":
                return 8.0, "Genel hız aralığı uygun (detaylı hesap için Phase 2)"

            if crit_key == "h2s_compatibility":
                compat = meter_data.get("h2s_compatible", "no")
                if not h2s:
                    return 10.0, "H₂S yok, tüm seçenekler uygun"
                if compat == "yes":
                    return 10.0, "NACE MR0175 uyumlu seçenek mevcut"
                if compat == "special":
                    return 6.0, "Özel malzeme ile uyum sağlanabilir"
                return 2.0, "H₂S servisi için önerilmez"

        if cat_key == "accuracy_metrology":
            if crit_key == "base_uncertainty":
                if is_gas:
                    unc = meter_data.get("base_uncertainty_gas")
                else:
                    unc = meter_data.get("base_uncertainty_liquid")
                if unc is None:
                    return 3.0, "Belirsizlik verisi yok"
                score = max(0.0, min(10.0, 10.0 - (unc / target_uncertainty) * 5.0))
                return score, f"Tipik belirsizlik ±{unc}% hedef içinde"
            if crit_key == "custody_transfer_approval":
                if meter_data.get("custody_transfer_approved", False):
                    return 10.0, "Custody transfer / MID onaylı"
                return 2.0, "Custody transfer onayı YOK"
            if crit_key == "reproducibility":
                val = meter_data.get("reproducibility", 5)
                return val, f"Tekrarlanabilirlik puanı: {val}/10"
            if crit_key == "long_term_stability":
                val = meter_data.get("long_term_drift", 5)
                return val, f"Uzun dönem kararlılık puanı: {val}/10"

        if cat_key == "operational_ease":
            if crit_key == "pressure_loss":
                pl_factor = meter_data.get("pressure_loss_factor", 0.5)
                score = max(0, 10 - pl_factor * 15)
                return score, f"Basınç kaybı faktörü: {pl_factor}"
            if crit_key == "straight_pipe_requirement":
                upstream = meter_data.get("min_straight_upstream", 15)
                score = max(0, 10 - upstream * 0.4)
                return score, f"Düz boru ihtiyacı: {upstream}D"
            if crit_key == "maintenance_burden":
                val = meter_data.get("maintenance_score", 5)
                return val, f"Bakım puanı: {val}/10"
            if crit_key == "fouling_resistance":
                val_key = "fouling_resistance_gas" if is_gas else "fouling_resistance_liquid"
                val = meter_data.get(val_key) or meter_data.get("fouling_resistance_gas", 5)
                return val, f"Kirlilik dayanımı: {val}/10"
            if crit_key == "pressure_rating_fit":
                max_p = meter_data.get("max_pressure_bar", 100)
                if design_p <= max_p:
                    return 10.0, f"Tasarım basıncı {design_p} bar ≤ maks {max_p} bar"
                return 3.0, f"Tasarım basıncı {design_p} bar > maks {max_p} bar"

        if cat_key == "cost":
            if crit_key == "capex":
                cf = meter_data.get("capex_factor", 3.0)
                score = max(1.0, min(10.0, 10.0 / cf))
                return score, f"Rölatif CAPEX: ×{cf}"
            if crit_key == "installation":
                val = meter_data.get("installation_complexity", 5)
                return val, f"Montaj kolaylığı: {val}/10"
            if crit_key == "calibration":
                val = meter_data.get("calibration_cost", 5)
                return val, f"Kalibrasyon kolaylığı: {val}/10"
            if crit_key == "opex":
                val = meter_data.get("opex_factor", 5)
                return val, f"OPEX verimliliği: {val}/10"

        if cat_key == "implementability":
            if crit_key == "lead_time":
                lt = meter_data.get("lead_time_weeks", 12)
                score = max(0, 10 - lt / 4)
                return score, f"Tedarik süresi: {lt} hafta"
            if crit_key == "local_expertise":
                val = meter_data.get("local_expertise", 5)
                return val, f"Yerel uzmanlık: {val}/10"
            if crit_key == "spare_parts":
                val = meter_data.get("spare_parts_availability", 5)
                return val, f"Yedek parça erişimi: {val}/10"
            if crit_key == "infrastructure":
                val = meter_data.get("infrastructure_requirements", 5)
                return val, f"Altyapı gereksinimi: {val}/10"
            if crit_key == "climate":
                val = meter_data.get("climate_suitability", 5)
                return val, f"İklim uyumu: {val}/10"
            if crit_key == "transport":
                val = meter_data.get("transport_score", 7)
                return val, f"Nakliye uygunluğu: {val}/10"

        if cat_key == "project_specific":
            if crit_key == "track_record":
                val = meter_data.get("track_record", 5)
                return val, f"Saha tecrübesi: {val}/10"
            if crit_key == "compactness":
                val = meter_data.get("compactness", 5)
                return val, f"Kompaktlık: {val}/10"
            if crit_key == "online_verification":
                if meter_data.get("online_verification", False):
                    return 10.0, "Online doğrulama mümkün"
                return 2.0, "Online doğrulama mümkün değil"
            if crit_key == "noise_environmental":
                val = 10 - meter_data.get("noise_level", 5)
                return val, f"Gürültü seviyesi: {10-val}/10"
            if crit_key == "wet_gas_capability":
                val = 10 if meter_data.get("wet_gas_capable", False) else 2
                return val, "Islak gaz için uygun" if val > 5 else "Islak gaz için önerilmez"

        return 5.0, "Genel değerlendirme (detaylı hesap sonraki fazda)"

    def _generate_summary(
        self, meter_key: str, categories: dict, inputs: dict
    ) -> tuple[list[str], list[str]]:
        strengths = []
        weaknesses = []

        fluid = inputs.get("fluid_type", "gas")
        is_gas = fluid.startswith("gas")

        if categories["technical_fitness"].score >= 8:
            strengths.append("Teknik uygunluk yüksek - akışkan tipi ve aralık uygun")
        elif categories["technical_fitness"].score < 4:
            weaknesses.append("Teknik uygunluk düşük - akışkan tipi veya boyut uyumsuz")

        if categories["accuracy_metrology"].score >= 8:
            strengths.append("Yüksek ölçüm doğruluğu ve metroloji uygunluğu")
        elif categories["accuracy_metrology"].score < 5:
            weaknesses.append("Ölçüm belirsizliği yüksek veya onay eksikliği")

        if categories["cost"].score >= 7:
            strengths.append("Düşük yatırım ve işletme maliyeti")
        elif categories["cost"].score < 4:
            weaknesses.append("Yüksek yatırım/işletme maliyeti")

        def is_it_high(cat_name):
            return categories.get(cat_name, CategoryScore("_", 0, 0)).score >= 7

        def is_it_low(cat_name):
            return categories.get(cat_name, CategoryScore("_", 10, 0)).score < 5

        if is_it_low("implementability"):
            weaknesses.append("Sahada uygulanabilirlik kısıtlı - tedarik/uzmanlık sorunu olabilir")
        if is_it_high("implementability"):
            strengths.append("Kolay tedarik ve yerel destek mevcut")

        if categories["operational_ease"].score >= 7:
            strengths.append("Düşük basınç kaybı, az bakım, kolay işletme")
        elif categories["operational_ease"].score < 4:
            weaknesses.append("Yüksek basınç kaybı veya bakım gereksinimi")

        return strengths, weaknesses

    def _compute_auxiliary_details(self, meter_key: str, inputs: dict) -> dict:
        meter_data = self.specs["meters"].get(meter_key, {})
        nps = inputs.get("nps", 6)
        qmax = inputs.get("qmax", 100)

        upstream = meter_data.get("min_straight_upstream", 10)
        downstream = meter_data.get("min_straight_downstream", 5)

        if qmax > 0 and "orifice" in meter_key:
            beta = 0.55
            dp_pa = beta ** 2 * qmax * 10
        else:
            dp_pa = 0.05 * qmax

        return {
            "straight_pipe_upstream_diameters": upstream,
            "straight_pipe_downstream_diameters": downstream,
            "straight_pipe_total_m": round((upstream + downstream) * nps * 0.0254, 2) if isinstance(nps, (int, float)) else 0,
            "estimated_dp_bar": round(dp_pa / 100000, 4),
        }
