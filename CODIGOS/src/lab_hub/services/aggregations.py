"""Shared PostgreSQL summaries; one round trip independent of the month count."""
from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from sqlalchemy import String, and_, cast, func, literal, select, union_all

from lab_hub.config import get_settings
from lab_hub.db.models import Cause, Machine, Material, WasteRecord, WasteType

settings = get_settings()
MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def get_month_utc_range(year: int, month: int, tz: ZoneInfo):
    """Calendar boundaries converted individually, preserving Santiago DST."""
    start = datetime(year, month, 1, tzinfo=tz)
    return start.astimezone(ZoneInfo("UTC")), (start + relativedelta(months=1)).astimezone(ZoneInfo("UTC"))


def period_filters(start_date=None, end_date=None, tz=None):
    tz = tz or settings.timezone
    result = []
    if start_date:
        result.append(WasteRecord.recorded_at >= datetime.combine(start_date, time.min, tzinfo=tz))
    if end_date:
        result.append(WasteRecord.recorded_at < datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=tz))
    return result


def previous_period(start_date, end_date):
    """Inclusive period of the same number of local calendar days, immediately before."""
    days = (end_date - start_date).days + 1
    return start_date - timedelta(days=days), start_date - timedelta(days=1)


def get_aggregations(db, *, start_date=None, end_date=None, waste_type_id=None,
                     material_id=None, machine_id=None, cause_id=None, tz=None, source=None,
                     comparison_start_date=None, comparison_end_date=None):
    tz = tz or settings.timezone
    today = datetime.now(tz).date()
    if start_date and end_date and start_date > end_date:
        raise ValueError("Rango de fechas inválido.")
    dimensions = []
    for field, value in (("waste_type_id", waste_type_id), ("material_id", material_id),
                         ("machine_id", machine_id), ("cause_id", cause_id), ("source", source)):
        if value:
            dimensions.append(getattr(WasteRecord, field) == value)
    filters = [*dimensions, *period_filters(start_date, end_date, tz)]
    effective_end = min(end_date or today, today)
    prev_start, prev_end = previous_period(start_date, effective_end) if start_date and start_date <= effective_end else (None, None)
    if comparison_start_date is not None or comparison_end_date is not None:
        if comparison_start_date is None or comparison_end_date is None or comparison_start_date > comparison_end_date:
            raise ValueError("Periodo de comparación inválido.")
        prev_start, prev_end = comparison_start_date, comparison_end_date

    def summary(kind, conditions):
        return select(literal(kind).label("kind"), literal("").label("id"),
                      literal("").label("code"), literal("").label("name"),
                      func.count(WasteRecord.id).label("count"),
                      func.coalesce(func.sum(WasteRecord.weight_g), 0).label("weight_g")).where(*conditions)

    branches = [summary("total", filters),
                summary("current", [*filters, *period_filters(today.replace(day=1), today, tz)]),
                summary("previous", [*dimensions, *period_filters(prev_start, prev_end, tz)] if prev_start else [literal(False)])]
    for kind, model, field in (("by_waste_type", WasteType, "waste_type_id"),
                               ("by_cause", Cause, "cause_id"), ("by_machine", Machine, "machine_id"),
                               ("by_material", Material, "material_id")):
        branches.append(select(literal(kind), cast(model.id, String), model.code, model.name,
                               func.count(WasteRecord.id), func.coalesce(func.sum(WasteRecord.weight_g), 0))
                        .select_from(model).outerjoin(WasteRecord, and_(getattr(WasteRecord, field) == model.id, *filters))
                        .group_by(model.id, model.code, model.name))
    month = func.to_char(func.timezone(str(tz), WasteRecord.recorded_at), "YYYY-MM")
    branches.append(select(literal("monthly"), month, literal(""), literal(""),
                           func.count(WasteRecord.id), func.coalesce(func.sum(WasteRecord.weight_g), 0))
                    .where(*filters).group_by(month))
    branches.append(select(literal("by_source"), WasteRecord.source, literal(""), WasteRecord.source,
                           func.count(WasteRecord.id), func.coalesce(func.sum(WasteRecord.weight_g), 0))
                    .where(*filters).group_by(WasteRecord.source))
    # Metadata shares the round trip. No per-month queries or Python record scans.
    branches.append(select(literal("range"), literal(""),
                           cast(func.max(WasteRecord.recorded_at).filter(WasteRecord.source == "google_forms"), String),
                           cast(func.min(WasteRecord.recorded_at), String), literal(0), literal(0)))
    rows = db.execute(union_all(*branches)).mappings().all()
    result = {key: [] for key in ("by_waste_type", "by_cause", "by_machine", "by_material", "by_source")}
    monthly = {}
    first = last_forms = None
    for row in rows:
        kind = row["kind"]
        if kind == "range":
            first = datetime.fromisoformat(row["name"]).astimezone(tz).date() if row["name"] else None
            last_forms = datetime.fromisoformat(row["code"]).astimezone(tz).isoformat() if row["code"] else None
            continue
        grams = Decimal(str(row["weight_g"] or 0))
        values = {"count": int(row["count"]), "total_weight_g": str(grams), "total_weight_kg": str(grams / Decimal(1000))}
        if kind in ("total", "current", "previous"):
            result[kind] = values
        elif kind == "monthly":
            monthly[row["id"]] = values
        elif kind == "by_source":
            result[kind].append({"source": row["id"], **values})
        else:
            result[kind].append({"id": row["id"], "code": row["code"], "name": row["name"], **values})
    for key in ("by_waste_type", "by_cause", "by_machine", "by_material"):
        result[key].sort(key=lambda r: r["name"])
    series_end = (end_date or today).replace(day=1)
    series_start = start_date.replace(day=1) if start_date else min(
        (first or today).replace(day=1), today.replace(day=1) - relativedelta(months=5))
    series = []
    current = series_start
    while current <= series_end:
        period = current.strftime("%Y-%m")
        series.append({"period": period, "label": f"{MONTHS[current.month - 1]} {current.year}",
                       **monthly.get(period, {"count": 0, "total_weight_g": "0", "total_weight_kg": "0"})})
        current += relativedelta(months=1)

    def top_name(items):
        positive = [r for r in items if r["count"]]
        if not positive:
            return "Sin registros"
        maximum = max(Decimal(r["total_weight_g"]) for r in positive)
        names = [r["name"] for r in positive if Decimal(r["total_weight_g"]) == maximum]
        return " y ".join(names) + (" (empate)" if len(names) > 1 else "")

    total, current, previous = (result.pop(k) for k in ("total", "current", "previous"))
    return {**result, "total_records": total["count"], "total_weight_g": total["total_weight_g"],
            "total_weight_kg": total["total_weight_kg"], "current_month_records": current["count"],
            "current_month_weight_kg": current["total_weight_kg"], "monthly_series": series,
            "top_category_by_mass": top_name(result["by_waste_type"]),
            "top_cause_by_mass": top_name(result["by_cause"]), "last_google_forms_received_at": last_forms,
            "previous_period": {**previous, "total_records": previous["count"],
                                "start_date": prev_start.isoformat() if prev_start else None,
                                "end_date": prev_end.isoformat() if prev_end else None}}
