import streamlit as st
import tempfile
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".."))
from metering_designer.core.weights import CATEGORY_LABELS_TR
from metering_designer.core.i18n import get_text
from metering_designer.report.excel_report import generate_excel_report
from metering_designer.report.pdf_report import generate_pdf_report, generate_pdf_from_results, HAS_WEASYPRINT
from metering_designer.instruments.schematic import render_schematic_png_bytes

lang = st.session_state.lang
t = lambda k: get_text(k, lang)

st.header(t("report_header"))
st.caption(t("report_caption"))

selected = st.session_state.selected_meter
proc = st.session_state.process
req = st.session_state.requirements
eng = st.session_state.engineering or {}

if not selected or not proc:
    st.warning(t("report_no_selection"))
    if st.button(t("report_back_results"), key="nav_report_back_results"):
        st.session_state.page = "results"
        st.rerun()
    st.stop()

# ═══════════════ PROJE ÖZETİ ═══════════════
st.subheader(t("report_project_summary"))
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(t("report_project"), st.session_state.project.get("name", "-"))
with col2:
    st.metric(t("report_selected_meter"), selected.name_tr if lang != "en" else selected.name_en)
with col3:
    st.metric(t("report_score"), f"{selected.total_score:.0f}/100")

col4, col5, col6 = st.columns(3)
with col4:
    st.metric(t("report_fluid"), proc.get("fluid_type", "-"))
with col5:
    st.metric(t("report_service"), proc.get("service_type", "-"))
with col6:
    pipe = eng.get("pipe", {})
    if pipe and "error" not in pipe:
        st.metric(t("report_wall_thickness"), f"{pipe.get('t_required_mm', 0):.1f} mm")

st.divider()

# ═══════════════ ŞEMATİK ═══════════════
st.subheader(t("report_schematic"))
sp = eng.get("straight_pipe")
layout = eng.get("instrument_layout")
cond_key = eng.get("conditioner_selected")
up_conf = proc.get("upstream_config", "single_bend_90")
try:
    png_b64 = render_schematic_png_bytes(
        selected.meter_key, proc.get("nps", 8), upstream_config=up_conf,
        conditioner_key=cond_key, straight_pipe=sp, lang=lang,
        upstream_config_label=up_conf.replace("_", " ").title(),
    )
    st.image(f"data:image/png;base64,{png_b64.decode()}", use_container_width=True)
    _schematic_b64_for_pdf = png_b64.decode()
except Exception as e:
    st.warning(f"Şematik oluşturulamadı: {e}")
    _schematic_b64_for_pdf = None

if layout:
    rows = []
    for inst in layout.get("instruments", []):
        rows.append({
            t("instrument_type_label"): inst["type"],
            t("instrument_tag_label"): ", ".join(inst["tag_list"]),
            t("instrument_pos_label"): f"{inst['position_D']:+.1f}D",
            t("instrument_pos_m_label"): f"{inst['position_m']:.2f} m",
            t("instrument_side_label"): t(inst["side"]) if inst["side"] in ("upstream", "downstream") else inst["side"],
        })
    st.caption(t("report_instrument_table"))
    st.dataframe(rows, hide_index=True, use_container_width=True)

st.divider()

# ═══════════════ PUANLAMA ÖZETİ ═══════════════
st.subheader(t("report_category_scores"))
pdata = []
for ck, cl in CATEGORY_LABELS_TR.items():
    cat = selected.categories.get(ck)
    if cat:
        pdata.append({t("category_legend"): t(f"weights_cat_{ck}") if ck in CATEGORY_LABELS_TR else cl,
                      t("score_value"): f"{cat.score:.1f}/10",
                      t("report_weight"): f"%{cat.weight*100:.0f}"})
st.dataframe(pdata, hide_index=True, use_container_width=True)

st.divider()

# ═══════════════ STANDARTLAR ═══════════════
st.subheader(t("report_standards"))
standards = [
    ("AGA Report No. 9 | ISO 17089", t("report_std_checked").format(t("report_std_usm")) if "ultrasonic" in selected.meter_key else "—"),
    ("ISO 5167-2 | AGA Report No. 3", t("report_std_checked").format(t("report_std_orifice")) if "orifice" in selected.meter_key else "—"),
    ("AGA Report No. 7 | ISO 9951", t("report_std_checked").format(t("report_std_turbine")) if "turbine" in selected.meter_key else "—"),
    ("AGA Report No. 11", t("report_std_checked").format(t("report_std_coriolis")) if "coriolis" in selected.meter_key else "—"),
    ("API MPMS Ch.4", t("report_std_checked").format(t("report_std_pd")) if "positive_displacement" in selected.meter_key else "—"),
    ("ASME B31.3", t("report_std_checked").format(t("report_std_b313"))),
    ("ASME B16.5", t("report_std_checked").format(t("report_std_b165"))),
    ("ISO 15156 / NACE MR0175", t("report_std_sour") if req.get("h2s") else t("report_std_sweet")),
    ("IEC 60079-10-1", t("report_std_checked").format(t("report_std_ex"))),
    ("IEC 61511", t("report_std_checked").format(t("report_std_sil"))),
    ("ISO 5168", t("report_std_checked").format(t("report_std_unc"))),
    ("ISO 6976", t("report_std_checked").format(t("report_std_hv"))),
]
std_df = [{t("report_std_col"): s[0], t("report_note_col"): s[1]} for s in standards]
st.dataframe(std_df, hide_index=True, use_container_width=True)

st.divider()

# ═══════════════ İNDİRME ═══════════════
st.subheader(t("report_download"))

col_dl1, col_dl2 = st.columns(2)

with col_dl1:
    # TXT Summary
    report_text = f"""=== {t('report_txt_title')} ===
{'='*60}
{t('report_project')}: {st.session_state.project.get('name', '-')}
{t('report_location')}: {st.session_state.project.get('location', '-')}
{t('report_date')}: {st.session_state.project.get('date', '-')}

{t('report_selected_meter')}: {selected.name_tr if lang != 'en' else selected.name_en}
{t('report_score')}: {selected.total_score:.0f}/100 ({selected.tier_label})

{t('report_process_data')}:
  {t('report_fluid')}: {proc.get('fluid_type', '-')}
  Qmin/Qnom/Qmax: {proc.get('qmin',0)} / {proc.get('qnormal',0)} / {proc.get('qmax',0)}
  P {t('report_operating')}: {proc.get('oper_p_bar',0)} barg
  T {t('report_operating')}: {proc.get('oper_t_c',0)} °C
  NPS: {proc.get('nps', 0)}

{t('report_category_scores')}:
"""
    for ck, cl in CATEGORY_LABELS_TR.items():
        cat = selected.categories.get(ck)
        if cat:
            label = t(f"weights_cat_{ck}") if ck in CATEGORY_LABELS_TR else cl
            report_text += f"  {label}: {cat.score:.1f}/10 (ağırlık: %{cat.weight*100:.0f})\n"

    report_text += f"\n{t('strengths')}:\n"
    for s in selected.strengths:
        report_text += f"  + {s}\n"
    report_text += f"\n{t('report_cautions')}:\n"
    for w in selected.weaknesses:
        report_text += f"  - {w}\n"

    report_text += f"\n{t('report_standards')}:\n"
    for s in standards:
        if s[1] != "—":
            report_text += f"  {s[0]}: {s[1]}\n"

    report_text += f"\n{'='*60}\nMetering Station Designer v0.3.0\n"

    st.download_button(t("report_dl_txt"), data=report_text,
                       file_name=f"rapor_{st.session_state.project.get('name','proje')}.txt",
                       use_container_width=True)

with col_dl2:
    try:
        excel_bytes = generate_excel_report(
            project=st.session_state.project,
            process=proc,
            requirements=req,
            scored_meters=st.session_state.results or [],
            selected_meter=selected,
            engineering=eng,
            conditioners=eng.get("conditioner_scores"),
            lang=lang,
        )
        st.download_button(t("report_dl_excel"),
                           data=excel_bytes,
                           file_name=f"rapor_{st.session_state.project.get('name','proje')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    except Exception as e:
        st.warning(f"Excel raporu oluşturulamadı: {e}")

# PDF Download
if HAS_WEASYPRINT:
    try:
        uncertainty = eng.get("uncertainty", {})
        _tmp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        _tmp_pdf.close()
        instrument_rows = []
        if layout:
            for inst in layout.get("instruments", []):
                instrument_rows.append({
                    "tag": ", ".join(inst["tag_list"]),
                    "type": inst["type"],
                    "count": inst["count"],
                    "position_D": inst["position_D"],
                    "side": t(inst["side"]) if inst["side"] in ("upstream", "downstream") else inst["side"],
                    "standard": inst["standard"],
                })
        pdf_path = generate_pdf_report({
            "meter_type": selected.name_tr if lang != "en" else selected.name_en,
            "standard_ref": "ISO 5167 / AGA / ASME / IEC",
            "pressure": proc.get("oper_p_bar", 0),
            "temperature": proc.get("oper_t_c", 0),
            "flow_max": proc.get("qmax", 0),
            "flow_min": proc.get("qmin", 0),
            "density_op": pipe.get("rho_kg_m3", 0) if not isinstance(pipe, dict) else pipe.get("rho_kg_m3", 0),
            "viscosity": pipe.get("mu_Pa_s", 1.2e-5) if not isinstance(pipe, dict) else pipe.get("mu_Pa_s", 1.2e-5),
            "z_factor": pipe.get("Z", 1) if not isinstance(pipe, dict) else pipe.get("Z", 1),
            "sizing_results": pipe if isinstance(pipe, dict) else {},
            "uncertainty_components": uncertainty.get("components", []),
            "combined_uncertainty": uncertainty.get("combined_standard_uncertainty_pct", 0),
            "expanded_k2": uncertainty.get("expanded_uncertainty_k2_95pct", 0),
            "gas_properties": {
                "M_mix": pipe.get("M_mix", 0),
                "rho_std_kg_m3": pipe.get("rho_std_kg_m3", 0),
                "kappa": pipe.get("kappa", 1.3),
            },
            "notes": [selected.notes] if hasattr(selected, "notes") and selected.notes else [],
            "schematic_png_b64": _schematic_b64_for_pdf,
            "instrument_table_rows": instrument_rows,
            "straight_pipe": sp,
        }, output_path=_tmp_pdf.name, lang=lang)
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        try:
            os.unlink(_tmp_pdf.name)
        except OSError:
            pass
        st.download_button(t("report_dl_pdf"),
                           data=pdf_bytes,
                           file_name=f"rapor_{st.session_state.project.get('name','proje')}.pdf",
                           mime="application/pdf",
                           use_container_width=True)
    except Exception as e:
        st.warning(f"PDF raporu oluşturulamadı: {e}")
else:
    st.caption(t("report_pdf_need_install"))

# JSON download
json_data = {
    "proje": {**st.session_state.project},
    "proses": {k: str(v) if isinstance(v, (dict, list)) else v for k, v in proc.items()},
    "metre": {"tip": selected.name_tr, "key": selected.meter_key, "puan": selected.total_score, "tier": selected.tier_label},
    "kategoriler": {cl: cat.score for ck, cl in CATEGORY_LABELS_TR.items() if (cat := selected.categories.get(ck))},
    "standartlar": [s[0] for s in standards if s[1] != "—"],
    "engineering": {"pipe": str(eng.get("pipe", {})), "ex": str(eng.get("ex", {}))},
}
st.download_button(t("report_dl_json"), data=json.dumps(json_data, indent=2, ensure_ascii=False),
                   file_name=f"veri_{st.session_state.project.get('name','proje')}.json", use_container_width=True)

st.divider()
if st.button(t("report_back_engineering"), use_container_width=True, key="nav_report_back_eng"):
    st.session_state.page = "engineering"
    st.rerun()
