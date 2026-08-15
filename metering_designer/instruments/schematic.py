"""
Single-line flow schematic (SFG) of the metering run.

Renders a matplotlib figure showing pipe run, upstream disturbance,
flow conditioner, meter symbol, instrument tap locations (PT/TT/dP),
straight-pipe length requirements in D and metres, and optional
manufacturing-tolerance callouts for informative purposes.
"""

import io

from metering_designer.instruments.layout import compute_instrument_layout

# Meter drawing styles per normalized key
METER_DRAWING = {
    "orifice": "plate",
    "venturi": "venturi",
    "v_cone": "cone",
    "ultrasonic": "usm",
    "turbine": "turbine",
    "coriolis": "coriolis",
    "vortex": "vortex",
    "positive_displacement": "pd",
}

_INSTRUMENT_COLOR = {
    "pressure": "#1f77b4",
    "temperature": "#d62728",
    "differential_pressure": "#2ca02c",
}


def _text(lang: str, tr: str, en: str) -> str:
    return tr if lang != "en" else en


def render_schematic(
    meter_key: str,
    nps: int = 8,
    upstream_config: str = "single_bend_90",
    conditioner_key: str | None = None,
    straight_pipe: dict | None = None,
    tolerances: dict | None = None,
    lang: str = "tr",
    upstream_config_label: str | None = None,
) -> "figure":
    """Build a matplotlib Figure of the metering run.

    Returns a Figure; the caller renders it (st.pyplot) or serializes it.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle, Polygon, FancyArrow, FancyBboxPatch

    fig, ax = plt.subplots(figsize=(13, 5))
    fig.patch.set_facecolor("white")

    layout = compute_instrument_layout(meter_key, nps, conditioner_key=conditioner_key)

    od_m = layout["od_m"]
    up_D = float((straight_pipe or {}).get("upstream_required_diameters", 18) or 18)
    down_D = float((straight_pipe or {}).get("downstream_required_diameters", 5) or 5)

    x0 = -(up_D + 2)      # start of drawn pipe
    x1 = (down_D + 2)     # end of drawn pipe
    y0, y1 = 0.05, 0.95   # axes fraction; use fixed y placement

    # Pipeline (single line)
    ax.plot([x0, x1], [0, 0], color="#333", linewidth=3.0, solid_capstyle="butt")

    # Flow arrow (at far left of the run, pointing right)
    ax.add_patch(FancyArrow(
        x0 + 0.3, 0.32, 1.6, 0, width=0.06, length_includes_head=True,
        head_width=0.25, head_length=0.5, color="#333",
    ))

    # Upstream disturbance symbol
    dist_label = upstream_config_label or upstream_config.replace("_", " ").title()
    disturbance_D = -(up_D + 1)
    ax.plot([disturbance_D, disturbance_D], [-0.22, -0.06], color="#795548", linewidth=2.5)
    ax.text(disturbance_D, 0.0, "",
            ha="center", va="center", fontsize=9)
    _draw_disturbance(ax, disturbance_D, upstream_config)

    # Conditioner (if any) upstream of meter
    if conditioner_key:
        cond_x = -2.0
        ax.text(cond_x, -0.28, condenser_label(conditioner_key, lang),
                ha="center", va="top", fontsize=8, color="#00897b")
        rect = FancyBboxPatch((cond_x - 0.35, -0.11), 0.7, 0.22,
                              boxstyle="round,pad=0.02", linewidth=1.5,
                              edgecolor="#00897b", facecolor="#e0f2f1")
        ax.add_patch(rect)
        ax.text(cond_x, 0.0, "FC", ha="center", va="center", fontsize=8, color="#004d40")

    # Meter symbol
    _draw_meter(ax, meter_key, od_m)

    # Straight-pipe dimension lines & labels
    _draw_dimension(ax, x0, -up_D, -0.20,
                    f"Up (D): {up_D:.0f}D = {up_D * od_m:.2f} m", "#1a5276")
    _draw_dimension(ax, x0, x1, -0.20,
                    f"Down (D): {down_D:.0f}D = {down_D * od_m:.2f} m", "#7d3c98")

    # Instruments
    for inst in layout["instruments"]:
        x = inst["position_D"]
        _draw_instrument(ax, x, inst["type"], inst["tag_list"][0] if inst["tag_list"] else "",
                         lang)

    # Tolerance callouts (manufacturing info only)
    if tolerances:
        _draw_tolerances(ax, tolerances, lang)

    title = _text(lang, "Akış Hattı Şematik (SFG)",
                  "Metering Run Schematic (SFG)")
    ax.set_title(title, fontsize=13, fontweight="bold", color="#1a5276", pad=18)
    ax.set_xlim(x0 - 0.5, x1 + 0.5)
    ax.set_ylim(-0.85, 1.0)
    ax.axis("off")

    ax.text(len(ax.get_xlim()) * 0.5, -0.75, _text(lang,
            f"NPS {nps}  •  D = {od_m * 1000:.1f} mm  •  metre: {meter_key}",
            f"NPS {nps}  •  D = {od_m * 1000:.1f} mm  •  meter: {meter_key}"),
            ha="center", va="center", fontsize=9, color="#666")

    fig.tight_layout()
    return fig


def condenser_label(key: str, lang: str) -> str:
    labels = {
        "zanker": ("Zanker", "Zanker"),
        "cpa_50e": ("CPA 50E", "CPA 50E"),
        "tube_bundle_19": ("19-Tüp Demeti", "19-Tube Bundle"),
        "perforated": ("Perfore Plaka", "Perforated Plate"),
        "gallagher": ("Gallagher", "Gallagher"),
    }
    return labels.get(key, (key.title(), key.title()))[0 if lang != "en" else 1]


def render_schematic_png_bytes(
    meter_key: str,
    nps: int = 8,
    upstream_config: str = "single_bend_90",
    conditioner_key: str | None = None,
    straight_pipe: dict | None = None,
    tolerances: dict | None = None,
    lang: str = "tr",
    dpi: int = 110,
) -> bytes:
    """Serialize the schematic to PNG bytes (used for reports/UI)."""
    fig = render_schematic(meter_key, nps, upstream_config, conditioner_key,
                           straight_pipe, tolerances, lang)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    import matplotlib.pyplot as plt

    plt.close(fig)
    return buf.getvalue()


# ── internal drawing helpers ────────────────────────────────────────────
def _draw_disturbance(ax, x, upstream_config):
    """Small glyphs for common upstream disturbances."""
    cfg = upstream_config or ""
    if "bend" in cfg:
        from matplotlib.patches import Arc, FancyArrow
        ax.add_patch(Arc((x + 0.3, -0.12), 0.55, 0.35, theta1=90, theta2=360,
                          color="#795548", linewidth=2.0))
    elif "valve" in cfg:
        ax.text(x, 0.14, "V", ha="center", va="center", fontsize=10, color="#795548")
        ax.plot([x, x], [-0.09, 0.09], color="#795548", linewidth=2.0)
    elif "reducer" in cfg:
        ax.plot([x - 0.25, x + 0.25], [0.10, -0.10], color="#795548", linewidth=2.0)
        ax.plot([x - 0.25, x + 0.25], [-0.10, 0.10], color="#795548", linewidth=2.0)
    else:
        ax.text(x, 0.0, "○", ha="center", va="center", fontsize=12, color="#795548")


def _draw_meter(ax, meter_key, od_m):
    from matplotlib.patches import Circle, Rectangle, Polygon

    key = meter_key.lower()
    drawing = "plate"
    if "v_cone" in key or "vcone" in key:
        drawing = "cone"
    elif "venturi" in key:
        drawing = "venturi"
    elif "ultrasonic" in key:
        drawing = "usm"
    elif "turbine" in key:
        drawing = "turbine"
    elif "coriolis" in key:
        drawing = "coriolis"
    elif "vortex" in key:
        drawing = "vortex"
    elif "positive_displacement" in key or "pd_meter" in key or "pd" == key:
        drawing = "pd"

    label = {
        "plate": "Orifice", "venturi": "Venturi", "cone": "V-Cone",
        "usm": "USM", "turbine": "Turbine", "coriolis": "Coriolis",
        "vortex": "Vortex", "pd": "PD Meter",
    }[drawing]

    if drawing == "plate":
        ax.plot([0, 0], [-0.12, 0.12], color="#1a5276", linewidth=4.0)
    elif drawing == "venturi":
        ax.add_patch(Polygon([[-0.45, 0.0], [0.0, 0.08], [0.0, -0.08]], closed=True,
                              edgecolor="#1a5276", facecolor="#cfe2f3", linewidth=1.5))
        ax.plot([0.0, 0.45], [0.08, 0.0], color="#1a5276", linewidth=2.0)
        ax.plot([0.0, 0.45], [-0.08, 0.0], color="#1a5276", linewidth=2.0)
    elif drawing == "cone":
        ax.add_patch(Polygon([[-0.15, 0.22], [-0.20, -0.22], [0.55, -0.16], [0.55, 0.16]],
                              closed=True, edgecolor="#1a5276", facecolor="#cfe2f3",
                              linewidth=1.5))
    elif drawing == "usm":
        ax.add_patch(Rectangle((-0.45, -0.18), 0.9, 0.36, linewidth=1.5,
                                edgecolor="#1a5276", facecolor="#cfe2f3"))
        ax.plot([-0.3, 0.3], [0.0, 0.0], color="#1a5276", linewidth=1.5)
    elif drawing == "turbine":
        axes_circle = Circle((0.0, 0.0), 0.20, linewidth=1.5,
                             edgecolor="#1a5276", facecolor="#cfe2f3")
        ax.add_patch(axes_circle)
        ax.plot([-0.14, 0.14], [0.0, 0.0], color="#1a5276", linewidth=1.2)
        ax.plot([0.0, 0.0], [-0.14, 0.14], color="#1a5276", linewidth=1.2)
    elif drawing == "coriolis":
        ax.add_patch(Circle((-0.3, 0.0), 0.18, linewidth=1.5,
                            edgecolor="#1a5276", facecolor="#cfe2f3"))
        ax.add_patch(Circle((0.3, 0.0), 0.18, linewidth=1.5,
                            edgecolor="#1a5276", facecolor="#cfe2f3"))
    elif drawing == "vortex":
        ax.add_patch(Rectangle((-0.35, -0.16), 0.7, 0.32, linewidth=1.5,
                                edgecolor="#1a5276", facecolor="#cfe2f3"))
        ax.plot([0.0, 0.0], [-0.10, 0.10], color="#1a5276", linewidth=2.0)
    else:  # pd
        ax.add_patch(Rectangle((-0.40, -0.16), 0.8, 0.32, linewidth=1.5,
                                edgecolor="#1a5276", facecolor="#cfe2f3"))

    ax.text(0.0, 0.30, label, ha="center", va="bottom", fontsize=9,
            color="#1a5276", fontweight="bold")


def _draw_instrument(ax, x, itype, tag, lang):
    from matplotlib.patches import Circle

    color = _INSTRUMENT_COLOR.get(itype, "#333")
    cx = x
    symbol = {
        "pressure": "PT", "temperature": "TT", "differential_pressure": "dP",
    }.get(itype, "TX")

    # Tap line
    ax.plot([cx, cx], [0.0, 0.10], color=color, linewidth=1.2)

    if itype == "differential_pressure":
        # Two taps (high/low) with small connector
        ax.plot([cx - 0.18, cx + 0.18], [0.0, 0.0], color=color, linewidth=1.2)
        circ = Circle((cx - 0.18, 0.14), 0.10, linewidth=1.3, edgecolor=color,
                      facecolor="white")
        circ2 = Circle((cx + 0.18, 0.14), 0.10, linewidth=1.3, edgecolor=color,
                       facecolor="white")
        ax.add_patch(circ)
        ax.add_patch(circ2)
        ax.text(cx - 0.18, 0.14, "H", ha="center", va="center", fontsize=7, color=color)
        ax.text(cx + 0.18, 0.14, "L", ha="center", va="center", fontsize=7, color=color)
        tag_x = cx
    else:
        circ = Circle((cx, 0.14), 0.10, linewidth=1.3, edgecolor=color, facecolor="white")
        ax.add_patch(circ)
        ax.text(cx, 0.14, symbol, ha="center", va="center", fontsize=6.5, color=color,
                fontweight="bold")
        tag_x = cx

    if tag:
        ax.text(tag_x, 0.27, tag, ha="center", va="bottom", fontsize=8, color=color)
    # Position label in diameters below the line
    ax.text(cx, -0.30, f"{x:+g}D", ha="center", va="top", fontsize=7, color="#888")


def _draw_dimension(ax, xa, xb, y, text, color):
    txt = text
    ax.annotate("", xy=(xb, y), xytext=(xa, y),
                arrowprops=dict(arrowstyle="<->", color="#555", lw=1.0))
    ax.plot([xa, xa], [y, y + 0.02], color="#555", lw=1.0)
    ax.plot([xb, xb], [y, y + 0.02], color="#555", lw=1.0)
    ax.text((xa + xb) / 2, y - 0.06, txt, ha="center", va="top", fontsize=8, color=color)


def _draw_tolerances(ax, tolerances, lang):
    """Informative manufacturing tolerance callouts near the meter."""
    # Render as a stacked text block (info box) under the schematic legend
    lines = [_text(lang, "Üretim Toleransları (bilgilendirme):",
                   "Manufacturing tolerances (informational):")]
    for key, val in list(tolerances.items())[:5]:
        lines.append(f"  • {key}: {val}")

    box_x = -0.05
    ax.text(box_x, 0.55, "\n".join(lines), ha="left", va="center",
            fontsize=8, color="#7f5f00",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#fff9db",
                      edgecolor="#f0d264", alpha=0.95))