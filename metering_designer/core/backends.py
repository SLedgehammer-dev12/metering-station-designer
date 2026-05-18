"""
Multi-backend fallback chain for gas property calculations.

Priority:
  Layer 1: pyaga8 (Equinor) - NIST-certified AGA8 GERG-2008 & DETAIL, Rust
  Layer 2: CoolProp - HEOS/SRK/PR EOS, 100+ fluids
  Layer 3: thermo (Caleb Bell) - HHV/LHV, Wobbe, chemical database  
  Layer 4: Internal DAK/Papay correlation - pure Python, always available
"""

import math

try:
    import pyaga8
    HAS_PYAGA8 = True
except ImportError:
    HAS_PYAGA8 = False

try:
    import CoolProp.CoolProp as CP
    HAS_COOLPROP = True
except ImportError:
    HAS_COOLPROP = False

try:
    import thermo
    HAS_THERMO = True
except ImportError:
    HAS_THERMO = False

try:
    import fluids
    HAS_FLUIDS = True
except ImportError:
    HAS_FLUIDS = False

from metering_designer.fluids.aga8 import calc_density as internal_z

R = 8.314462618

COMPONENT_MAP_PYAGA8 = {
    "C1": "methane", "C2": "ethane", "C3": "propane",
    "iC4": "isobutane", "nC4": "n_butane", "iC5": "isopentane",
    "nC5": "n_pentane", "C6": "hexane", "C6plus": "hexane",
    "N2": "nitrogen", "CO2": "carbon_dioxide", "H2S": "hydrogen_sulfide",
}

CP_FLUID_NAMES = {
    "C1": "Methane", "C2": "Ethane", "C3": "Propane",
    "iC4": "IsoButane", "nC4": "n-Butane", "iC5": "Isopentane",
    "nC5": "n-Pentane", "C6": "n-Hexane",
    "N2": "Nitrogen", "CO2": "CarbonDioxide", "H2S": "HydrogenSulfide",
}


def _make_pyaga8_comp(composition: dict[str, float]) -> "pyaga8.Composition":
    comp = pyaga8.Composition()
    total = 0.0
    for key, name in COMPONENT_MAP_PYAGA8.items():
        mol = composition.get(key, 0)
        if mol > 0:
            setattr(comp, name, mol)
            total += mol
    for key in composition:
        if key not in COMPONENT_MAP_PYAGA8 and composition[key] > 0:
            setattr(comp, "n_butane", getattr(comp, "n_butane", 0) + composition[key])
            total += composition[key]
    if abs(total - 1.0) > 0.001:
        for name in COMPONENT_MAP_PYAGA8.values():
            val = getattr(comp, name, 0)
            if total > 0:
                setattr(comp, name, val / total)
    return comp


def _z_pyaga8_detail(P_kPa: float, T_K: float, composition: dict) -> tuple[float, float, float, str]:
    comp = _make_pyaga8_comp(composition)
    d = pyaga8.Detail()
    d.set_composition(comp)
    d.pressure = P_kPa
    d.temperature = T_K
    d.calc_density()
    Z = d.z
    d_kmol_m3 = d.d

    # M computed from composition (pyaga8 mm needs calc_properties which is slow)
    MOLAR_MASSES = {"C1": 16.043, "C2": 30.07, "C3": 44.096, "iC4": 58.123, "nC4": 58.123,
                    "iC5": 72.15, "nC5": 72.15, "C6": 86.177, "C6plus": 90.0,
                    "N2": 28.013, "CO2": 44.01, "H2S": 34.082}
    total = sum(v for v in composition.values() if v > 0)
    M = sum(composition.get(k, 0) * MOLAR_MASSES.get(k, 0) for k in MOLAR_MASSES)
    M = M / total if total > 0 else 20.0
    return Z, d_kmol_m3, M, "pyaga8 DETAIL (NIST/AGA8-92DC)"


def _z_coolprop(P_Pa: float, T_K: float, composition: dict) -> tuple[float, float, float, str]:
    total = sum(v for v in composition.values() if v > 0)
    x_clean = {CP_FLUID_NAMES.get(k, k): v / total for k, v in composition.items()
               if v > 0 and k in CP_FLUID_NAMES}
    if not x_clean:
        raise ValueError("No CoolProp-compatible components in composition")

    fluids_str = "&".join(x_clean.keys())
    mole_frac = list(x_clean.values())

    try:
        Z = CP.PropsSI("Z", "P", P_Pa, "T", T_K, fluids_str)
        Dmass = CP.PropsSI("D", "P", P_Pa, "T", T_K, fluids_str)
        Mmass = CP.PropsSI("M", "P", P_Pa, "T", T_K, fluids_str)
        return Z, Dmass / Mmass, Mmass * 1000, "CoolProp HEOS (GERG-2008 fallback)"
    except Exception:
        Z_meth = CP.PropsSI("Z", "P", P_Pa, "T", T_K, "Methane")
        D_meth = CP.PropsSI("D", "P", P_Pa, "T", T_K, "Methane")
        return Z_meth, D_meth / 0.016043, 0.016043, "CoolProp Methane-only (mixture failed)"


def _z_thermo(P_Pa: float, T_K: float, composition: dict) -> tuple[float, float, float, str]:
    total = sum(v for v in composition.values() if v > 0)
    if total <= 0:
        raise ValueError("Empty composition")

    x_norm = {k: v / total for k, v in composition.items() if v > 0}
    comp_names = {k: CP_FLUID_NAMES.get(k, k) for k in x_norm}

    try:
        mix = thermo.mixture.Mixture(
            [comp_names[k] for k in x_norm],
            zs=[x_norm[k] for k in x_norm],
            T=T_K, P=P_Pa,
        )
        Z = mix.Z_g
        rho_mol = mix.V_g ** -1 if hasattr(mix, "V_g") else P_Pa / (Z * R * T_K)
        M = mix.MW
        return Z, rho_mol / 1000, M, "thermo PRMIX EOS"
    except Exception as e:
        raise ValueError(f"thermo calculation failed: {e}")


def _z_internal(P_bar: float, T_C: float, composition: dict) -> tuple[float, float, float, str]:
    result = internal_z(P_bar, T_C, composition)
    Z = result.get("Z", 1.0)
    d_kmol = result.get("density_kmol_m3", 0)
    M = result.get("M_mix", 20)
    return Z, d_kmol, M, "Internal DAK/Papay (pure Python)"


def calc_z_factor(P_bar: float, T_C: float, composition: dict[str, float]) -> dict:
    """
    Calculate compressibility factor Z with automatic fallback.
    Returns dict with Z, density (kg/m³), molar mass, backend used.
    """
    T_K = T_C + 273.15
    P_Pa = P_bar * 1e5
    P_kPa = P_bar * 100

    errors = []

    # Layer 1: pyaga8 (best)
    if HAS_PYAGA8 and composition:
        try:
            Z, d_kmol, M, backend = _z_pyaga8_detail(P_kPa, T_K, composition)
            if Z > 0.1 and Z < 3.0:
                return {
                    "Z": round(Z, 6),
                    "density_kg_m3": round(d_kmol * M, 4),
                    "density_kmol_m3": round(d_kmol, 6),
                    "M_mix": round(M, 4),
                    "backend": backend,
                    "backend_layer": 1,
                }
            else:
                errors.append(f"pyaga8 returned invalid Z={Z}")
        except Exception as e:
            errors.append(f"pyaga8: {e}")

    # Layer 2: CoolProp
    if HAS_COOLPROP:
        try:
            Z, d_kmol, M, backend = _z_coolprop(P_Pa, T_K, composition)
            if Z > 0.1 and Z < 3.0:
                return {
                    "Z": round(Z, 6),
                    "density_kg_m3": round(d_kmol * M / 1000 if d_kmol > 0 else 0, 4),
                    "density_kmol_m3": round(d_kmol / 1000 if d_kmol > 0 else 0, 6),
                    "M_mix": round(M / 1000 if M > 1 else M, 4),
                    "backend": backend,
                    "backend_layer": 2,
                }
            else:
                errors.append(f"CoolProp returned invalid Z={Z}")
        except Exception as e:
            errors.append(f"CoolProp: {e}")

    # Layer 3: thermo
    if HAS_THERMO:
        try:
            Z, d_kmol, M, backend = _z_thermo(P_Pa, T_K, composition)
            if Z > 0.1 and Z < 3.0:
                return {
                    "Z": round(Z, 6),
                    "density_kg_m3": round(d_kmol * M, 4),
                    "density_kmol_m3": round(d_kmol, 6),
                    "M_mix": round(M, 4),
                    "backend": backend,
                    "backend_layer": 3,
                }
            else:
                errors.append(f"thermo returned invalid Z={Z}")
        except Exception as e:
            errors.append(f"thermo: {e}")

    # Layer 4: Internal fallback
    try:
        Z, d_kmol, M, backend = _z_internal(P_bar, T_C, composition)
        return {
            "Z": round(Z, 6),
            "density_kg_m3": round(d_kmol * M, 4),
            "density_kmol_m3": round(d_kmol, 6),
            "M_mix": round(M, 4),
            "backend": backend,
            "backend_layer": 4,
            "fallback_errors": errors if errors else [],
        }
    except Exception as e:
        errors.append(f"Internal: {e}")
        return {
            "Z": 1.0,
            "density_kg_m3": 0.0,
            "density_kmol_m3": 0.0,
            "M_mix": 20.0,
            "backend": "None (all backends failed)",
            "backend_layer": 5,
            "errors": errors,
        }


def calc_heating_value(composition: dict[str, float]) -> dict:
    """Calculate gross/net heating value and Wobbe index."""
    cv_data = {
        "C1": [39.84, 35.88], "C2": [70.29, 64.35], "C3": [101.2, 93.18],
        "iC4": [133.0, 122.8], "nC4": [133.0, 122.8], "iC5": [163.5, 151.3],
        "nC5": [163.5, 151.3], "C6": [194.0, 179.8], "C6plus": [210.0, 195.0],
        "H2S": [25.33, 23.33], "N2": [0, 0], "CO2": [0, 0],
    }
    if HAS_THERMO:
        try:
            total = sum(v for v in composition.values() if v > 0)
            x_norm = {k: v / total for k, v in composition.items() if v > 0}
            from thermo import Mixture
            mix = Mixture(
                [CP_FLUID_NAMES.get(k, k) for k in x_norm],
                zs=[x_norm[k] for k in x_norm],
            )
            return {
                "gross_CV_MJ_m3": round(mix.Hc / 1e6, 4) if hasattr(mix, "Hc") else 0,
                "net_CV_MJ_m3": round(mix.LHV_mass * mix.MW / 1000, 4) if hasattr(mix, "LHV_mass") else 0,
                "backend": "thermo library",
            }
        except Exception:
            pass

    gross = sum(composition.get(c, 0) * v[0] for c, v in cv_data.items())
    net = sum(composition.get(c, 0) * v[1] for c, v in cv_data.items())
    return {
        "gross_CV_MJ_m3": round(gross, 4),
        "net_CV_MJ_m3": round(net, 4),
        "backend": "Internal ISO 6976 data",
    }


def get_backend_status() -> dict:
    return {
        "pyaga8": HAS_PYAGA8,
        "coolprop": HAS_COOLPROP,
        "thermo": HAS_THERMO,
        "fluids": HAS_FLUIDS,
        "internal_dak": True,
    }
