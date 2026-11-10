import hashlib
import textwrap
import json
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
import dash
from dash import dcc, html, dash_table, Input, Output
import plotly.graph_objects as go
from lab_hub.config import get_settings
from lab_hub.db.session import SessionLocal
from lab_hub.services.aggregations import get_aggregations
from lab_hub.db.models import WasteType, Material, Machine, Cause, WasteRecord

settings = get_settings()

COLOR_BG = "#0B1411"
COLOR_PANEL = "#14231D"
COLOR_PRIMARY = "#64D6A0"
COLOR_TEXT = "#F4F8F5"
COLOR_TEXT_MUTED = "#BCCEC3"
COLOR_BORDER = "#2B4237"
COLOR_SECONDARY = "#3FA87E"

app = dash.Dash(
    __name__,
    requests_pathname_prefix="/dashboard/",
    routes_pathname_prefix="/",
    title="QR Lab Hub — Dashboard",
    suppress_callback_exceptions=True
)

app.index_string = app.index_string.replace('<html>', '<html lang="es">').replace(
    '{%favicon%}', '<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">')
server = app.server


@app.callback(Output("monthly-mail-status", "children"), Input("interval-refresh", "n_intervals"))
def monthly_mail_status(_):
    from lab_hub.services.report_status import monthly_delivery_status
    try:
        with SessionLocal() as db:
            status = monthly_delivery_status(db)
        lines = []
        if not status["email_enabled"]:
            lines.append("Correo externo deshabilitado (EMAIL_ENABLED=false).")
        if not status["auto_send_from"]:
            lines.append("Envío automático sin activar: falta REPORT_AUTO_SEND_FROM.")
        lines.append(f"Próxima comprobación: {status['next_scheduled_at']}.")
        lines.extend(f"{p['period']}: {p['status']}." for p in status["periods"])
        return " ".join(lines)
    except Exception:
        return "Estado del correo mensual no disponible. Consulte Informes."


@app.callback(Output("sheets-status", "children"), Input("interval-refresh", "n_intervals"))
def sheets_status(_):
    if not settings.GOOGLE_SHEETS_ID:
        return ""
    try:
        status = json.loads(Path("storage/sheets-status.json").read_text(encoding="utf-8"))
        checked = datetime.fromisoformat(status["checked_at"])
        label = checked.astimezone(settings.timezone).strftime("%d/%m %H:%M:%S")
        age = datetime.now(checked.tzinfo) - checked
        if status.get("error") or age.total_seconds() > 150:
            return f"Sheets: sincronización pendiente. Última consulta: {label}. Datos guardados conservados."
        rejected = status.get("rejected", [])
        if rejected:
            return f"Sheets: {len(rejected)} fila(s) pendiente(s) de corrección. Consulta: {label}."
        return f"Sheets sincronizado: {label}."
    except (OSError, ValueError, KeyError, TypeError):
        return "Sheets: esperando primera sincronización."


def category_colors(rows):
    palette = ["#64D6A0", "#8EC9FF", "#FFC982", "#C4AFF5", "#FFAAAA", "#9ED8D5"]
    return [palette[int(hashlib.sha256(r["code"].encode()).hexdigest(), 16) % len(palette)] for r in rows]


def axis_label(value):
    return "<br>".join(textwrap.wrap(value, 22))



def get_catalog_options():
    db = SessionLocal()
    try:
        wt = [{"label": "Todos los tipos", "value": "ALL"}] + [
            {"label": x.name, "value": str(x.id)}
            for x in db.query(WasteType).filter(WasteType.is_active.is_(True)).order_by(WasteType.name).all()
        ]
        mat = [{"label": "Todos los materiales", "value": "ALL"}] + [
            {"label": x.name, "value": str(x.id)}
            for x in db.query(Material).filter(Material.is_active.is_(True)).order_by(Material.name).all()
        ]
        mach = [{"label": "Todas las máquinas", "value": "ALL"}] + [
            {"label": x.name, "value": str(x.id)}
            for x in db.query(Machine).filter(Machine.is_active.is_(True)).order_by(Machine.name).all()
        ]
        cause = [{"label": "Todas las causas", "value": "ALL"}] + [
            {"label": x.name, "value": str(x.id)}
            for x in db.query(Cause).filter(Cause.is_active.is_(True)).order_by(Cause.name).all()
        ]
        return wt, mat, mach, cause
    finally:
        db.close()


wt_opts, mat_opts, mach_opts, cause_opts = get_catalog_options()

app.layout = html.Div(
    className="lab-layout",
    style={
        "backgroundColor": COLOR_BG,
        "color": COLOR_TEXT,
        "minHeight": "100vh",
        "fontFamily": "Segoe UI, -apple-system, sans-serif",
        "display": "flex",
        "flexDirection": "row",
    },
    children=[
        # Auto-refresh interval (15s)
        dcc.Interval(id="interval-refresh", interval=15000, n_intervals=0),

        # Sidebar (Lateral izquierdo)
        html.Div(
            id="sidebar",
            style={
                "width": "280px",
                "minWidth": "280px",
                "backgroundColor": COLOR_PANEL,
                "borderRight": f"1px solid {COLOR_BORDER}",
                "padding": "1.5rem",
                "display": "flex",
                "flexDirection": "column",
                "gap": "1.2rem",
            },
            children=[
                html.Div([
                    html.H2("Re-Fab · Lab881", style={"color": COLOR_PRIMARY, "margin": "0 0 0.25rem 0", "fontSize": "1.4rem"}),
                    html.P("Panel de Residuos", style={"color": COLOR_TEXT_MUTED, "margin": 0, "fontSize": "0.85rem"}),
                ]),
                html.Hr(style={"borderColor": COLOR_BORDER, "margin": "0.5rem 0"}),
                html.P(id="sheets-status", role="status", style={"fontSize": "0.85rem"}),
                html.P(id="monthly-mail-status", role="status", style={"fontSize": "0.85rem"}),
                # Navigation
                html.Div([
                    html.Label("NAVEGACIÓN", style={"color": COLOR_TEXT_MUTED, "fontSize": "0.75rem", "fontWeight": "bold"}),
                    html.Div([
                        html.A("Nuevo registro", href="/r/token-general", style={"color": COLOR_PRIMARY, "display": "block", "padding": "0.5rem 0"}),
                        html.A("📊 Resumen", href="#summary-section", style={"color": COLOR_TEXT, "display": "block", "padding": "0.4rem 0", "textDecoration": "none"}),
                        html.A("📋 Registros", href="#table-section", style={"color": COLOR_TEXT, "display": "block", "padding": "0.4rem 0", "textDecoration": "none"}),
                        html.A("📄 Informes PDF", href="/reports", target="_blank", style={"color": COLOR_TEXT, "display": "block", "padding": "0.4rem 0", "textDecoration": "none"}),
                    ], style={"marginTop": "0.5rem"}),
                ]),
                html.Hr(style={"borderColor": COLOR_BORDER, "margin": "0.5rem 0"}),
                # Filters
                html.Div([
                    html.Label("FILTROS", style={"color": COLOR_TEXT_MUTED, "fontSize": "0.75rem", "fontWeight": "bold", "marginBottom": "0.5rem", "display": "block"}),

                    html.Label("Métrica en gráficos:", style={"color": COLOR_TEXT_MUTED, "fontSize": "0.8rem"}),
                    dcc.RadioItems(
                        id="filter-metric",
                        options=[
                            {"label": " Masa (kg)", "value": "kg"},
                            {"label": " Registros", "value": "count"},
                        ],
                        value="kg",
                        inline=True,
                        style={"color": COLOR_TEXT, "fontSize": "0.85rem", "marginBottom": "0.8rem"}
                    ),

                    html.Label("Desde (Chile)", htmlFor="filter-start", style={"fontSize": "0.8rem"}),
                    dcc.Input(id="filter-start", type="date", style={"width": "100%"}),
                    html.Label("Hasta (Chile)", htmlFor="filter-end"),
                    dcc.Input(id="filter-end", type="date", style={"width": "100%", "marginBottom": "1rem"}),
                    html.Label("Tipo de Residuo:", htmlFor="filter-waste-type", style={"color": COLOR_TEXT_MUTED, "fontSize": "0.8rem"}),
                    dcc.Dropdown(
                        id="filter-waste-type",
                        options=wt_opts,
                        value="ALL",
                        clearable=False,
                        style={"color": "#111", "fontSize": "0.85rem", "marginBottom": "0.8rem"}
                    ),

                    html.Label("Material:", htmlFor="filter-material", style={"color": COLOR_TEXT_MUTED, "fontSize": "0.8rem"}),
                    dcc.Dropdown(
                        id="filter-material",
                        options=mat_opts,
                        value="ALL",
                        clearable=False,
                        style={"color": "#111", "fontSize": "0.85rem", "marginBottom": "0.8rem"}
                    ),

                    html.Label("Máquina:", style={"color": COLOR_TEXT_MUTED, "fontSize": "0.8rem"}),
                    dcc.Dropdown(
                        id="filter-machine",
                        options=mach_opts,
                        value="ALL",
                        clearable=False,
                        style={"color": "#111", "fontSize": "0.85rem", "marginBottom": "0.8rem"}
                    ),

                    html.Label("Origen:", htmlFor="filter-source"),
                    dcc.Dropdown(id="filter-source", value="ALL", clearable=False,
                        options=[{"label": "Todos los orígenes", "value": "ALL"},
                                 {"label": "Manual", "value": "manual"},
                                 {"label": "Google Forms", "value": "google_forms"},
                                 {"label": "ESP32", "value": "esp32"}],
                        style={"color": "#111", "marginBottom": "0.8rem"}),
                    html.Label("Causa:", htmlFor="filter-cause", style={"color": COLOR_TEXT_MUTED, "fontSize": "0.8rem"}),
                    dcc.Dropdown(
                        id="filter-cause",
                        options=cause_opts,
                        value="ALL",
                        clearable=False,
                        style={"color": "#111", "fontSize": "0.85rem", "marginBottom": "0.8rem"}
                    ),
                ]),
                html.Div(
                    id="last-update-text", children="Cargando datos?", role="status",
                    style={"color": COLOR_TEXT_MUTED, "fontSize": "0.75rem", "marginTop": "auto"}
                )
            ]
        ),

        # Main Content Area
        html.Div(
            className="lab-main",
            style={
                "flex": 1,
                "padding": "1.5rem 2rem",
                "overflowY": "auto",
                "display": "flex",
                "flexDirection": "column",
                "gap": "1.5rem",
            },
            children=[
                html.Header([html.P("Re-Fab · Lab881", className="brand"),
                    html.H1("Residuos del laboratorio"),
                    html.P("Masa, causas y registros. Filtra el periodo que quieres revisar.")]),
                # Top Summary Cards (4 indicators)
                html.Div(
                    id="summary-section",
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(auto-fit, minmax(200px, 1fr))",
                        "gap": "1rem",
                    },
                    children=[
                        html.Div(
                            style={"backgroundColor": COLOR_PANEL, "padding": "1.2rem", "borderRadius": "8px", "border": f"1px solid {COLOR_BORDER}"},
                            children=[
                                html.P("TOTAL REGISTROS", style={"color": COLOR_TEXT_MUTED, "fontSize": "0.75rem", "margin": 0, "fontWeight": "bold"}),
                                html.H3(id="card-total-records", children="Cargando…", style={"color": COLOR_TEXT, "fontSize": "1.8rem", "margin": "0.4rem 0 0 0"}),
                            ]
                        ),
                        html.Div(
                            style={"backgroundColor": COLOR_PANEL, "padding": "1.2rem", "borderRadius": "8px", "border": f"1px solid {COLOR_BORDER}"},
                            children=[
                                html.P("MASA TOTAL ACUMULADA", style={"color": COLOR_TEXT_MUTED, "fontSize": "0.75rem", "margin": 0, "fontWeight": "bold"}),
                                html.H3(id="card-total-mass", children="Cargando…", style={"color": COLOR_PRIMARY, "fontSize": "1.8rem", "margin": "0.4rem 0 0 0"}),
                            ]
                        ),
                        html.Div(
                            style={"backgroundColor": COLOR_PANEL, "padding": "1.2rem", "borderRadius": "8px", "border": f"1px solid {COLOR_BORDER}"},
                            children=[
                                html.P("REGISTROS ESTE MES", style={"color": COLOR_TEXT_MUTED, "fontSize": "0.75rem", "margin": 0, "fontWeight": "bold"}),
                                html.H3(id="card-month-records", children="Cargando…", style={"color": COLOR_TEXT, "fontSize": "1.8rem", "margin": "0.4rem 0 0 0"}),
                            ]
                        ),
                        html.Div(
                            style={"backgroundColor": COLOR_PANEL, "padding": "1.2rem", "borderRadius": "8px", "border": f"1px solid {COLOR_BORDER}"},
                            children=[
                                html.P("MAYOR CATEGORÍA EN MASA", style={"color": COLOR_TEXT_MUTED, "fontSize": "0.75rem", "margin": 0, "fontWeight": "bold"}),
                                html.H3(id="card-top-category", children="N/A", style={"color": COLOR_TEXT, "fontSize": "1.2rem", "margin": "0.4rem 0 0 0", "overflow": "hidden", "textOverflow": "ellipsis", "whiteSpace": "nowrap"}),
                            ]
                        ),
                    ]
                ),

                html.Div(id="forms-reception", role="status", className="reception-status"),
                html.P(id="empty-state", role="status", className="empty-state"),
                dcc.Loading(dcc.Graph(id="chart-by-source", config={"displayModeBar": False},
                    style={"height": "250px"}), color=COLOR_PRIMARY),
                # Middle Charts: Waste Type & Causes
                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(min(100%, 300px), 1fr))", "gap": "1rem"},
                    children=[
                        html.Div(
                            style={"backgroundColor": COLOR_PANEL, "padding": "1rem", "borderRadius": "8px", "border": f"1px solid {COLOR_BORDER}"},
                            children=[
                                html.H4("Desglose por Tipo de Residuo", style={"margin": "0 0 0.5rem 0", "color": COLOR_TEXT, "fontSize": "1rem"}),
                                dcc.Graph(id="chart-by-type", config={"displayModeBar": False}, style={"height": "260px"})
                            ]
                        ),
                        html.Div(
                            style={"backgroundColor": COLOR_PANEL, "padding": "1rem", "borderRadius": "8px", "border": f"1px solid {COLOR_BORDER}"},
                            children=[
                                html.H4("Desglose por Causa de Descarte", style={"margin": "0 0 0.5rem 0", "color": COLOR_TEXT, "fontSize": "1rem"}),
                                dcc.Graph(id="chart-by-cause", config={"displayModeBar": False}, style={"height": "260px"})
                            ]
                        ),
                    ]
                ),

                html.Div([
                    dcc.Graph(id="chart-by-machine", config={"displayModeBar": False}),
                    dcc.Graph(id="chart-by-material", config={"displayModeBar": False}),
                ], className="extra-charts"),

                # Bottom Chart: Monthly Chronological Series (Zero filled)
                html.Div(
                    style={"backgroundColor": COLOR_PANEL, "padding": "1rem", "borderRadius": "8px", "border": f"1px solid {COLOR_BORDER}"},
                    children=[
                        html.H4("Evolución Mensual Cronológica (Meses con cero incluidos)", style={"margin": "0 0 0.5rem 0", "color": COLOR_TEXT, "fontSize": "1rem"}),
                        dcc.Graph(id="chart-monthly", config={"displayModeBar": False}, style={"height": "280px"})
                    ]
                ),

                # Filtered Data Table
                html.Div(
                    id="table-section",
                    style={"backgroundColor": COLOR_PANEL, "padding": "1.2rem", "borderRadius": "8px", "border": f"1px solid {COLOR_BORDER}"},
                    children=[
                        html.H4("Registros Individuales", style={"margin": "0 0 1rem 0", "color": COLOR_TEXT, "fontSize": "1rem"}),
                        dash_table.DataTable(
                            id="records-table",
                            columns=[
                                {"name": "Fecha / Hora (Chile)", "id": "recorded_at_local"},
                                {"name": "Tipo", "id": "waste_type"},
                                {"name": "Material", "id": "material"},
                                {"name": "Máquina", "id": "machine"},
                                {"name": "Causa", "id": "cause"},
                                {"name": "Peso (g)", "id": "weight_g"},
                                {"name": "Peso (kg)", "id": "weight_kg"},
                                {"name": "Origen", "id": "source"},
                            ],
                            data=[],
                            style_cell={"fontFamily": "Segoe UI, sans-serif", "fontSize": "14px",
                                        "padding": "10px", "minWidth": "100px", "maxWidth": "220px",
                                        "whiteSpace": "normal", "height": "auto"},
                            page_size=10,
                            style_header={
                                "backgroundColor": "#1B2D26",
                                "color": COLOR_PRIMARY,
                                "fontWeight": "bold",
                                "border": f"1px solid {COLOR_BORDER}",
                                "textAlign": "left"
                            },
                            style_data={
                                "backgroundColor": COLOR_PANEL,
                                "color": COLOR_TEXT,
                                "border": f"1px solid {COLOR_BORDER}",
                                "fontSize": "0.85rem",
                                "textAlign": "left"
                            },
                            style_table={"overflowX": "auto"},
                        )
                    ]
                ),
            ]
        )
    ]
)


@app.callback(
    [
        Output("card-total-records", "children"),
        Output("card-total-mass", "children"),
        Output("card-month-records", "children"),
        Output("card-top-category", "children"),
        Output("chart-by-type", "figure"),
        Output("chart-by-cause", "figure"),
        Output("chart-monthly", "figure"),
        Output("records-table", "data"),
        Output("last-update-text", "children"),
    ],
    [
        Input("interval-refresh", "n_intervals"),
        Input("filter-metric", "value"),
        Input("filter-waste-type", "value"),
        Input("filter-material", "value"),
        Input("filter-machine", "value"),
        Input("filter-cause", "value"),
        Input("filter-start", "value"),
        Input("filter-end", "value"),
        Input("filter-source", "value"),
    ]
)
def update_dashboard(n_intervals, metric, wt_val, mat_val, mach_val, cause_val, start=None, end=None, source="ALL"):
    db = SessionLocal()
    try:
        start_d = date.fromisoformat(start) if start else None
        end_d = date.fromisoformat(end) if end else None
        if start_d and end_d and start_d > end_d:
            raise ValueError("La fecha inicial debe preceder a la final.")
        wt_id = None if wt_val == "ALL" else wt_val
        mat_id = None if mat_val == "ALL" else mat_val
        mach_id = None if mach_val == "ALL" else mach_val
        cause_id = None if cause_val == "ALL" else cause_val

        agg = get_aggregations(
            db,
            start_date=start_d, end_date=end_d,
            waste_type_id=wt_id,
            material_id=mat_id,
            machine_id=mach_id,
            cause_id=cause_id, source=None if source == "ALL" else source
        )

        total_records_txt = f"{agg['total_records']:,}"
        total_mass_txt = f"{agg['total_weight_kg']} kg"
        month_records_txt = f"{agg['current_month_records']:,}"
        top_cat_txt = agg["top_category_by_mass"]

        # Chart by Waste Type
        types_labels = [x["name"] for x in agg["by_waste_type"]]
        types_values = [float(x["total_weight_kg"] if metric == "kg" else x["count"]) for x in agg["by_waste_type"]]
        fig_type = go.Figure(
            data=[
                go.Bar(
                    x=types_labels,
                    y=types_values,
                    marker_color=category_colors(agg["by_waste_type"]),
                    text=types_values,
                    textposition="auto"
                )
            ]
        )
        fig_type.update_layout(
            margin=dict(l=20, r=20, t=10, b=30),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=COLOR_TEXT),
            yaxis=dict(title="kg" if metric == "kg" else "Registros", gridcolor=COLOR_BORDER),
            xaxis=dict(gridcolor=COLOR_BORDER)
        )

        # Chart by Cause
        causes_labels = [axis_label(x["name"]) for x in agg["by_cause"]]
        causes_values = [float(x["total_weight_kg"] if metric == "kg" else x["count"]) for x in agg["by_cause"]]
        fig_cause = go.Figure(
            data=[
                go.Bar(
                    y=causes_labels,
                    x=causes_values,
                    orientation="h",
                    marker_color=category_colors(agg["by_cause"]),
                    text=causes_values,
                    textposition="auto"
                )
            ]
        )
        fig_cause.update_layout(
            margin=dict(l=10, r=20, t=10, b=40),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=COLOR_TEXT),
            yaxis=dict(automargin=True),
            xaxis=dict(title="kg" if metric == "kg" else "Registros", gridcolor=COLOR_BORDER)
        )

        # Monthly Series Chart
        m_labels = [x["label"] for x in agg["monthly_series"]]
        m_values = [float(x["total_weight_kg"] if metric == "kg" else x["count"]) for x in agg["monthly_series"]]
        fig_monthly = go.Figure(
            data=[
                go.Bar(
                    x=m_labels,
                    y=m_values,
                    marker_color=COLOR_PRIMARY,
                    text=m_values,
                    textposition="auto"
                )
            ]
        )
        fig_monthly.update_layout(
            margin=dict(l=20, r=20, t=10, b=30),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=COLOR_TEXT),
            yaxis=dict(title="kg" if metric == "kg" else "Registros", gridcolor=COLOR_BORDER),
            xaxis=dict(gridcolor=COLOR_BORDER)
        )

        if agg["total_records"] == 0:
            for fig in (fig_type, fig_cause, fig_monthly):
                fig.add_annotation(text="Sin registros para estos filtros", xref="paper", yref="paper",
                                   x=0.5, y=0.5, showarrow=False)

        # Table records
        q_records = db.query(WasteRecord)
        if source != "ALL":
            q_records = q_records.filter(WasteRecord.source == source)
        if wt_id:
            q_records = q_records.filter(WasteRecord.waste_type_id == wt_id)
        if mat_id:
            q_records = q_records.filter(WasteRecord.material_id == mat_id)
        if mach_id:
            q_records = q_records.filter(WasteRecord.machine_id == mach_id)
        if cause_id:
            q_records = q_records.filter(WasteRecord.cause_id == cause_id)

        from datetime import time, timedelta
        if start_d:
            q_records = q_records.filter(WasteRecord.recorded_at >= datetime.combine(start_d, time.min, tzinfo=settings.timezone))
        if end_d:
            q_records = q_records.filter(WasteRecord.recorded_at < datetime.combine(end_d + timedelta(days=1), time.min, tzinfo=settings.timezone))
        rows = q_records.order_by(WasteRecord.recorded_at.desc()).all()
        table_data = []
        for r in rows:
            loc_time = r.recorded_at.astimezone(settings.timezone).strftime("%Y-%m-%d %H:%M:%S")
            table_data.append({
                "recorded_at_local": loc_time,
                "waste_type": r.waste_type.name if r.waste_type else "",
                "material": r.material.name if r.material else "",
                "machine": r.machine.name if r.machine else "",
                "cause": r.cause.name if r.cause else "",
                "weight_g": str(r.weight_g),
                "weight_kg": str((r.weight_g / Decimal("1000")).quantize(Decimal("0.001"))),
                "source": r.source
            })

        now_str = datetime.now(settings.timezone).strftime("%Y-%m-%d %H:%M:%S")
        last_update = f"Última actualización: {now_str}"

        return (
            total_records_txt,
            total_mass_txt,
            month_records_txt,
            top_cat_txt,
            fig_type,
            fig_cause,
            fig_monthly,
            table_data,
            last_update
        )
    except Exception as exc:
        message = str(exc) if isinstance(exc, ValueError) else "Base de datos no disponible; se conservan los últimos valores."
        return (*([dash.no_update] * 8), f"Error: {message}")
    finally:
        db.close()



@app.callback(
    Output("chart-by-machine", "figure"), Output("chart-by-material", "figure"),
    Input("interval-refresh", "n_intervals"), Input("filter-metric", "value"),
    Input("filter-waste-type", "value"), Input("filter-material", "value"),
    Input("filter-machine", "value"), Input("filter-cause", "value"),
    Input("filter-start", "value"), Input("filter-end", "value"),
    Input("filter-source", "value"),
)
def update_dimension_charts(n, metric, wt, mat, machine, cause, start, end, source="ALL"):
    try:
        with SessionLocal() as db:
            agg = get_aggregations(db, start_date=date.fromisoformat(start) if start else None,
                end_date=date.fromisoformat(end) if end else None,
                source=None if source == "ALL" else source,
                **{key: None if value == "ALL" else value for key, value in
                   zip(("waste_type_id", "material_id", "machine_id", "cause_id"), (wt, mat, machine, cause))})
        figures = []
        for key, title in (("by_machine", "Máquinas"), ("by_material", "Materiales")):
            rows = agg[key]
            fig = go.Figure(go.Bar(y=[axis_label(r["name"]) for r in rows], orientation="h",
                x=[float(r["total_weight_kg"] if metric == "kg" else r["count"]) for r in rows],
                marker_color=category_colors(rows)))
            fig.update_layout(title=title, paper_bgcolor=COLOR_PANEL, plot_bgcolor=COLOR_PANEL,
                font_color=COLOR_TEXT, xaxis_title="kg" if metric == "kg" else "Registros",
                yaxis=dict(automargin=True), margin=dict(l=10,r=15,t=50,b=50))
            if agg["total_records"] == 0:
                fig.add_annotation(text="Sin registros para estos filtros", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            figures.append(fig)
        return figures
    except Exception:
        return dash.no_update, dash.no_update


@app.callback(
    Output("forms-reception", "children"), Output("chart-by-source", "figure"),
    Input("interval-refresh", "n_intervals"), Input("filter-source", "value"),
    Input("filter-start", "value"), Input("filter-end", "value"),
    Input("filter-waste-type", "value"), Input("filter-material", "value"),
    Input("filter-machine", "value"), Input("filter-cause", "value"),
    Input("filter-metric", "value"),
)
def update_sources(n, source, start, end, wt, mat, machine, cause, metric):
    try:
        with SessionLocal() as db:
            agg = get_aggregations(db, source=None if source == "ALL" else source,
                start_date=date.fromisoformat(start) if start else None,
                end_date=date.fromisoformat(end) if end else None,
                **{key: None if value == "ALL" else value for key, value in
                   zip(("waste_type_id", "material_id", "machine_id", "cause_id"), (wt, mat, machine, cause))})
        stamp = agg["last_google_forms_received_at"]
        message = ("Última respuesta recibida de Google Forms: " + datetime.fromisoformat(stamp).strftime("%d/%m/%Y %H:%M:%S")
                   + " · America/Santiago") if stamp else "Google Forms: todavía no se reciben respuestas."
        rows = agg["by_source"]
        labels = {"manual": "Manual", "google_forms": "Google Forms", "esp32": "ESP32"}
        fig = go.Figure(go.Bar(x=[labels.get(r["source"], r["source"]) for r in rows],
            y=[float(r["total_weight_kg"]) if metric == "kg" else r["count"] for r in rows],
            marker_color=[{"manual": COLOR_PRIMARY, "google_forms": "#8EC9FF", "esp32": "#C4AFF5"}.get(r["source"], COLOR_PRIMARY) for r in rows]))
        fig.update_layout(title="Origen de los registros", yaxis_title="kg" if metric == "kg" else "Registros",
            paper_bgcolor=COLOR_PANEL, plot_bgcolor=COLOR_PANEL, font_color=COLOR_TEXT,
            margin=dict(l=50, r=20, t=50, b=40))
        if not rows:
            fig.add_annotation(text="Sin registros para estos filtros", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return message, fig
    except Exception:
        return "Error al consultar recepción de Forms. Se conservan los últimos valores.", dash.no_update


# Collapse navigation on small screens; native details retains keyboard behavior.
sidebar = app.layout.children[1]
sidebar.children = [html.Details([html.Summary("Navegación y filtros · Re-Fab"), *sidebar.children],
                                id="navigation-panel", open=True)]
summary = app.layout.children[2].children[1]
summary.children.extend([
    html.Div([html.P("MASA ESTE MES", className="help"), html.H3("Cargando…", id="card-month-mass")], className="context-kpi"),
    html.Div([html.P("PRINCIPAL CAUSA POR MASA", className="help"), html.H3("Cargando…", id="card-top-cause")], className="context-kpi"),
])


@app.callback(
    Output("card-month-mass", "children"), Output("card-top-cause", "children"),
    Output("empty-state", "children"),
    Input("interval-refresh", "n_intervals"), Input("filter-source", "value"),
    Input("filter-start", "value"), Input("filter-end", "value"),
    Input("filter-waste-type", "value"), Input("filter-material", "value"),
    Input("filter-machine", "value"), Input("filter-cause", "value"),
)
def update_context_kpis(n, source, start, end, wt, mat, machine, cause):
    try:
        with SessionLocal() as db:
            agg = get_aggregations(db, source=None if source == "ALL" else source,
                start_date=date.fromisoformat(start) if start else None,
                end_date=date.fromisoformat(end) if end else None,
                **{key: None if value == "ALL" else value for key, value in
                   zip(("waste_type_id", "material_id", "machine_id", "cause_id"), (wt, mat, machine, cause))})
        message = "Sin registros para estos filtros. Amplía el periodo o registra un residuo." if not agg["total_records"] else ""
        return agg["current_month_weight_kg"] + " kg", agg["top_cause_by_mass"], message
    except Exception:
        return dash.no_update, dash.no_update, "No se pudieron cargar los datos. Reintenta; se conservan los últimos valores."
