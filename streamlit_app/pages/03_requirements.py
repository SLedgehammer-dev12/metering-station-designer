import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".."))

req = st.session_state.requirements

st.header("🔧 Gereksinimler & Standartlar")
st.caption("Proje özel gereksinimlerini ve standart seçimlerini belirtin.")

col1, col2 = st.columns(2)
with col1:
    h2s = st.toggle("Sour Servis (H₂S içeriyor)", value=req.get("h2s", False))
    req["h2s"] = h2s
    if h2s:
        h2s_ppm = st.number_input("H₂S Konsantrasyonu (ppm)", min_value=0.0, value=float(req.get("h2s_ppm", 100.0)), step=1.0)
        req["h2s_ppm"] = h2s_ppm
    else:
        req["h2s_ppm"] = 0.0

with col2:
    ex_zone = st.selectbox("Ex Zone Sınıfı",
                           ["zone_0", "zone_1", "zone_2", "none"],
                           index=["zone_0", "zone_1", "zone_2", "none"].index(req.get("ex_zone", "zone_2"))
                           if req.get("ex_zone") in ["zone_0", "zone_1", "zone_2", "none"] else 2,
                           format_func=lambda x: {"zone_0": "Zone 0", "zone_1": "Zone 1",
                                                   "zone_2": "Zone 2", "none": "Ex gereksiz"}.get(x, x))
    req["ex_zone"] = ex_zone

    has_gas_detection = st.toggle("Gaz Dedektörü Mevcut", value=req.get("has_gas_detection", True))
    req["has_gas_detection"] = has_gas_detection

st.divider()

col3, col4 = st.columns(2)
with col3:
    target_unc = st.select_slider("Hedef Ölçüm Belirsizliği (±%)",
                                   options=[0.1, 0.2, 0.5, 1.0, 1.5, 2.0, 5.0],
                                   value=float(req.get("target_uncertainty", 1.0)))
    req["target_uncertainty"] = target_unc
    st.caption(f"Seçilen: ±{target_unc}%")

with col4:
    location_type = st.selectbox("Proje Bölgesi",
                                 ["turkey", "europe", "middle_east", "africa", "other"],
                                 index=["turkey", "europe", "middle_east", "africa", "other"].index(
                                     req.get("location", "turkey")) if req.get("location") in ["turkey", "europe", "middle_east", "africa", "other"] else 0,
                                 format_func=lambda x: {"turkey": "Türkiye", "europe": "Avrupa",
                                                         "middle_east": "Orta Doğu", "africa": "Afrika",
                                                         "other": "Diğer"}.get(x, x))
    req["location"] = location_type

col5, col6 = st.columns(2)
with col5:
    ambient_min = st.number_input("Min Çevre Sıcaklığı (°C)", min_value=-60, max_value=30,
                                   value=int(req.get("ambient_min_C", -10)))
    req["ambient_min_C"] = ambient_min
with col6:
    ambient_max = st.number_input("Max Çevre Sıcaklığı (°C)", min_value=-20, max_value=70,
                                   value=int(req.get("ambient_max_C", 45)))
    req["ambient_max_C"] = ambient_max

st.divider()
col7, col8 = st.columns(2)
with col7:
    power = st.selectbox("Güç Kaynağı", ["grid", "solar", "generator", "unknown"],
                         format_func=lambda x: {"grid": "Şebeke", "solar": "Solar", "generator": "Jeneratör", "unknown": "Bilinmiyor"}.get(x, x),
                         index=["grid", "solar", "generator", "unknown"].index(req.get("power_source", "grid"))
                         if req.get("power_source") in ["grid", "solar", "generator", "unknown"] else 0)
    req["power_source"] = power
with col8:
    site_limit = st.number_input("Saha Düz Boru Limiti (m) (opsiyonel)", min_value=0.0,
                                  value=float(req.get("site_length_limit_m", 0.0)), step=0.1)
    req["site_length_limit_m"] = site_limit

col_nav1, col_nav2, col_nav3 = st.columns([1, 1, 1])
with col_nav1:
    if st.button("⬅️ Geri", use_container_width=True):
        st.session_state.page = "process"
        st.rerun()
with col_nav2:
    if st.button("➡️ Ağırlıkları Ayarla", use_container_width=True):
        st.session_state.page = "weights"
        st.rerun()
with col_nav3:
    if st.button("🚀 Hesapla (Varsayılan Ağırlıklar)", use_container_width=True, type="primary"):
        st.session_state.page = "results"
        st.rerun()
