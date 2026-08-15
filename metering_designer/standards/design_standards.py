"""
Design-standard registry (per-meter-type).

After the user picks a metering device the app asks which standard the design
should follow. Each standard profile carries the calculation constraints,
defaults (tap type, design differential pressure) and informational notes used
by the sizing routines and the engineering UI.

Current coverage: orifice (ISO 5167-2 / AGA Report No.3) and ultrasonic
(AGA Report No.9 / ISO 17089). Other meter types intentionally return an empty
list until their profiles are added — the UI hides the selector for them.
"""

# Public profiles keyed by meter type. ``beta_limits`` and ``beta_recommended``
# are (min, max) tuples; ``dp_range_mbar`` is the selectable design pressure
# loss band; ``velocity_range`` applies to USMs; ``notes`` is I18N key.
METER_STANDARDS = {
    "orifice": {
        "iso5167_2": {
            "name": "ISO 5167-2:2022",
            "description_key": "std_orifice_iso_desc",
            "standard_ref": "ISO 5167-2:2022",
            "default_tap": "corner",
            "beta_limits": (0.1, 0.75),
            "beta_recommended": (0.2, 0.65),
            "D_min_mm": 50.0,
            "dp_recommended_mbar": 250,
            "dp_range_mbar": (20, 1000),
            "cd_formula": "Reader-Harris/Gallagher (1998)",
            "notes": ["std_orifice_iso_note1", "std_orifice_iso_note2"],
        },
        "aga3": {
            "name": "AGA Report No.3 / API MPMS Ch.14.3",
            "description_key": "std_orifice_aga_desc",
            "standard_ref": "AGA Report No.3 / API MPMS Ch.14.3",
            "default_tap": "flange",
            "beta_limits": (0.1, 0.75),
            "beta_recommended": (0.2, 0.65),
            "D_min_mm": 50.0,
            "dp_recommended_mbar": 250,
            "dp_range_mbar": (20, 1000),
            "cd_formula": "Reader-Harris/Gallagher (AGA 3, 1992)",
            "notes": ["std_orifice_aga_note1", "std_orifice_aga_note2"],
        },
    },
    "ultrasonic": {
        "aga9": {
            "name": "AGA Report No.9",
            "description_key": "std_usm_aga9_desc",
            "standard_ref": "AGA Report No.9",
            "velocity_range": (0.3, 30.0),
            "notes": ["std_usm_aga9_note1"],
        },
        "iso17089": {
            "name": "ISO 17089-1",
            "description_key": "std_usm_iso_desc",
            "standard_ref": "ISO 17089-1",
            "velocity_range": (0.3, 30.0),
            "notes": ["std_usm_iso_note1"],
        },
    },
}

# Evaluate each meter_key against the right registry bucket (e.g. "v_cone" -> "vcone").
_METER_KEY_ALIASES = {
    "v_cone": "vcone",
}


def _bucket_for(meter_key: str) -> str | None:
    """Resolve a meter key (selection label) to a METER_STANDARDS bucket."""
    key = _METER_KEY_ALIASES.get(meter_key, meter_key)
    for bucket in METER_STANDARDS:
        if bucket in key:
            return bucket
    return None


def list_standards(meter_key: str) -> list[dict]:
    """Return selectable standard option dicts for a meter type.

    Returns [] for meter types whose profiles are not yet implemented (the UI
    keeps the selector hidden in that case).
    """
    bucket = _bucket_for(meter_key)
    if bucket is None:
        return []
    options = []
    for std_id, profile in METER_STANDARDS[bucket].items():
        options.append({
            "id": std_id,
            "name": profile["name"],
            "description_key": profile.get("description_key", ""),
            "standard_ref": profile.get("standard_ref", profile["name"]),
        })
    return options


def get_standard(meter_key: str, standard_id: str | None) -> dict | None:
    """Return the profile dict for a meter + standard, or None.

    A missing/unknown standard falls back to the meter's default so callers
    always get coherent limits.
    """
    bucket = _bucket_for(meter_key)
    if bucket is None:
        return None
    profiles = METER_STANDARDS[bucket]
    if standard_id in profiles:
        return profiles[standard_id]
    default_id = default_standard(meter_key)
    return profiles[default_id] if default_id in profiles else None


def default_standard(meter_key: str) -> str | None:
    """Return the id of the first (default) standard for a meter type."""
    bucket = _bucket_for(meter_key)
    if bucket is None:
        return None
    profiles = METER_STANDARDS[bucket]
    return next(iter(profiles)) if profiles else None