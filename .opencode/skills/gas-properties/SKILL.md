---
name: gas-properties
description: Natural gas thermodynamics and fluid properties. Use ONLY when computing gas compressibility (Z-factor), density, calorific value, Wobbe index, viscosity, or implementing AGA 8/GERG-2008 EOS calculations. Covers metering_designer/fluids/aga8.py, metering_designer/fluids/gas.py, metering_designer/core/backends.py, pyaga8, CoolProp integration.
---

# Natural Gas Properties & Thermodynamics

## Backend Fallback Chain

```
Layer 1 (BEST): pyaga8 (Equinor/NIST)
  Method: AGA8-92DC DETAIL or GERG-2008
  API: comp = Composition(); comp.methane = 0.90; d = Detail(); d.set_composition(comp)
  Units: P in kPa, T in K, density in kmol/m³
  Requires: pip install pyaga8

Layer 2: CoolProp  
  Method: GERG-2008 HEOS, SRK, PR
  API: CP.PropsSI("Z", "P", P_Pa, "T", T_K, fluid_string)
  Units: SI (Pa, K, kg/m³)
  Requires: pip install CoolProp

Layer 3: thermo (Caleb Bell)
  Method: PRMIX EOS, HHV/LHV
  API: thermo.mixture.Mixture(compounds, zs, T, P)
  Requires: pip install thermo

Layer 4: Internal DAK/Papay
  Method: Dranchuk-Abou-Kassem Z-factor correlation
  API: internal calc_density(P_bar, T_C, composition)
  Always available, pure Python
```

## Key Gas Constants
- R = 8.314462618 J/(mol·K)
- Standard conditions: T = 15°C (288.15 K), P = 1.01325 bara
- Natural gas isentropic exponent κ ≈ 1.3

## Critical Properties (Kay's Rule)
T_pc = Σ y_i × T_c_i    (pseudo-critical temperature)
P_pc = Σ y_i × P_c_i    (pseudo-critical pressure)
T_pr = T / T_pc          (pseudo-reduced temperature)
P_pr = P / P_pc          (pseudo-reduced pressure)

## Wichert-Aziz Correction (for acid gases)
ε = 120 × (A^0.9 − A^1.6) + 15 × (B^0.5 − B^4.0)
  where A = y_CO2 + y_H2S, B = y_H2S
T_pc' = T_pc − ε
P_pc' = P_pc × T_pc' / (T_pc + B·(1−B)·ε)

## DAK Z-factor Equation
Z = 1 + T1·ρ_r + T2·ρ_r² − T3·ρ_r⁵ + T4·(1 + A11·ρ_r²)·ρ_r²·exp(−A11·ρ_r²)

Coefficients:
A1=0.3265, A2=−1.0700, A3=−0.5339, A4=0.01569, A5=−0.05165,
A6=0.5475, A7=−0.7361, A8=0.1844, A9=0.1056, A10=0.6134, A11=0.7210

Where:
ρ_r = 0.27·P_pr / (Z·T_pr)   [requires iteration]
T1 = A1 + A2/T_pr + A3/T_pr³
T2 = A4 + A5/T_pr
T3 = A5·A6/T_pr
T4 = A7/T_pr³

Valid range: 1.05 < T_pr < 3.0, 0 < P_pr < 15

## ISO 6976 Calorific Values (MJ/m³ at 15°C, 1.01325 bar)
| Component | Gross CV | Net CV |
|---|---|---|
| CH₄ (C1) | 39.84 | 35.88 |
| C₂H₆ (C2) | 70.29 | 64.35 |
| C₃H₈ (C3) | 101.2 | 93.18 |
| i-C₄H₁₀ | 133.0 | 122.8 |
| n-C₄H₁₀ | 133.0 | 122.8 |
| H₂S | 25.33 | 23.33 |
| N₂, CO₂ | 0 | 0 |

Wobbe Index = Gross CV / √(relative_density)

## pyaga8 API Quick Reference
```python
import pyaga8

comp = pyaga8.Composition()
comp.methane = 0.9137      # MUST sum to exactly 1.0
comp.ethane = 0.0406
comp.nitrogen = 0.0102
comp.carbon_dioxide = 0.0203

d = pyaga8.Detail()
d.set_composition(comp)
d.pressure = 4500.0         # kPa (NOT Pa!)
d.temperature = 313.15      # K
d.calc_density()            # Computes Z and d (density in kmol/m³)
Z = d.z                     # Compressibility factor
rho_kmol_m3 = d.d           # Molar density (kmol/m³)
# Convert: rho_kg_m3 = d.d * M_mix (kg/kmol)
# M_mix from composition: 16.043*0.9137 + 28.013*0.0102 + ...
```

## Density Conversions
P_Pa = Z · n/V[mol/m³] · R[J/mol·K] · T[K]
n/V = P_Pa / (Z · R · T)            [mol/m³]
ρ_kg = n/V · M_mix / 1000           [kg/m³]  (M_mix in g/mol)

## QA Reference Values
```
Composition: 90% CH₄, 4% C₂H₆, 1.5% C₃H₈, 1% N₂, 2% CO₂

At 1.01325 bar, 15°C:  Z ≈ 0.998,  ρ ≈ 0.75 kg/m³
At 45 bar, 40°C:       Z ≈ 0.919,  ρ ≈ 33.4 kg/m³
At 80 bar, 30°C:       Z ≈ 0.830,  ρ ≈ 67.8 kg/m³
M_mix ≈ 17.73 g/mol
Gross CV ≈ 40.8 MJ/m³
```
