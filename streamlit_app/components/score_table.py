import streamlit as st
from metering_designer.core.weights import CATEGORY_LABELS_TR
from metering_designer.core.i18n import get_text

lang = st.session_state.lang
t = lambda k: get_text(k, lang)


def render_score_table(results: list) -> object:
    if not results:
        st.info(t("no_eval_yet"))
        return None

    table_data = []
    for r in results:
        cat_scores = {}
        for ck, cv in r.categories.items():
            label = t(f"weights_cat_{ck}") if ck in CATEGORY_LABELS_TR else CATEGORY_LABELS_TR.get(ck, ck)
            cat_scores[label] = f"{cv.score:.1f}"
        table_data.append({
            t("score_rank"): len(table_data) + 1,
            t("meter_type"): r.name_tr if lang != "en" else r.name_en,
            "Tier": r.tier_label,
            t("total_score"): f"{r.total_score:.1f}",
            **cat_scores,
        })

    selected_idx = None
    selected_data = None
    names = [f"{'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else f'{i+1}. '} {r.name_tr if lang != 'en' else r.name_en} ({r.total_score:.1f})"
             for i, r in enumerate(results)]

    selection = st.radio(
        t("select_meter"),
        options=list(range(len(results))),
        format_func=lambda i: names[i],
        index=None,
        key="meter_selection",
    )

    if selection is not None and 0 <= selection < len(results):
        selected_data = results[selection]
        st.session_state.selected_meter_idx = selection

    # Tablo gösterimi
    col_spec = {
        t("score_rank"): st.column_config.NumberColumn(width=30),
        t("meter_type"): st.column_config.TextColumn(width=180),
        "Tier": st.column_config.TextColumn(width=50),
        t("total_score"): st.column_config.TextColumn(width=60),
    }
    for ck in CATEGORY_LABELS_TR:
        col_spec[t(f"weights_cat_{ck}")] = st.column_config.TextColumn(width=60)

    st.dataframe(
        table_data,
        column_config=col_spec,
        hide_index=True,
        use_container_width=True,
    )

    return selected_data