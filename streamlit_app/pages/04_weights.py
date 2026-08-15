import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".."))
from metering_designer.core.weights import DEFAULT_WEIGHTS, CATEGORY_LABELS_TR
from metering_designer.core.i18n import get_text

lang = st.session_state.get("lang", "tr")
t = lambda k: get_text(k, lang)

st.header(t("weights_header"))
st.caption(t("weights_caption"))

if st.session_state.weights is None:
    weights = dict(DEFAULT_WEIGHTS)
else:
    weights = dict(st.session_state.weights)

st.info(t("weights_hint"))
st.divider()

w_total = 0.0
weights_input = {}
for key in CATEGORY_LABELS_TR:
    default_pct = int(weights.get(key, DEFAULT_WEIGHTS.get(key, 0.2)) * 100)
    val = st.slider(t(f"weights_cat_{key}"), min_value=0, max_value=100, value=default_pct, step=5,
                    key=f"w_{key}")
    weights_input[key] = val
    w_total += val

st.divider()
if w_total != 100:
    st.warning(f"⚠️ {t('weights_total_ok')} %{w_total} ({t('weights_total_warn')}, {t('weights_remaining')}: %{100-w_total:+})")
else:
    st.success(f"✅ {t('weights_total_ok')} %{w_total}")

col1, col2 = st.columns(2)
with col1:
    if st.button(t("weights_reset"), use_container_width=True):
        st.session_state.weights = None
        st.rerun()
with col2:
    if st.button(t("weights_confirm"), use_container_width=True, type="primary"):
        if w_total == 100:
            normalized = {k: v / 100.0 for k, v in weights_input.items()}
            st.session_state.weights = normalized
            st.session_state.page = "results"
            st.rerun()
        else:
            st.error(f"⚠️ {t('weights_total_ok')} %{w_total}. {t('weights_error')}")