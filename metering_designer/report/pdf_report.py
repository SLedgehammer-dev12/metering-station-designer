"""
WeasyPrint-based PDF report generator (Phase C4).
Generates professional PDF reports from metering calculation data.
"""

import datetime
from pathlib import Path


try:
    import weasyprint
    HAS_WEASYPRINT = True
except (ImportError, OSError):
    HAS_WEASYPRINT = False


# HTML template for metering station design report
REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<style>
  @page {{
    size: A4;
    margin: 2cm;
    @top-center {{
      content: "Metering Station Design Report";
      font-size: 9pt;
      color: #666;
    }}
    @bottom-center {{
      content: "Page " counter(page) " of " counter(pages);
      font-size: 8pt;
      color: #666;
    }}
  }}
  body {{ font-family: 'DejaVu Sans', sans-serif; font-size: 10pt; color: #333; }}
  h1 {{ font-size: 18pt; color: #1a5276; border-bottom: 2px solid #1a5276; padding-bottom: 4px; }}
  h2 {{ font-size: 14pt; color: #2e86c1; margin-top: 20px; }}
  h3 {{ font-size: 12pt; color: #2471a3; }}
  table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
  th, td {{ padding: 6px 8px; text-align: left; border: 1px solid #ddd; }}
  th {{ background-color: #1a5276; color: white; font-weight: bold; }}
  tr:nth-child(even) {{ background-color: #f2f2f2; }}
  .header {{ text-align: center; margin-bottom: 20px; }}
  .header h1 {{ border: none; margin-bottom: 5px; }}
  .header p {{ color: #666; font-size: 9pt; }}
  .summary {{ background: #eaf2f8; padding: 12px; border-radius: 4px; margin: 10px 0; }}
  .schematic {{ text-align: center; margin: 10px 0; }}
  .schematic img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 4px; }}
  .schematic p {{ font-size: 9pt; color: #666; }}
  .warning {{ color: #e74c3c; font-weight: bold; }}
  .ok {{ color: #27ae60; font-weight: bold; }}
  .footer {{ margin-top: 30px; font-size: 8pt; color: #999; text-align: center; }}
</style>
</head>
<body>
<div class="header">
  <h1>Metering Station Design Report</h1>
  <p>Generated: {generated_at}</p>
</div>

<h2>1. {sec_project}</h2>
<table>
  <tr><th>{prop}</th><th>{value}</th></tr>
  <tr><td>{report_date}</td><td>{generated_at}</td></tr>
  <tr><td>{meter_type}</td><td>{meter_type_val}</td></tr>
  <tr><td>{standard_ref}</td><td>{standard_ref_val}</td></tr>
</table>

<h2>2. {sec_conditions}</h2>
<table>
  <tr><th>{param}</th><th>{value}</th><th>{unit}</th></tr>
  <tr><td>{op_pressure}</td><td>{pressure}</td><td>bar(g)</td></tr>
  <tr><td>{op_temperature}</td><td>{temperature}</td><td>°C</td></tr>
  <tr><td>{flow_max}</td><td>{flow_max_val}</td><td>Sm³/h</td></tr>
  <tr><td>{flow_min}</td><td>{flow_min_val}</td><td>Sm³/h</td></tr>
  <tr><td>{density_op}</td><td>{density_op_val}</td><td>kg/m³</td></tr>
  <tr><td>{viscosity}</td><td>{viscosity_val}</td><td>Pa·s</td></tr>
  <tr><td>{compressibility}</td><td>{z_factor}</td><td>—</td></tr>
</table>

<h2>3. {sec_sizing}</h2>
<table>
  <tr><th>{param}</th><th>{value}</th><th>{unit}</th></tr>
  {sizing_rows}
</table>

<h2>4. {sec_uncertainty}</h2>
<table>
  <tr><th>{component}</th><th>{value_pct}</th><th>{type}</th><th>{distribution}</th></tr>
  {uncertainty_rows}
</table>
<div class="summary">
  <strong>{combined_std}:</strong> {combined_uncertainty} %<br>
  <strong>{expanded_k2}:</strong> {expanded_k2_val} %
</div>

<h2>5. {sec_gas_props}</h2>
<table>
  <tr><th>{property}</th><th>{value}</th><th>{unit}</th></tr>
  {gas_rows}
</table>

{schematic_section}

<h2>6. {sec_notes}</h2>
{notes_section}

<div class="footer">
  <p>Metering Station Designer — Automatically Generated Report</p>
  <p>This report is for reference purposes. Final design must be verified by a qualified engineer.</p>
</div>
</body>
</html>
"""


def generate_pdf_report(
    data: dict,
    output_path: str | Path = "metering_report.pdf",
    lang: str = "tr",
) -> str:
    """Generate a PDF report from metering calculation data.

    Args:
        data: Dictionary with keys:
            - meter_type: str
            - standard_ref: str (e.g., "ISO 5167-2:2003 / AGA 3")
            - pressure: float (bar)
            - temperature: float (°C)
            - flow_max: float (Sm³/h)
            - flow_min: float (Sm³/h)
            - density_op: float (kg/m³)
            - viscosity: float (Pa·s)
            - z_factor: float
            - sizing_results: dict (key-value pairs for the sizing table)
            - uncertainty_components: list[dict]
            - combined_uncertainty: float (%)
            - expanded_k2: float (%)
            - gas_properties: dict
            - notes: list[str]
            - schematic_png_b64: str (optional, base64 PNG)
            - instrument_table_rows: list[dict] (optional)
            - straight_pipe: dict (optional)
        output_path: Path to save the PDF file.
        lang: "tr" or "en" for report section labels.

    Returns:
        Absolute path to generated PDF file, or error message string.
    """
    if not HAS_WEASYPRINT:
        msg = "WeasyPrint is not installed. Install with: pip install weasyprint"
        return msg

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Sizing rows
    sizing_items = data.get("sizing_results", {})
    sizing_rows = ""
    for key, val in sizing_items.items():
        if isinstance(val, float):
            val_str = f"{val:.4f}"
        else:
            val_str = str(val)
        sizing_rows += f"<tr><td>{key}</td><td>{val_str}</td><td>—</td></tr>\n"

    # Uncertainty rows
    uncertainty_components = data.get("uncertainty_components", [])
    uncertainty_rows = ""
    for comp in uncertainty_components:
        uncertainty_rows += (
            f"<tr><td>{comp.get('name', '')}</td>"
            f"<td>{comp.get('value_pct', 0):.4f}</td>"
            f"<td>{comp.get('type', '')}</td>"
            f"<td>{comp.get('distribution', '')}</td></tr>\n"
        )

    # Gas properties rows
    gas_items = data.get("gas_properties", {})
    gas_rows = ""
    for key, val in gas_items.items():
        if isinstance(val, float):
            val_str = f"{val:.4f}"
        else:
            val_str = str(val)
        gas_rows += f"<tr><td>{key}</td><td>{val_str}</td><td>—</td></tr>\n"

    # Notes section
    notes = data.get("notes", [])
    if notes:
        notes_html = "<ul>\n"
        for note in notes:
            notes_html += f"  <li>{note}</li>\n"
        notes_html += "</ul>\n"
    else:
        notes_html = "<p>No warnings.</p>\n"

    # Schematic section (optional base64 PNG embedded in <img>)
    schematic_html = ""
    png_b64 = data.get("schematic_png_b64")
    if png_b64:
        title = "Layout Schematic (SFG)" if lang != "tr" else "Yerleşim Şeması (SFG)"
        schematic_html = (
            f'<h2 style="margin-top:24px;">{title}</h2>\n'
            f'<div class="schematic"><img alt="schematic" '
            f'src="data:image/png;base64,{png_b64}"/></div>\n'
        )
    inst_rows_html = ""
    inst_rows = data.get("instrument_table_rows", [])
    if inst_rows:
        t_tag = "Tag" if lang != "tr" else "Etiket"
        t_type = "Type" if lang != "tr" else "Tip"
        t_count = "Count" if lang != "tr" else "Adet"
        t_pos = "Pos (D)" if lang != "tr" else "Konum (D)"
        t_side = "Side" if lang != "tr" else "Taraf"
        t_std = "Standard" if lang != "tr" else "Standart"
        for r in inst_rows:
            inst_rows_html += (
                f"<tr><td>{r.get('tag_list','')}</td><td>{r.get('type','')}</td>"
                f"<td>{r.get('count','')}</td><td>{r.get('position_D','')}</td>"
                f"<td>{r.get('side','')}</td><td>{r.get('standard','')}</td></tr>\n"
            )
        schematic_html += (
            f'<h3 style="margin-top:10px;">{"Instruments" if lang != "tr" else "Enstrümanlar"}</h3>\n'
            f"<table><tr><th>{t_tag}</th><th>{t_type}</th><th>{t_count}</th>"
            f"<th>{t_pos}</th><th>{t_side}</th><th>{t_std}</th></tr>\n"
            f"{inst_rows_html}</table>\n"
        )

    # Section labels by language
    L = {
        "tr": {
            "sec_project": "Proje Bilgisi",
            "sec_conditions": "İşletme Koşulları",
            "sec_sizing": "Metre Boyutlandırma Sonuçları",
            "sec_uncertainty": "Belirsizlik Bütçesi",
            "sec_gas_props": "Gaz Özellikleri",
            "sec_notes": "Notlar & Uyarılar",
            "prop": "Özellik", "value": "Değer", "unit": "Birim",
            "report_date": "Rapor Tarihi", "meter_type": "Metre Tipi",
            "standard_ref": "Standart Referansı", "param": "Parametre",
            "op_pressure": "İşletme Basıncı", "op_temperature": "İşletme Sıcaklığı",
            "flow_max": "Debi (max)", "flow_min": "Debi (min)",
            "density_op": "Yoğunluk (işletme)", "viscosity": "Viskozite",
            "compressibility": "Sıkıştırılabilirlik (Z)",
            "component": "Bileşen", "value_pct": "Değer (±%)", "type": "Tip",
            "distribution": "Dağılım", "combined_std": "Birleşik Standart Belirsizlik:",
            "expanded_k2": "Genişletilmiş Belirsizlik (k=2, %95):", "property": "Özellik",
        },
        "en": {
            "sec_project": "Project Information",
            "sec_conditions": "Operating Conditions",
            "sec_sizing": "Meter Sizing Results",
            "sec_uncertainty": "Uncertainty Budget",
            "sec_gas_props": "Gas Properties",
            "sec_notes": "Notes & Warnings",
            "prop": "Property", "value": "Value", "unit": "Unit",
            "report_date": "Report Date", "meter_type": "Meter Type",
            "standard_ref": "Standard Reference", "param": "Parameter",
            "op_pressure": "Operating Pressure", "op_temperature": "Operating Temperature",
            "flow_max": "Flow Rate (max)", "flow_min": "Flow Rate (min)",
            "density_op": "Density (operating)", "viscosity": "Viscosity",
            "compressibility": "Compressibility (Z)",
            "component": "Component", "value_pct": "Value (±%)", "type": "Type",
            "distribution": "Distribution", "combined_std": "Combined Standard Uncertainty:",
            "expanded_k2": "Expanded Uncertainty (k=2, 95%):", "property": "Property",
        },
    }[lang if lang in ("tr", "en") else "tr"]

    fmt = dict({
        "generated_at": now,
        "meter_type_val": data.get("meter_type", "N/A"),
        "standard_ref_val": data.get("standard_ref", "N/A"),
        "pressure": data.get("pressure", "N/A"),
        "temperature": data.get("temperature", "N/A"),
        "flow_max_val": data.get("flow_max", "N/A"),
        "flow_min_val": data.get("flow_min", "N/A"),
        "density_op_val": data.get("density_op", "N/A"),
        "viscosity_val": data.get("viscosity", "N/A"),
        "z_factor": data.get("z_factor", "N/A"),
        "sizing_rows": sizing_rows,
        "uncertainty_rows": uncertainty_rows,
        "combined_uncertainty": data.get("combined_uncertainty", "N/A"),
        "expanded_k2_val": data.get("expanded_k2", "N/A"),
        "gas_rows": gas_rows,
        "notes_section": notes_html,
        "schematic_section": schematic_html,
    })
    fmt.update(L)

    html = REPORT_TEMPLATE.format(**fmt)

    try:
        doc = weasyprint.HTML(string=html)
        output_path = Path(output_path).resolve()
        doc.write_pdf(str(output_path))
        return str(output_path)
    except Exception as e:
        return f"PDF generation failed: {e}"


def generate_pdf_from_results(
    meter_type: str,
    sizing_result: dict,
    uncertainty_result: dict,
    gas_result: dict,
    output_path: str | Path = "metering_report.pdf",
    lang: str = "tr",
) -> str:
    """Convenience wrapper that builds the data dict from individual results."""
    data = {
        "meter_type": meter_type,
        "standard_ref": uncertainty_result.get("coverage_factor_comment", "ISO 5168"),
        "pressure": gas_result.get("P_bar", sizing_result.get("P_oper_bar", 0)),
        "temperature": gas_result.get("T_C", sizing_result.get("T_oper_C", 0)),
        "flow_max": sizing_result.get("q_max_Sm3h", 0),
        "flow_min": sizing_result.get("q_min_Sm3h", 0),
        "density_op": gas_result.get("rho_oper_kg_m3", sizing_result.get("rho_kg_m3", 0)),
        "viscosity": gas_result.get("mu_Pa_s", sizing_result.get("mu_Pa_s", 0)),
        "z_factor": gas_result.get("Z", sizing_result.get("Z", 1)),
        "sizing_results": sizing_result,
        "uncertainty_components": uncertainty_result.get("components", []),
        "combined_uncertainty": uncertainty_result.get("combined_standard_uncertainty_pct", 0),
        "expanded_k2": uncertainty_result.get("expanded_uncertainty_k2_95pct", 0),
        "gas_properties": {k: v for k, v in gas_result.items() if isinstance(v, (int, float, str))},
        "notes": _split_notes(sizing_result.get("notes")),
    }
    return generate_pdf_report(data, output_path, lang)


def _split_notes(notes) -> list[str]:
    """Normalize notes field which may be a string ('; ' joined) or a list."""
    if not notes:
        return []
    if isinstance(notes, (list, tuple)):
        return [str(n) for n in notes]
    return [n.strip() for n in str(notes).split("; ") if n.strip()]
