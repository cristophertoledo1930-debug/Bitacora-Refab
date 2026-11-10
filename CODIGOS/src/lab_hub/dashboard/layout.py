"""Declarative dashboard structure; no database access at import time."""
from dash import dash_table, dcc, html

from .data import PRESETS

FILTERS = (("waste_type_id", "Tipo"), ("material_id", "Material"), ("machine_id", "Máquina"),
           ("cause_id", "Causa"), ("source", "Origen"))
COLUMNS = (("recorded_at_local", "Fecha/hora"), ("waste_type", "Tipo"), ("material", "Material"),
           ("machine", "Máquina"), ("cause", "Causa"), ("weight", "Peso"), ("source", "Origen"))


def preset_button(key, text):
    return html.Button(text, id="preset-" + key, n_clicks=0,
                       **{"aria-pressed": "true" if key == "month" else "false"})


def build_layout(new_record_url):
    return html.Main([
        dcc.Interval(id="interval-refresh", interval=15000, n_intervals=0),
        dcc.Store(id="agg-store"), dcc.Store(id="period-store", data="month"),
        dcc.Store(id="table-context"),
        dcc.Download(id="csv-download"),
        html.Header([
            html.Div([html.Div("RE-FAB · LAB881", className="brand"), html.H1("Residuos del laboratorio")]),
            html.Nav([html.A("+ Nuevo registro", href=new_record_url, className="button"),
                      html.A("Informes", href="/reports", className="button secondary")], **{"aria-label": "Acciones"}),
            html.Div("Este mes", id="active-period", className="active-period"),
            html.Div(id="system-chips", className="system-chips"),
            html.Div("Cargando…", id="last-update-text", className="last-update", role="status")
        ], className="dashboard-header"),
        html.Div(id="error-banner", role="alert", className="error-banner", **{"aria-live": "assertive"}),
        html.Section([
            html.Div([*[preset_button(k, text) for k, text in PRESETS[:3]],
                html.Details([html.Summary("Más"), html.Div([preset_button(k, text) for k, text in PRESETS[3:]], className="more-presets-content")],
                             className="more-presets", id="more-presets", open=True)], className="presets", **{"aria-label": "Periodo"}),
            html.Div([
                html.Div([html.Label("Desde", htmlFor="filter-start"), dcc.Input(id="filter-start", type="date")]),
                html.Div([html.Label("Hasta", htmlFor="filter-end"), dcc.Input(id="filter-end", type="date")]),
                html.Div(id="date-error", role="status", className="field-error")
            ], id="custom-dates", className="custom-dates", hidden=True),
            html.Details([html.Summary("Filtros", id="filters-summary"), html.Div([
                *[html.Div([html.Label(label, htmlFor="filter-" + field, id="label-filter-" + field),
                    dcc.Dropdown(id="filter-" + field, options=[{"label": "Todos", "value": "ALL"}],
                                 value="ALL", clearable=False, searchable=True, placeholder="Todos")], className="filter") for field, label in FILTERS],
                html.Div([html.Label("Métrica", htmlFor="filter-metric", id="label-filter-metric"),
                    dcc.Dropdown(id="filter-metric", options=[{"label": "kg", "value": "kg"},
                        {"label": "Registros", "value": "count"}], value="kg", clearable=False, searchable=False)], className="filter"),
                html.Button("Limpiar", id="clear-filters", n_clicks=0)
            ], className="filter-row")], id="filters-panel", open=True)
        ], className="filter-toolbar"),
        html.Div(id="dashboard-content", className="dashboard-content", children=html.P("Cargando…")),
        html.Section([
            html.Div([html.H2("Registros", id="records-heading"), html.Button("Exportar CSV", id="export-csv", n_clicks=0)], className="table-header"),
            html.Div(id="table-error", role="status", className="field-error"),
            html.Div(id="export-status", role="status", className="field-error"),
            dash_table.DataTable(id="records-table", columns=[{"id": key, "name": name} for key, name in COLUMNS], data=[],
                page_action="custom", page_current=0, page_size=25, page_count=0,
                sort_action="custom", sort_mode="single", sort_by=[{"column_id": "recorded_at_local", "direction": "desc"}]),
            html.Div(id="record-cards", className="record-cards"),
            html.Div([html.Button("Anterior", id="page-prev", n_clicks=0), html.Span(id="page-label"),
                      html.Button("Siguiente", id="page-next", n_clicks=0)], className="mobile-pagination")
        ], id="table-section", className="panel records-section"),
        html.Footer("America/Santiago · Actualización cada 15 s", className="dashboard-footer")
    ], className="dashboard-shell")
