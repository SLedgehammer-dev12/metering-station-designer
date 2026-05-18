import streamlit as st
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

st.cache_data.clear()

NPS_OPTIONS = [2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 30, 36, 42, 48]
FLUID_OPTIONS = ["doğal_gaz", "ham_petrol"]
FLUID_LABELS = {"doğal_gaz": "Doğal Gaz", "ham_petrol": "Ham Petrol"}
SERVICE_OPTIONS = {"custody_transfer": "Custody Transfer (Ticari)", "fiscal": "Fiscal (Resmi)", "process": "Proses Kontrol"}
EX_ZONE_OPTIONS = ["zone_0", "zone_1", "zone_2", "none"]
UPSTREAM_OPTIONS = {
    "single_bend_90": "Tek 90° dirsek",
    "double_bend_in_plane": "Çift dirsek (düzlem içi)",
    "double_bend_out_of_plane": "Çift dirsek (düzlem dışı)",
    "reducer_expander": "Redüksiyon / Genişletici",
    "full_ball_valve": "Tam geçişli küresel vana",
    "control_valve": "Regülatör / Kontrol vanası",
}
MATERIAL_OPTIONS = {
    "A106_GrB": "A106 Gr.B Karbon Çelik",
    "A333_Gr6": "A333 Gr.6 (-46°C) Düşük Sıcaklık",
    "A312_TP304": "SS 304 Paslanmaz",
    "A312_TP316": "SS 316 Paslanmaz",
    "A312_Duplex_2205": "Duplex SS 2205",
    "API_5L_X52": "API 5L X52",
}
