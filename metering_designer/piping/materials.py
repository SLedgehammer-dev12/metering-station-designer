"""
Material selection per ISO 15156 / NACE MR0175 for sour service.
"""

MATERIAL_RECOMMENDATIONS = {
    "carbon_steel_sweet": {
        "material_key": "A106_GrB",
        "name": "A106 Grade B Karbon Çelik",
        "standard": "ASTM A106 Gr.B",
        "applies_to": ["sweet_gas", "sweet_liquid", "non_sour"],
        "max_temp_C": 400,
        "min_temp_C": -29,
        "h2s_limit_ppm": 0,
        "nace_standard": "Not required",
    },
    "carbon_steel_low_temp": {
        "material_key": "A333_Gr6",
        "name": "A333 Grade 6 Düşük Sıcaklık Karbon Çelik",
        "standard": "ASTM A333 Gr.6",
        "applies_to": ["sweet_gas", "sweet_liquid", "non_sour", "low_temp"],
        "max_temp_C": 400,
        "min_temp_C": -46,
        "h2s_limit_ppm": 0,
        "nace_standard": "Not required",
    },
    "carbon_steel_sour": {
        "material_key": "A106_GrB",
        "name": "A106 Gr.B + NACE MR0175 / ISO 15156",
        "standard": "ASTM A106 Gr.B (NACE compliant)",
        "applies_to": ["sour_gas", "sour_liquid"],
        "max_temp_C": 260,
        "min_temp_C": -29,
        "h2s_limit_ppm": 100000,
        "nace_standard": "ISO 15156-2 / NACE MR0175",
        "notes": "Hardness ≤ HRC 22, SSC resistant per NACE TM0177",
    },
    "ss_316_sour": {
        "material_key": "A312_TP316",
        "name": "SS 316 (NACE MR0175)",
        "standard": "ASTM A312 TP316",
        "applies_to": ["sour_gas", "sour_liquid", "high_temp"],
        "max_temp_C": 450,
        "min_temp_C": -196,
        "h2s_limit_ppm": 100000,
        "nace_standard": "ISO 15156-3",
        "notes": "Solution annealed condition, chloride limited application",
    },
    "duplex_2205_sour": {
        "material_key": "A312_Duplex_2205",
        "name": "Duplex SS 2205 (NACE MR0175)",
        "standard": "ASTM A790 S31803",
        "applies_to": ["sour_gas", "sour_liquid", "high_pressure", "high_temp", "chlorides", "offshore"],
        "max_temp_C": 315,
        "min_temp_C": -50,
        "h2s_limit_ppm": 100000,
        "nace_standard": "ISO 15156-3",
        "notes": "PREN ≥ 35, high strength, SSC resistant. Suitable for high chloride.",
    },
    "super_duplex_2507": {
        "material_key": "A312_SDSS_2507",
        "name": "Super Duplex SS 2507 (UNS S32750)",
        "standard": "ASTM A790 S32750",
        "applies_to": ["sour_gas", "sour_liquid", "high_chloride", "offshore", "subsea"],
        "max_temp_C": 300,
        "min_temp_C": -50,
        "h2s_limit_ppm": 500000,
        "nace_standard": "ISO 15156-3 Level VII",
        "notes": "PREN > 40, maximum chloride + H₂S resistance. Premium offshore/subsea.",
    },
    "ss_316L_sour": {
        "material_key": "A312_TP316L",
        "name": "SS 316L (Low Carbon, NACE)",
        "standard": "ASTM A312 TP316L",
        "applies_to": ["sour_gas", "sour_liquid", "chlorides_limited", "welded"],
        "max_temp_C": 400,
        "min_temp_C": -196,
        "h2s_limit_ppm": 100000,
        "nace_standard": "ISO 15156-3",
        "notes": "Low carbon for welded joints. Chloride limited (<1000 ppm @ 60°C, <100 ppm @ 150°C).",
    },
    "carbon_steel_h2s_restricted": {
        "material_key": "A106_GrB_SSC",
        "name": "A106 Gr.B (SSC Tested + HIC Resistant)",
        "standard": "ASTM A106 Gr.B + NACE TM0284",
        "applies_to": ["sour_gas", "sour_liquid", "restricted_sour"],
        "max_temp_C": 260,
        "min_temp_C": -29,
        "h2s_limit_ppm": 50000,
        "nace_standard": "ISO 15156-2 / NACE MR0175 + TM0284",
        "notes": "HIC tested per NACE TM0284. Hardness ≤ HRC 22. SSC tested per TM0177. Max 50,000 ppm H₂S.",
    },
    "api_5l_x52_sour": {
        "material_key": "API_5L_X52",
        "name": "API 5L X52 PSL2 + NACE SSC Test",
        "standard": "API 5L X52 PSL2 + NACE TM0177",
        "applies_to": ["sour_gas", "high_strength"],
        "max_temp_C": 400,
        "min_temp_C": -30,
        "h2s_limit_ppm": 50000,
        "nace_standard": "ISO 15156-2 / NACE MR0175",
        "notes": "Hardness ≤ HRC 22, with SSC testing per NACE TM0177. Max 50,000 ppm H₂S.",
    },
    "api_5l_b_sweet": {
        "material_key": "API_5L_B",
        "name": "API 5L B PSL2 — Düşük Basınç",
        "standard": "API 5L B PSL2",
        "applies_to": ["sweet_gas", "sweet_liquid", "non_sour", "low_pressure"],
        "max_temp_C": 400, "min_temp_C": -30,
        "h2s_limit_ppm": 100,
        "nace_standard": "ISO 15156-2 / NACE MR0175 (SSC test ile)",
        "notes": "Düşük mukavemetli hat borusu. Sour servis için SSC testi önerilir.",
    },
    "api_5l_x42": {
        "material_key": "API_5L_X42",
        "name": "API 5L X42 PSL2 — Orta Basınç",
        "standard": "API 5L X42 PSL2",
        "applies_to": ["sweet_gas", "sweet_liquid", "non_sour"],
        "max_temp_C": 400, "min_temp_C": -30,
        "h2s_limit_ppm": 500,
        "nace_standard": "ISO 15156-2 / NACE MR0175 (SSC test ile)",
    },
    "api_5l_x46": {
        "material_key": "API_5L_X46",
        "name": "API 5L X46 PSL2 — Orta-Yüksek Basınç",
        "standard": "API 5L X46 PSL2",
        "applies_to": ["sweet_gas", "sweet_liquid"],
        "max_temp_C": 400, "min_temp_C": -30,
        "h2s_limit_ppm": 1000,
        "nace_standard": "ISO 15156-2 / NACE MR0175 (SSC test ile)",
    },
    "api_5l_x56": {
        "material_key": "API_5L_X56",
        "name": "API 5L X56 PSL2 — Yüksek Basınç",
        "standard": "API 5L X56 PSL2",
        "applies_to": ["sweet_gas", "sweet_liquid", "high_strength"],
        "max_temp_C": 400, "min_temp_C": -30,
        "h2s_limit_ppm": 5000,
        "nace_standard": "ISO 15156-2 / NACE MR0175 (SSC test zorunlu)",
    },
    "api_5l_x60": {
        "material_key": "API_5L_X60",
        "name": "API 5L X60 PSL2 — Yüksek Basınç",
        "standard": "API 5L X60 PSL2",
        "applies_to": ["sweet_gas", "sweet_liquid", "high_strength"],
        "max_temp_C": 400, "min_temp_C": -30,
        "h2s_limit_ppm": 5000,
        "nace_standard": "ISO 15156-2 / NACE MR0175 (SSC test zorunlu)",
    },
    "api_5l_x65": {
        "material_key": "API_5L_X65",
        "name": "API 5L X65 PSL2 — Çok Yüksek Basınç",
        "standard": "API 5L X65 PSL2",
        "applies_to": ["sweet_gas", "sweet_liquid", "high_strength"],
        "max_temp_C": 400, "min_temp_C": -30,
        "h2s_limit_ppm": 3000,
        "nace_standard": "ISO 15156-2 / NACE MR0175 (SSC test zorunlu)",
    },
    "api_5l_x70": {
        "material_key": "API_5L_X70",
        "name": "API 5L X70 PSL2 — Ultra Yüksek Basınç",
        "standard": "API 5L X70 PSL2",
        "applies_to": ["sweet_gas", "sweet_liquid", "high_strength", "offshore"],
        "max_temp_C": 400, "min_temp_C": -30,
        "h2s_limit_ppm": 1000,
        "nace_standard": "Restricted per ISO 15156-2. Requires special qualification for sour service.",
        "notes": "Sour servis kısıtlı (H₂S < 1000 ppm). Özel yeterlilik gerekir.",
    },
    "api_5l_x80": {
        "material_key": "API_5L_X80",
        "name": "API 5L X80 PSL2 — Maksimum Dayanım",
        "standard": "API 5L X80 PSL2",
        "applies_to": ["sweet_gas", "high_strength", "ultimate_pressure"],
        "max_temp_C": 400, "min_temp_C": -20,
        "h2s_limit_ppm": 100,
        "nace_standard": "NOT recommended for sour service per ISO 15156-2",
        "notes": "Sour servis için ÖNERİLMEZ. Sadece sweet gaz hatları.",
    },
}


def select_material(
    h2s: bool = False,
    h2s_ppm: float = 0.0,
    min_temp_C: float = -20,
    max_temp_C: float = 100,
    is_gas: bool = True,
    high_pressure: bool = False,
    has_chlorides: bool = False,
    chloride_ppm: float = 0,
    offshore: bool = False,
) -> dict:
    candidates = []

    for key, mat in MATERIAL_RECOMMENDATIONS.items():
        if h2s and h2s_ppm > mat["h2s_limit_ppm"]:
            continue
        if not h2s and "sweet" not in str(mat["applies_to"]).lower() and "non_sour" not in str(mat["applies_to"]).lower():
            continue
        if h2s and has_chlorides and "chlorides" in key:
            pass  # Keep chloride-compatible materials
        if h2s and has_chlorides and "chlorides_limited" in str(mat.get("notes", "")) and chloride_ppm > 1000:
            continue  # Skip chloride-limited materials for high chloride
        if max_temp_C > mat["max_temp_C"]:
            continue
        if min_temp_C < mat["min_temp_C"]:
            continue
        if offshore and "offshore" in str(mat.get("applies_to", [])):
            mat["score"] = mat.get("score", 0) + 3

        score = 5
        if h2s:
            if mat["h2s_limit_ppm"] >= 100000:
                score += 3
            if has_chlorides and "Duplex" in mat.get("name", ""):
                score += 2
            if has_chlorides and "316" in mat.get("name", "") and chloride_ppm > 1000:
                score -= 2
                continue
            if "HIC" in mat.get("name", "") and h2s_ppm > 50000:
                score += 1
        else:
            score += 2

        candidates.append({
            "key": key,
            "name": mat["name"],
            "standard": mat["standard"],
            "max_temp_C": mat["max_temp_C"],
            "min_temp_C": mat["min_temp_C"],
            "nace": mat["nace_standard"],
            "score": score,
        })

    candidates.sort(key=lambda x: -x["score"])
    return candidates[0] if candidates else {
        "key": "A106_GrB",
        "name": "A106 Grade B",
        "standard": "ASTM A106 Gr.B",
        "nace": "Not applicable",
    }
