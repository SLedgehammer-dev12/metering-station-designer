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
        key="proc_fluid_type",
    )
    proc["fluid_type"] = fluid_type

with col2:
    service = st.selectbox(t("process_service"), ["custody_transfer", "fiscal", "process"],
                           index=["custody_transfer", "fiscal", "process"].index(proc.get("service_type", "process"))
                           if proc.get("service_type") in ["custody_transfer", "fiscal", "process"] else 2,
                           format_func=lambda x: {"custody_transfer": t("custody_transfer"),
                                                  "fiscal": t("fiscal"),
                                                  "process": t("process_control")}.get(x, x),
                           help=t("process_service_help"),
                           key="proc_service")
    proc["service_type"] = service
with col3:
    nps = st.selectbox(t("process_nps"), NPS_OPTIONS,
                       index=NPS_OPTIONS.index(int(proc.get("nps", 8)))
                           if proc.get("nps") in NPS_OPTIONS else 3,
                       help=t("process_nps_help"),
                       key="proc_nps")
    proc["nps"] = nps

st.divider()
col_a, col_b, col_c = st.columns(3)

from metering_designer.core.units import (
    PRESSURE_UNITS, TEMPERATURE_UNITS, FLOW_UNITS, convert_display,
)

_P_INT = {label: unit for label, unit in PRESSURE_UNITS}
_T_INT = {label: unit for label, unit in TEMPERATURE_UNITS}
_F_INT = {label: unit for label, unit in FLOW_UNITS}
_P_STEP = {"barg": 0.5, "psig": 5.0, "kPa": 50.0, "MPa(g)": 0.05}
_T_STEP = {"°C": 1.0, "°F": 2.0, "K": 1.0}
_Q_STEP = {"Sm³/h": 100.0, "m³/h": 100.0, "MMscf/h": 0.001}


def _swap_units(unit_key, options, base_unit, members):
    """Live-convert widget values when a unit selector changes.

    members: list of (widget_key, base_key, default_base, min_base, max_base)
    """
    new_label = st.session_state[unit_key]
    old_label = proc.get(unit_key, options[0][0])
    if new_label == old_label:
        return
    opt = dict(options)
    new_pint, old_pint = opt[new_label], opt[old_label]
    for wkey, bkey, dflt, mlo, mhi in members:
        cur = st.session_state.get(wkey)
        if cur is None:
            cur = convert_display(float(proc.get(bkey, dflt)), base_unit, old_pint)
        base = convert_display(cur, old_pint, base_unit)
        if mlo is not None:
            base = max(base, float(mlo))
        if mhi is not None:
            base = min(base, float(mhi))
        proc[bkey] = base
        st.session_state[wkey] = round(convert_display(base, base_unit, new_pint), 6)
    proc[unit_key] = new_label


with col_a:
    p_unit_label = proc.get("unit_p", "barg")
    p_idx = [l for l, _ in PRESSURE_UNITS].index(p_unit_label) if p_unit_label in [l for l, _ in PRESSURE_UNITS] else 0
    st.selectbox(t("process_unit_p"), [l for l, _ in PRESSURE_UNITS], index=p_idx,
                 key="proc_unit_p", on_change=_swap_units,
                 args=("proc_unit_p", PRESSURE_UNITS, "bar",
                       [("proc_oper_p", "oper_p_bar", 40.0, None, None),
                        ("proc_design_p", "design_p_bar", 50.0, None, None)]))
    proc["unit_p"] = st.session_state["proc_unit_p"]
    p_pint = _P_INT[proc.get("unit_p", "barg")]

    oper_p = st.number_input(t("process_oper_p"), min_value=0.0,
                             value=float(round(convert_display(float(proc.get("oper_p_bar", 40.0)), "bar", p_pint), 4)),
                             step=_P_STEP.get(proc.get("unit_p", "barg"), 0.5),
                             help=t("process_oper_p_help"), key="proc_oper_p")
    proc["oper_p_bar"] = convert_display(oper_p, p_pint, "bar")
    design_p = st.number_input(t("process_design_p"), min_value=0.0,
                               value=float(round(convert_display(float(proc.get("design_p_bar", 50.0)), "bar", p_pint), 4)),
                               step=_P_STEP.get(proc.get("unit_p", "barg"), 0.5),
                               help=t("process_design_p_help"), key="proc_design_p")
    proc["design_p_bar"] = convert_display(design_p, p_pint, "bar")

with col_b:
    t_unit_label = proc.get("unit_t", "°C")
    t_idx = [l for l, _ in TEMPERATURE_UNITS].index(t_unit_label) if t_unit_label in [l for l, _ in TEMPERATURE_UNITS] else 0
    st.selectbox(t("process_unit_t"), [l for l, _ in TEMPERATURE_UNITS], index=t_idx,
                 key="proc_unit_t", on_change=_swap_units,
                 args=("proc_unit_t", TEMPERATURE_UNITS, "degC",
                       [("proc_oper_t", "oper_t_c", 40.0, -50.0, 200.0),
                        ("proc_design_t", "design_t_c", 60.0, -50.0, 200.0)]))
    proc["unit_t"] = st.session_state["proc_unit_t"]
    t_pint = _T_INT[proc.get("unit_t", "°C")]

    oper_t = st.number_input(t("process_oper_t"),
                             min_value=float(round(convert_display(-50, "degC", t_pint), 1)),
                             max_value=float(round(convert_display(200, "degC", t_pint), 1)),
                             value=float(round(convert_display(float(proc.get("oper_t_c", 40)), "degC", t_pint), 1)),
                             step=_T_STEP.get(proc.get("unit_t", "°C"), 1.0),
                             help=t("process_oper_t_help"), key="proc_oper_t")
    proc["oper_t_c"] = convert_display(oper_t, t_pint, "degC")
    design_t = st.number_input(t("process_design_t"),
                               min_value=float(round(convert_display(-50, "degC", t_pint), 1)),
                               max_value=float(round(convert_display(200, "degC", t_pint), 1)),
                               value=float(round(convert_display(float(proc.get("design_t_c", 60)), "degC", t_pint), 1)),
                               step=_T_STEP.get(proc.get("unit_t", "°C"), 1.0),
                               help=t("process_design_t_help"), key="proc_design_t")
    proc["design_t_c"] = convert_display(design_t, t_pint, "degC")

with col_c:
    q_unit_label = proc.get("unit_q", "Sm³/h")
    q_idx = [l for l, _ in FLOW_UNITS].index(q_unit_label) if q_unit_label in [l for l, _ in FLOW_UNITS] else 0
    st.selectbox(t("process_unit_q"), [l for l, _ in FLOW_UNITS], index=q_idx,
                 key="proc_unit_q", on_change=_swap_units,
                 args=("proc_unit_q", FLOW_UNITS, "Sm3/hour",
                       [("proc_qmin", "qmin", 5000.0, 0.0, None),
                        ("proc_qnorm", "qnormal", 10000.0, 0.0, None),
                        ("proc_qmax", "qmax", 30000.0, 0.0, None)]))
    proc["unit_q"] = st.session_state["proc_unit_q"]
    q_pint = _F_INT[proc.get("unit_q", "Sm³/h")]

    qmin = st.number_input(t("process_qmin"), min_value=0.0,
                           value=round(convert_display(float(proc.get("qmin", 5000)), "Sm3/hour", q_pint), 2),
                           step=_Q_STEP.get(proc.get("unit_q", "Sm³/h"), 100.0),
                           help=t("process_qmin_help"), key="proc_qmin")
    proc["qmin"] = convert_display(qmin, q_pint, "Sm3/hour")
    qnormal = st.number_input(t("process_qnorm"), min_value=0.0,
                              value=round(convert_display(float(proc.get("qnormal", 10000)), "Sm3/hour", q_pint), 2),
                              step=_Q_STEP.get(proc.get("unit_q", "Sm³/h"), 100.0),
                              help=t("process_qnorm_help"), key="proc_qnorm")
    proc["qnormal"] = convert_display(qnormal, q_pint, "Sm3/hour")
    qmax = st.number_input(t("process_qmax"), min_value=0.0,
                           value=round(convert_display(float(proc.get("qmax", 30000)), "Sm3/hour", q_pint), 2),
                           step=_Q_STEP.get(proc.get("unit_q", "Sm³/h"), 100.0),
                           help=t("process_qmax_help"), key="proc_qmax")
    proc["qmax"] = convert_display(qmax, q_pint, "Sm3/hour")

st.divider()
st.subheader(t("process_config_header"))
_up_labels = {k: t(f"up_{k}") for k in UPSTREAM_OPTIONS}
_mat_labels = {k: t(f"mat_{k}") for k in MATERIAL_OPTIONS}
col_d, col_e = st.columns(2)
with col_d:
    up_conf = st.selectbox(t("process_upstream_config"), list(UPSTREAM_OPTIONS.keys()),
                           format_func=lambda x: _up_labels.get(x, x),
                           index=list(UPSTREAM_OPTIONS.keys()).index(proc.get("upstream_config", "single_bend_90"))
                           if proc.get("upstream_config") in UPSTREAM_OPTIONS else 0,
                           key="proc_upstream")
    proc["upstream_config"] = up_conf
with col_e:
    mat = st.selectbox(t("process_material"), list(MATERIAL_OPTIONS.keys()),
                       format_func=lambda x: _mat_labels.get(x, x),
                       index=list(MATERIAL_OPTIONS.keys()).index(proc.get("material", "A106_GrB"))
                       if proc.get("material") in MATERIAL_OPTIONS else 0,
                       key="proc_material")
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
                                              help=t("process_comp_help").format(comp=comp_label[comp]),
                                              key=f"proc_comp_{comp}")
    total = sum(composition.values())
    if abs(total - 100) > 0.5:
        st.warning(f"⚠️ {t('process_total_sum')} {total:.2f}% ({t('process_comp_total_ok')})")
    else:
        st.success(f"✅ {t('process_total_sum')} {total:.2f}%")
    proc["composition"] = composition
else:
    api = st.number_input(t("process_api"), min_value=5.0, max_value=70.0,
                          value=float(proc.get("api_gravity", 35.0)), step=0.1, key="proc_api")
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
    if st.button(t("process_back"), use_container_width=True, key="nav_process_back"):
        st.session_state.page = "project"
        st.rerun()
with col_nav2:
    if st.button(t("process_continue"), use_container_width=True, type="primary", key="nav_process_continue"):
        st.session_state.page = "requirements"
        st.rerun()