import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".."))
from streamlit_app.config import NPS_OPTIONS, FLUID_OPTIONS, FLUID_LABELS, UPSTREAM_OPTIONS, MATERIAL_OPTIONS
from metering_designer.core.validation import validate_process_inputs, check_composition_sanity

st.header("⚙️ Proses & Akışkan Verileri")
st.caption("Proses koşullarını ve akışkan özelliklerini girin.")

proc = st.session_state.process

col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    fluid_type = st.selectbox(
        "Akışkan Tipi",
        FLUID_OPTIONS,
        format_func=lambda x: FLUID_LABELS.get(x, x),
        index=FLUID_OPTIONS.index(proc.get("fluid_type", "doğal_gaz")) if proc.get("fluid_type") in FLUID_OPTIONS else 0,
    )
    proc["fluid_type"] = fluid_type

with col2:
    service = st.selectbox("Servis Tipi", ["custody_transfer", "fiscal", "process"],
                           index=["custody_transfer", "fiscal", "process"].index(proc.get("service_type", "process"))
                           if proc.get("service_type") in ["custody_transfer", "fiscal", "process"] else 2)
    proc["service_type"] = service
with col3:
    nps = st.selectbox("Hat Çapı (NPS)", NPS_OPTIONS,
                       index=NPS_OPTIONS.index(int(proc.get("nps", 8)))
                           if proc.get("nps") in NPS_OPTIONS else 3)
    proc["nps"] = nps

st.divider()
col_a, col_b, col_c = st.columns(3)
with col_a:
    oper_p = st.number_input("İşletme Basıncı (barg)", min_value=0.1, value=float(proc.get("oper_p_bar", 40.0)), step=1.0)
    proc["oper_p_bar"] = oper_p
    design_p = st.number_input("Tasarım Basıncı (barg)", min_value=0.1, value=float(proc.get("design_p_bar", 50.0)), step=1.0)
    proc["design_p_bar"] = design_p
with col_b:
    oper_t = st.number_input("İşletme Sıcaklığı (°C)", min_value=-50, max_value=200, value=int(proc.get("oper_t_c", 40)), step=1)
    proc["oper_t_c"] = oper_t
    design_t = st.number_input("Tasarım Sıcaklığı (°C)", min_value=-50, max_value=200, value=int(proc.get("design_t_c", 60)), step=1)
    proc["design_t_c"] = design_t
with col_c:
    qmin = st.number_input("Q min (Sm³/h)", min_value=0, value=int(proc.get("qmin", 5000)), step=100)
    proc["qmin"] = qmin
    qnormal = st.number_input("Q normal (Sm³/h)", min_value=0, value=int(proc.get("qnormal", 10000)), step=100)
    proc["qnormal"] = qnormal
    qmax = st.number_input("Q max (Sm³/h)", min_value=0, value=int(proc.get("qmax", 30000)), step=100)
    proc["qmax"] = qmax

st.divider()
st.subheader("Hat Konfigürasyonu")
col_d, col_e = st.columns(2)
with col_d:
    up_conf = st.selectbox("Upstream Konfigürasyon", list(UPSTREAM_OPTIONS.keys()),
                           format_func=lambda x: UPSTREAM_OPTIONS.get(x, x),
                           index=list(UPSTREAM_OPTIONS.keys()).index(proc.get("upstream_config", "single_bend_90"))
                           if proc.get("upstream_config") in UPSTREAM_OPTIONS else 0)
    proc["upstream_config"] = up_conf
with col_e:
    mat = st.selectbox("Boru Malzemesi", list(MATERIAL_OPTIONS.keys()),
                       format_func=lambda x: MATERIAL_OPTIONS.get(x, x),
                       index=list(MATERIAL_OPTIONS.keys()).index(proc.get("material", "A106_GrB"))
                       if proc.get("material") in MATERIAL_OPTIONS else 0)
    proc["material"] = mat

proc["od_mm"] = NPS_TO_OD.get(nps, nps * 25.4)

st.divider()
st.subheader("Gaz Kompozisyonu (mol%)")
st.caption("Sadece doğal gaz seçildiğinde doldurun.")

comp_names = ["C1", "C2", "C3", "iC4", "nC4", "iC5", "nC5", "C6", "C6plus", "N2", "CO2", "H2S"]
defaults = {"C1": 90.0, "C2": 4.0, "C3": 1.5, "N2": 1.0, "CO2": 2.0, "H2S": 0.001}
if fluid_type == "doğal_gaz":
    gcols = st.columns(4)
    composition = {}
    for i, comp in enumerate(comp_names):
        col = gcols[i % 4]
        default_val = float(proc.get("composition", {}).get(comp, defaults.get(comp, 0)))
        composition[comp] = col.number_input(comp, min_value=0.0, max_value=100.0,
                                              value=default_val, step=0.01, format="%.2f")
    total = sum(composition.values())
    if abs(total - 100) > 0.5:
        st.warning(f"⚠️ Toplam: {total:.2f}% (100% olmalı)")
    else:
        st.success(f"✅ Toplam: {total:.2f}%")
    proc["composition"] = composition
else:
    api = st.number_input("API Gravite", min_value=5.0, max_value=70.0,
                           value=float(proc.get("api_gravity", 35.0)), step=0.1)
    proc["api_gravity"] = api

NPS_TO_OD = {2: 60.3, 3: 88.9, 4: 114.3, 6: 168.3, 8: 219.1, 10: 273.1, 12: 323.8,
             14: 355.6, 16: 406.4, 18: 457.2, 20: 508.0, 24: 609.6}

st.divider()

# Validation
errors = validate_process_inputs(proc)
warnings = []
if proc.get("fluid_type") in ("doğal_gaz", "gas") and proc.get("composition"):
    warnings = check_composition_sanity({k: v / 100 if v > 1 else v for k, v in proc.get("composition", {}).items()})

if errors:
    for e in errors:
        st.error(f"❌ {e}")
if warnings:
    for w in warnings:
        st.warning(f"⚠️ {w}")
if not errors:
    st.success(f"✅ Tüm proses girdileri geçerli")

col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("⬅️ Geri - Proje Bilgisi", use_container_width=True):
        st.session_state.page = "project"
        st.rerun()
with col_nav2:
    if st.button("➡️ Devam Et - Gereksinimler", use_container_width=True, type="primary"):
        st.session_state.page = "requirements"
        st.rerun()
