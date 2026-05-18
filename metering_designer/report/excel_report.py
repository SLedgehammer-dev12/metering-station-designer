"""
Excel report generation for metering station design.
"""

import io
from typing import Optional

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

from metering_designer.core.weights import CATEGORY_LABELS_TR


def generate_excel_report(
    project: dict,
    process: dict,
    requirements: dict,
    scored_meters: list,
    selected_meter,
    engineering: dict,
    conditioners: Optional[list] = None,
) -> io.BytesIO:
    if not HAS_OPENPYXL:
        raise ImportError("openpyxl gereklidir: pip install openpyxl")

    wb = Workbook()

    # --- Colors ---
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=14, bold=True, color="1F4E79")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )

    def style_header(ws, row, cols):
        for c in range(1, cols + 1):
            cell = ws.cell(row=row, column=c)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
            cell.border = thin_border

    # Sheet 1: Executive Summary
    ws1 = wb.active
    ws1.title = "Ozet"

    ws1.cell(row=1, column=1, value="ÖLÇÜM İSTASYONU DİZAYN RAPORU").font = title_font
    ws1.merge_cells("A1:D1")
    ws1.cell(row=2, column=1, value=f"Proje: {project.get('name','-')}  |  Konum: {project.get('location','-')}")
    ws1.cell(row=3, column=1, value=f"Tarih: {project.get('date','-')}  |  Etiket: {project.get('tag','-')}")

    ws1.cell(row=5, column=1, value="SEÇILEN METRE").font = Font(bold=True, size=12)
    ws1.cell(row=6, column=1, value=f"Tip: {selected_meter.name_tr}")
    ws1.cell(row=6, column=2, value=f"Puan: {selected_meter.total_score}/100")
    ws1.cell(row=6, column=3, value=f"Tier: {selected_meter.tier_label}")

    ws1.cell(row=8, column=1, value="PROSES ÖZETI").font = Font(bold=True, size=12)
    row = 9
    for k, v in [("Akışkan", process.get("fluid_type","-")),
                  ("Q min/nom/max", f"{process.get('qmin',0)}/{process.get('qnormal',0)}/{process.get('qmax',0)}"),
                  ("P işl / tas", f"{process.get('oper_p_bar',0)} / {process.get('design_p_bar',0)} barg"),
                  ("T işl / tas", f"{process.get('oper_t_c',0)} / {process.get('design_t_c',0)} °C"),
                  ("NPS", process.get("nps", "-"))]:
        ws1.cell(row=row, column=1, value=k).font = Font(bold=True)
        ws1.cell(row=row, column=2, value=str(v))
        row += 1

    # Sheet 2: Scoring Details
    ws2 = wb.create_sheet("Puanlama")
    ws2.cell(row=1, column=1, value="METRE PUANLAMA DETAYI").font = title_font
    ws2.merge_cells("A1:G1")

    headers = ["Sıra", "Metre Tipi", "Toplam Puan", "Tier"] + list(CATEGORY_LABELS_TR.values())
    for c, h in enumerate(headers, 1):
        ws2.cell(row=3, column=c, value=h)
    style_header(ws2, 3, len(headers))

    for i, m in enumerate(scored_meters, 1):
        r = i + 3
        ws2.cell(row=r, column=1, value=i)
        ws2.cell(row=r, column=2, value=m.name_tr)
        ws2.cell(row=r, column=3, value=m.total_score)
        ws2.cell(row=r, column=4, value=m.tier_label)
        col = 5
        for ck in CATEGORY_LABELS_TR:
            cat = m.categories.get(ck)
            ws2.cell(row=r, column=col, value=round(cat.score, 2) if cat else 0)
            col += 1

    for c in range(1, len(headers) + 1):
        ws2.column_dimensions[get_column_letter(c)].width = 18

    # Sheet 3: Detailed Scoring (selected meter)
    ws3 = wb.create_sheet("Detay Puan")
    ws3.cell(row=1, column=1, value=f"DETAY PUANLAMA: {selected_meter.name_tr}").font = title_font
    ws3.cell(row=3, column=1, value="Kategori").font = Font(bold=True)
    ws3.cell(row=3, column=2, value="Kriter").font = Font(bold=True)
    ws3.cell(row=3, column=3, value="Puan (0-10)").font = Font(bold=True)
    ws3.cell(row=3, column=4, value="Ağırlık").font = Font(bold=True)
    ws3.cell(row=3, column=5, value="Açıklama").font = Font(bold=True)
    style_header(ws3, 3, 5)

    r = 4
    for ck, cl in CATEGORY_LABELS_TR.items():
        cat = selected_meter.categories.get(ck)
        if not cat:
            continue
        ws3.cell(row=r, column=1, value=cl).font = Font(bold=True)
        ws3.cell(row=r, column=2, value=f"{cat.score:.2f} (ağırlık: {cat.weight*100:.0f}%)")
        r += 1
        for crit in cat.criteria:
            ws3.cell(row=r, column=2, value=crit.name)
            ws3.cell(row=r, column=3, value=round(crit.score, 2))
            ws3.cell(row=r, column=4, value=round(crit.weight * 100, 0))
            ws3.cell(row=r, column=5, value=crit.justification)
            r += 1

    ws3.column_dimensions["E"].width = 60

    # Sheet 4: Flow Conditioner
    if conditioners:
        ws4 = wb.create_sheet("Akis Düzenleyici")
        ws4.cell(row=1, column=1, value="AKIŞ DÜZENLEYICI PUANLAMA").font = title_font
        headers_c = ["Sıra", "Tip", "Toplam Puan", "K Faktörü", "Düz Boru Azaltma", "ISO Uyumlu", "Etkili Uzunluk (m)"]
        for c, h in enumerate(headers_c, 1):
            ws4.cell(row=3, column=c, value=h)
        style_header(ws4, 3, len(headers_c))
        for i, cond in enumerate(conditioners[:5], 1):
            r = i + 3
            ws4.cell(row=r, column=1, value=i)
            ws4.cell(row=r, column=2, value=cond["name_tr"])
            ws4.cell(row=r, column=3, value=cond["total_score"])
            ws4.cell(row=r, column=4, value=cond["k_factor"])
            ws4.cell(row=r, column=5, value=cond["reduction_pct"])
            ws4.cell(row=r, column=6, value="Evet" if cond["iso_compliant"] else "Hayır")
            ws4.cell(row=r, column=7, value=cond["effective_length_m"])

    # Sheet 5: Standards Checklist
    ws5 = wb.create_sheet("Standartlar")
    ws5.cell(row=1, column=1, value="STANDARTLAR KONTROL LISTESI").font = title_font
    ws5.cell(row=3, column=1, value="Standart").font = Font(bold=True)
    ws5.cell(row=3, column=2, value="Uygulandı").font = Font(bold=True)
    ws5.cell(row=3, column=3, value="Not").font = Font(bold=True)
    style_header(ws5, 3, 3)

    standards = [
        ("ASME B31.3", "✓", "Proses borulama dizaynı"),
        ("ASME B16.5", "✓", "Flanş seçimi"),
        ("ISO 15156 / NACE MR0175", "✓" if requirements.get("h2s") else "—", "Sour servis malzeme"),
        ("IEC 60079-10-1", "✓", "Ex zone sınıflandırma"),
        ("IEC 61511", "✓", "SIL değerlendirme"),
        ("ISO 5168", "✓", "Belirsizlik bütçesi"),
        ("ISO 6976", "✓", "Gaz ısıl değer hesabı"),
    ]
    meter_standards = {"ultrasonic": "AGA 9 / ISO 17089", "orifice": "ISO 5167-2 / AGA 3",
                        "turbine": "AGA 7 / ISO 9951", "coriolis": "AGA 11 / ISO 10790",
                        "vortex": "ISO 17089-2", "positive_displacement": "API MPMS Ch.4"}
    if selected_meter.meter_key in meter_standards:
        standards.insert(0, (meter_standards[selected_meter.meter_key], "✓", "Metre tipi standardı"))

    for i, (std, status, note) in enumerate(standards, 4):
        ws5.cell(row=i, column=1, value=std)
        ws5.cell(row=i, column=2, value=status)
        ws5.cell(row=i, column=3, value=note)
    ws5.column_dimensions["A"].width = 30
    ws5.column_dimensions["C"].width = 40

    # Save
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
