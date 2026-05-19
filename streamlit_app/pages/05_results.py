import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".."))
from streamlit_app.components.score_table import render_score_table
from streamlit_app.components.radar_chart import render_radar_chart
from streamlit_app.components.justification_card import render_justification_card
from metering_designer.meters.selector import evaluate_all_meters
from metering_designer.core.weights import DEFAULT_WEIGHTS, CATEGORY_LABELS_TR

st.header("📊 Sonuçlar & Puanlama")
st.caption("Çok kriterli değerlendirme sonuçları - tüm metre tipleri puanlandı.")

proc = st.session_state.process
req = st.session_state.requirements
weights = st.session_state.weights if st.session_state.weights else DEFAULT_WEIGHTS

if not proc or not proc.get("fluid_type"):
    st.warning("⚠️ Önce proses bilgilerini girin.")
    if st.button("⬅️ Proses Sayfasına Dön"):
        st.session_state.page = "process"
        st.rerun()
    st.stop()

if st.session_state.results is None:
    with st.spinner("🔄 Tüm metre tipleri değerlendiriliyor..."):
        inputs = {
            "fluid_type": proc.get("fluid_type", "gas"),
            "nps": proc.get("nps", 8),
            "od_mm": proc.get("od_mm", 219.1),
            "oper_p_bar": proc.get("oper_p_bar", 40.0),
            "design_p_bar": proc.get("design_p_bar", 50.0),
            "oper_t_c": proc.get("oper_t_c", 40.0),
            "design_t_c": proc.get("design_t_c", 60.0),
            "qmin": proc.get("qmin", 5000),
            "qnormal": proc.get("qnormal", 10000),
            "qmax": proc.get("qmax", 30000),
            "composition": proc.get("composition", {}),
            "upstream_config": proc.get("upstream_config", "single_bend_90"),
            "material": proc.get("material", "A106_GrB"),
            "service_type": proc.get("service_type", "process"),
            "h2s": req.get("h2s", False),
            "h2s_ppm": req.get("h2s_ppm", 0.0),
            "ex_zone": req.get("ex_zone", "zone_2"),
            "target_uncertainty": req.get("target_uncertainty", 1.0),
            "location": req.get("location", "turkey"),
            "has_gas_detection": req.get("has_gas_detection", True),
            "ambient_min_C": req.get("ambient_min_C", -10),
            "ambient_max_C": req.get("ambient_max_C", 45),
            "power_source": req.get("power_source", "grid"),
            "site_length_limit_m": req.get("site_length_limit_m", 0.0),
        }

        results = evaluate_all_meters(inputs, weights=weights, fluid_type=inputs["fluid_type"])
        st.session_state.results = results

results = st.session_state.results
if not results:
    st.error("Değerlendirme sonucu alınamadı.")
    st.stop()

st.success(f"✅ {len(results)} metre tipi değerlendirildi — en yüksek puan: {results[0].name_tr} ({results[0].total_score:.0f}/100)")

with st.expander("📖 Bu sonuçlar ne anlama geliyor?", expanded=False):
    st.markdown("""
    **Puanlama 0-100 arasındadır. Program 6 kategoride 30'dan fazla kriteri değerlendirir:**
    
    | Kategori | Anlamı |
    |---|---|
    | 🔧 Teknik Uygunluk | Metre bu akışkan, basınç, çapta çalışabilir mi? |
    | 🎯 Doğruluk | Ölçüm hatası ne kadar düşük? Custody transfer onaylı mı? |
    | ⚙️ İşletme Kolaylığı | Basınç kaybı, bakım ihtiyacı, düz boru gereksinimi |
    | 💰 Maliyet | Yatırım (CAPEX) + işletme (OPEX) maliyeti |
    | 📦 Uygulanabilirlik | Tedarik süresi, yerel destek, nakliye |
    | 🔄 Proje Özel | Saha tecrübesi, kompaktlık, online doğrulama |
    
    **Tier Sınıflandırması:**
    - ★★★ (85-100): **Optimal** — En iyi tercih
    - ★★☆ (70-84): **İyi Alternatif** — Küçük ödünler var
    - ★☆☆ (50-69): **Değerlendirilebilir** — Ciddi kısıtlamalar
    - —– (<50): **Önerilmez** — Temel gereksinimleri karşılamıyor
    """)

st.divider()

# Bölüm A: Sıralı Puan Tablosu
st.subheader("🏆 Sıralı Puan Tablosu")
selected = render_score_table(results)

# Bölüm B: Seçilen metre güncelle
if selected:
    st.session_state.selected_meter = selected

# Bölüm C: Radar Chart
if selected:
    st.subheader("📊 Kategori Bazında Karşılaştırma (İlk 3)")
    render_radar_chart(results[:3])

# Bölüm D: Gerekçe Kartı
if selected:
    st.subheader("📋 Detaylı Gerekçelendirme")
    render_justification_card(selected)
    else:
        st.info("👆 Detayları görmek için yukarıdaki tablodan bir metre seçin.")

# E: Parallel Comparison
if len(results) >= 2:
    with st.expander("🔄 Paralel Karşılaştırma (Trade-off Analizi)", expanded=False):
        st.caption("Yan yana karşılaştırma — farkları ve tercih sebeplerini görün.")
        compare = st.multiselect("Karşılaştırılacak metreler:", [r.name_tr for r in results],
                                  default=[r.name_tr for r in results[:3]])
        if len(compare) >= 2:
            comp_meters = [r for r in results if r.name_tr in compare]
            comp_data = []
            for r in comp_meters:
                row = {"Metre": r.name_tr, "Puan": f"{r.total_score:.0f}", "Tier": r.tier_label}
                for ck in CATEGORY_LABELS_TR:
                    cat = r.categories.get(ck)
                    row[CATEGORY_LABELS_TR[ck]] = f"{cat.score:.1f}" if cat else "-"
                comp_data.append(row)
            st.dataframe(comp_data, hide_index=True, use_container_width=True)

            # Key difference analysis
            if len(comp_meters) == 2:
                a, b = comp_meters
                diffs = []
                for ck in CATEGORY_LABELS_TR:
                    ca = a.categories.get(ck)
                    cb = b.categories.get(ck)
                    if ca and cb and abs(ca.score - cb.score) > 0.3:
                        winner = a if ca.score > cb.score else b
                        diffs.append(f"**{CATEGORY_LABELS_TR[ck]}**: {winner.name_tr} {abs(ca.score-cb.score):.1f} puan önde")
                if diffs:
                    st.markdown("##### Ana Farklar:")
                    for d in diffs:
                        st.markdown(f"- {d}")

st.divider()

# Detay Mühendislik Sayfasına Geçiş
if selected:
    col_nav1, col_nav2, col_nav3 = st.columns([1, 1, 1])
    with col_nav1:
        if st.button("⬅️ Geri - Ağırlıklar", use_container_width=True):
            st.session_state.page = "weights"
            st.rerun()
    with col_nav2:
        if st.button(f"📐 Seçimi Onayla: {selected.name_tr}", use_container_width=True, type="primary"):
            st.session_state.selected_meter = selected
            st.session_state.page = "engineering"
            st.rerun()
    with col_nav3:
        if st.button("🔄 Yeniden Hesapla", use_container_width=True):
            st.session_state.results = None
            st.rerun()
