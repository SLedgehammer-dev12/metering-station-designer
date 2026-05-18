import json
import os

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "knowledge")


def load_meter_specs() -> dict:
    path = os.path.join(KNOWLEDGE_DIR, "meter_specs.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_meter_keys(fluid_type: str = None) -> list[str]:
    data = load_meter_specs()
    meters = data.get("meters", {})
    if fluid_type:
        return [
            k for k, v in meters.items()
            if fluid_type.startswith("gas") and "gas" in v.get("fluids", [])
            or fluid_type.startswith("liquid") and "liquid" in v.get("fluids", [])
        ]
    return list(meters.keys())


def get_meter_spec(meter_key: str) -> dict:
    data = load_meter_specs()
    return data.get("meters", {}).get(meter_key, {})
