"""Pure display components. Project tokens override the skill's default style."""
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from html import escape
from pathlib import Path
import re

from dash import dcc, html
import plotly.graph_objects as go

from .data import (fmt_count, fmt_delta, fmt_mass, fmt_percent, fmt_source, number,
                   period_label, settings)


@lru_cache(maxsize=1)
def tokens():
    """Plotly requires resolved colors; CSS remains the single token source."""
    root = Path(__file__).resolve().parent
    css = (root.parent / "static/theme.css").read_text(encoding="utf-8")
    css += (root / "assets/dashboard.css").read_text(encoding="utf-8")
    return dict(re.findall(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{6})", css))


def figure_base(figure, title, height=320, unit="kg"):
    colors = tokens()
    figure.update_layout(title={"text": title, "font": {"size": 16}}, height=height,
        paper_bgcolor=colors["panel"], plot_bgcolor=colors["panel"],
        font={"color": colors["text"], "family": "Segoe UI, system-ui"}, separators=",.",
        margin={"l": 20, "r": 80, "t": 52, "b": 48}, showlegend=False, barcornerradius=4,
        xaxis={"gridcolor": colors["border"], "zeroline": False, "automargin": True},
        yaxis={"gridcolor": colors["border"], "zeroline": False, "automargin": True},
        hoverlabel={"bgcolor": colors["input"], "font_color": colors["text"]})
    return figure


def display_value(value, metric):
    return fmt_mass(value) if metric == "kg" else fmt_count(value) + " reg."


def ranking_rows(rows, metric):
    key = "total_weight_g" if metric == "kg" else "count"
    positive = sorted((r for r in rows if number(r[key]) > 0),
                      key=lambda r: (-number(r[key]), r["name"]))
    if len(positive) <= 8:
        return positive
    others = positive[8:]
    return [*positive[:8], {"name": f"Otros ({len(others)})", "count": sum(r["count"] for r in others),
                            "total_weight_g": str(sum(number(r["total_weight_g"]) for r in others))}]


def ranking_chart(rows, title, metric="kg"):
    key = "total_weight_g" if metric == "kg" else "count"
    ranked = ranking_rows(rows, metric)
    total = sum(number(r[key]) for r in rows)
    values = [number(r[key]) for r in ranked]
    texts = [f"{display_value(v, metric)} · {fmt_percent(v * 100 / total if total else 0)}" for v in values]
    names = [r["name"] for r in ranked]
    figure = go.Figure(go.Bar(x=[float(v / 1000 if metric == "kg" else v) for v in values],
        y=[n if len(n) <= 28 else n[:27] + "…" for n in names], orientation="h",
        marker_color=tokens()["primary"], text=texts, textposition="outside", cliponaxis=False,
        customdata=[f"{escape(n)}<br>{text}" for n, text in zip(names, texts)], hovertemplate="%{customdata}<extra></extra>"))
    # Plot area is 32px per row + 40px; title and axis margins are additional.
    figure_base(figure, title, 32 * len(ranked) + 140)
    figure.update_yaxes(autorange="reversed", tickfont_size=11)
    figure.update_xaxes(title="kg" if metric == "kg" else "Registros", rangemode="tozero", tickformat=",.0f" if metric != "kg" else ",.2f")
    return figure


def monthly_chart(rows, metric="kg", mobile=False):
    rows = rows[-6:] if mobile else rows[-24:]
    current = datetime.now(settings.timezone).strftime("%Y-%m")
    colors = tokens()
    figure = go.Figure(go.Bar(x=[r["label"] + ("<br>en curso" if r["period"] == current else "") for r in rows],
        y=[float(number(r["total_weight_g"]) / 1000) if metric == "kg" else r["count"] for r in rows],
        marker={"color": colors["primary"], "opacity": [0.45 if r["period"] == current else 1 for r in rows]},
        customdata=[f"{r['label']}: {fmt_mass(r['total_weight_g'])} ({fmt_count(r['count'])} reg.)" for r in rows],
        hovertemplate="%{customdata}<extra></extra>"))
    figure_base(figure, "Evolución mensual", 320)
    figure.update_yaxes(title="kg" if metric == "kg" else "Registros", rangemode="tozero", tickformat=",.2f" if metric == "kg" else ",.0f")
    return figure


def graph(figure, graph_id=None, class_name=""):
    if graph_id in ("chart-by-cause", "chart-by-type", "chart-by-machine", "chart-by-material"):
        class_name += " ranking-" + str(len(figure.data[0].x))
    if graph_id == "chart-by-source":
        class_name += " source-chart"
    # The wrapper owns a definite CSS height. Dash's responsive graph fills it.
    chart = dcc.Graph(figure=figure, responsive=True,
        config={"displayModeBar": False, "locale": "es", "responsive": True},
        **({"id": graph_id} if graph_id else {}))
    return html.Div(chart, className="chart " + class_name)


def accessible_table(rows, metric):
    key = "total_weight_g" if metric == "kg" else "count"
    total = sum(number(r[key]) for r in rows)
    return html.Details([html.Summary("Ver datos del gráfico"), html.Table([
        html.Thead(html.Tr([html.Th("Categoría", scope="col"), html.Th("Valor", scope="col"), html.Th("Porcentaje", scope="col")])),
        html.Tbody([html.Tr([html.Th(r["name"], scope="row"), html.Td(display_value(r[key], metric)),
            html.Td(fmt_percent(number(r[key]) * 100 / total if total else 0))]) for r in rows])])], className="chart-data")


def status_chip(state, link=None):
    content = [html.Span("●", **{"aria-hidden": "true"}), " " + state["text"]]
    return html.A(content, href=link, className="status-chip " + state["state"]) if link else html.Span(content, className="status-chip " + state["state"], role="status")


def kpi(label, value, delta="", title=None):
    return html.Div([html.Div(label, className="kpi-label"), html.Div(value, className="kpi-value"),
                     html.Div(delta, className="kpi-delta")], className="kpi", title=title)


def kpis(agg):
    count, grams = agg["total_records"], number(agg["total_weight_g"])
    prev = agg["previous_period"]
    baseline = prev.get("label", "periodo anterior")
    causes = [r for r in agg["by_cause"] if r["count"]]
    top = max((number(r["total_weight_g"]) for r in causes), default=Decimal(0))
    title = agg["top_cause_by_mass"]
    truncated = title if len(title) <= 28 else title[:27] + "…"
    return html.Div([
        kpi("MASA PERIODO", fmt_mass(grams), fmt_delta(grams, prev["total_weight_g"], baseline)),
        kpi("REGISTROS", fmt_count(count), fmt_delta(count, prev["total_records"], baseline)),
        kpi("PROMEDIO/REGISTRO", fmt_mass(grams / count if count else 0)),
        kpi("PRINCIPAL CAUSA", truncated + " · " + fmt_percent(top * 100 / grams if grams else 0), fmt_mass(top), title)
    ], className="kpi-grid")


def origin(agg, metric):
    key = "total_weight_g" if metric == "kg" else "count"
    rows = agg["by_source"]
    known = {r["source"]: number(r[key]) for r in rows if r["source"] in ("manual", "google_forms", "esp32")}
    other = sum(number(r[key]) for r in rows if r["source"] not in ("manual", "google_forms", "esp32"))
    parts = [(fmt_source(source), known.get(source, 0), f"series-{i}") for i, source in enumerate(("manual", "google_forms", "esp32"), 1)]
    if other:
        parts.append(("Otros", other, "muted"))
    total = sum(value for _, value, _ in parts)
    figure = go.Figure()
    legend = []
    for name, value, token in parts:
        if not value:
            continue
        share = value * 100 / total if total else 0
        text = f"{name} · {fmt_percent(share)} · {display_value(value, metric)}"
        figure.add_bar(x=[float(share)], y=["Origen"], orientation="h", name=name, width=18 / (140 - 45 - 10),
            marker={"color": tokens()[token], "line": {"width": 2, "color": tokens()["panel"]}},
            customdata=[text], hovertemplate="%{customdata}<extra></extra>")
        legend.append(html.Li(text, className="legend-" + token))
    figure_base(figure, "Origen", 140)
    figure.update_layout(barmode="stack", margin={"l": 10, "r": 10, "t": 45, "b": 10})
    figure.update_xaxes(visible=False, range=[0, 100])
    figure.update_yaxes(visible=False, range=[-.5, .5], fixedrange=True)
    return html.Section([graph(figure, "chart-by-source"), html.Ul(legend, className="origin-legend")], className="panel")


def empty_state(filters, new_record_url, options=None):
    active = []
    for field, label in (("waste_type_id", "Tipo"), ("material_id", "Material"), ("machine_id", "Máquina"),
                         ("cause_id", "Causa"), ("source", "Origen")):
        if filters.get(field):
            name = next((r["label"] for r in (options or {}).get(field, []) if r["value"] == filters[field]), "seleccionado")
            active.append(f"{label}: {name}")
    return html.Div([html.H2("No hay registros para " + period_label(filters)), html.P(" · ".join(active)),
        html.Button("Limpiar filtros", id={"type": "clear-filters", "index": "empty"}, n_clicks=0),
        html.A("+ Nuevo registro", href=new_record_url, className="button")], className="empty-state")


def dashboard_content(snapshot, metric, new_record_url):
    agg = snapshot["agg"]
    if not agg["total_records"]:
        return empty_state(snapshot["filters"], new_record_url, snapshot["options"])
    series = agg["monthly_series"]
    monthly = html.Section([graph(monthly_chart(series, metric), "chart-monthly", "desktop-monthly"),
        graph(monthly_chart(series, metric, mobile=True), "chart-monthly-mobile", "mobile-monthly"),
        html.P("Últimos 24 meses" if len(series) > 24 else "", className="series-note"),
        accessible_table([{**r, "name": r["label"]} for r in series[-24:]], metric)], className="panel")
    rankings = []
    for key, title, chart_id in (("by_cause", "Por causa", "chart-by-cause"),
        ("by_waste_type", "Por tipo de residuo", "chart-by-type"), ("by_machine", "Por máquina", "chart-by-machine"),
        ("by_material", "Por material", "chart-by-material")):
        rows = agg[key]
        rankings.append(html.Section([graph(ranking_chart(rows, title, metric), chart_id),
                                     accessible_table(ranking_rows(rows, metric), metric)], className="panel"))
    return [kpis(agg), monthly, html.Div(rankings, className="rankings"), origin(agg, metric)]
