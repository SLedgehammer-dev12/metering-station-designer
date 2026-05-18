# Changelog

All notable changes to Metering Station Designer.

## v1.0.0 (2026-05-18) — Initial Release

### Core Engine
- 6-category weighted scoring engine (Technical Fitness, Accuracy & Metrology, Operational Ease, Cost, Implementability, Project Specific)
- 30+ sub-criteria evaluated per meter type
- Tier classification: ★★★ Optimal (85+), ★★☆ Good (70-85), ★☆☆ Adequate (50-70), — Not Recommended (<50)
- 8 supported meter types: Orifice, Ultrasonic, Turbine, Coriolis, PD, Vortex, V-Cone, Venturi

### Gas Properties
- NIST-certified Z-factor via pyaga8 (Equinor/Equinor)
- 4-layer automatic fallback: pyaga8 → CoolProp → thermo → Internal DAK/Papay
- ISO 6976 gas composition, heating value, Wobbe Index
- Kay's rule + Wichert-Aziz correction for acid gases

### Detailed Meter Sizing
- **Orifice**: β ratio, Cd (Reader-Harris/Gallagher), expansibility ε, permanent ΔP
- **Ultrasonic**: Path configuration, k-factor, velocity check per AGA 9
- **Turbine**: K-factor, bearing life estimate, over-range protection
- **Coriolis**: Meter size selection, zero drift effect, tube condition
- **PD Meter**: Slip estimation, viscosity effect, K-factor
- **Vortex**: Frequency, Strouhal number, v_min limit, K-factor
- **V-Cone**: β ratio, Cd, permanent pressure loss (very low)
- **Venturi (Classical)**: Cd=0.995, β=0.5, machined convergent

### Pipe & Flange Design
- ASME B31.3 wall thickness (Eq. 3a) with corrosion allowance + mill tolerance
- ASME B16.5 P-T rating interpolation → flange class selection
- Schedule recommendation per ASME B36.10M
- Materials: A106 Gr.B, A333 Gr.6, SS304/316/321, Duplex 2205, SuperDuplex 2507

### Material Selection (ISO 15156 / NACE MR0175)
- Sour service (H₂S) with HIC/SSC testing awareness
- Chloride-aware selection (316L vs Duplex vs SuperDuplex)
- Offshore/subsea material recommendations

### Flow Conditioner Scoring
- 5 conditioner types: CPA 50E, Zanker Plate, 19-Tube Bundle, Perforated Plate, Gallagher Slotted
- 6-criteria weighted scoring: pressure loss, straight pipe reduction, ISO compliance, maintenance, cost, installation

### Safety & Metrology
- **Ex Classification**: IEC 60079-10-1, gas group (IIA/IIB/IIC), temperature class (T1-T6), Zone 1/2
- **SIL Assessment**: IEC 61511 risk graph method, SIL 1/2/3
- **Uncertainty Budget**: ISO 5168 format, 7 component types, GC composition component included

### Inspection Module
- Dynamic checklist builder — generates measurement forms from meter + conditioner selection
- 6 inspection databases: orifice plate, meter tube, USM body/transducers, turbine body, Coriolis body, flow conditioners (Zanker/CPA/tube bundle/perforated), piping
- 8 tolerance types: percentage_or_absolute, range_from_D, percentage, conditional_max, max_value, min_value, range, min_length_D, enum
- Geometric deviation → uncertainty impact calculation per ISO 5168
- 2-tab UI: Measurement Input + Evaluation Results
- Excel compliance report with per-clause standard violation tracking

### Reports
- **TXT**: Summary text report
- **Excel**: 5-sheet detailed report (overview, scoring, criteria, conditioners, standards)
- **PDF**: 3-page engineering summary per reportlab
- **JSON**: Full project serialization for save/load

### UI & UX
- 8-page Streamlit interface with Plotly radar charts
- TR/EN language toggle (30+ translated keys)
- Project Save/Load via JSON
- Parallel comparison mode — side-by-side meter analysis with trade-off insights
- Input validation on all process data entry

### Testing
- 27 test suite (scoring, sizing, inspection, materials, backends, validation)
- 100% test pass rate

### Deployment
- Dockerfile for containerized deployment
- `build_windows.bat` — Nuitka standalone Windows .exe build
- `installer.iss` — Inno Setup Windows installer script
- `.github/workflows/test.yml` — CI test pipeline
- `.github/workflows/build.yml` — Windows release build pipeline
