"""
Multi-backend fallback chain for gas property calculations.

Priority:
  Layer 1: pyaga8 (Equinor) - NIST-certified AGA8 GERG-2008 & DETAIL, Rust
  Layer 2: CoolProp - HEOS/SRK/PR EOS, 100+ fluids
  Layer 3: thermo (Caleb Bell) - HHV/LHV, Wobbe, chemical database  
  Layer 4: Internal DAK/Papay correlation - pure Python, always available
"""

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
from metering_designer.fluids.data import get_molar_masses, get_cv_data
from metering_designer.core.result import Result

R = 8.314462618
DATASET_VERSION = "1.0"

# pyaga8 Detail supports the full 21-component GERG-2008 set. Every key the
# engine can emit must map to its pyaga8 field so unknown components are never
# silently folded into n_butane (which distorts Pc/Tc and molar mass).
COMPONENT_MAP_PYAGA8 = {
    "C1": "methane", "C2": "ethane", "C3": "propane",
    "iC4": "isobutane", "nC4": "n_butane", "iC5": "isopentane",
    "nC5": "n_pentane", "C6": "hexane", "C6plus": "hexane",
    "N2": "nitrogen", "CO2": "carbon_dioxide", "H2S": "hydrogen_sulfide",
    "H2": "hydrogen", "He": "helium", "Ar": "argon", "O2": "oxygen",
    "CO": "carbon_monoxide", "H2O": "water",
    "nC7": "heptane", "C7": "heptane", "C8": "octane",
    "C9": "nonane", "C10": "decane",
}

CP_FLUID_NAMES = {
    "C1": "Methane", "C2": "Ethane", "C3": "Propane",
    "iC4": "IsoButane", "nC4": "n-Butane", "iC5": "Isopentane",
    "nC5": "n-Pentane", "C6": "n-Hexane",
    "N2": "Nitrogen", "CO2": "CarbonDioxide", "H2S": "HydrogenSulfide",
    "H2": "Hydrogen", "He": "Helium", "Ar": "Argon", "O2": "Oxygen",
    "CO": "CarbonMonoxide", "H2O": "Water",
    "nC7": "n-Heptane", "C7": "n-Heptane", "C8": "n-Octane",
    "C9": "n-Nonane", "C10": "n-Decane",
}


def _make_pyaga8_comp(composition: dict[str, float]) -> "pyaga8.Composition":
    comp = pyaga8.Composition()
    total = 0.0
    for key, name in COMPONENT_MAP_PYAGA8.items():
        mol = composition.get(key, 0)
        if mol > 0:
            setattr(comp, name, mol)
            total += mol
    if abs(total - 1.0) > 0.001 and total > 0:
        for name in COMPONENT_MAP_PYAGA8.values():
            val = getattr(comp, name, 0)
            setattr(comp, name, val / total)
    # pyaga8 panics when fractions do not sum to exactly 1.0; force the last
    # nonzero component to absorb any floating-point residual.
    names = [n for n in COMPONENT_MAP_PYAGA8.values() if getattr(comp, n, 0) > 0]
    if names:
        remaining = 1.0 - sum(getattr(comp, n, 0) for n in names[:-1])
        setattr(comp, names[-1], max(0.0, remaining))
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
    MOLAR_MASSES = get_molar_masses()
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

    try:
        # PropsSI has no mole-fraction argument; pass the composition through
        # AbstractState so mixture Z/density are computed at the real mole
        # fractions instead of failing and falling back to pure methane.
        AS = CP.AbstractState("HEOS", fluids_str)
        AS.set_mole_fractions(list(x_clean.values()))
        AS.update(CP.PT_INPUTS, P_Pa, T_K)
        Z = AS.keyed_output(CP.iZ)
        Dmass = AS.keyed_output(CP.iDmass)
        MOLAR_MASSES = get_molar_masses()
        # Molar mass from the internal table (g/mol == kg/kmol numerically).
        M_gmol = sum(composition.get(k, 0) * MOLAR_MASSES.get(k, 0)
                     for k in MOLAR_MASSES) / total if total > 0 else 20.0
        # Contract: d_kmol in kmol/m³, M in g/mol.
        return Z, Dmass / M_gmol, M_gmol, "CoolProp HEOS (GERG-2008 mixture)"
    except Exception:
        Z_meth = CP.PropsSI("Z", "P", P_Pa, "T", T_K, "Methane")
        D_meth = CP.PropsSI("D", "P", P_Pa, "T", T_K, "Methane")
        M_mmol = 0.016043
        return Z_meth, D_meth / (M_mmol * 1000), M_mmol * 1000, "CoolProp Methane-only (mixture failed)"


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


def calc_speed_of_sound_pyaga8(P_bar: float, T_C: float, composition: dict) -> float | None:
    """Real-gas speed of sound via pyaga8 Detail ``w`` (m/s), or None.

    The ideal-gas formula c = sqrt(kappa·R·T/M) ignores the compressibility
    gradient and is several percent off at high pressure. pyaga8 exposes the
    GERG-2008 acoustic speed directly, so use it when available.
    """
    if not HAS_PYAGA8:
        return None
    try:
        comp = _make_pyaga8_comp(composition)
        d = pyaga8.Detail()
        d.set_composition(comp)
        d.pressure = P_bar * 100
        d.temperature = T_C + 273.15
        d.calc_density()
        d.calc_properties()
        w = getattr(d, "w", None)
        return float(w) if w is not None else None
    except BaseException:
        # pyaga8 may panic (BaseException) on unsupported compositions.
        return None


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
        except BaseException as e:
            # pyaga8 raises PanicException (BaseException) on unnormalized or
            # unsupported compositions — must not crash the fallback chain.
            errors.append(f"pyaga8 panic: {e}")

    # Layer 2: CoolProp
    if HAS_COOLPROP:
        try:
            Z, d_kmol, M, backend = _z_coolprop(P_Pa, T_K, composition)
            if Z > 0.1 and Z < 3.0:
                result = {
                    "Z": round(Z, 6),
                    "density_kg_m3": round(d_kmol * M, 4),
                    "density_kmol_m3": round(d_kmol, 6),
                    "M_mix": round(M, 4),
                    "backend": backend,
                    "backend_layer": 2,
                }
                if "Methane-only" in backend:
                    result["warnings"] = [
                        "CoolProp mixture EOS failed — using pure methane Z-factor. "
                        "Results may be inaccurate for non-standard gas compositions."
                    ]
                return result
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
    cv_data = get_cv_data()
    total = sum(v for v in composition.values() if v > 0)
    if total <= 0:
        return {
            "gross_CV_MJ_m3": 0,
            "net_CV_MJ_m3": 0,
            "backend": "Internal ISO 6976 data (empty composition)",
        }
    # Normalize fraction-type (mole fraction 0..1) vs percent-type (sum=100).
    # The 'thermo' library branch is intentionally not used: its Hc/LHV
    # attributes are unit-inconsistent (J/kg, sign-reversed) and unreliable
    # across versions, so the certified ISO 6976 internal data is always used.
    x_norm = {k: v / total for k, v in composition.items() if v > 0 and k in cv_data}

    gross = sum(x_norm.get(c, 0) * v[0] for c, v in cv_data.items())
    net = sum(x_norm.get(c, 0) * v[1] for c, v in cv_data.items())
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


def calc_z_factor_result(P_bar: float, T_C: float, composition: dict[str, float]) -> Result:
    """Calculate Z-factor with provenance tracking."""
    import datetime
    result = Result()
    try:
        data = calc_z_factor(P_bar, T_C, composition)
        result.data = data
        backend_layer = data.get("backend_layer", 4)
        backend_name = data.get("backend", "internal")
        result.add_provenance(
            function_name="calc_z_factor",
            parameters={"P_bar": P_bar, "T_C": T_C},
            standard_ref=f"AGA 8:1994 (backend_layer={backend_layer}, {backend_name})",
        )
        if data.get("Z", 1.0) <= 0.1 or data.get("Z", 1.0) >= 3.0:
            result.warnings.append(f"Z-factor out of expected range: {data.get('Z')}")
        if "errors" in data:
            result.errors.extend(data["errors"])
        if "warnings" in data:
            result.warnings.extend(data["warnings"])
    except Exception as e:
        result.errors.append(str(e))
    return result
