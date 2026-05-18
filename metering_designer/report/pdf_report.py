"""
PDF report generation using reportlab.
3-page summary engineering report for metering station design.
"""

import io
import os
from typing import Optional

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.units import mm, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable,
    )
    from reportlab.platypus.flowables import KeepTogether
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def generate_pdf_report(
    project: dict,
    process: dict,
    requirements: dict,
    selected_meter,
    engineering: dict,
    conditioners: Optional[list] = None,
    language: str = "tr",
) -> io.BytesIO:
    if not HAS_REPORTLAB:
        raise ImportError("reportlab gereklidir: pip install reportlab")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("CustomTitle", parent=styles["Title"], fontSize=16, spaceAfter=6*mm, textColor=HexColor("#1F4E79"))
    h2_style = ParagraphStyle("CustomH2", parent=styles["Heading2"], fontSize=13, spaceBefore=5*mm, spaceAfter=3*mm, textColor=HexColor("#1F4E79"))
    h3_style = ParagraphStyle("CustomH3", parent=styles["Heading3"], fontSize=11, spaceBefore=3*mm, spaceAfter=2*mm)
    body_style = ParagraphStyle("CustomBody", parent=styles["Normal"], fontSize=9.5, spaceAfter=2*mm, leading=13)
    small_style = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, spaceAfter=1*mm, leading=10)
    header_style = ParagraphStyle("Header", fontSize=8, textColor=HexColor("#666666"))

    story = []

    # --- PAGE 1: Cover / Summary ---
    story.append(Paragraph("ÖLÇÜM İSTASYONU DİZAYN RAPORU", title_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=HexColor("#1F4E79")))
    story.append(Spacer(1, 5*mm))

    proj_name = project.get("name", "-") or project.get("name", "-")
    proj_loc = project.get("location", "-") or project.get("location", "-")

    info_data = [
        [Paragraph("<b>Proje:</b>", body_style), Paragraph(str(proj_name), body_style)],
        [Paragraph("<b>Konum:</b>", body_style), Paragraph(str(proj_loc), body_style)],
        [Paragraph("<b>Akışkan:</b>", body_style), Paragraph(str(process.get("fluid_type", "-")), body_style)],
        [Paragraph("<b>Servis Tipi:</b>", body_style), Paragraph(str(process.get("service_type", "-")), body_style)],
    ]
    info_table = Table(info_data, colWidths=[40*mm, 120*mm])
    info_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(info_table)

    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(f"<b>SEÇİLEN METRE: {selected_meter.name_tr}</b>", h2_style))
    story.append(Paragraph(f"Toplam Puan: <b>{selected_meter.total_score:.0f}/100</b> ({selected_meter.tier_label})", body_style))

    # Process summary table
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("Proses Özeti", h3_style))
    proc_data = [
        ["Parametre", "Değer", "Birim"],
        ["Q min", str(process.get("qmin", "-")), "Sm³/h" if "gas" in str(process.get("fluid_type","")) else "m³/h"],
        ["Q normal", str(process.get("qnormal", "-")), "Sm³/h" if "gas" in str(process.get("fluid_type","")) else "m³/h"],
        ["Q max", str(process.get("qmax", "-")), "Sm³/h" if "gas" in str(process.get("fluid_type","")) else "m³/h"],
        ["P işletme", str(process.get("oper_p_bar", "-")), "barg"],
        ["T işletme", str(process.get("oper_t_c", "-")), "°C"],
        ["P tasarım", str(process.get("design_p_bar", "-")), "barg"],
        ["T tasarım", str(process.get("design_t_c", "-")), "°C"],
        ["NPS", str(process.get("nps", "-")), "\""],
    ]
    proc_table = Table(proc_data, colWidths=[40*mm, 35*mm, 40*mm])
    proc_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#F0F4F8")]),
    ]))
    story.append(proc_table)

    # Category scores
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph("Kategori Puanları", h3_style))

    from metering_designer.core.weights import CATEGORY_LABELS_TR
    score_data = [["Kategori", "Puan (/10)", "Ağırlık (%)"]]
    for ck, cl in CATEGORY_LABELS_TR.items():
        cat = selected_meter.categories.get(ck)
        if cat:
            score_data.append([cl, f"{cat.score:.1f}", f"%{cat.weight*100:.0f}"])
    score_data.append(["TOPLAM", f"{selected_meter.total_score:.0f}/100", "100%"])

    score_table = Table(score_data, colWidths=[60*mm, 40*mm, 40*mm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, -1), (-1, -1), HexColor("#E8EEF4")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    story.append(score_table)

    # --- PAGE 2: Engineering Details ---
    story.append(PageBreak())
    story.append(Paragraph("DETAY MÜHENDİSLİK HESAPLARI", h2_style))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#1F4E79")))

    # Piep design
    pipe = engineering.get("pipe", {})
    sched = engineering.get("schedule", {})
    if pipe and "error" not in pipe:
        story.append(Paragraph("Boru Tasarımı (ASME B31.3)", h3_style))
        pd_data = [
            ["Parametre", "Değer"],
            ["Dış Çap", f"{pipe.get('od_mm', '-')} mm"],
            ["Malzeme", str(pipe.get("material", "-"))],
            ["Min Et Kalınlığı", f"{pipe.get('t_min_pressure_mm', '-')} mm"],
            ["Korozyon Payı Dahil", f"{pipe.get('t_required_mm', '-')} mm"],
            ["Tolerans Dahil", f"{pipe.get('t_with_tolerance_mm', '-')} mm"],
        ]
        if sched.get("recommended"):
            pd_data.append(["Önerilen Schedule", f"{sched['recommended']['schedule_name']} ({sched['recommended']['wall_mm']} mm)"])
        pd_table = Table(pd_data, colWidths=[60*mm, 60*mm])
        pd_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#2E7D32")),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))
        story.append(pd_table)

    # Meter sizing
    md = engineering.get("meter_details", {})
    if md:
        story.append(Spacer(1, 5*mm))
        story.append(Paragraph(f"Metre Boyutlandırma ({selected_meter.name_tr})", h3_style))
        md_keys = list(md.keys())[:8]
        md_data = [["Parametre", "Değer"]]
        for k in md_keys:
            if k not in ("notes", "sizing_note"):
                md_data.append([k.replace("_", " ").title(), str(md[k])])
        if len(md_data) > 1:
            md_table = Table(md_data, colWidths=[60*mm, 60*mm])
            md_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#E65100")),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]))
            story.append(md_table)

    # Ex / SIL
    ex = engineering.get("ex", {})
    sil = engineering.get("sil", {})
    unc = engineering.get("uncertainty", {})
    if ex:
        story.append(Spacer(1, 5*mm))
        story.append(Paragraph("Emniyet & Metroloji", h3_style))
        safety_data = [["Parametre", "Değer"]]
        if ex: safety_data.append(["Ex Zone", str(ex.get("zone", "-"))])
        if ex: safety_data.append(["Gaz Grubu", str(ex.get("gas_group", "-"))])
        if sil: safety_data.append(["SIL", str(sil.get("sil_rating", "-"))])
        if unc: safety_data.append(["Belirsizlik (k=2)", f"±{unc.get('expanded_uncertainty_k2_95pct', '-')}%"])
        safety_table = Table(safety_data, colWidths=[60*mm, 60*mm])
        safety_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#C62828")),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))
        story.append(safety_table)

    # Flow conditioner
    if conditioners and len(conditioners) > 0:
        story.append(Spacer(1, 5*mm))
        story.append(Paragraph("Akış Düzenleyici Seçimi", h3_style))
        fc_data = [["Tip", "Puan", "K", "ISO Uyumlu", "L(m)"]]
        for c in conditioners[:3]:
            fc_data.append([
                c["name_tr"],
                f"{c['total_score']:.0f}",
                str(c["k_factor"]),
                "✓" if c["iso_compliant"] else "✗",
                str(c["effective_length_m"]),
            ])
        fc_table = Table(fc_data, colWidths=[35*mm, 20*mm, 20*mm, 25*mm, 25*mm])
        fc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1565C0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))
        story.append(fc_table)

    # --- PAGE 3: Standards & Recommendations ---
    story.append(PageBreak())
    story.append(Paragraph("STANDARTLAR & ÖNERİLER", h2_style))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#1F4E79")))

    standards = [
        ("ASME B31.3", "Proses borulama dizaynı"),
        ("ASME B16.5", "Flanş basınç sınıfı seçimi"),
        ("IEC 60079-10-1", "Ex zone sınıflandırması"),
        ("IEC 61511", "SIL değerlendirme (fonksiyonel güvenlik)"),
        ("ISO 5168", "Belirsizlik bütçesi hesabı"),
        ("ISO 6976", "Gaz ısıl değer hesabı"),
    ]
    meter_standards = {"ultrasonic": "AGA 9 / ISO 17089", "orifice": "ISO 5167-2 / AGA 3",
                        "turbine": "AGA 7 / ISO 9951", "coriolis": "AGA 11 / ISO 10790",
                        "positive_displacement": "API MPMS Ch.4", "vortex": "ISO 17089-2"}
    if selected_meter.meter_key in meter_standards:
        standards.insert(0, (meter_standards[selected_meter.meter_key], "Metre tipi standardı"))
    if requirements.get("h2s"):
        standards.insert(3, ("ISO 15156 / NACE MR0175", "Sour servis malzeme seçimi"))

    std_data = [["Standart", "Açıklama"]]
    std_data.extend(standards)
    std_table = Table(std_data, colWidths=[55*mm, 85*mm])
    std_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#F0F4F8")]),
    ]))
    story.append(std_table)

    story.append(Spacer(1, 10*mm))
    story.append(Paragraph("Güçlü Yönler:", h3_style))
    for s in selected_meter.strengths:
        story.append(Paragraph(f"• {s}", body_style))

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("Dikkat Edilmesi Gerekenler:", h3_style))
    for w in selected_meter.weaknesses:
        story.append(Paragraph(f"• {w}", body_style))
    if not selected_meter.weaknesses:
        story.append(Paragraph("Belirgin zayıflık tespit edilmedi.", body_style))

    story.append(Spacer(1, 12*mm))
    story.append(HRFlowable(width="40%", thickness=0.5, color=HexColor("#CCCCCC")))
    story.append(Paragraph("Metering Station Designer v0.3.0 | Otomatik oluşturulmuştur", small_style))

    doc.build(story)
    buffer.seek(0)
    return buffer
