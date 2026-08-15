import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".."))
from streamlit_app.config import NPS_OPTIONS, FLUID_OPTIONS, UPSTREAM_OPTIONS, MATERIAL_OPTIONS
from metering_designer.core.validation import validate_process_inputs, check_composition_sanity
from metering_designer.core.i18n import get_text

lang = st.session_state.get("lang", "tr")
t = lambda k: get_text(k, lang)

NPS_TO_OD = {2: 60.3, 3: 88.9, 4: 114.3, 6: 168.3, 8: 219.1, 10: 273.1, 12: 323.8,
             14: 355.6, 16: 406.4, 18: 457.2, 20: 508.0, 24: 609.6}

st.header(t("process_header"))
st.caption(t("process_caption"))

proc = st.session_state.process

col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    fluid_type = st.selectbox(
        t("process_fluid_type"),
        FLUID_OPTIONS,
        format_func=lambda x: {"doğal_gaz": t("natural_gas"), "ham_petrol": t("crude_oil")}.get(x, x),
        index=FLUID_OPTIONS.index(proc.get("fluid_type", "doğal_gaz")) if proc.get("fluid_type") in FLUID_OPTIONS else 0,
        help=t("process_fluid_help"),
    )
    proc["fluid_type"] = fluid_type

with col2:
    service = st.selectbox(t("process_service"), ["custody_transfer", "fiscal", "process"],
                           index=["custody_transfer", "fiscal", "process"].index(proc.get("service_type", "process"))
                           if proc.get("service_type") in ["custody_transfer", "fiscal", "process"] else 2,
                           format_func=lambda x: {"custody_transfer": t("custody_transfer"),
                                                  "fiscal": t("fiscal"),
                                                  "process": t("process_control")}.get(x, x),
                           help=t("process_service_help"))
    proc["service_type"] = service
with col3:
    nps = st.selectbox(t("process_nps"), NPS_OPTIONS,
                       index=NPS_OPTIONS.index(int(proc.get("nps", 8)))
                           if proc.get("nps") in NPS_OPTIONS else 3,
                       help=t("process_nps_help"))
    proc["nps"] = nps

st.divider()
col_a, col_b, col_c = st.columns(3)
with col_a:
    oper_p = st.number_input(t("process_oper_p"), min_value=0.1, value=float(proc.get("oper_p_bar", 40.0)), step=1.0,
                             help=t("process_oper_p_help"))
    proc["oper_p_bar"] = oper_p
    design_p = st.number_input(t("process_design_p"), min_value=0.1, value=float(proc.get("design_p_bar", 50.0)), step=1.0,
                               help=t("process_design_p_help"))
    proc["design_p_bar"] = design_p
with col_b:
    oper_t = st.number_input(t("process_oper_t"), min_value=-50, max_value=200, value=int(proc.get("oper_t_c", 40)), step=1,
                             help=t("process_oper_t_help"))
    proc["oper_t_c"] = oper_t
    design_t = st.number_input(t("process_design_t"), min_value=-50, max_value=200, value=int(proc.get("design_t_c", 60)), step=1,
                               help=t("process_design_t_help"))
    proc["design_t_c"] = design_t
with col_c:
    qmin = st.number_input(t("process_qmin"), min_value=0, value=int(proc.get("qmin", 5000)), step=100,
                           help=t("process_qmin_help"))
    proc["qmin"] = qmin
    qnormal = st.number_input(t("process_qnorm"), min_value=0, value=int(proc.get("qnormal", 10000)), step=100,
                              help=t("process_qnorm_help"))
    proc["qnormal"] = qnormal
    qmax = st.number_input(t("process_qmax"), min_value=0, value=int(proc.get("qmax", 30000)), step=100,
                           help=t("process_qmax_help"))
    proc["qmax"] = qmax

st.divider()
st.subheader(t("process_config_header"))
_up_labels = {k: t(f"up_{k}") for k in UPSTREAM_OPTIONS}
_mat_labels = {k: t(f"mat_{k}") for k in MATERIAL_OPTIONS}
col_d, col_e = st.columns(2)
with col_d:
    up_conf = st.selectbox(t("process_upstream_config"), list(UPSTREAM_OPTIONS.keys()),
                           format_func=lambda x: _up_labels.get(x, x),
                           index=list(UPSTREAM_OPTIONS.keys()).index(proc.get("upstream_config", "single_bend_90"))
                           if proc.get("upstream_config") in UPSTREAM_OPTIONS else 0)
    proc["upstream_config"] = up_conf
with col_e:
    mat = st.selectbox(t("process_material"), list(MATERIAL_OPTIONS.keys()),
                       format_func=lambda x: _mat_labels.get(x, x),
                       index=list(MATERIAL_OPTIONS.keys()).index(proc.get("material", "A106_GrB"))
                       if proc.get("material") in MATERIAL_OPTIONS else 0)
    proc["material"] = mat

proc["od_mm"] = NPS_TO_OD.get(nps, nps * 25.4)

st.divider()
st.subheader(t("process_comp_header"))
st.caption(t("process_comp_caption"))

comp_names = ["C1", "C2", "C3", "iC4", "nC4", "iC5", "nC5", "C6", "C6plus", "N2", "CO2", "H2S"]
defaults = {"C1": 90.0, "C2": 4.0, "C3": 1.5, "N2": 1.0, "CO2": 2.0, "H2S": 0.001}
comp_label = {c: t(f"comp_{c}") for c in comp_names}
if fluid_type == "doğal_gaz":
    gcols = st.columns(4)
    composition = {}
    for i, comp in enumerate(comp_names):
        col = gcols[i % 4]
        default_val = float(proc.get("composition", {}).get(comp, defaults.get(comp, 0)))
        composition[comp] = col.number_input(comp_label[comp], min_value=0.0, max_value=100.0,
                                              value=default_val, step=0.01, format="%.2f",
                                              help=t("process_comp_help").format(comp=comp_label[comp]))
    total = sum(composition.values())
    if abs(total - 100) > 0.5:
        st.warning(f"⚠️ {t('process_total_sum')} {total:.2f}% ({t('process_comp_total_ok')})")
    else:
        st.success(f"✅ {t('process_total_sum')} {total:.2f}%")
    proc["composition"] = composition
else:
    api = st.number_input(t("process_api"), min_value=5.0, max_value=70.0,
                          value=float(proc.get("api_gravity", 35.0)), step=0.1)
    proc["api_gravity"] = api

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
    st.success(t("process_validate_ok"))

col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button(t("process_back"), use_container_width=True):
        st.session_state.page = "project"
        st.rerun()
with col_nav2:
    if st.button(t("process_continue"), use_container_width=True, type="primary"):
        st.session_state.page = "requirements"
        st.rerun()