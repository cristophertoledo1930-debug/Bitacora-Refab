"""One data callback owns each refresh; every renderer consumes its store."""
import math
from dash import ALL, Input, Output, State, ctx, html, no_update
from dash.exceptions import PreventUpdate

from lab_hub.db.session import SessionLocal
from .components import dashboard_content, status_chip
from .data import (FIELDS, PRESETS, export_csv, fmt_count, load_snapshot, parse_filters,
                   period_label, record_rows)


def refresh_data(n, preset, start, end, wt, material, machine, cause, source, previous):
    """Validate before opening a session; errors never replace valid data with zeros."""
    try:
        filters = parse_filters(preset, start, end, (wt, material, machine, cause, source))
    except ValueError as exc:
        return no_update, str(exc), str(exc), no_update, no_update
    try:
        with SessionLocal() as db:
            snapshot = load_snapshot(db, filters)
        table_class = "panel records-section" + (" empty" if not snapshot["agg"]["total_records"] else "")
        return snapshot, "", "", "dashboard-content", table_class
    except Exception:
        last = previous.get("updated") if previous else None
        message = "Base de datos no disponible. " + (f"Datos desactualizados desde {last}." if last else "Sin datos válidos disponibles.")
        return no_update, message, "", "dashboard-content stale", "panel records-section stale" + (
            " empty" if previous and not previous["agg"]["total_records"] else "")


def table_page(snapshot, page, sort_by, context=None, trigger=None):
    key = {"filters": snapshot["filters"], "sort_by": sort_by or []}
    pages = math.ceil(snapshot["agg"]["total_records"] / 25)
    if context != key:
        page = 0
    elif trigger == "page-prev":
        page = (page or 0) - 1
    elif trigger == "page-next":
        page = (page or 0) + 1
    return max(0, min((page or 0), max(0, pages - 1))), key


def render_records(snapshot, page, sort_by, context=None, trigger=None):
    if not snapshot:
        return (no_update,) * 8
    count = snapshot["agg"]["total_records"]
    pages = math.ceil(count / 25)
    page, context = table_page(snapshot, page, sort_by, context, trigger)
    if not count:
        return [], 0, [], "Registros (0)", "0 / 0", "", 0, context
    try:
        with SessionLocal() as db:
            rows = list(record_rows(db, snapshot["filters"], page or 0, sort_by))
        cards = [html.Article([html.P(row["recorded_at_local"], title="America/Santiago"),
            html.Div(row["weight"], className="record-weight"), html.P(row["waste_type"] + " · " + row["cause"]),
            html.P(row["material"] + " · " + row["machine"]), html.P(row["source"])], className="record-card") for row in rows]
        return rows, pages, cards, f"Registros ({fmt_count(count)})", f"{fmt_count(page + 1)} / {fmt_count(pages)}", "", page, context
    except Exception:
        return no_update, no_update, no_update, no_update, no_update, "No se pueden cargar registros. Se conservan los datos anteriores.", no_update, no_update


def register_callbacks(app, new_record_url):
    @app.callback(Output("period-store", "data"), Output("filter-start", "value"), Output("filter-end", "value"),
        *[Output("filter-" + key, "value") for key in FIELDS],
        *[Input("preset-" + key, "n_clicks") for key, _ in PRESETS],
        Input("clear-filters", "n_clicks"),
        Input({"type": "clear-filters", "index": ALL}, "n_clicks"), prevent_initial_call=True)
    def select_period(*clicks):
        trigger = ctx.triggered_id
        if trigger == "clear-filters" or isinstance(trigger, dict):
            # Inserting the empty-state button may trigger an ALL callback with zero clicks.
            if isinstance(trigger, dict) and not any(clicks[-1]):
                raise PreventUpdate
            return "month", None, None, *(["ALL"] * 5)
        preset = trigger.removeprefix("preset-")
        return preset, no_update, no_update, *([no_update] * 5)

    @app.callback(*[Output("preset-" + key, "aria-pressed") for key, _ in PRESETS],
                  Output("custom-dates", "hidden"), Input("period-store", "data"))
    def preset_state(preset):
        return *["true" if key == preset else "false" for key, _ in PRESETS], preset != "custom"

    app.callback(Output("agg-store", "data"), Output("error-banner", "children"), Output("date-error", "children"),
        Output("dashboard-content", "className"), Output("table-section", "className"),
        Input("interval-refresh", "n_intervals"), Input("period-store", "data"), Input("filter-start", "value"),
        Input("filter-end", "value"), *[Input("filter-" + key, "value") for key in FIELDS], State("agg-store", "data"))(refresh_data)

    @app.callback(Output("dashboard-content", "children"), Output("active-period", "children"),
        Output("last-update-text", "children"), Output("system-chips", "children"),
        Output("filters-summary", "children"), *[Output("filter-" + key, "options") for key in FIELDS],
        Input("agg-store", "data"), Input("filter-metric", "value"))
    def render(snapshot, metric):
        if not snapshot:
            raise PreventUpdate
        count = sum(bool(snapshot["filters"].get(k)) for k in FIELDS)
        return (dashboard_content(snapshot, metric, new_record_url), period_label(snapshot["filters"]),
            "Actualizado " + snapshot["updated"] + " (cada 15 s)",
            [status_chip(snapshot["sheets"]), status_chip(snapshot["mail"], "/reports")],
            f"Filtros ({count})", *[snapshot["options"][key] for key in FIELDS])

    @app.callback(Output("records-table", "data"), Output("records-table", "page_count"),
        Output("record-cards", "children"), Output("records-heading", "children"), Output("page-label", "children"),
        Output("table-error", "children"), Output("records-table", "page_current"), Output("table-context", "data"),
        Input("agg-store", "data"), Input("records-table", "page_current"), Input("records-table", "sort_by"),
        Input("page-prev", "n_clicks"), Input("page-next", "n_clicks"), State("table-context", "data"))
    def update_records(snapshot, page, sort_by, prev, next_, context):
        return render_records(snapshot, page, sort_by, context, ctx.triggered_id)

    @app.callback(Output("csv-download", "data"), Output("export-status", "children"), Input("export-csv", "n_clicks"),
        State("agg-store", "data"), State("records-table", "sort_by"), prevent_initial_call=True)
    def download(clicks, snapshot, sort_by):
        if not clicks or not snapshot:
            raise PreventUpdate
        try:
            with SessionLocal() as db:
                content = export_csv(db, snapshot["filters"], sort_by)
            return {"content": content, "filename": "residuos.csv", "type": "text/csv;charset=utf-8"}, ""
        except Exception:
            return no_update, "No se pudo exportar. Reintenta."
