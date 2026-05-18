import streamlit as st
import sys, os, json, io
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".."))
from metering_designer.core.weights import CATEGORY_LABELS_TR
from metering_designer.report.excel_report import generate_excel_report
from metering_designer.report.pdf_report import generate_pdf_report, HAS_REPORTLAB

st.header("📄 Rapor")
st.caption("Proje özet raporu, standartlar kontrol listesi ve indirilebilir dokümanlar.")

selected = st.session_state.selected_meter
proc = st.session_state.process
req = st.session_state.requirements
eng = st.session_state.engineering or {}

if not selected or not proc:
    st.warning("Önce bir metre seçin ve detay mühendislik sayfasını çalıştırın.")
    if st.button("⬅️ Sonuçlara Dön"):
        st.session_state.page = "results"
        st.rerun()
    st.stop()

# ═══════════════ PROJE ÖZETİ ═══════════════
st.subheader("📋 Proje Özeti")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Proje", st.session_state.project.get("name", "-"))
with col2:
    st.metric("Seçilen Metre", selected.name_tr)
with col3:
    st.metric("Puan", f"{selected.total_score:.0f}/100")

col4, col5, col6 = st.columns(3)
with col4:
    st.metric("Akışkan", proc.get("fluid_type", "-"))
with col5:
    st.metric("Servis", proc.get("service_type", "-"))
with col6:
    pipe = eng.get("pipe", {})
    if pipe and "error" not in pipe:
        st.metric("Et Kalınlığı", f"{pipe.get('t_required_mm', 0):.1f} mm")

st.divider()

# ═══════════════ PUANLAMA ÖZETİ ═══════════════
st.subheader("📊 Kategori Puanları")
pdata = []
for ck, cl in CATEGORY_LABELS_TR.items():
    cat = selected.categories.get(ck)
    if cat:
        pdata.append({"Kategori": cl, "Puan": f"{cat.score:.1f}/10", "Ağırlık": f"%{cat.weight*100:.0f}"})
st.dataframe(pdata, hide_index=True, use_container_width=True)

st.divider()

# ═══════════════ STANDARTLAR ═══════════════
st.subheader("✅ Standartlar Kontrol Listesi")
standards = [
    ("AGA Report No. 9 | ISO 17089", "✅ USM hesaplamaları" if "ultrasonic" in selected.meter_key else "—"),
    ("ISO 5167-2 | AGA Report No. 3", "✅ Orifis hesaplamaları" if "orifice" in selected.meter_key else "—"),
    ("AGA Report No. 7 | ISO 9951", "✅ Türbin hesaplamaları" if "turbine" in selected.meter_key else "—"),
    ("AGA Report No. 11", "✅ Coriolis hesaplamaları" if "coriolis" in selected.meter_key else "—"),
    ("API MPMS Ch.4", "✅ PD metre hesaplamaları" if "positive_displacement" in selected.meter_key else "—"),
    ("ASME B31.3", "✅ Boru et kalınlığı dizaynı"),
    ("ASME B16.5", "✅ Flanş basınç sınıfı"),
    ("ISO 15156 / NACE MR0175", "✅ Sour servis" if req.get("h2s") else "— Sweet servis, gerekmiyor"),
    ("IEC 60079-10-1", "✅ Ex zone sınıflandırması"),
    ("IEC 61511", "✅ SIL değerlendirme"),
    ("ISO 5168", "✅ Belirsizlik bütçesi"),
    ("ISO 6976", "✅ Gaz ısıl değer hesabı"),
]
std_df = [{"Standart": s[0], "Not": s[1]} for s in standards]
st.dataframe(std_df, hide_index=True, use_container_width=True)

st.divider()

# ═══════════════ İNDİRME ═══════════════
st.subheader("📥 Rapor İndir")

col_dl1, col_dl2 = st.columns(2)

with col_dl1:
    # TXT Summary
    report_text = f"""=== ÖLÇÜM İSTASYONU DİZAYN RAPORU ===
{'='*60}
Proje: {st.session_state.project.get('name', '-')}
Konum: {st.session_state.project.get('location', '-')}
Tarih: {st.session_state.project.get('date', '-')}

SEÇİLEN METRE: {selected.name_tr}
Puan: {selected.total_score:.0f}/100 ({selected.tier_label})

PROSES VERİLERİ:
  Akışkan: {proc.get('fluid_type', '-')}
  Qmin/Qnom/Qmax: {proc.get('qmin',0)} / {proc.get('qnormal',0)} / {proc.get('qmax',0)}
  P işletme: {proc.get('oper_p_bar',0)} barg
  T işletme: {proc.get('oper_t_c',0)} °C
  NPS: {proc.get('nps', 0)}

KATEGORİ PUANLARI:
"""
    for ck, cl in CATEGORY_LABELS_TR.items():
        cat = selected.categories.get(ck)
        if cat:
            report_text += f"  {cl}: {cat.score:.1f}/10 (ağırlık: %{cat.weight*100:.0f})\n"

    report_text += f"\nGÜÇLÜ YÖNLER:\n"
    for s in selected.strengths:
        report_text += f"  + {s}\n"
    report_text += f"\nDİKKAT EDİLECEKLER:\n"
    for w in selected.weaknesses:
        report_text += f"  - {w}\n"

    report_text += f"\nSTANDARTLAR:\n"
    for s in standards:
        if s[1] != "—":
            report_text += f"  {s[0]}: {s[1]}\n"

    report_text += f"\n{'='*60}\nMetering Station Designer v0.3.0\n"

    st.download_button("📥 TXT Rapor İndir", data=report_text,
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
            conditioners=eng.get("conditioners"),
        )
        st.download_button("📥 Excel Rapor İndir (.xlsx)",
                           data=excel_bytes,
                           file_name=f"rapor_{st.session_state.project.get('name','proje')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    except Exception as e:
        st.warning(f"Excel raporu oluşturulamadı: {e}")

# PDF Download
if HAS_REPORTLAB:
    try:
        pdf_bytes = generate_pdf_report(
            project=st.session_state.project,
            process=proc,
            requirements=req,
            selected_meter=selected,
            engineering=eng,
            conditioners=eng.get("conditioners"),
        )
        st.download_button("📥 PDF Rapor İndir (.pdf)",
                           data=pdf_bytes,
                           file_name=f"rapor_{st.session_state.project.get('name','proje')}.pdf",
                           mime="application/pdf",
                           use_container_width=True)
    except Exception as e:
        st.warning(f"PDF raporu oluşturulamadı: {e}")
else:
    st.caption("PDF rapor için: pip install reportlab")

# JSON download
json_data = {
    "proje": {**st.session_state.project},
    "proses": {k: str(v) if isinstance(v, (dict, list)) else v for k, v in proc.items()},
    "metre": {"tip": selected.name_tr, "key": selected.meter_key, "puan": selected.total_score, "tier": selected.tier_label},
    "kategoriler": {cl: cat.score for ck, cl in CATEGORY_LABELS_TR.items() if (cat := selected.categories.get(ck))},
    "standartlar": [s[0] for s in standards if s[1] != "—"],
    "engineering": {"pipe": str(eng.get("pipe", {})), "ex": str(eng.get("ex", {}))},
}
st.download_button("📥 JSON Veri İndir", data=json.dumps(json_data, indent=2, ensure_ascii=False),
                   file_name=f"veri_{st.session_state.project.get('name','proje')}.json", use_container_width=True)

st.divider()
if st.button("⬅️ Detay Mühendislik Sayfasına Dön", use_container_width=True):
    st.session_state.page = "engineering"
    st.rerun()
