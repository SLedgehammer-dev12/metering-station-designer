import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".."))
from metering_designer.core.i18n import get_text

lang = st.session_state.get("lang", "tr")
t = lambda k: get_text(k, lang)

req = st.session_state.requirements

st.header(t("requirements_header"))
st.caption(t("requirements_caption"))

col1, col2 = st.columns(2)
with col1:
    h2s = st.toggle(t("requirements_h2s"), value=req.get("h2s", False),
                    help=t("requirements_h2s_help"), key="req_h2s")
    req["h2s"] = h2s
    if h2s:
        h2s_ppm = st.number_input(t("requirements_h2s_ppm"), min_value=0.0, value=float(req.get("h2s_ppm", 100.0)), step=1.0,
                                  help=t("requirements_h2s_ppm_help"), key="req_h2s_ppm")
        req["h2s_ppm"] = h2s_ppm
    else:
        req["h2s_ppm"] = 0.0

with col2:
    ex_zone = st.selectbox(t("requirements_ex_zone"),
                           ["zone_0", "zone_1", "zone_2", "none"],
                           index=["zone_0", "zone_1", "zone_2", "none"].index(req.get("ex_zone", "zone_2"))
                           if req.get("ex_zone") in ["zone_0", "zone_1", "zone_2", "none"] else 2,
                           format_func=lambda x: {"zone_0": t("ex_zone_zone_0"),
                                                  "zone_1": t("ex_zone_zone_1"),
                                                  "zone_2": t("ex_zone_zone_2"),
                                                  "none": t("ex_zone_none")}.get(x, x),
                           help=t("requirements_ex_help"),
                           key="req_ex_zone")
    req["ex_zone"] = ex_zone

    has_gas_detection = st.toggle(t("requirements_gas_detector"), value=req.get("has_gas_detection", True),
                                  help=t("requirements_gas_help"), key="req_gas_det")
    req["has_gas_detection"] = has_gas_detection
    req["has_gas_detection"] = has_gas_detection

st.divider()

col3, col4 = st.columns(2)
with col3:
    target_unc = st.select_slider(t("requirements_target_unc"),
                                   options=[0.1, 0.2, 0.5, 1.0, 1.5, 2.0, 5.0],
                                   value=float(req.get("target_uncertainty", 1.0)),
                                   help=t("requirements_target_unc_help"),
                                   key="req_target_unc")
    req["target_uncertainty"] = target_unc
    st.caption(f"{t('requirements_selected')} ±{target_unc}%")

with col4:
    location_type = st.selectbox(t("requirements_region"),
                                 ["turkey", "europe", "middle_east", "africa", "other"],
                                 index=["turkey", "europe", "middle_east", "africa", "other"].index(
                                     req.get("location", "turkey")) if req.get("location") in ["turkey", "europe", "middle_east", "africa", "other"] else 0,
                                 format_func=lambda x: {"turkey": t("loc_turkey"), "europe": t("loc_europe"),
                                                        "middle_east": t("loc_middle_east"), "africa": t("loc_africa"),
                                                        "other": t("loc_other")}.get(x, x),
                                 key="req_location")
    req["location"] = location_type

col5, col6 = st.columns(2)
with col5:
    ambient_min = st.number_input(t("requirements_ambient_min"), min_value=-60, max_value=30,
                                  value=int(req.get("ambient_min_C", -10)), key="req_amb_min")
    req["ambient_min_C"] = ambient_min
with col6:
    ambient_max = st.number_input(t("requirements_ambient_max"), min_value=-20, max_value=70,
                                  value=int(req.get("ambient_max_C", 45)), key="req_amb_max")
    req["ambient_max_C"] = ambient_max

st.divider()
col7, col8 = st.columns(2)
with col7:
    power = st.selectbox(t("requirements_power"), ["grid", "solar", "generator", "unknown"],
                         format_func=lambda x: {"grid": t("power_grid"), "solar": t("power_solar"),
                                                "generator": t("power_generator"), "unknown": t("power_unknown")}.get(x, x),
                         index=["grid", "solar", "generator", "unknown"].index(req.get("power_source", "grid"))
                         if req.get("power_source") in ["grid", "solar", "generator", "unknown"] else 0,
                         key="req_power")
    req["power_source"] = power
with col8:
    site_limit = st.number_input(t("requirements_site_limit"), min_value=0.0,
                                 value=float(req.get("site_length_limit_m", 0.0)), step=0.1, key="req_site_limit")
    req["site_length_limit_m"] = site_limit

col_nav1, col_nav2, col_nav3 = st.columns([1, 1, 1])
with col_nav1:
    if st.button(t("requirements_back"), use_container_width=True, key="nav_req_back"):
        st.session_state.page = "process"
        st.rerun()
with col_nav2:
    if st.button(t("requirements_next_weights"), use_container_width=True, key="nav_req_weights"):
        st.session_state.page = "weights"
        st.rerun()
with col_nav3:
    if st.button(t("requirements_calc"), use_container_width=True, type="primary", key="nav_req_calc"):
        st.session_state.page = "results"
        st.rerun()