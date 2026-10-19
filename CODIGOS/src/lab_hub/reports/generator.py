import os
import io
import hashlib
from decimal import Decimal
from datetime import datetime, date
from zoneinfo import ZoneInfo
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
)

from lab_hub.config import get_settings

settings = get_settings()

COLOR_PRIMARY_HEX = "#3FA87E"
COLOR_DARK_HEX = "#14231D"


def generate_chart_image(monthly_series: list[dict]) -> bytes:
    """Generates a static bar chart using Matplotlib and returns PNG bytes."""
    fig, ax = plt.subplots(figsize=(6.5, 2.4), dpi=150)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#F9FBF9")

    labels = [x["label"] for x in monthly_series]
    values = [float(x["total_weight_kg"]) for x in monthly_series]

    bars = ax.bar(labels, values, color="#3FA87E", width=0.5, edgecolor="#256B50")
    ax.set_ylabel("Masa (kg)", fontsize=8, color="#333333")
    ax.tick_params(axis="both", which="major", labelsize=7.5)
    ax.grid(axis="y", linestyle="--", alpha=0.5, color="#D0D0D0")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            f"{height:.2f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=7,
            fontweight="bold",
            color="#14231D"
        )

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def build_monthly_pdf(
    snapshot: dict,
    output_path: str,
    period: str,
    revision: int = 1
) -> tuple[str, str]:
    """
    Builds a complete monthly report PDF from an immutable snapshot dictionary.
    Returns (output_path, sha256_hash).
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor(COLOR_DARK_HEX),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#555555"),
        spaceAfter=15,
    )
    section_style = ParagraphStyle(
        "ReportSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor(COLOR_PRIMARY_HEX),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#222222"),
    )
    note_style = ParagraphStyle(
        "ReportNote",
        parent=styles["Italic"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#666666"),
        spaceBefore=10,
    )

    elements = []

    # Title & Subtitle
    elements.append(Paragraph("QR Lab Hub — Informe Mensual de Residuos", title_style))
    gen_time = datetime.now(settings.timezone).strftime("%Y-%m-%d %H:%M:%S %Z")
    elements.append(
        Paragraph(
            f"<b>Periodo:</b> {period} &bull; <b>Revisión:</b> {revision} &bull; <b>Generado:</b> {gen_time}",
            subtitle_style,
        )
    )

    # Key Metrics Table
    tot_rec = snapshot.get("total_records", 0)
    tot_kg = snapshot.get("total_weight_kg", "0.000")
    tot_g = snapshot.get("total_weight_g", "0.000")
    top_cat = snapshot.get("top_category_by_mass", "N/A")

    summary_data = [
        ["Total Registros", "Masa Total (kg)", "Masa Total (g)", "Mayor Categoría"],
        [str(tot_rec), f"{tot_kg} kg", f"{tot_g} g", Paragraph(escape(top_cat), body_style)]
    ]
    summary_table = Table(summary_data, colWidths=[120, 120, 120, 170])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(COLOR_DARK_HEX)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F0F6F2")),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.black),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
        ("TOPPADDING", (0, 1), (-1, 1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 12))

    if tot_rec == 0:
        elements.append(Paragraph("<b>Nota:</b> Durante este periodo calendario no se registraron residuos en el laboratorio.", body_style))
        elements.append(Spacer(1, 12))

    # Waste Types Breakdown
    by_type = snapshot.get("by_waste_type", [])
    if by_type:
        elements.append(Paragraph("Desglose por Tipo de Residuo", section_style))
        t_data = [["Tipo de Residuo", "Cantidad de Registros", "Masa Total (g)", "Masa Total (kg)"]]
        for item in by_type:
            t_data.append([Paragraph(escape(item["name"]), body_style), str(item["count"]), f"{item['total_weight_g']} g", f"{item['total_weight_kg']} kg"])
        t_table = Table(t_data, colWidths=[200, 110, 110, 110], repeatRows=1)
        t_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAEAEA")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_table)
        elements.append(Spacer(1, 10))

    # Causes Breakdown
    by_cause = snapshot.get("by_cause", [])
    if by_cause:
        elements.append(Paragraph("Desglose por Causa de Descarte", section_style))
        c_data = [["Causa", "Cantidad de Registros", "Masa Total (g)", "Masa Total (kg)"]]
        for item in by_cause:
            c_data.append([Paragraph(escape(item["name"]), body_style), str(item["count"]), f"{item['total_weight_g']} g", f"{item['total_weight_kg']} kg"])
        c_table = Table(c_data, colWidths=[200, 110, 110, 110], repeatRows=1)
        c_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAEAEA")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(c_table)
        elements.append(Spacer(1, 10))

    for key, heading in (("by_machine", "Desglose por Máquina"), ("by_material", "Desglose por Material")):
        rows = snapshot.get(key, [])
        if rows:
            elements.append(Paragraph(heading, section_style))
            data = [["Nombre", "Registros", "Masa (g)", "Masa (kg)"]]
            data += [[Paragraph(escape(row["name"]), body_style), str(row["count"]),
                      row["total_weight_g"], row["total_weight_kg"]] for row in rows]
            table = Table(data, colWidths=[200, 110, 110, 110], repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAEAEA")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            elements.append(table)

    # Monthly Context Chart
    monthly_series = snapshot.get("monthly_series", [])
    if monthly_series:
        elements.append(Paragraph("Evolución Cronológica de Masa (kg)", section_style))
        chart_bytes = generate_chart_image(monthly_series)
        chart_img_io = io.BytesIO(chart_bytes)
        img = Image(chart_img_io, width=480, height=180)
        elements.append(img)
        elements.append(Spacer(1, 10))

    # Methodological Note
    elements.append(
        Paragraph(
            "<b>Nota Metodológica:</b> Este informe consolida los registros obtenidos a través del sistema QR Lab Hub "
            "durante el periodo mensual especificado, normalizados bajo el huso horario oficial de Chile (America/Santiago). "
            "Las cifras representan mediciones operativas internas y no constituyen clasificaciones regulatorias ni tratamiento de residuos.",
            note_style
        )
    )

    doc.build(elements)

    with open(output_path, "rb") as f:
        content = f.read()
    sha256 = hashlib.sha256(content).hexdigest()

    return output_path, sha256

