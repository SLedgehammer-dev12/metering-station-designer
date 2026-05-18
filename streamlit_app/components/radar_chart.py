import streamlit as st
import plotly.graph_objects as go
from metering_designer.core.weights import CATEGORY_LABELS_TR


def render_radar_chart(scored_meters: list):
    if not scored_meters:
        st.info("Yeterli veri yok.")
        return

    categories = list(CATEGORY_LABELS_TR.values())
    cat_keys = list(CATEGORY_LABELS_TR.keys())

    fig = go.Figure()
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    for i, meter in enumerate(scored_meters[:5]):
        scores = []
        for ck in cat_keys:
            cat = meter.categories.get(ck)
            scores.append(cat.score if cat else 0)
        scores.append(scores[0])

        fig.add_trace(go.Scatterpolar(
            r=scores,
            theta=categories + [categories[0]],
            name=f"{meter.name_tr} ({meter.total_score:.1f})",
            line_color=colors[i % len(colors)],
            fill="toself" if i == len(scored_meters) - 1 else None,
            opacity=0.7,
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10]),
            angularaxis=dict(direction="clockwise"),
        ),
        showlegend=True,
        height=450,
        margin=dict(l=40, r=40, t=20, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)
