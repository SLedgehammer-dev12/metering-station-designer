import streamlit as st
from metering_designer.core.weights import CATEGORY_LABELS_TR


def render_score_table(results: list) -> object:
    if not results:
        st.info("Henüz değerlendirme yapılmadı.")
        return None

    table_data = []
    for r in results:
        cat_scores = {}
        for ck, cv in r.categories.items():
            cat_scores[CATEGORY_LABELS_TR.get(ck, ck)] = f"{cv.score:.1f}"
        table_data.append({
            "Sıra": len(table_data) + 1,
            "Metre Tipi": r.name_tr,
            "Tier": r.tier_label,
            "Toplam Puan": f"{r.total_score:.1f}",
            **cat_scores,
        })

    selected_idx = None
    selected_data = None
    names = [f"{'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else f'{i+1}. '} {r.name_tr} ({r.total_score:.1f})"
             for i, r in enumerate(results)]

    selection = st.radio(
        "Metre seçiniz:",
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
        "Sıra": st.column_config.NumberColumn(width=30),
        "Metre Tipi": st.column_config.TextColumn(width=180),
        "Tier": st.column_config.TextColumn(width=50),
        "Toplam Puan": st.column_config.TextColumn(width=60),
    }
    for ck in CATEGORY_LABELS_TR.values():
        col_spec[ck] = st.column_config.TextColumn(width=60)

    st.dataframe(
        table_data,
        column_config=col_spec,
        hide_index=True,
        use_container_width=True,
    )

    return selected_data
