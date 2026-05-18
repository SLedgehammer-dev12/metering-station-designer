# AGENTS.md — OpenCode Sub-Agent Task Definitions

This file defines sub-agent roles, file ownership, and task boundaries for parallel AI-assisted development.

---

## Sub-Agent Assignments

### Agent 1: `scoring-engine`
**Files:**
- `metering_designer/core/scoring_engine.py`
- `metering_designer/core/weights.py`
- `metering_designer/meters/specs.py`
- `knowledge/meter_specs.json`
- `knowledge/meter_scoring.json`
- `tests/test_scoring.py`

**Responsibilities:**
- Add/update scoring criteria in the 6-category framework
- Tune default weights based on industry feedback
- Add new meter types to `meter_specs.json` with full parameter sets
- Maintain tier threshold classification logic
- Write corresponding unit tests

---

### Agent 2: `meter-sizing`
**Files:**
- `metering_designer/meters/*.py` (orifice, ultrasonic, turbine, coriolis, pd_meter, vortex, vcone)
- `metering_designer/auxiliaries/straight_pipe.py`
- `metering_designer/auxiliaries/pressure_loss.py`
- `metering_designer/fluids/gas.py`

**Responsibilities:**
- Implement detailed sizing calculations for new meter types (Annubar, Classical Venturi)
- Improve existing sizing algorithms (Cd correlations, expansibility factors)
- Calibrate sizing outputs against commercial software benchmarks
- Maintain `BaseMeter` interface

---

### Agent 3: `inspection-compliance`
**Files:**
- `metering_designer/inspection/*.py`
- `knowledge/inspection_*.json` (6 files)
- `metering_designer/inspection/tolerance_engine.py`
- `metering_designer/inspection/uncertainty_impact.py`
- `metering_designer/inspection/compliance_report.py`

**Responsibilities:**
- Update inspection tolerance databases from latest standard revisions
- Add inspection support for new equipment types (V-Cone, Venturi)
- Improve geometric-uncertainty impact model
- Validate tolerances against ISO 5167-2:2022, AGA 9 latest editions

---

### Agent 4: `ui-frontend`
**Files:**
- `streamlit_app/app.py`
- `streamlit_app/pages/*.py` (8 files)
- `streamlit_app/components/*.py` (3 files)
- `streamlit_app/config.py`

**Responsibilities:**
- UI/UX improvements (layout, styling, accessibility)
- Add new pages for new features
- Responsive design for different screen sizes
- Language/translation improvements (i18n)
- Optimize Streamlit session state management

---

### Agent 5: `backend-infra`
**Files:**
- `metering_designer/core/backends.py`
- `metering_designer/core/validation.py`
- `metering_designer/core/i18n.py`
- `metering_designer/piping/*.py`
- `metering_designer/safety/*.py`
- `metering_designer/metrology/*.py`
- `metering_designer/report/*.py`

**Responsibilities:**
- Maintain fallback chain (pyaga8/CoolProp/thermo compatibility)
- Input validation logic
- Material database updates (new alloys, standards)
- Report generation (Excel, PDF)
- Safety classification updates (IEC/ATEX revisions)

---

## General Rules

| Rule | Detail |
|---|---|
| **File Boundaries** | Each agent works only in its assigned file group. Cross-boundary changes require coordination. |
| **API Changes** | If a public function signature changes, update all downstream callers and increment CHANGELOG. |
| **Tests Required** | No PR accepted without corresponding tests. Minimum 1 test per new feature. |
| **JSON Integrity** | Always validate JSON with `python -m json.tool` before committing database changes. |
| **Branch Strategy** | `feat/<agent>-<description>` branches → PR to `main` |
| **Commit Format** | `agent: brief description` (e.g., `scoring: add V-Cone to meter_specs.json`) |

---

## Quick Start for Agents

```bash
# Clone & install
git clone <repo-url>
cd metering-station-designer
pip install -r requirements.txt

# Run existing tests to confirm baseline
pytest tests/ -v

# Run the app locally
streamlit run streamlit_app/app.py

# Edit assigned files → add tests → open PR
```

---

## File Ownership Matrix

| Module | Agent 1 | Agent 2 | Agent 3 | Agent 4 | Agent 5 |
|---|---|---|---|---|---|
| `core/` scoring | ✅ Owns | — | — | — | — |
| `core/` backends/validation/i18n | — | — | — | — | ✅ Owns |
| `meters/*.py` | — | ✅ Owns | — | — | — |
| `inspection/*.py` | — | — | ✅ Owns | — | — |
| `streamlit_app/` | — | — | — | ✅ Owns | — |
| `piping/` `safety/` `metrology/` `report/` | — | — | — | — | ✅ Owns |
| `knowledge/meter_*.json` | ✅ Owns | — | — | — | — |
| `knowledge/inspection_*.json` | — | — | ✅ Owns | — | — |
| `knowledge/asme_*.json` `gas_*.json` | — | — | — | — | ✅ Owns |
| `tests/` | Share | Share | Share | Share | Share |
