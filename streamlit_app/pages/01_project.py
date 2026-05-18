import streamlit as st

st.header("📋 Proje Bilgisi")
st.caption("Ölçüm istasyonu temel proje bilgilerini girin.")

col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Proje Adı", value=st.session_state.project.get("name", ""))
    tag = st.text_input("Proje No / Etiket", value=st.session_state.project.get("tag", ""))
with col2:
    location = st.text_input("Konum / Sahası", value=st.session_state.project.get("location", ""))
    date = st.date_input("Tarih")

st.session_state.project["name"] = name
st.session_state.project["tag"] = tag
st.session_state.project["location"] = location

st.divider()
with st.expander("📝 Açıklama"):
    desc = st.text_area("Proje Açıklaması", value=st.session_state.project.get("description", ""))
    st.session_state.project["description"] = desc

if st.button("➡️ Devam Et - Proses Bilgileri", use_container_width=True, type="primary"):
    if not name:
        st.warning("Lütfen proje adı girin.")
    st.session_state.page = "process"
    st.rerun()
