"""Validation, localized display and bounded database reads for the dashboard."""
import csv
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from io import StringIO
import json
import logging
from pathlib import Path
from uuid import UUID

from dateutil.relativedelta import relativedelta
from sqlalchemy import String, cast, func, literal, select, union_all

from lab_hub.config import get_settings
from lab_hub.db.models import Cause, Machine, Material, ReportDelivery, ReportRun, WasteRecord, WasteType
from lab_hub.services.aggregations import MONTHS, get_aggregations, period_filters, previous_period

settings = get_settings()
logger = logging.getLogger(__name__)
SOURCE_LABELS = {"manual": "Manual", "google_forms": "Google Forms", "esp32": "ESP32"}
FIELDS = ("waste_type_id", "material_id", "machine_id", "cause_id", "source")
PRESETS = (("month", "Este mes"), ("previous", "Mes anterior"), ("three", "3 meses"),
           ("year", "12 meses"), ("all", "Todo"), ("custom", "Personalizado"))


def number(value):
    if value is None:
        logger.warning("Dashboard: valor de masa nulo tratado como cero")
        return Decimal(0)
    return Decimal(str(value))


def fmt_number(value, decimals=0):
    value = number(value).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    return f"{value:,.{decimals}f}".translate(str.maketrans({",": ".", ".": ","}))


def fmt_mass(grams):
    grams = number(grams)
    kg = grams / 1000
    if abs(kg) < Decimal("0.01"):
        return fmt_number(grams, 0 if grams == grams.to_integral() else 1) + " g"
    return fmt_number(kg, 1 if abs(kg) >= 10 else 2) + " kg"


def fmt_count(value):
    return fmt_number(value)


def fmt_percent(value):
    value = number(value)
    return fmt_number(value, 1 if 0 < abs(value) < 1 else 0) + " %"


def fmt_source(value):
    return SOURCE_LABELS.get(value, (value or "otro").replace("_", " ").capitalize())


def fmt_date(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.astimezone(settings.timezone).strftime("%d-%m-%Y %H:%M")


def fmt_delta(current, previous, label):
    previous = number(previous)
    if not previous:
        return "— · Sin datos del periodo anterior"
    delta = (number(current) - previous) * 100 / previous
    return f"{'▲' if delta >= 0 else '▼'} {fmt_percent(abs(delta))} vs {label}"


def comparison_period(preset, start, end):
    """Preset comparisons follow calendar months; custom ranges use equal day counts."""
    if start is None:
        return None, None, "periodo anterior"
    shift = {"month": 1, "previous": 1, "three": 3, "year": 12}.get(preset)
    if shift:
        prev_start, prev_end = start - relativedelta(months=shift), end - relativedelta(months=shift)
        if preset == "previous":
            prev_end = start - timedelta(days=1)
        first, last = MONTHS[prev_start.month - 1], MONTHS[prev_end.month - 1]
        if (prev_start.year, prev_start.month) == (prev_end.year, prev_end.month):
            label = f"{first} {prev_start.year}"
        elif prev_start.year == prev_end.year:
            label = f"{first}–{last} {prev_end.year}"
        else:
            label = f"{first} {prev_start.year}–{last} {prev_end.year}"
    else:
        prev_start, prev_end = previous_period(start, end)
        label = f"{prev_start:%d-%m-%Y} – {prev_end:%d-%m-%Y}"
    return prev_start, prev_end, label


def parse_filters(preset="month", start=None, end=None, values=None, today=None):
    today = today or datetime.now(settings.timezone).date()
    if preset == "custom":
        try:
            start = date.fromisoformat(start) if start else None
            end = date.fromisoformat(end) if end else today
        except (TypeError, ValueError):
            raise ValueError("Introduce fechas válidas.") from None
        if start and start > end:
            raise ValueError("La fecha inicial debe preceder a la final.")
    elif preset == "all":
        start, end = None, today
    elif preset == "previous":
        end = today.replace(day=1) - timedelta(days=1)
        start = end.replace(day=1)
    else:
        months = {"month": 0, "three": 2, "year": 11}
        if preset not in months:
            raise ValueError("Selecciona un periodo válido.")
        start, end = today.replace(day=1) - relativedelta(months=months[preset]), today
    if start and start > today:
        raise ValueError("El rango es posterior a hoy.")
    end = min(end, today)
    result = {"start_date": start.isoformat() if start else None, "end_date": end.isoformat()}
    prev_start, prev_end, label = comparison_period(preset, start, end)
    result.update(preset=preset, comparison_start_date=prev_start.isoformat() if prev_start else None,
                  comparison_end_date=prev_end.isoformat() if prev_end else None, comparison_label=label)
    for key, value in zip(FIELDS, values or [None] * 5):
        if value in (None, "ALL", ""):
            result[key] = None
        elif key == "source":
            result[key] = str(value)
        else:
            try:
                result[key] = str(UUID(str(value)))
            except ValueError:
                raise ValueError("Selección de catálogo inválida.") from None
    return result


def query_args(filters):
    dates = ("start_date", "end_date", "comparison_start_date", "comparison_end_date")
    return {key: date.fromisoformat(value) if key in dates and value else value
            for key, value in filters.items() if key in (*dates, *FIELDS)}


def period_label(filters):
    start = date.fromisoformat(filters["start_date"]).strftime("%d-%m-%Y") if filters["start_date"] else "Inicio"
    end = date.fromisoformat(filters["end_date"]).strftime("%d-%m-%Y")
    count = sum(bool(filters.get(k)) for k in FIELDS)
    return f"{start} – {end}" + (f" · {count} filtros activos" if count else "")


def catalog_and_mail(db):
    branches = []
    for field, model in zip(FIELDS, (WasteType, Material, Machine, Cause)):
        branches.append(select(literal(field).label("kind"), cast(model.id, String).label("value"),
                               model.name.label("label")).where(model.is_active.is_(True)))
    branches.append(select(literal("source"), WasteRecord.source, WasteRecord.source).distinct())
    latest = select(func.max(ReportRun.period)).where(ReportRun.period.like("____-__")).scalar_subquery()
    branches.append(select(literal("mail"), ReportRun.period, ReportDelivery.status)
                    .outerjoin(ReportDelivery, ReportDelivery.report_run_id == ReportRun.id)
                    .where(ReportRun.period == latest))
    options = {key: [{"label": "Todos", "value": "ALL"}] for key in FIELDS}
    mail = []
    for row in db.execute(union_all(*branches)):
        if row.kind == "mail":
            mail.append((row.value, row.label or "pending"))
        else:
            options[row.kind].append({"value": row.value, "label": fmt_source(row.label) if row.kind == "source" else row.label})
    for values in options.values():
        values[1:] = sorted(values[1:], key=lambda r: r["label"])
    if not mail:
        return options, {"text": "Correo: sin datos", "state": "pending"}
    # Successful historical deliveries take precedence over pending revisions.
    states = {status for _, status in mail}
    state = next(s for s in ("uncertain", "sending", "failed", "sent", "pending") if s in states)
    label = {"sent": "enviado", "failed": "falló", "uncertain": "por confirmar", "sending": "en curso", "pending": "pendiente"}[state]
    return options, {"text": f"Informe {mail[0][0]}: {label}", "state": "ok" if state == "sent" else "error" if state == "failed" else "pending"}


def sheets_state(path=Path("storage/sheets-status.json")):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        checked = datetime.fromisoformat(data["checked_at"])
        if checked.tzinfo is None:
            raise ValueError("Fecha sin zona")
        age = (datetime.now(checked.tzinfo) - checked).total_seconds()
        if data.get("error"):
            return {"text": "Sheets: error", "state": "error"}
        if data.get("rejected") or age > 150:
            return {"text": "Sheets: pendiente", "state": "pending"}
        return {"text": "Sheets OK", "state": "ok"}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {"text": "Sheets: sin datos", "state": "pending"}


def load_snapshot(db, filters):
    # Both queries see one PostgreSQL snapshot; rendering never queries aggregations.
    if not db.in_transaction():
        db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
    agg = get_aggregations(db, **query_args(filters))
    agg["previous_period"]["label"] = filters.get("comparison_label", "periodo anterior")
    options, mail = catalog_and_mail(db)
    return {"agg": agg, "filters": filters, "options": options, "mail": mail,
            "sheets": sheets_state(), "updated": datetime.now(settings.timezone).strftime("%H:%M:%S")}


def records_query(filters):
    args = query_args(filters)
    query = select(WasteRecord.recorded_at, WasteType.name.label("waste_type"), Material.name.label("material"),
                   Machine.name.label("machine"), Cause.name.label("cause"), WasteRecord.weight_g, WasteRecord.source)
    query = query.join(WasteType).join(Material).join(Machine).join(Cause)
    for field in FIELDS:
        if args.get(field):
            query = query.where(getattr(WasteRecord, field) == args[field])
    return query.where(*period_filters(args["start_date"], args["end_date"]))


SORT_FIELDS = {"recorded_at_local": WasteRecord.recorded_at, "weight": WasteRecord.weight_g,
               "waste_type": WasteType.name, "material": Material.name, "machine": Machine.name,
               "cause": Cause.name, "source": WasteRecord.source}


def record_rows(db, filters, page=0, sort_by=None, export=False):
    query = records_query(filters)
    sort = (sort_by or [{"column_id": "recorded_at_local", "direction": "desc"}])[0]
    column = SORT_FIELDS.get(sort["column_id"], WasteRecord.recorded_at)
    query = query.order_by(column.asc() if sort["direction"] == "asc" else column.desc(), WasteRecord.id.desc())
    if not export:
        query = query.offset(max(0, page) * 25).limit(25)
    rows = db.execute(query.execution_options(yield_per=500) if export else query).mappings()
    for row in rows:
        yield {"recorded_at_local": fmt_date(row["recorded_at"]),
               **{key: row[key] for key in ("waste_type", "material", "machine", "cause")},
               "weight": fmt_mass(row["weight_g"]), "source": fmt_source(row["source"])}


def export_csv(db, filters, sort_by=None):
    output = StringIO(newline="")
    writer = csv.writer(output, delimiter=";")
    writer.writerow(("Fecha/hora", "Tipo", "Material", "Máquina", "Causa", "Peso", "Origen"))
    for row in record_rows(db, filters, sort_by=sort_by, export=True):
        # Spreadsheet formula injection protection for names controlled by catalogs.
        writer.writerow("'" + str(v) if str(v).startswith(("=", "+", "-", "@")) else v for v in row.values())
    return "\ufeff" + output.getvalue()
