import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".."))
from metering_designer.core.weights import DEFAULT_WEIGHTS, CATEGORY_LABELS_TR

st.header("⚖️ Ağırlık Ayarları")
st.caption("Her kategorinin puanlama ağırlığını özelleştirin. Varsayılanlar önerilir.")

if st.session_state.weights is None:
    weights = dict(DEFAULT_WEIGHTS)
else:
    weights = dict(st.session_state.weights)

st.info("💡 Her kategorinin önemini projenize göre ayarlayın. Toplam %100 olmalıdır.")
st.divider()

w_total = 0.0
weights_input = {}
for key, label in CATEGORY_LABELS_TR.items():
    default_pct = int(weights.get(key, DEFAULT_WEIGHTS.get(key, 0.2)) * 100)
    val = st.slider(f"{label}", min_value=0, max_value=100, value=default_pct, step=5,
                    key=f"w_{key}")
    weights_input[key] = val
    w_total += val

st.divider()
if w_total != 100:
    st.warning(f"⚠️ Toplam: %{w_total} (%100 olmalı, kalan: %{100-w_total:+})")
else:
    st.success(f"✅ Toplam: %{w_total}")

col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 Varsayılana Dön", use_container_width=True):
        st.session_state.weights = None
        st.rerun()
with col2:
    if st.button("✅ Ağırlıkları Onayla ve İlerle", use_container_width=True, type="primary"):
        if w_total == 100:
            normalized = {k: v / 100.0 for k, v in weights_input.items()}
            st.session_state.weights = normalized
            st.session_state.page = "results"
            st.rerun()
        else:
            st.error(f"Toplam %{w_total}. %100 olmalıdır.")
