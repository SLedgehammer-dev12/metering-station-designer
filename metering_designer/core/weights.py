DEFAULT_WEIGHTS = {
    "technical_fitness": 0.25,
    "accuracy_metrology": 0.25,
    "operational_ease": 0.15,
    "cost": 0.15,
    "implementability": 0.10,
    "project_specific": 0.10,
}


CATEGORY_LABELS_TR = {
    "technical_fitness": "Teknik Uygunluk",
    "accuracy_metrology": "Doğruluk & Metroloji",
    "operational_ease": "İşletme Kolaylığı",
    "cost": "Maliyet",
    "implementability": "Uygulanabilirlik",
    "project_specific": "Proje Özel Faktörler",
}


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        return dict(DEFAULT_WEIGHTS)
    return {k: v / total for k, v in weights.items()}


def weight_name_tr(key: str) -> str:
    return CATEGORY_LABELS_TR.get(key, key)
