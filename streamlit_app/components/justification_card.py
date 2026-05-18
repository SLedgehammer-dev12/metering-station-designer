import streamlit as st


def render_justification_card(meter):
    if not meter:
        return

    tier_color_map = {"green": "#00cc66", "blue": "#3399ff", "orange": "#ff9900", "red": "#ff3333"}
    color = tier_color_map.get(meter.tier_color, "#666")

    st.markdown(f"""
    <div style="border-left: 4px solid {color}; padding: 1rem; background: #f8f9fa; border-radius: 4px;">
        <h3 style="margin:0">{meter.name_tr} <span style="color:{color};">{meter.tier_label}</span></h3>
        <p style="font-size: 0.9rem; color: #666;">Toplam Puan: <strong>{meter.total_score:.1f}/100</strong></p>
    </div>
    """, unsafe_allow_html=True)

    col_s, col_w = st.columns(2)
    with col_s:
        st.markdown("##### ✅ Güçlü Yönler")
        if meter.strengths:
            for s in meter.strengths:
                st.markdown(f"- {s}")
        else:
            st.markdown("*Belirgin güçlü yön yok*")

    with col_w:
        st.markdown("##### ⚠️ Zayıf Yönler / Dikkat")
        if meter.weaknesses:
            for w in meter.weaknesses:
                st.markdown(f"- {w}")
        else:
            st.markdown("*Belirgin zayıflık yok*")

    st.divider()

    st.markdown("##### 📊 Kategori Kırılımı")
    from metering_designer.core.weights import CATEGORY_LABELS_TR

    for ck, cl in CATEGORY_LABELS_TR.items():
        cat = meter.categories.get(ck)
        if cat:
            pct = cat.score / 10 * 100 if cat.score > 0 else 0
            bar_color = "#00cc66" if cat.score >= 7 else "#ff9900" if cat.score >= 4 else "#ff3333"
            bar_w = max(pct * 0.8, 5)
            st.markdown(f"**{cl}**: {cat.score:.1f}/10 ({cat.weight*100:.0f}%)")
            st.markdown(f'<div style="background:#eee;border-radius:4px;height:18px;width:100%">'
                        f'<div style="background:{bar_color};border-radius:4px;height:18px;width:{bar_w}%;'
                        f'display:flex;align-items:center;justify-content:center;font-size:10px;color:white">'
                        f'{cat.score:.1f}</div></div>',
                        unsafe_allow_html=True)

    st.divider()

    # Yardımcı detaylar
    details = meter.details or {}
    if details:
        st.markdown("##### 🔧 Yardımcı Bilgiler")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Düz Boru (Upstream)", f"{details.get('straight_pipe_upstream_diameters', '-')}D")
        with col_b:
            st.metric("Düz Boru (Toplam)", f"{details.get('straight_pipe_total_m', '-')} m")
        with col_c:
            st.metric("Tahmini ΔP", f"{details.get('estimated_dp_bar', '-')} bar")
