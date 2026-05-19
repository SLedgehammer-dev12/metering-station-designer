---
name: metering-standards
description: Natural gas and oil metering station standards. Use ONLY when the user asks about metering standards compliance, ISO 5167, AGA 3/7/8/9/11, API MPMS, ASME B31.3/B16.5, IEC 60079, IEC 61511, ISO 15156 (NACE), or meter/pipe design per industry specifications. Do not use for general programming or unrelated topics.
---

# Metering Station Standards Knowledge

## Core Standards by Category

### Flow Measurement (Primary Element)
| Standard | Title | Applies To |
|---|---|---|
| ISO 5167-1:2022 | General principles | All DP meters |
| ISO 5167-2:2022 | Orifice plates | β 0.1–0.75, D ≥ 50mm, Re limits |
| ISO 5167-3 | Nozzles and Venturi nozzles | — |
| ISO 5167-4 | Venturi tubes (classical) | Machined convergent, rough cast |
| ISO 5167-5 | Cone meters (V-Cone) | β 0.45–0.85 |
| AGA Report No. 3 | Orifice metering of natural gas | ANSI/API MPMS Ch.14.3 equivalent |
| AGA Report No. 7 | Turbine meters for gas | Custody transfer |
| AGA Report No. 9 | Ultrasonic meters for gas | Multi-path, custody transfer |
| AGA Report No. 11 | Coriolis meters for gas | Mass-based measurement |

### Gas Properties
| Standard | Title | Notes |
|---|---|---|
| AGA Report No. 8 | Compressibility factor | DETAIL and GROSS methods |
| ISO 12213-2 | Natural gas compressibility | Equivalent to AGA 8 |
| ISO 6976 | Calorific value, density, Wobbe | Gas composition → energy |

### Pipe Design & Materials
| Standard | Title | Key Parameters |
|---|---|---|
| ASME B31.3 | Process piping | Wall thickness: Eq. (3a) |
| ASME B31.4 | Liquid hydrocarbon piping | — |
| ASME B31.8 | Gas transmission piping | Design factor 0.72 |
| ASME B16.5 | Pipe flanges | Class 150–2500, P-T ratings |
| ASME B36.10M | Welded/seamless pipe | Schedule dimensions |
| ISO 15156 / NACE MR0175 | Sour service materials | H₂S limits, hardness ≤ HRC 22 |

### Safety & Metrology
| Standard | Title | Applies To |
|---|---|---|
| IEC 60079-10-1 | Hazardous area classification | Zone, gas group, T class |
| IEC 61511 | Functional safety (SIS) | SIL 1/2/3 via risk graph |
| ISO 5168 | Measurement uncertainty | RSS of component uncertainties |
| OIML R 137 | Gas meters (legal metrology) | Custody transfer type approval |
| API MPMS Ch.4 | Proving systems | Meter calibration |

### Inspection Tolerances (Key Values)

**Orifice Plate (ISO 5167-2 §5):**
- d (bore): ±0.05% or ±0.01mm (larger)
- E (plate thickness): 0.005D ≤ E ≤ 0.02D
- e (edge thickness): 0.005D ≤ E ≤ 0.02D
- Edge sharpness: No visible light reflection (90° test)
- Ra (upstream surface): ≤ 0.4μm for β > 0.6; ≤ 0.8μm for β ≤ 0.6
- Flatness: ≤ 0.01mm per 100mm

**Meter Tube (ISO 5167-2 §6):**
- D (internal diameter): ±0.3% (≥4 angles × 3 axial positions)
- Ovality: ≤ 0.3% D
- Weld protrusion: ≤ 2mm or h/D ≤ 0.015
- Straight length upstream: Per Table 3 (β-dependent, 5D–44D)
- Straight length downstream: ≥ 5D (minimum)

**USM Body (AGA 9 §3-4):**
- Body diameter: ±0.25% D (custody transfer)
- Body ovality: ≤ 0.5% D
- Transducer angular position: ±0.5°
- Transducer axial position: ±0.5mm
- Transducer protrusion: ≤ 1% D (flush mount)

**Flow Conditioners (ISO 5167-1 Table 4):**
- Zanker: Delik toleransı ±2% veya ±0.1mm
- CPA 50E: Merkez delik ±0.2mm
- 19-Tube Bundle: Tube ID ±0.1mm, length 2D ±0.5D

## Units Conventions
- Pressure: barg (gauge) for process; MPa for ASME formulas
- Temperature: °C for input; K for thermodynamic calculations
- Dimensions: mm for pipe/plate; m for lengths
- Flow: Sm³/h (standard) for gas; m³/h for liquid
- Viscosity: cP for liquids; Pa·s for gas
- Density: kg/m³

## Reference Values for QA
- Natural gas at 45 barg, 40°C: Z ≈ 0.92, ρ ≈ 33 kg/m³
- Natural gas at 1 bara, 15°C (std): Z ≈ 0.998, ρ ≈ 0.75 kg/m³
- ASME B31.3 for NPS8, 50 barg, A106 Gr.B: t_min ≈ 4mm
- Orifice β=0.65, Re=10⁶: Cd ≈ 0.602 (RHG)
