import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".."))
from streamlit_app.components.score_table import render_score_table
from streamlit_app.components.radar_chart import render_radar_chart
from streamlit_app.components.justification_card import render_justification_card
from metering_designer.meters.selector import evaluate_all_meters
from metering_designer.core.weights import DEFAULT_WEIGHTS, CATEGORY_LABELS_TR
from metering_designer.core.i18n import get_text

lang = st.session_state.lang
t = lambda k: get_text(k, lang)

st.header(t("results_header"))
st.caption(t("results_caption"))

proc = st.session_state.process
req = st.session_state.requirements
weights = st.session_state.weights if st.session_state.weights else DEFAULT_WEIGHTS

if not proc or not proc.get("fluid_type"):
    st.warning(t("results_first_enter_process"))
    if st.button(t("results_back_process"), key="nav_results_back_process"):
        st.session_state.page = "process"
        st.rerun()
    st.stop()

if st.session_state.results is None:
    with st.spinner(t("results_loading")):
        inputs = {
            "fluid_type": proc.get("fluid_type", "gas"),
            "nps": proc.get("nps", 8),
            "od_mm": proc.get("od_mm", 219.1),
            "oper_p_bar": proc.get("oper_p_bar", 40.0),
            "design_p_bar": proc.get("design_p_bar", 50.0),
            "oper_t_c": proc.get("oper_t_c", 40.0),
            "design_t_c": proc.get("design_t_c", 60.0),
            "qmin": proc.get("qmin", 5000),
            "qnormal": proc.get("qnormal", 10000),
            "qmax": proc.get("qmax", 30000),
            "composition": proc.get("composition", {}),
            "upstream_config": proc.get("upstream_config", "single_bend_90"),
            "material": proc.get("material", "A106_GrB"),
            "service_type": proc.get("service_type", "process"),
            "h2s": req.get("h2s", False),
            "h2s_ppm": req.get("h2s_ppm", 0.0),
            "ex_zone": req.get("ex_zone", "zone_2"),
            "target_uncertainty": req.get("target_uncertainty", 1.0),
            "location": req.get("location", "turkey"),
            "has_gas_detection": req.get("has_gas_detection", True),
            "ambient_min_C": req.get("ambient_min_C", -10),
            "ambient_max_C": req.get("ambient_max_C", 45),
            "power_source": req.get("power_source", "grid"),
            "site_length_limit_m": req.get("site_length_limit_m", 0.0),
        }

        results = evaluate_all_meters(inputs, weights=weights, fluid_type=inputs["fluid_type"])
        st.session_state.results = results

results = st.session_state.results
if not results:
    st.error(t("results_no_result"))
    st.stop()

st.success(f"✅ {len(results)} {t('results_evaluated')} — {t('results_top_score')}: {results[0].name_tr} ({results[0].total_score:.0f}/100)")

with st.expander(t("results_explain_title"), expanded=False):
    st.markdown(t("results_explain_body"))

st.divider()

# Bölüm A: Sıralı Puan Tablosu
st.subheader(t("results_tier_table"))
selected = render_score_table(results)

# Bölüm B: Seçilen metre güncelle
if selected:
    st.session_state.selected_meter = selected

# Bölüm C: Radar Chart
if selected:
    st.subheader(t("results_radar"))
    render_radar_chart(results[:3])

# Bölüm D: Gerekçe Kartı
if selected:
    st.subheader(t("results_justify"))
    render_justification_card(selected)
else:
    st.info(t("results_select_hint"))

# E: Parallel Comparison
if len(results) >= 2:
    with st.expander(t("results_compare"), expanded=False):
        st.caption(t("results_compare_caption"))
        compare = st.multiselect(t("results_compare_select"), [r.name_tr for r in results],
                                  default=[r.name_tr for r in results[:3]], key="results_compare_sel")
        if len(compare) >= 2:
            comp_meters = [r for r in results if r.name_tr in compare]
            comp_data = []
            for r in comp_meters:
                row = {t("results_col_meter"): r.name_tr, t("score_value"): f"{r.total_score:.0f}", "Tier": r.tier_label}
                for ck in CATEGORY_LABELS_TR:
                    cat = r.categories.get(ck)
                    row[t(f"weights_cat_{ck}")] = f"{cat.score:.1f}" if cat else "-"
                comp_data.append(row)
            st.dataframe(comp_data, hide_index=True, use_container_width=True)

            # Key difference analysis
            if len(comp_meters) == 2:
                a, b = comp_meters
                diffs = []
                for ck in CATEGORY_LABELS_TR:
                    ca = a.categories.get(ck)
                    cb = b.categories.get(ck)
                    if ca and cb and abs(ca.score - cb.score) > 0.3:
                        winner = a if ca.score > cb.score else b
                        diffs.append(f"**{t(f'weights_cat_{ck}')}**: {winner.name_tr} {abs(ca.score-cb.score):.1f} {t('results_points_ahead')}")
                if diffs:
                    st.markdown(t("results_key_diffs"))
                    for d in diffs:
                        st.markdown(f"- {d}")

st.divider()

# Detay Mühendislik Sayfasına Geçiş
if selected:
    col_nav1, col_nav2, col_nav3 = st.columns([1, 1, 1])
    with col_nav1:
        if st.button(t("results_back_weights"), use_container_width=True, key="nav_results_back_weights"):
            st.session_state.page = "weights"
            st.rerun()
    with col_nav2:
        if st.button(f"{t('results_confirm')} {selected.name_tr}", use_container_width=True, type="primary", key="nav_results_confirm"):
            st.session_state.selected_meter = selected
            st.session_state.page = "engineering"
            st.rerun()
    with col_nav3:
        if st.button(t("results_recalc"), use_container_width=True, key="nav_results_recalc"):
            st.session_state.results = None
            st.rerun()
