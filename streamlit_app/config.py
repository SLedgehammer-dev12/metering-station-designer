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
    "A106_GrB": "A106 Gr.B — Karbon Çelik (≤400°C, Standart)",
    "A333_Gr6": "A333 Gr.6 — Düşük Sıcaklık Karbon Çelik (-46°C)",
    "A312_TP304": "SS 304 — Paslanmaz Çelik",
    "A312_TP316": "SS 316 — Paslanmaz Çelik (Korozyon Dayanımlı)",
    "A312_Duplex_2205": "Duplex SS 2205 — Yüksek Dayanım + Korozyon",
    "API_5L_B": "API 5L B — Düşük Basınç Hat Borusu (241 MPa)",
    "API_5L_X42": "API 5L X42 — Orta Basınç (290 MPa)",
    "API_5L_X46": "API 5L X46 — Orta-Yüksek Basınç (317 MPa)",
    "API_5L_X52": "API 5L X52 — Yüksek Basınç (359 MPa)",
    "API_5L_X56": "API 5L X56 — Yüksek Basınç (386 MPa)",
    "API_5L_X60": "API 5L X60 — Yüksek Basınç (414 MPa)",
    "API_5L_X65": "API 5L X65 — Çok Yüksek Basınç (448 MPa)",
    "API_5L_X70": "API 5L X70 — Ultra Yüksek Basınç (483 MPa)",
    "API_5L_X80": "API 5L X80 — Maksimum Dayanım (552 MPa)",
}
