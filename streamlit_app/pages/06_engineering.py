import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".."))
from metering_designer.core.weights import CATEGORY_LABELS_TR
from metering_designer.piping.wall_thickness import calc_min_wall_thickness, get_od_from_nps, calc_flange_min_class
from metering_designer.piping.materials import select_material
from metering_designer.piping.schedule import recommend_schedule
from metering_designer.safety.ex_classification import classify_ex
from metering_designer.safety.sil import assess_sil
from metering_designer.metrology.uncertainty import calc_uncertainty_budget
from metering_designer.auxiliaries.straight_pipe import calc_straight_pipe
from metering_designer.auxiliaries.pressure_loss import estimate_permanent_pressure_loss
from metering_designer.conditioners.scoring import score_all_conditioners, recommend_conditioner
from metering_designer.fluids.gas import calc_gas_properties

st.header("📐 Detay Mühendislik")
st.caption("Seçilen metre tipi için detaylı mühendislik hesaplamaları.")

selected = st.session_state.selected_meter
proc = st.session_state.process
req = st.session_state.requirements

if not selected:
    st.warning("⚠️ Henüz bir metre seçilmedi.")
    if st.button("⬅️ Sonuçlara Dön"):
        st.session_state.page = "results"
        st.rerun()
    st.stop()

st.success(f"🔍 Seçilen: {selected.name_tr} (Puan: {selected.total_score:.1f}/100 {selected.tier_label})")

# Gas properties for detailed calculations
nps = proc.get("nps", 8)
design_p = proc.get("design_p_bar", 50)
design_t = proc.get("design_t_c", 50)
oper_p = proc.get("oper_p_bar", 40)
oper_t = proc.get("oper_t_c", 40)
qmin = proc.get("qmin", 5000)
qmax = proc.get("qmax", 30000)
qnorm = proc.get("qnormal", 10000)
material = proc.get("material", "A106_GrB")
od_mm = proc.get("od_mm", 219.1)

# Compute gas properties
gas = {"rho_oper_kg_m3": 40, "rho_std_kg_m3": 0.75, "mu_dynamic_Pa_s": 1.5e-6, "Z_oper": 0.9}
if proc.get("composition") and proc.get("fluid_type") == "doğal_gaz":
    try:
        gas = calc_gas_properties(proc["composition"], oper_p, oper_t, design_p, design_t)
    except Exception:
        pass

rho_oper = gas.get("rho_oper_kg_m3", 40)
rho_std = gas.get("rho_std_kg_m3", 0.75)
mu = gas.get("mu_dynamic_Pa_s", 1.5e-6)
Z_oper = gas.get("Z_oper", 0.9)

# ═══════════════ 1. METRE BOYUTLANDIRMA ═══════════════
st.subheader("1️⃣ Metre Boyutlandırma")

meter_key = selected.meter_key
meter_details = {}

if "orifice" in meter_key:
    from metering_designer.meters.orifice import size_orifice_for_flow
    meter_details = size_orifice_for_flow(qmax, qmin, od_mm * 0.88, oper_p, oper_t, rho_oper, mu, Z_oper, rho_std)
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("β Oranı (d/D)", f"{meter_details.get('beta', 0):.4f}")
    with col_b:
        st.metric("Orifis Çapı", f"{meter_details.get('d_mm', 0):.1f} mm")
    with col_c:
        st.metric("Cd (RHG)", f"{meter_details.get('Cd', 0):.5f}")
    col_d, col_e, col_f = st.columns(3)
    with col_d:
        st.metric("ΔP @ Qmax", f"{meter_details.get('dp_at_qmax_mbar', 0):.0f} mbar")
    with col_e:
        st.metric("Kalıcı ΔP", f"{meter_details.get('dp_permanent_mbar', 0):.0f} mbar")
    with col_f:
        st.metric("Re", f"{meter_details.get('Re', 0):.0f}")
    if meter_details.get("notes"):
        st.caption(meter_details["notes"])

elif "ultrasonic" in meter_key:
    from metering_designer.meters.ultrasonic import size_ultrasonic
    meter_details = size_ultrasonic(nps, qmax, qmin, oper_p, oper_t, rho_oper, mu, rho_std)
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Önerilen Konfig.", f"{meter_details.get('recommended_paths', 4)}-yollu")
    with col_b:
        st.metric("Max Hız", f"{meter_details.get('v_max_ms', 0):.1f} m/s")
    with col_c:
        st.metric("Metre Boyutu", f"NPS {meter_details.get('meter_size_nps', nps)}")
    col_d, col_e = st.columns(2)
    with col_d:
        st.metric("K-Faktörü", f"{meter_details.get('k_factor_estimated', 0):.4f}")
    with col_e:
        st.metric("Tipik Belirsizlik", f"±{meter_details.get('typical_uncertainty_pct', 0.4)}%")
    st.info(meter_details.get("sizing_note", ""))

elif "turbine" in meter_key:
    from metering_designer.meters.turbine import size_turbine
    meter_details = size_turbine(nps, qmax, qmin, oper_p, oper_t, rho_oper, mu, rho_std)
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Maks Kapasite", f"{meter_details.get('q_act_max_m3h', 0):.0f} m³/h")
    with col_b:
        st.metric("K-Faktörü", f"{int(meter_details.get('K_factor_pulses_per_m3', 0))} puls/m³")
    with col_c:
        st.metric("Rulman Ömrü", f"{meter_details.get('estimated_bearing_life_h', 0):.0f} h")
    col_d, col_e = st.columns(2)
    with col_d:
        st.metric("Turndown", f"1:{meter_details.get('turndown_actual', 0):.0f}")
    with col_e:
        st.metric("ΔP", f"{meter_details.get('dp_estimate_mbar', 0):.1f} mbar")
    st.info(meter_details.get("sizing_note", ""))

elif "coriolis" in meter_key:
    from metering_designer.meters.coriolis import size_coriolis
    meter_details = size_coriolis(nps, qmax, qmin, oper_p, oper_t, rho_oper, mu, rho_std)
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Metre Boyutu", f"NPS {meter_details.get('meter_size_inches', 2)}\"")
    with col_b:
        st.metric("Kapasite Kullanımı", f"%{meter_details.get('capacity_percent', 0):.0f}")
    with col_c:
        st.metric("ΔP", f"{meter_details.get('dp_estimate_mbar', 0):.0f} mbar")
    col_d, col_e = st.columns(2)
    with col_d:
        st.metric("Sıfır Etkisi @Qmin", f"%{meter_details.get('zero_effect_at_qmin_pct', 0):.3f}")
    with col_e:
        st.metric("Kütlesel Debi", f"{meter_details.get('qm_max_kg_s', 0):.1f} kg/s")
    st.info(meter_details.get("sizing_note", ""))

elif "positive_displacement" in meter_key or "pd" in meter_key:
    from metering_designer.meters.pd_meter import size_pd_meter
    q_act_max = qmax * rho_std / rho_oper if rho_oper > 0 else qmax
    q_act_min = qmin * rho_std / rho_oper if rho_oper > 0 else qmin
    meter_details = size_pd_meter(nps, q_act_max, q_act_min, rho_oper, 5.0, oper_p, oper_t)
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Metre Boyutu", f"NPS {meter_details.get('meter_size_inches', nps)}\"")
    with col_b:
        st.metric("Kapasite", f"%{meter_details.get('capacity_percent', 0):.0f}")
    with col_c:
        st.metric("K-Faktörü", f"{meter_details.get('K_factor_pulses_per_m3', 0)} puls/m³")
    col_d, col_e = st.columns(2)
    with col_d:
        st.metric("Slip @ Qmin", f"%{meter_details.get('slip_pct_at_qmin', 0):.3f}")
    with col_e:
        st.metric("ΔP", f"{meter_details.get('delta_p_mbar', 0):.0f} mbar")
    st.info(meter_details.get("sizing_note", ""))

elif "vortex" in meter_key:
    from metering_designer.meters.vortex import size_vortex
    is_gas = proc.get("fluid_type", "gas") in ("doğal_gaz", "gas")
    meter_details = size_vortex(nps, qmax, qmin, oper_p, oper_t, rho_oper, mu, rho_std, is_gas)
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Max Hız", f"{meter_details.get('v_max_ms', 0):.1f} m/s")
    with col_b:
        st.metric("Frekans", f"{meter_details.get('f_max_hz', 0):.0f} Hz")
    with col_c:
        st.metric("K-Faktörü", f"{meter_details.get('K_factor_pulses_per_m3', 0)} puls/m³")
    col_d, col_e = st.columns(2)
    with col_d:
        st.metric("Turndown", f"1:{meter_details.get('turndown_actual', 0):.0f}")
    with col_e:
        st.metric("ΔP", f"{meter_details.get('dp_mbar', 0):.1f} mbar")
    if not meter_details.get("velocity_ok", True):
        st.warning("Hız vortex sınırları dışında!")
    if not meter_details.get("frequency_ok", True):
        st.warning("Frekans çok düşük!")
    st.info(meter_details.get("notes", ""))

elif "v_cone" in meter_key or "vcone" in meter_key:
    from metering_designer.meters.vcone import size_v_cone
    is_gas = proc.get("fluid_type", "gas") in ("doğal_gaz", "gas")
    meter_details = size_v_cone(nps, qmax, qmin, oper_p, oper_t, rho_oper, mu, rho_std, is_gas)
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("β Oranı", f"{meter_details.get('beta', 0):.4f}")
    with col_b:
        st.metric("Koni Çapı", f"{meter_details.get('d_cone_mm', 0):.1f} mm")
    with col_c:
        st.metric("Cd", f"{meter_details.get('Cd', 0):.5f}")
    col_d, col_e = st.columns(2)
    with col_d:
        st.metric("ΔP", f"{meter_details.get('dp_mbar', 0):.0f} mbar")
    with col_e:
        st.metric("Kalıcı ΔP", f"{meter_details.get('dp_perm_mbar', 0):.0f} mbar")
    st.info(meter_details.get("notes", ""))

st.session_state.engineering = {"meter_details": meter_details, "gas": gas}

st.divider()

# ═══════════════ 2. BORU TASARIMI ═══════════════
st.subheader("2️⃣ Boru Tasarımı (ASME B31.3 + Schedule)")

pipe = calc_min_wall_thickness(design_p, design_t, od_mm, material)
if "error" not in pipe:
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Min Et Kalınlığı", f"{pipe.get('t_min_pressure_mm', 0):.2f} mm")
    with col_b:
        st.metric("Korozyon Payı Dahil", f"{pipe.get('t_required_mm', 0):.2f} mm")
    with col_c:
        st.metric("Malzeme", material.replace("_", " "))

    # Schedule recommendation
    sched = recommend_schedule(nps, pipe.get("t_with_tolerance_mm", pipe.get("t_required_mm", 0)))
    if sched.get("recommended"):
        st.success(f"Önerilen: **{sched['recommended']['schedule_name']}** ({sched['recommended']['wall_mm']} mm) | NPS {nps} OD: {sched['od_mm']} mm")
        with st.expander("Diğer Schedule Seçenekleri"):
            for s in sched.get("available_schedules", []):
                st.caption(f"  {s['name']}: {s['wall']} mm")
    else:
        st.warning(sched.get("notes", ""))
    st.session_state.engineering["pipe"] = pipe
    st.session_state.engineering["schedule"] = sched
else:
    st.error(pipe.get("error"))

# Flange
flange = calc_flange_min_class(design_p, design_t, "carbon_steel" if "A106" in material else "ss_304" if "304" in material else "carbon_steel")
if "error" not in flange:
    st.metric("Flanş Sınıfı", f"Class {flange.get('flange_class', '?')}#")
else:
    st.warning(flange.get("error"))

st.divider()

# ═══════════════ 3. AKIŞ DÜZENLEYICI PUANLAMA ═══════════════
st.subheader("3️⃣ Akış Düzenleyici Önerisi")
st.caption("Çok kriterli puanlama ile en uygun akış düzenleyici seçimi.")

up_conf = proc.get("upstream_config", "single_bend_90")
sp = calc_straight_pipe(meter_key, nps, up_conf)
site_limit = req.get("site_length_limit_m", 0.0)
straight_total = sp.get("total_required_m", 4.0)

col_s1, col_s2 = st.columns(2)
with col_s1:
    st.metric("Gerekli Düz Boru (Toplam)", f"{straight_total:.2f} m")
with col_s2:
    st.metric("Saha Limiti", f"{site_limit} m" if site_limit > 0 else "Limitsiz")

conditioner_results = score_all_conditioners(meter_key, nps, up_conf, site_limit, straight_total)

if conditioner_results:
    best_cond = conditioner_results[0]
    st.session_state.engineering["conditioners"] = conditioner_results

    st.markdown(f"**En Uygun: {best_cond['name_tr']}** ({best_cond['total_score']:.0f}/100)")

    # Show conditioner scoring table
    cond_data = []
    for c in conditioner_results[:4]:
        cond_data.append({
            "Tip": c["name_tr"],
            "Puan": f"{c['total_score']:.0f}",
            "K": c["k_factor"],
            "Azaltma": f"%{c['reduction_pct']:.0f}",
            "ISO Uyumlu": "✅" if c["iso_compliant"] else "❌",
            "L (m)": c["effective_length_m"],
        })
    st.dataframe(cond_data, hide_index=True, use_container_width=True)

    # Show note about selected conditioner
    if best_cond["effective_length_m"] <= straight_total * 0.7:
        st.success(f"✅ {best_cond['name_tr']} gerekli düz boruyu ~%30 kısaltır")
    else:
        st.info(f"Düz boru kısaltması gerekmiyorsa akış düzenleyici opsiyoneldir")

st.divider()

# ═══════════════ 4. EX / SIL / Belirsizlik ═══════════════
st.subheader("4️⃣ Emniyet & Metroloji")

col_ex, col_sil, col_unc = st.columns(3)
with col_ex:
    ex = classify_ex(fluid_type=proc.get("fluid_type", "gas"), h2s=req.get("h2s", False),
                     has_gas_detection=req.get("has_gas_detection", True))
    st.metric("Ex Zone", ex.get("zone", "-"))
    st.caption(f"Grup {ex.get('gas_group', '-')} | T{ex.get('temperature_class', '3').replace('T', '')} | IP66")

with col_sil:
    sil = assess_sil(consequence="serious" if proc.get("service_type") == "custody_transfer" else "minor")
    st.metric("SIL", sil.get("sil_rating", "-"))

with col_unc:
    unc = calc_uncertainty_budget(meter_key)
    st.metric("Belirsizlik (k=2)", f"±{unc.get('expanded_uncertainty_k2_95pct', 0):.3f}%")

st.session_state.engineering["ex"] = ex
st.session_state.engineering["sil"] = sil
st.session_state.engineering["uncertainty"] = unc
st.session_state.engineering["straight_pipe"] = sp

st.divider()

# Gezinme
col_n1, col_n2 = st.columns(2)
with col_n1:
    if st.button("⬅️ Sonuçlara Dön", use_container_width=True):
        st.session_state.page = "results"
        st.rerun()
with col_n2:
    if st.button("📄 Raporu Görüntüle", use_container_width=True, type="primary"):
        st.session_state.page = "report"
        st.rerun()
