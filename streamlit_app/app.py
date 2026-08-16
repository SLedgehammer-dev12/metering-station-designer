import importlib.util
import os

import streamlit as st

from metering_designer.core.i18n import get_text

st.set_page_config(
    page_title="Ölçüm İstasyonu Dizayn Asistanı",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.markdown("# 📊 Ölçüm İstasyonu")
st.sidebar.markdown("## Dizayn & Metre Seçim Asistanı")
st.sidebar.markdown("---")

# Language toggle
st.session_state.setdefault("lang", "tr")
lang = st.session_state.lang
lang_labels = {"tr": "🇹🇷 Türkçe", "en": "🇬🇧 English"}
lang_choice = st.sidebar.selectbox("Dil / Language", list(lang_labels.keys()),
                                    format_func=lambda x: lang_labels[x],
                                    index=list(lang_labels.keys()).index(lang),
                                    key="lang_select")
if lang_choice != lang:
    st.session_state.lang = lang_choice
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("**" + get_text("app_phase_label", lang) + "**")
st.sidebar.markdown(get_text("app_phase_desc", lang))
st.sidebar.markdown("---")

# Automatic update check (runs once per process; result cached)
from metering_designer.core.updates import (
    check_in_background,
    get_app_version,
    get_download_state,
    start_download,
)

_app_version = get_app_version()
_update = check_in_background()
_dl = get_download_state()
if _update.get("update_available"):
    _v = _update.get("latest", "")
    _asset = _update.get("platform_asset") or {}
    with st.sidebar.expander(f":rocket: {get_text('update_available', lang).format(v=_v)}", expanded=True):
        if _dl.get("status") == "running":
            st.progress(_dl.get("progress", 0.0))
            st.caption(get_text("update_downloading", lang).format(pct=100 * _dl.get("progress", 0.0)))
        elif _dl.get("status") == "done":
            st.success(get_text("update_download_done", lang).format(path=_dl.get("dest", "")))
            if _dl.get("sha_ok"):
                st.info(get_text("update_download_verified", lang))
            import sys as _sys
            st.markdown(get_text("update_replace_mac" if _sys.platform == "darwin" else "update_replace_windows", lang))
        elif _dl.get("status") == "failed":
            st.error(get_text("update_download_failed", lang).format(error=_dl.get("error", "")))
        else:
            if _asset.get("browser_download_url"):
                if st.button(get_text("update_download_btn", lang).format(v=_v), key="update_download_btn"):
                    start_download()
                    st.rerun()
            else:
                st.info(get_text("update_no_asset", lang))
    st.sidebar.success(f"{get_text('app_version', lang)}: v{_app_version}")
elif _update.get("error") is None and _update.get("latest"):
    st.sidebar.caption(f"{get_text('app_version', lang)}: v{_app_version} · {get_text('update_latest', lang).format(v=_update['latest'])}")
else:
    st.sidebar.caption(f"{get_text('app_version', lang)}: v{_app_version}")

st.sidebar.markdown("---")

PAGE_KEYS = ["project", "process", "requirements", "weights", "results", "engineering", "report", "inspection"]
_PAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")
PAGE_FILES = {
    "project": "01_project.py",
    "process": "02_process.py",
    "requirements": "03_requirements.py",
    "weights": "04_weights.py",
    "results": "05_results.py",
    "engineering": "06_engineering.py",
    "report": "07_report.py",
    "inspection": "08_inspection.py",
}

st.session_state.setdefault("lang", "tr")
st.session_state.setdefault("page", "project")
st.session_state.setdefault("project", {})
st.session_state.setdefault("process", {})
st.session_state.setdefault("requirements", {})
lang = st.session_state.lang

# Build localized page labels
for _k in PAGE_KEYS:
    st.session_state.setdefault(_k, None)
st.session_state.setdefault("selected_meter", None)
st.session_state.setdefault("engineering", None)
st.session_state.setdefault("results", None)
page_labels = {k: get_text(k, lang) for k in PAGE_KEYS}
page_label_list = list(page_labels.values())
# Sync the sidebar radio to programmatic page changes made by page-bottom buttons
st.session_state["page_nav_radio"] = page_labels.get(st.session_state.page, page_label_list[0])

nav = st.sidebar.radio("Menü", page_label_list, key="page_nav_radio")
# Map back from label to key
for key, label in page_labels.items():
    if label == nav:
        st.session_state.page = key
        break
st.sidebar.markdown("---")

st.sidebar.markdown("---")

# Save/Load Project
with st.sidebar.expander("💾 Kaydet / Yükle"):
    import json as _json
    if st.button("📥 Projeyi İndir (JSON)", use_container_width=True, key="save_btn"):
        state_data = {}
        for k in ["project","process","requirements","weights","lang"]:
            if k in st.session_state:
                v = st.session_state[k]
                state_data[k] = {str(kk): str(vv) for kk, vv in v.items()} if isinstance(v, dict) else v
        st.download_button("⬇ İndir", _json.dumps(state_data, indent=2, ensure_ascii=False, default=str),
                          file_name=f"{st.session_state.get('project',{}).get('name','proje')}.json",
                          use_container_width=True)
    uploaded = st.file_uploader("JSON yükle", type=["json"], label_visibility="collapsed")
    if uploaded:
        try:
            data = _json.loads(uploaded.read())
            for k, v in data.items():
                st.session_state[k] = v
            st.session_state.page = "project"
            st.session_state.results = None
            st.session_state.selected_meter = None
            st.session_state.engineering = None
            st.success("✅ Proje yüklendi!")
            st.rerun()
        except Exception as e:
            st.error(f"Yükleme hatası: {e}")

st.sidebar.markdown("---")

if st.sidebar.button("🔄 Sıfırla"):
    for k in list(st.session_state.keys()):
        if k in ("project", "process", "requirements", "weights", "results", "selected_meter", "engineering"):
            if k == "weights":
                st.session_state[k] = None
            elif k == "results":
                st.session_state[k] = None
            elif k == "selected_meter":
                st.session_state[k] = None
            elif k == "engineering":
                st.session_state[k] = None
            else:
                st.session_state[k] = {}
    st.rerun()

page_file = os.path.join(_PAGE_DIR, PAGE_FILES.get(st.session_state.page, ""))
if page_file and os.path.exists(page_file):
    _spec = importlib.util.spec_from_file_location(f"page_{st.session_state.page}", page_file)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
