import streamlit as st

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
                                    index=list(lang_labels.keys()).index(lang))
if lang_choice != lang:
    st.session_state.lang = lang_choice
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("**Faz 3 - v0.3.0**")
st.sidebar.markdown("Standart bazlı çok kriterli dizayn")
st.sidebar.markdown("---")

from metering_designer.core.i18n import get_text

PAGE_KEYS = ["project", "process", "requirements", "weights", "results", "engineering", "report", "inspection"]
PAGE_FILES = {
    "project": "pages/01_project.py",
    "process": "pages/02_process.py",
    "requirements": "pages/03_requirements.py",
    "weights": "pages/04_weights.py",
    "results": "pages/05_results.py",
    "engineering": "pages/06_engineering.py",
    "report": "pages/07_report.py",
    "inspection": "pages/08_inspection.py",
}

st.session_state.setdefault("lang", "tr")
st.session_state.setdefault("page", "project")
lang = st.session_state.lang

# Build localized page labels
page_labels = {k: get_text(k, lang) for k in PAGE_KEYS}
page_label_list = list(page_labels.values())
current_idx = PAGE_KEYS.index(st.session_state.page)

nav = st.sidebar.radio("Menü", page_label_list, index=current_idx)
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

page_file = PAGE_FILES.get(st.session_state.page)
if page_file:
    exec(open(page_file).read())
