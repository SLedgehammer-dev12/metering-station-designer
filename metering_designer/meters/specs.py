import json
import os

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "knowledge")


def load_meter_specs() -> dict:
    path = os.path.join(KNOWLEDGE_DIR, "meter_specs.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_fluid_type(fluid_type: str = None) -> str:
    """Map UI labels (TR/EN) to canonical fluid keys 'gas'/'liquid'."""
    if fluid_type is None:
        return fluid_type
    f = str(fluid_type).strip().lower()
    if f in ("doğal_gaz", "dogal_gaz", "gaz", "gas", "natural_gas"):
        return "gas"
    if f in ("ham_petrol", "sıvı", "sivi", "petrol", "oil", "liquid"):
        return "liquid"
    return fluid_type


def get_meter_keys(fluid_type: str = None) -> list[str]:
    data = load_meter_specs()
    meters = data.get("meters", {})
    if fluid_type:
        ft = normalize_fluid_type(fluid_type)
        if ft == "gas":
            return [k for k, v in meters.items() if "gas" in v.get("fluids", [])]
        if ft == "liquid":
            return [k for k, v in meters.items() if "liquid" in v.get("fluids", [])]
        return []
    return list(meters.keys())


def get_meter_spec(meter_key: str) -> dict:
    data = load_meter_specs()
    return data.get("meters", {}).get(meter_key, {})
