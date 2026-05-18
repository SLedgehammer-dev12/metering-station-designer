"""
Input validation module for metering station designer.
Validates all user inputs with detailed error messages.
"""

from typing import Any, Optional


class ValidationError(Exception):
    pass


def validate_project_inputs(project: dict) -> list[str]:
    errors = []
    if not project.get("name"):
        errors.append("Proje adı zorunludur.")
    if not project.get("location"):
        errors.append("Konum/saha bilgisi önerilir.")
    return errors


def validate_process_inputs(proc: dict) -> list[str]:
    errors = []

    # Fluid type
    ft = proc.get("fluid_type", "")
    if ft not in ("doğal_gaz", "ham_petrol", "gas", "liquid"):
        errors.append(f"Geçersiz akışkan tipi: {ft}")

    # NPS
    nps = proc.get("nps", 0)
    if not isinstance(nps, (int, float)) or nps < 0.5 or nps > 48:
        errors.append(f"NPS {nps} geçerli aralık dışında (0.5-48)")

    # Pressure
    design_p = proc.get("design_p_bar", 0)
    oper_p = proc.get("oper_p_bar", 0)
    if design_p <= 0:
        errors.append("Tasarım basıncı > 0 olmalıdır.")
    if oper_p <= 0:
        errors.append("İşletme basıncı > 0 olmalıdır.")
    if design_p < oper_p:
        errors.append(f"Tasarım basıncı ({design_p}) işletme basıncından ({oper_p}) küçük olamaz.")
    if design_p > 420:
        errors.append(f"Tasarım basıncı {design_p} bar ASME B31.3 sınırlarını aşıyor (max 420 bar).")

    # Temperature
    design_t = proc.get("design_t_c", 0)
    oper_t = proc.get("oper_t_c", 0)
    if design_t < -46 or design_t > 700:
        errors.append(f"Tasarım sıcaklığı {design_t}°C malzeme sınırları dışında (-46 to 700°C).")

    # Flow
    qmax = proc.get("qmax", 0)
    qmin = proc.get("qmin", 0)
    if qmax <= 0:
        errors.append("Q max > 0 olmalıdır.")
    if qmin <= 0:
        errors.append("Q min > 0 olmalıdır.")
    if qmin > qmax:
        errors.append(f"Q min ({qmin}) Q max'tan ({qmax}) büyük olamaz.")

    # Composition validation for gas
    if ft in ("doğal_gaz", "gas"):
        comp = proc.get("composition", {})
        if comp:
            total = sum(v for v in comp.values() if v > 0)
            if abs(total - 100.0) > 1.0 and abs(total - 1.0) > 0.02:
                errors.append(f"Gaz kompozisyonu toplamı {total:.1f}% (100% olmalıdır).")
            if total > 100.5 or total < 99.5:
                pass

            for c, v in comp.items():
                if v < 0:
                    errors.append(f"Bileşen {c} negatif olamaz: {v}")
                if v > 100:
                    errors.append(f"Bileşen {c} 100%'ü aşamaz: {v}")

    return errors


def validate_requirements(req: dict) -> list[str]:
    errors = []

    ex_zone = req.get("ex_zone", "")
    if ex_zone not in ("zone_0", "zone_1", "zone_2", "none", ""):
        errors.append(f"Geçersiz Ex zone: {ex_zone}")

    target_unc = req.get("target_uncertainty", 1.0)
    if target_unc <= 0 or target_unc > 10:
        errors.append(f"Hedef belirsizlik {target_unc}% geçerli aralık dışında (0-10%).")

    h2s_ppm = req.get("h2s_ppm", 0)
    if h2s_ppm < 0:
        errors.append("H₂S konsantrasyonu negatif olamaz.")
    if h2s_ppm > 1000000:
        errors.append(f"H₂S {h2s_ppm} ppm gerçekçi değil (>1M ppm).")

    ambient_min = req.get("ambient_min_C", -10)
    ambient_max = req.get("ambient_max_C", 45)
    if ambient_min > ambient_max:
        errors.append(f"Min sıcaklık ({ambient_min}) max'tan ({ambient_max}) büyük olamaz.")
    if ambient_min < -60 or ambient_max > 70:
        errors.append("Çevre sıcaklığı -60 ile +70°C arasında olmalıdır.")

    site_limit = req.get("site_length_limit_m", 0)
    if site_limit < 0:
        errors.append("Saha düz boru limiti negatif olamaz.")

    return errors


def validate_all(
    project: Optional[dict] = None,
    process: Optional[dict] = None,
    requirements: Optional[dict] = None,
) -> list[str]:
    errors = []
    if project:
        errors.extend(validate_project_inputs(project))
    if process:
        errors.extend(validate_process_inputs(process))
    if requirements:
        errors.extend(validate_requirements(requirements))
    return errors


def check_composition_sanity(composition: dict) -> list[str]:
    warnings = []
    c1 = composition.get("C1", 0)
    h2s = composition.get("H2S", 0) 
    co2 = composition.get("CO2", 0)
    n2 = composition.get("N2", 0)

    if c1 < 70:
        warnings.append(f"CH₄ oranı düşük (%{c1:.1f}): düşük ısıl değer beklenir.")
    if h2s > 5:
        warnings.append(f"H₂S yüksek (%{h2s:.1f}): sour servis, özel malzeme gereksinimi.")
    if co2 > 20:
        warnings.append(f"CO₂ yüksek (%{co2:.1f}): düşük ısıl değer + korozyon riski.")
    if n2 > 15:
        warnings.append(f"N₂ yüksek (%{n2:.1f}): aşırı inert, düşük ısıl değer.")

    return warnings
