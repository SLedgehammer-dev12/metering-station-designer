# Changelog

All notable changes to Metering Station Designer.

## Unreleased

### UI Stability & Unit Selection
- **Stable widget identities**: all Streamlit widgets across `app.py` + 8 pages now carry explicit `key=` (nav buttons, nav radio, unit selectors). Previously, widgets without keys got position-based auto-IDs, so a change in the widget tree above a nav button (e.g. the H2S toggle or fluid composition grid) silently shifted the button's ID and browser click-through broke. Sidebar page radio is pre-synced (`page_nav_radio`) and all `rerun()`s follow it.
- **Selectable process units with live conversion** on `02_process.py`: pressure (`barg/psig/kPa/MPa`), temperature (`°C/°F/K`) and flow (`Sm³/h/m³/h/MMscf/h`) pickers; changing a unit immediately re-displays the field value in the new unit via `convert_display()` (pint) while the underlying `proc[]` values stay SI (`bar`, `°C`, `Sm³/h`). `scf`/`mmscf` defined in `core/units.py`.
- **Inspection measurement-point schematics** (`08_inspection.py`): each measurement parameter now draws a "where to measure" figure — pipe cross-section with angular points (0°/45°/90°/135°) plus axial measurement planes in D, colored by inspection status (PASS/FAIL/PENDING). Rendered via `render_measurement_points_schematic()` in `instruments/schematic.py`.

### Flow Conditioner Selection & Layout
- **User-selectable flow conditioner** on the Engineering page (`06_engineering.py`): pick none/Zanker/CPA 50E/Gallagher/19-Tube Bundle/Perforated Plate, and straight-pipe requirements recalculate live (upstream/downstream diameters + meters).
- `calc_straight_pipe()` accepts `with_conditioner` and returns `with_conditioner`/`conditioner_notes` fields; Gallagher reduction per AGA 9, Zanker/CPA per ISO 5167-1 Table 4.
- **Instrument placement database** (`knowledge/instrument_placements.json`) for 8 meter types (PT/TT/dP position in diameters, auto-tags, standard refs, TR/EN notes) with `metering_designer/instruments/layout.py` (`compute_instrument_layout`, `summarize_layout`). Conditioner adds a dedicated upstream PT.
- **SFG schematic** (`metering_designer/instruments/schematic.py`): single-line matplotlib drawing with upstream disturbance glyphs, flow conditioner symbol, per-meter drawing (plate/venturi/cone/USM/turbine/coriolis/vortex/PD), instrument bubble symbols + tags, straight-pipe dimension lines, and manufacturing-tolerance callout box; PNG serialization for reports.

### Full i18n (Turkish / English)
- `core/i18n.py` now hosts **300+ keys** in both TR and EN (parity enforced by `test_i18n_full_coverage`).
- All 8 Streamlit pages **and** the 3 result components (`score_table`, `radar_chart`, `justification_card`) render through `get_text()`; language toggle updates header/nav/pages/table columns/help/validation messages.
- Report generation is language-aware: `generate_excel_report(..., lang=)`, `generate_pdf_report(..., lang=)` with TR/EN section labels; PDF embeds the SFG schematic + instrument table rows.
- Inspection page shows a tolerance annotated schematic and localized tabs/labels.

### Metrology & Inspection
- `calc_uncertainty_budget_detailed()` accepts `geometric_contribution_pct` to fold inspection-derived geometric deviation into the ISO 5168 budget (RSS-combined, GUM-propagated via `uncertainties`). Backward compatible (default 0.0).

### Bugfixes & Hardening
- **UI emit path**: syntax fix in `05_results.py`, `NPS_TO_OD` import fix in `02_process.py`, session-state initialization for project/process/requirements keys (Click-through no longer crashes).
- **Scoring**: `classify_score()` handles exact 100.0 boundary; weight dicts are normalized (unknown keys dropped, sums to 1). Turkish fluid labels (`doğal_gaz`) normalize via `normalize_fluid_type()` in scoring + Ex classification.
- **Backends**: pyaga8 non-unity composition raises `PanicException` (a `BaseException`) — now caught and normalization applied; CoolProp output units contract enforced (`g/mol`, `kmol/m³`); heating value computed internally (thermo branch could return negative Hc) with percent/fraction agreement.
- **Sizing**: PD meter zero-viscosity div-by-zero guard; turbine negative pressure raises `ValueError`; ultrasound sizing feed guarded when design temp is 0°C.
- **Safety**: Zone 0 protection recommendation added; `classify_ex()` uses normalized fluid type so Turkish labels resolve to natural gas.
- **Materials/Piping**: `select_material()` no longer mutates the global `MATERIAL_RECOMMENDATIONS` dict; ambient/range temperature keys parsed in stress tables (`ambient`, `-29_to_40`); flange class selection no longer applies a hidden 1.05 margin; `calc_min_wall_thickness()` raises `ValueError` for mill tolerance ≥ 100 % instead of `ZeroDivisionError`.
- **Inspection**: partial measurements report PENDING, failed checks prefixed `FAIL`; qualitative checks start from a neutral `None` value; reference values carry `nominal_angle`/`t_min_mm` and symbolic bounds (`1.5×d_hole`) resolved so inspection databases reference the right equipment dims.
- **Report**: `_split_notes` accepts both list and string input.

### Testing
- New `tests/test_hardening.py` — 33 regression tests covering all hotspots above plus geometric-uncertainty correctness, page-compile checks, cross-language page smoke (`test_all_pages_render_tr_and_en`) and page-key coverage (`test_i18n_key_use_in_pages`).
- New `tests/test_straight_pipe.py` (8), `tests/test_pdf_report.py` (lang + schematic + instrument rows), `tests/test_schematic.py`, `tests/test_instrument_layout.py`.
- Full suite: **307 passed, 3 skipped**.

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
