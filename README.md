# Metering Station Designer v1.0.0

**Ölçüm İstasyonu Dizayn Asistanı** — Doğal gaz ve petrol hatları için standart bazlı çok kriterli metre seçimi, mühendislik hesaplamaları ve geometrik denetim.

*Multi-criteria meter selection, detailed engineering calculations, and geometric inspection for natural gas and oil metering stations — fully compliant with ISO, AGA, ASME, and IEC standards.*

---

## Capabilities / Yetkinlikler

### Design / Dizayn
| Feature | Standards | Description |
|---|---|---|
| **Multi-criteria Meter Selection** | AGA 3/7/9/11, ISO 5167, API MPMS | 8 meter types ranked by weighted scoring across 6 categories, 30+ criteria |
| **Gas Properties (Z-factor)** | AGA 8 / ISO 12213 | NIST-certified via pyaga8 (Equinor), fallback to CoolProp → thermo → DAK |
| **Pipe Design** | ASME B31.3 / B31.4 / B31.8 | Wall thickness, schedule recommendation, flange class per B16.5 |
| **Material Selection** | ISO 15156 / NACE MR0175 | Sour service, chlorides, offshore — Duplex 2205, SuperDuplex 2507, HIC-tested CS |
| **Flow Conditioner Scoring** | ISO 5167-1 Table 4 | CPA 50E, Zanker, 19-Tube Bundle, Gallagher — 6-criteria weighted scoring |
| **Ex / SIL / Uncertainty** | IEC 60079, IEC 61511, ISO 5168 | Zone classification, SIL risk graph, full uncertainty budget with GC component |

### Inspection / Denetim
| Feature | Standards | Description |
|---|---|---|
| **Dynamic Checklist Builder** | ISO 5167-2, AGA 9, AGA 7, AGA 11 | Builds complete measurement lists from meter + conditioner selection |
| **Tolerance Engine** | 6 tolerance types | percentage, range, max_value, conditional_max, enum, min_length |
| **Geometric Deviation → Uncertainty** | ISO 5168 | Maps each geometric non-conformance to additional measurement uncertainty |
| **Compliance Report** | — | Excel (.xlsx) 3-sheet report with clause-level standard violation tracking |

### Reports / Rapor
| Format | Contents |
|---|---|
| **TXT** | Summary — meter, scores, process data, standards checklist |
| **Excel** | 5 sheets — overview, scoring details, per-criterion breakdown, flow conditioners, standards |
| **PDF** | 3 pages — cover, engineering details, standards & recommendations |
| **JSON** | Full project data serialization, save/load support |

---

## Architecture / Mimari

```
metering-station-designer/
├── metering_designer/           # Core Python library
│   ├── core/                    # Scoring engine, fallback chain, validation, i18n
│   ├── fluids/                  # AGA8 / DAK Z-factor, gas/liquid properties
│   ├── piping/                  # ASME B31.3 wall thickness, B16.5 flange, materials
│   ├── meters/                  # 8 meter sizing modules + selector + scoring
│   ├── conditioners/            # Flow conditioner scoring engine
│   ├── auxiliaries/             # Straight pipe, pressure loss
│   ├── safety/                  # Ex classification (IEC 60079), SIL (IEC 61511)
│   ├── metrology/               # Uncertainty budget (ISO 5168)
│   ├── inspection/              # Dynamic checklist, tolerance engine, compliance report
│   └── report/                  # Excel + PDF report generators
│
├── knowledge/                   # 11 JSON standards databases
│   ├── gas_components.json      # ISO 6976 component properties
│   ├── meter_specs.json         # 8 meter types + 5 flow conditioner specs
│   ├── meter_scoring.json       # 6-category scoring weights & thresholds
│   ├── asme_b313_stress.json    # ASME B31.3 stress table
│   ├── asme_b165_ratings.json   # ASME B16.5 P-T rating tables
│   ├── inspection_orifice.json   # ISO 5167-2 tolerance database
│   ├── inspection_usm.json      # AGA 9 tolerance database
│   ├── inspection_turbine.json   # AGA 7 tolerance database
│   ├── inspection_coriolis.json  # AGA 11 tolerance database
│   ├── inspection_conditioners.json  # ISO 5167-1 Table 4 tolerances
│   └── inspection_piping.json    # ASME B31.3 piping tolerances
│
├── streamlit_app/               # 8-page Streamlit UI
│   ├── app.py                   # Entry point, sidebar nav, language toggle, save/load
│   ├── pages/                   # 01_project → 08_inspection (2-tab)
│   └── components/              # radar_chart, score_table, justification_card
│
└── tests/                       # 27 test suite
```

---

## Quick Start / Hızlı Başlangıç

### Option 1 — pip
```bash
pip install -r requirements.txt
streamlit run streamlit_app/app.py
```

### Option 2 — Docker
```bash
docker build -t metering-designer .
docker run -p 8501:8501 metering-designer
```

### Option 3 — Windows .exe (Build from source)
```bash
build_windows.bat
# Output: dist\app.dist\app.exe
```

---

## Backend Fallback Chain

| Layer | Library | Method | Always Available? |
|---|---|---|---|
| **1** (Best) | `pyaga8` (Equinor) | NIST AGA8-92DC DETAIL | Requires pip install |
| **2** | `CoolProp` | GERG-2008 HEOS / SRK / PR | Requires pip install |
| **3** | `thermo` (Caleb Bell) | PRMIX EOS + HHV/LHV | Requires pip install |
| **4** (Last) | Internal DAK/Papay | Pure Python, zero deps | ✅ Always |

---

## Meter Types Supported / Desteklenen Metreler

| Meter | Standard(s) | Sizing | Inspection |
|---|---|---|---|
| Orifice Plate | ISO 5167-2, AGA 3 | ✅ β ratio, Cd(RHG), ε, ΔP | ✅ 7 plate + 7 tube params |
| Ultrasonic (USM) | AGA 9, ISO 17089 | ✅ Path config, k-factor, velocity | ✅ 4 body + 3 transducer params |
| Turbine | AGA 7, ISO 9951 | ✅ K-factor, bearing life, over-range | ✅ 4 body params |
| Coriolis | AGA 11, ISO 10790 | ✅ Meter size, zero drift, ΔP | ✅ 3 body params |
| PD Meter | API MPMS Ch.4 | ✅ Slip, viscosity effect, K-factor | Limited |
| Vortex | ISO 17089-2 | ✅ Frequency, Strouhal, v_min | Limited |
| V-Cone | ISO 5167-5 | ✅ β ratio, Cd, ΔP (perm) | Limited |
| Venturi (Classical) | ISO 5167-4 | ✅ Cd=0.995, β=0.5, low ΔP | — |

---

## Tests / Testler

```bash
pytest tests/ -v           # 27 tests
pytest tests/ --co -q       # 27 collected
```

---

## 🇹🇷 Türkçe Özet

**Metering Station Designer**, doğal gaz ve petrol ölçüm istasyonlarının dizaynı ve mevcut istasyonların standart uygunluğunun denetlenmesi için geliştirilmiş açık kaynaklı bir mühendislik aracıdır.

**Temel Özellikler:**
- 8 farklı akışmetre tipi için 6 kategorili, ağırlıklı puanlama sistemi
- NIST onaylı AGA 8-92DC DETAIL metodu ile Z-faktörü hesabı (Equinor/pyaga8)
- ASME B31.3 boru et kalınlığı, B16.5 flanş sınıfı, ISO 15156 malzeme seçimi
- Geometrik denetim modülü: ISO 5167-2, AGA 9, AGA 7 standartlarına uygunluk kontrolü
- TXT, Excel, PDF ve JSON formatlarında rapor
- TR/EN dil desteği, proje kaydetme/yükleme

**Kurulum:** `pip install -r requirements.txt`, ardından `streamlit run streamlit_app/app.py`

**Standartlar:** ISO 5167-1/2/4/5, AGA Report No. 3/7/8/9/11, API MPMS Ch.4/14, ASME B31.3/4/8, ASME B16.5, ISO 15156 (NACE MR0175), IEC 60079-10-1, IEC 61511, ISO 5168, ISO 6976, ISO 12213-2.

---

## Requirements

- Python ≥ 3.10
- See `requirements.txt` for full list
- Optional: Docker for containerized deployment
- Optional: Nuitka + Inno Setup for Windows .exe build
