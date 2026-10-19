import json
from datetime import datetime, date
from decimal import Decimal
import dash
from dash import dcc, html, dash_table, Input, Output, State
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

server = app.server


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
                    html.H2("QR Lab Hub", style={"color": COLOR_PRIMARY, "margin": "0 0 0.25rem 0", "fontSize": "1.4rem"}),
                    html.P("Panel de Residuos", style={"color": COLOR_TEXT_MUTED, "margin": 0, "fontSize": "0.85rem"}),
                ]),
                html.Hr(style={"borderColor": COLOR_BORDER, "margin": "0.5rem 0"}),
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

                    html.Label("Desde / hasta (Chile)", style={"fontSize": "0.8rem"}),
                    dcc.Input(id="filter-start", type="date", style={"width": "100%"}),
                    dcc.Input(id="filter-end", type="date", style={"width": "100%", "marginBottom": "1rem"}),
                    html.Label("Tipo de Residuo:", style={"color": COLOR_TEXT_MUTED, "fontSize": "0.8rem"}),
                    dcc.Dropdown(
                        id="filter-waste-type",
                        options=wt_opts,
                        value="ALL",
                        clearable=False,
                        style={"color": "#111", "fontSize": "0.85rem", "marginBottom": "0.8rem"}
                    ),

                    html.Label("Material:", style={"color": COLOR_TEXT_MUTED, "fontSize": "0.8rem"}),
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

                    html.Label("Causa:", style={"color": COLOR_TEXT_MUTED, "fontSize": "0.8rem"}),
                    dcc.Dropdown(
                        id="filter-cause",
                        options=cause_opts,
                        value="ALL",
                        clearable=False,
                        style={"color": "#111", "fontSize": "0.85rem", "marginBottom": "0.8rem"}
                    ),
                ]),
                html.Div(
                    id="last-update-text",
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
                                html.H3(id="card-total-records", children="0", style={"color": COLOR_TEXT, "fontSize": "1.8rem", "margin": "0.4rem 0 0 0"}),
                            ]
                        ),
                        html.Div(
                            style={"backgroundColor": COLOR_PANEL, "padding": "1.2rem", "borderRadius": "8px", "border": f"1px solid {COLOR_BORDER}"},
                            children=[
                                html.P("MASA TOTAL ACUMULADA", style={"color": COLOR_TEXT_MUTED, "fontSize": "0.75rem", "margin": 0, "fontWeight": "bold"}),
                                html.H3(id="card-total-mass", children="0.000 kg", style={"color": COLOR_PRIMARY, "fontSize": "1.8rem", "margin": "0.4rem 0 0 0"}),
                            ]
                        ),
                        html.Div(
                            style={"backgroundColor": COLOR_PANEL, "padding": "1.2rem", "borderRadius": "8px", "border": f"1px solid {COLOR_BORDER}"},
                            children=[
                                html.P("REGISTROS ESTE MES", style={"color": COLOR_TEXT_MUTED, "fontSize": "0.75rem", "margin": 0, "fontWeight": "bold"}),
                                html.H3(id="card-month-records", children="0", style={"color": COLOR_TEXT, "fontSize": "1.8rem", "margin": "0.4rem 0 0 0"}),
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
    ]
)
def update_dashboard(n_intervals, metric, wt_val, mat_val, mach_val, cause_val, start=None, end=None):
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
            cause_id=cause_id
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
                    marker_color=COLOR_PRIMARY,
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
        causes_labels = [x["name"] for x in agg["by_cause"]]
        causes_values = [float(x["total_weight_kg"] if metric == "kg" else x["count"]) for x in agg["by_cause"]]
        fig_cause = go.Figure(
            data=[
                go.Bar(
                    x=causes_labels,
                    y=causes_values,
                    marker_color=COLOR_SECONDARY,
                    text=causes_values,
                    textposition="auto"
                )
            ]
        )
        fig_cause.update_layout(
            margin=dict(l=20, r=20, t=10, b=30),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=COLOR_TEXT),
            yaxis=dict(title="kg" if metric == "kg" else "Registros", gridcolor=COLOR_BORDER),
            xaxis=dict(gridcolor=COLOR_BORDER)
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

        # Table records
        q_records = db.query(WasteRecord)
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
)
def update_dimension_charts(n, metric, wt, mat, machine, cause, start, end):
    try:
        with SessionLocal() as db:
            agg = get_aggregations(db, start_date=date.fromisoformat(start) if start else None,
                end_date=date.fromisoformat(end) if end else None,
                **{key: None if value == "ALL" else value for key, value in
                   zip(("waste_type_id", "material_id", "machine_id", "cause_id"), (wt, mat, machine, cause))})
        figures = []
        for key, title in (("by_machine", "Máquinas"), ("by_material", "Materiales")):
            rows = agg[key]
            fig = go.Figure(go.Bar(x=[r["name"] for r in rows],
                y=[float(r["total_weight_kg"] if metric == "kg" else r["count"]) for r in rows],
                marker_color=COLOR_PRIMARY))
            fig.update_layout(title=title, paper_bgcolor=COLOR_PANEL, plot_bgcolor=COLOR_PANEL,
                font_color=COLOR_TEXT, yaxis_title="kg" if metric == "kg" else "Registros", margin=dict(l=45,r=15,t=50,b=80))
            figures.append(fig)
        return figures
    except Exception:
        return dash.no_update, dash.no_update
