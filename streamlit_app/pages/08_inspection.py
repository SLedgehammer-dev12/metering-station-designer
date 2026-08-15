import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".."))

from metering_designer.core.i18n import get_text
from metering_designer.inspection.builder import (
    build_inspection_checklist, evaluate_report,
    METER_LABELS_TR, CONDITIONER_LABELS_TR,
)
from metering_designer.inspection.uncertainty_impact import compute_geometric_uncertainty
from metering_designer.metrology.uncertainty import calc_uncertainty_budget_detailed
from metering_designer.inspection.compliance_report import generate_compliance_report, HAS_OPENPYXL

lang = st.session_state.lang
t = lambda k: get_text(k, lang)

st.header(t("inspection_header"))
st.caption(t("inspection_caption"))

st.session_state.setdefault("inspection_report", None)

tab1, tab2 = st.tabs([t("inspection_tab_input"), t("inspection_tab_results")])

# ═══════════════ TAB 1: INPUT ═══════════════
with tab1:
    st.subheader(t("inspection_equipment"))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        meter_type = st.selectbox(t("inspection_meter"), list(METER_LABELS_TR.keys()),
                                   format_func=lambda x: METER_LABELS_TR.get(x, x),
                                   key="insp_meter")
    with col2:
        cond_options = ["none"] + list(CONDITIONER_LABELS_TR.keys())
        cond_type = st.selectbox(t("inspection_cond"), cond_options,
                                  format_func=lambda x: CONDITIONER_LABELS_TR.get(x, t("inspection_none")) if x != "none" else t("inspection_none"),
                                  key="insp_cond")
        if cond_type == "none":
            cond_type = None

    with col3:
        nps = st.number_input(t("inspection_nps"), min_value=2, max_value=48, value=8, step=2, key="insp_nps")
    with col4:
        D_mm = st.number_input(t("inspection_d"), min_value=10.0, value=202.7, step=0.1, key="insp_D")

    beta = None
    if "orifice" in meter_type:
        beta = st.number_input(t("inspection_beta"), min_value=0.1, max_value=0.75, value=0.65, step=0.01, key="insp_beta")

    if st.button(t("inspection_build"), use_container_width=True, type="primary", key="nav_insp_build"):
        report = build_inspection_checklist(
            meter_type=meter_type, conditioner_type=cond_type,
            nps=nps, beta=beta, D_mm=D_mm,
        )
        st.session_state.inspection_report = report
        st.session_state.inspection_meter = meter_type
        st.session_state.inspection_cond = cond_type
        st.rerun()

    report = st.session_state.get("inspection_report")
    if not report:
        st.info(t("inspection_hint"))
        st.stop()

    st.divider()

    # Render dynamic forms for each component
    for comp_idx, comp in enumerate(report.components):
        st.subheader(f"{comp.component_name} — {comp.standard}")

        for param_idx, param in enumerate(comp.parameters):
            is_qual = param.is_qualitative
            status = param.overall_status

            col_a, col_b = st.columns([3, 1])
            with col_a:
                crit_icon = {"CRITICAL": "🔴", "MAJOR": "🟡", "MINOR": "🟢"}.get(param.criticality, "⚪")
                st.markdown(f"**{crit_icon} {param.label}** — {param.standard_clause}")
            with col_b:
                if status == "PASS":
                    st.success("PASS")
                elif status == "FAIL":
                    st.error("FAIL")
                elif status == "CONDITIONAL":
                    st.warning("COND")
                else:
                    st.caption("PENDING")

            if is_qual and param.options:
                opts = [opt["label_tr"] for opt in param.options]
                vals = [opt["value"] for opt in param.options]
                cur_val = param.qualitative_value
                cur_idx = vals.index(cur_val) if cur_val in vals else 0

                choice = st.radio(
                    param.label, opts, index=cur_idx, horizontal=True,
                    key=f"param_{comp_idx}_{param_idx}_qual"
                )
                param.qualitative_value = vals[opts.index(choice)]
            else:
                n_pts = len(param.points)
                if n_pts <= 1:
                    pt = param.points[0]
                    val = st.number_input(
                        f"{param.label} ({param.unit})",
                        value=pt.measured if pt.measured is not None else pt.nominal,
                        step=0.01 if param.unit == "mm" else 0.1,
                        key=f"pt_{comp_idx}_{param_idx}_0",
                    )
                    pt.measured = val
                    pt.nominal = (pt.nominal or val)
                    tol = pt.tol_upper or pt.tol_lower
                    if tol:
                        st.caption(f"{t('inspection_tolerance')} {'±' + str(tol) if pt.tol_upper == abs(pt.tol_lower or 0) else f'{pt.tol_lower} — {pt.tol_upper}'} {param.unit}")
                elif n_pts <= 6:
                    cols = st.columns(min(n_pts, 4))
                    for i, pt in enumerate(param.points):
                        with cols[i % len(cols)]:
                            val = st.number_input(
                                f"{pt.position_label}",
                                value=pt.measured if pt.measured is not None else pt.nominal,
                                step=0.01 if param.unit == "mm" else 0.1,
                                key=f"pt_{comp_idx}_{param_idx}_{i}",
                                label_visibility="visible",
                            )
                            pt.measured = val
                            pt.nominal = (pt.nominal or val)
                else:
                    n_cols = 3
                    for row_start in range(0, n_pts, n_cols):
                        cols = st.columns(n_cols)
                        for c in range(n_cols):
                            i = row_start + c
                            if i >= n_pts:
                                break
                            pt = param.points[i]
                            with cols[c]:
                                val = st.number_input(
                                    f"{pt.position_label}",
                                    value=pt.measured if pt.measured is not None else pt.nominal,
                                    step=0.01 if param.unit == "mm" else 0.1,
                                    key=f"pt_{comp_idx}_{param_idx}_{i}",
                                )
                                pt.measured = val
                                pt.nominal = (pt.nominal or val)

            self_status = param.overall_status
            if param.points and any(getattr(pt, "position_label", "") for pt in param.points):
                try:
                    from metering_designer.instruments.schematic import (
                        render_measurement_points_schematic,
                    )
                    fig = render_measurement_points_schematic(
                        param.label, param.points, meter_type, int(nps), lang,
                    )
                    st.pyplot(fig, use_container_width=True)
                except Exception:
                    pass

            st.divider()

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button(t("inspection_clear"), use_container_width=True, key="nav_insp_clear"):
            if "inspection_report" in st.session_state:
                del st.session_state.inspection_report
            st.rerun()
    with col_b2:
        if st.button(t("inspection_evaluate"), use_container_width=True, type="primary", key="nav_insp_evaluate"):
            evaluate_report(report)
            st.rerun()


# ═══════════════ TAB 2: RESULTS ═══════════════
with tab2:
    report = st.session_state.get("inspection_report")
    if not report:
        st.info(t("inspection_go_tab1"))
        st.stop()

    evaluate_report(report)
    geo_unc = compute_geometric_uncertainty(report)

    # Tolerance schematic (informational drawing with tolerance callouts)
    st.subheader(t("inspection_import_tolerance"))
    st.caption(t("inspection_tol_caption"))
    try:
        # Build a lightweight tolerance summary from the inspection parameters
        tol_list = []
        seen = set()
        for comp in report.components:
            for p in comp.parameters:
                for pt in p.points:
                    tol = pt.tol_upper or pt.tol_lower
                    if tol is not None:
                        key = f"{p.label[:24]}" if len(p.label) > 24 else p.label
                        if key not in seen:
                            seen.add(key)
                            tol_list.append((key, f"{pt.tol_lower}…{pt.tol_upper} {p.unit}"))
        tol_summary = dict(tol_list)
        from metering_designer.instruments.schematic import render_schematic
        fig = render_schematic(
            meter_key=report.meter_type,
            nps=report.nps,
            conditioner_key=report.conditioner_type,
            tolerances=tol_summary or None,
            lang=lang,
        )
        st.pyplot(fig)
    except Exception as e:
        st.warning(t("inspection_tol_not_avail"))
        st.caption(str(e))

    st.divider()

    # Overall status
    st.subheader(t("inspection_overall"))
    status = report.overall_status
    if "FAIL" in status:
        st.error(f"🔴 {status}")
    elif "CONDITIONAL" in status:
        st.warning(f"🟡 {status}")
    else:
        st.success(f"🟢 {status}")

    # Progress bar
    rate = report.pass_rate
    st.progress(rate / 100, text=f"{t('inspection_pass_rate')} %{rate:.1f} ({report.passed_params}/{report.total_params})")

    st.divider()

    # Component breakdown table
    st.subheader(t("inspection_breakdown"))
    comp_data = []
    for comp in report.components:
        comp_data.append({
            t("inspection_col_comp"): comp.component_name,
            t("inspection_col_pass"): comp.passed_count,
            t("inspection_col_fail"): comp.failed_count,
            t("inspection_col_pending"): sum(1 for s in comp.all_statuses if s == "PENDING"),
            t("inspection_col_crit"): len(comp.critical_failures),
            t("inspection_col_status"): comp.component_status,
        })
    st.dataframe(comp_data, hide_index=True, use_container_width=True)

    # Critical failures
    crit = report.get_critical_failures()
    if crit:
        st.subheader(t("inspection_critical"))
        for p in crit:
            comp = next((c for c in report.components if p in c.parameters), None)
            st.error(f"**{p.label}** — {p.standard_clause} ({comp.component_name if comp else ''})")

    # All failures
    failed = [p for p in report.all_inspections if p.overall_status == "FAIL" and p.criticality != "CRITICAL"]
    if failed:
        st.subheader(t("inspection_major_minor"))
        for p in failed:
            comp = next((c for c in report.components if p in c.parameters), None)
            st.warning(f"**{p.label}** — {p.standard_clause} ({comp.component_name if comp else ''})")

    # Conditional
    cond = [p for p in report.all_inspections if p.overall_status == "CONDITIONAL"]
    if cond:
        st.subheader(t("inspection_conditional"))
        for p in cond:
            comp = next((c for c in report.components if p in c.parameters), None)
            st.info(f"**{p.label}** — {p.standard_clause} ({comp.component_name if comp else ''})")

    # Uncertainty impact
    st.divider()
    st.subheader(t("inspection_unc_impact"))
    base_unc = calc_uncertainty_budget_detailed(meter_type)["combined_standard_uncertainty_pct"]
    final_budget = calc_uncertainty_budget_detailed(meter_type, geometric_contribution_pct=geo_unc)
    combined_unc = final_budget["combined_standard_uncertainty_pct"]
    expanded_k2 = final_budget["expanded_uncertainty_k2_95pct"]

    col_u1, col_u2, col_u3 = st.columns(3)
    with col_u1:
        st.metric(t("inspection_unc_metric"), f"±{base_unc:.4f}%")
    with col_u2:
        st.metric(t("inspection_geo_contribution"), f"+{geo_unc:.4f}%")
    with col_u3:
        delta = expanded_k2 - base_unc * 2
        delta_str = f"+{delta:.4f}%" if delta > 0 else "0"
        st.metric(t("inspection_total_k2"), f"±{expanded_k2:.4f}%", delta_str)

    # Standards clause violations
    st.divider()
    st.subheader(t("inspection_std_violations"))
    for comp in report.components:
        for param in comp.parameters:
            icon = {"PASS": "✅", "FAIL": "❌", "CONDITIONAL": "⚠️", "PENDING": "⬜"}.get(param.overall_status, "⬜")
            st.caption(f"{icon} {param.standard_clause} — {param.label}")

    # Download
    st.divider()
    st.subheader(t("inspection_download"))
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if HAS_OPENPYXL:
            try:
                buf = generate_compliance_report(report)
                st.download_button(t("inspection_excel"), data=buf,
                                   file_name="geometrik_denetim_raporu.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)
            except Exception as e:
                st.warning(f"Excel raporu oluşturulamadı: {e}")
    with col_d2:
        txt = f"{t('inspection_report_title')}\n{'='*60}\n"
        txt += f"Metre: {report.meter_type} | NPS: {report.nps} | D: {report.D_mm}mm\n"
        txt += f"Kondisyoner: {report.conditioner_type or t('inspection_none')}\n"
        txt += f"Genel Durum: {report.overall_status}\n"
        txt += f"Geçiş Oranı: %{report.pass_rate:.1f} ({report.passed_params}/{report.total_params})\n"
        txt += f"Geometrik Belirsizlik Katkısı: {geo_unc:.4f}%\n"
        st.download_button(t("inspection_txt"), data=txt, file_name="denetim_ozet.txt", use_container_width=True)

    if st.button(t("inspection_fix"), use_container_width=True, key="nav_insp_fix"):
        pass  # stays on same page, user clicks Tab 1 manually
