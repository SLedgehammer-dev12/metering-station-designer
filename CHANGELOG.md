# Changelog

All notable changes to Metering Station Designer.

## [Unreleased] - engineering-accuracy fixes

### Real-Gas Thermodynamics (`core/backends.py`, `fluids/gas.py`)
- `calc_speed_of_sound` is now Z-aware and `calc_speed_of_sound_real` was added (`pyaga8` `w` preferred, `√(κ·Z·R·T/M)` fallback).
- `_calc_viscosity` rewritten with the density-based LGE correlation (low-pressure fallback retained); `calc_speed_of_sound_pyaga8` added.
- `_z_coolprop` rewritten via `AbstractState("HEOS")` + `set_mole_fractions`; fixed a 1000× molar-density unit bug (`Dmass/M_gmol`).
- `COMPONENT_MAP_PYAGA8` extended to the full 21-component pyaga8 map (H2, He, Ar, O2, CO, H2O, nC7, C7–C10…); unknown keys are no longer folded into n-butane.
- `gauge_to_absolute()` added to `core/units.py`; the engineering page consumes absolute pressure (`oper_p_abs`) for gas properties and all sizing calls.

### Standard-Driven Meter Sizing (`meters/*`, `auxiliaries/`)
- `calc_beta_ratio` requires `p1_Pa` (absolute upstream pressure); the expansibility factor uses it instead of a hard-coded 4.5 MPa; results carry `p1_Pa_abs`.
- Corner-tap `L1` corrected 0.5→1.0 (ISO 5167-2 D-D/2 taps).
- Classical Venturi re-implemented per ISO 5167-4 (Cd=0.995, ISO ε, β iterated to the design ΔP, 15 % permanent loss).
- V-Cone reports the physical cone diameter `d_cone = D·√(1−β²)` and effective throat `At = A_pipe·β²`; vortex dead K-factor line removed.
- `pipe_id_mm(nps, schedule)` added to `piping/__init__.py`; orifice/V-Cone/vortex/USM sizing and the engineering page now use schedule-based IDs instead of `OD·0.88`.
- Straight-pipe requirements and permanent-pressure-loss models per meter (vortex/V-Cone/Venturi/Coriolis/PD).

### Piping & Safety (`piping/`, `safety/`)
- Burst and B31.8 wall thickness now use SMYS; B31.8 applies the location-class design factor (0.72/0.60/0.50/0.40) plus temperature derating.
- API RP 14E erosional-velocity C-factors updated to SI values (122 continuous / 152.5 intermittent).
- IEC 60079-14: Ex d (flameproof) no longer recommended for Zone 0; gas detection may downgrade Zone 1→Zone 2 but never erases a hazardous zone.

### Scoring & Validation (`core/`)
- Removed unreachable `fluid_compatibility` branch; `estimated_dp_bar` now uses the physical Δp ∝ q² orifice scaling (≈250 mbar @ 30 000 Sm³/h) instead of a fabricated formula.
- `validate_project_inputs`/`validate_all` return `(errors, warnings)`; a missing project location is now a warning, not a blocking error.

### Inspection & Schematic (`inspection/`, `instruments/`, UI)
- New vortex (`knowledge/inspection_vortex.json`, ISO 12764) and positive-displacement (`knowledge/inspection_pd_meter.json`, API MPMS 5.2) inspection components; their checklists no longer degenerate to piping-only.
- Inspection default bore now uses `pipe_id_mm` (schedule 40) instead of `OD·0.88`.
- SFG schematic straight-pipe dimension lines are anchored at the meter (previously the "down" line spanned the whole run).
- `streamlit_app/app.py` loads pages via `importlib.util` instead of `exec(open(...).read())`.

## [1.2.0] - 2026-08-15

### Design-Standard Framework (staged)
- **Standard-per-meter selection**: new `metering_designer/standards/design_standards.py` registry (`list_standards` / `get_standard` / `default_standard`) with profiles for **orifice** (`iso5167_2` + `aga3`) and **ultrasonic** (`aga9` + `iso17089`). Unimplemented meter types return an empty list so the UI keeps the selector hidden until profiles are added in a later update.
- **Engineering page standard selector**: after meter selection the design standard picker appears; the chosen standard drives the calculation defaults, limits and references (`06_engineering.py`).
- **User-selectable design ΔP (orifice)**: `dp_design_mbar` input (20–1000 mbar) on `06_engineering.py`; `size_orifice_for_flow` now sizes for the chosen ΔP (default 250 mbar preserved) and β is derived from the standard equation.
- **Advisory messages**: `generate_design_advisories()` in `orifice.py` returns structured guidance — β in/out of recommended band (0.2–0.65), low ΔP@Qmin (transmitter accuracy risk), design-ΔP confirmation — rendered as `st.info`/`st.warning` in the UI.
- **Standard-aware calculations**: `calc_beta_ratio`/`size_orifice_for_flow` accept `standard` and resolve tap-type defaults per standard (ISO → corner, AGA-3 → flange); `size_ultrasonic` accepts `standard` and applies the profile's velocity limits; results carry `standard` / `standard_name` / `standard_ref`. Audit-trail provenance now uses the resolved `standard_ref`.
- New i18n keys (TR + EN): `engineering_standard_label`, `engineering_dp_design*`, `metric_dp_at_qmin`, `metric_turndown`, `metric_tap_type`, `std_*` advisory/description keys.

### Platform-Aware Releases & macOS Support
- **macOS build** in `.github/workflows/build.yml`: `build-macos` job runs on `macos-latest` (Apple Silicon, arm64), builds an app bundle with `--windowed`, applies ad-hoc `codesign --force --deep -s -`, packages it as a drag-and-drop `MeteringStationDesigner_macOS_arm64.dmg` (via `hdiutil`) and uploads it to the release alongside the Windows zip.
- **Per-platform release tags**: `v1.2.0` (both platforms), `v1.2.0-win` (Windows only), `v1.2.0-mac` (macOS only). Each build job is gated with `if: contains(github.ref, '-mac'/' -win')` so a single-platform fix only rebuilds that platform.
- **Asset-aware update check** (`core/updates.py`): `fetch_releases()` + `find_platform_release()` scan recent releases and only signal an update when the newest release ships an artifact for the *running* OS. A Windows-only release no longer notifies macOS users and vice-versa; per-OS version tracks stay independent. Deprecated reliance on the global `releases/latest` tag for update decisions.
- **Packaged app version detection**: frozen builds now embed a `VERSION` file (`--add-data "VERSION;."`/`"VERSION:."`) which `get_app_version()` reads from `sys._MEIPASS` before falling back to package metadata / `pyproject.toml`.
- **Semi-automatic download**: the update banner offers a platform download button (`start_download()`), streams the matching asset with progress, verifies SHA-256 against the GitHub asset digest, and shows OS-specific replace instructions (`update_replace_mac` / `update_replace_windows`).
- New i18n keys (TR + EN): `update_download_btn`, `update_downloading`, `update_download_done`, `update_download_verified`, `update_download_failed`, `update_replace_mac`, `update_replace_windows`, `update_no_asset`.

## [1.1.0] - 2026-08-15

### Automatic Update Check
- On startup, the app checks the GitHub releases API (`core/updates.py`) in a background thread and shows a sidebar banner when a newer release exists (`update_available`), along with `git pull` + `pip install` instructions; otherwise it shows the current version (`app_version`). Offline/SSL/404 failures degrade gracefully to a no-update result — the check never blocks the UI and runs at most once every 6 hours per process via an in-memory cache. `get_app_version()` reads from package metadata or `pyproject.toml`; `compare_versions()` uses `packaging.Version`.
- Click-through hardening for the version banner: version/update text is fully localized via new i18n keys (`update_available`, `update_latest`, `update_instruction`, etc.).

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
