# Contributing to Metering Station Designer

## Branch Strategy

```
main              ← stable, release-ready
  ├── feat/*      ← new features (per AGENTS.md sub-agent)
  ├── fix/*       ← bug fixes
  └── docs/*      ← documentation updates
```

- **`main`**: Protected. All changes via PR.
- **Branch naming**: `feat/<agent>-<brief>` (e.g., `feat/scoring-vcone`, `feat/ui-dark-mode`)
- **Commit format**: `<agent>: <message>` (e.g., `sizing: fix orifice Cd for Re < 5000`)

## Pull Request Checklist

- [ ] Code follows existing style (4-space indent, snake_case, English docstrings)
- [ ] At least 1 test added/modified
- [ ] `pytest tests/ -v` passes locally (all 27+ tests)
- [ ] No new JSON syntax errors (`python -m json.tool knowledge/*.json`)
- [ ] CHANGELOG.md entry added under "Unreleased"
- [ ] If API changed: `AGENTS.md` updated, downstream callers checked

## Code Style

- **Python**: PEP 8 with 4-space indentation
- **Docstrings**: English, triple-quote, brief description + Args/Returns for public functions
- **JSON keys**: `snake_case`, consistent with existing knowledge base files
- **Type hints**: Required for all new public function signatures
- **Imports**: Standard library → third-party → local, grouped with empty line separator

## Testing

```bash
# All tests
pytest tests/ -v

# Single test file
pytest tests/test_scoring.py -v

# Specific test
pytest tests/test_scoring.py::test_all_meters_gas -v
```

Minimum test requirements:
- **New meter type**: 1 sizing test, 1 edge case test
- **New inspection parameter**: 1 tolerance test, 1 fill-and-eval test
- **New UI feature**: 1 integration test (backend logic only, UI not tested)

## JSON Knowledge Base Rules

1. Validate before commit: `python -m json.tool <file> > /dev/null`
2. New meter entries: use existing entry as template
3. Tolerance data: cite exact standard clause in comments
4. All numeric values: SI units unless explicitly noted

## Development Setup

```bash
git clone <repo-url>
cd metering-station-designer
pip install -r requirements.txt
pip install pytest          # dev dependency
streamlit run streamlit_app/app.py    # test UI
```

## Release Process

1. CHANGELOG "Unreleased" renamed to version tag
2. `pyproject.toml` version bumped
3. PR to `main` with all feature branches
4. `git tag v<version>` after merge
5. GitHub Actions builds Windows .exe + uploads to Release tab

### Per-Platform Releases

A single base version can be released for both platforms or for only one. The
tag suffix selects which platforms get a new package:

| Tag | Builds | Assets |
|-----|--------|--------|
| `v1.2.0` | Windows + macOS | `MeteringStationDesigner_Windows.zip`, `MeteringStationDesigner_macOS_arm64.dmg` |
| `v1.2.0-win` | Windows only | `MeteringStationDesigner_Windows.zip` |
| `v1.2.0-mac` | macOS only | `MeteringStationDesigner_macOS_arm64.dmg` |

Rules:
- Any platform release bumps the base version in `pyproject.toml` (minor/patch); the
  suffix only says *where* the change applies.
- Tags must be pushed as a *non-draft, non-prerelease* GitHub Release so the
  asset upload steps can attach binaries to them.
- The in-app update check is asset-aware: each OS only reports an update when the
  newest release actually ships an artifact for it (`core/updates.py` →
  `find_platform_release`). A `-mac` release therefore does *not* notify Windows
  users, and vice-versa.
- Create the release before/at push time so `Build Release` can upload:
  `gh release create v1.2.0-mac --title "v1.2.0 (macOS only)" --notes "…"`
