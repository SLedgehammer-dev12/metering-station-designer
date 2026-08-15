import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".."))
from metering_designer.core.i18n import get_text

lang = st.session_state.get("lang", "tr")
t = lambda k: get_text(k, lang)

st.header(t("project_header"))
st.caption(t("project_caption"))

col1, col2 = st.columns(2)
with col1:
    name = st.text_input(t("project_name"), value=st.session_state.project.get("name", ""), key="proj_name")
    tag = st.text_input(t("project_tag"), value=st.session_state.project.get("tag", ""), key="proj_tag")
with col2:
    location = st.text_input(t("project_location"), value=st.session_state.project.get("location", ""), key="proj_location")
    date = st.date_input(t("project_date"), key="proj_date")

st.session_state.project["name"] = name
st.session_state.project["tag"] = tag
st.session_state.project["location"] = location

st.divider()
with st.expander(t("project_expander_desc")):
    desc = st.text_area(t("project_desc"), value=st.session_state.project.get("description", ""), key="proj_desc")
    st.session_state.project["description"] = desc

if st.button(t("project_continue"), use_container_width=True, type="primary", key="nav_project_continue"):
    if not name:
        st.warning(t("project_name_required"))
    st.session_state.page = "process"
    st.rerun()