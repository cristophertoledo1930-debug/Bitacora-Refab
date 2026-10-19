from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from lab_hub.config import get_settings
from lab_hub.db.models import (
    WasteRecord,
    WasteType,
    Material,
    Machine,
    Cause,
)

settings = get_settings()


def get_month_utc_range(year: int, month: int, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """
    Computes start (inclusive) and end (exclusive) in UTC for a calendar month in specified timezone.
    Guarantees proper DST handling in America/Santiago.
    """
    start_local = datetime(year, month, 1, 0, 0, 0, tzinfo=tz)
    # Next month
    if month == 12:
        end_local = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=tz)
    else:
        end_local = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=tz)

    start_utc = start_local.astimezone(ZoneInfo("UTC"))
    end_utc = end_local.astimezone(ZoneInfo("UTC"))
    return start_utc, end_utc


def get_aggregations(
    db: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    waste_type_id: UUID | None = None,
    material_id: UUID | None = None,
    machine_id: UUID | None = None,
    cause_id: UUID | None = None,
    tz: ZoneInfo | None = None,
) -> dict:
    tz = tz or settings.timezone

    if start_date and end_date and start_date > end_date:
        raise ValueError("Rango de fechas inválido.")

    # Base filter criteria
    filters = []

    if start_date:
        start_dt_local = datetime.combine(start_date, time.min, tzinfo=tz)
        start_utc = start_dt_local.astimezone(ZoneInfo("UTC"))
        filters.append(WasteRecord.recorded_at >= start_utc)

    if end_date:
        # Exclusive next day
        end_dt_local = datetime.combine(end_date + relativedelta(days=1), time.min, tzinfo=tz)
        end_utc = end_dt_local.astimezone(ZoneInfo("UTC"))
        filters.append(WasteRecord.recorded_at < end_utc)

    if waste_type_id:
        filters.append(WasteRecord.waste_type_id == waste_type_id)
    if material_id:
        filters.append(WasteRecord.material_id == material_id)
    if machine_id:
        filters.append(WasteRecord.machine_id == machine_id)
    if cause_id:
        filters.append(WasteRecord.cause_id == cause_id)

    # 1. Total summary
    tot_query = db.query(
        func.count(WasteRecord.id).label("total_count"),
        func.coalesce(func.sum(WasteRecord.weight_g), 0).label("total_weight_g")
    )
    if filters:
        tot_query = tot_query.filter(and_(*filters))
    tot_res = tot_query.first()
    total_records = tot_res.total_count if tot_res else 0
    total_weight_g = Decimal(str(tot_res.total_weight_g)) if tot_res else Decimal("0")
    total_weight_kg = (total_weight_g / Decimal("1000")).quantize(Decimal("0.001"))

    # 2. Current month in Santiago
    now_local = datetime.now(tz)
    cur_m_start_utc, cur_m_end_utc = get_month_utc_range(now_local.year, now_local.month, tz)
    cur_m_count = db.query(func.count(WasteRecord.id)).filter(
        *filters,
        WasteRecord.recorded_at >= cur_m_start_utc,
        WasteRecord.recorded_at < cur_m_end_utc
    ).scalar() or 0

    # 3. By waste type
    q_type = db.query(
        WasteType.id,
        WasteType.code,
        WasteType.name,
        func.count(WasteRecord.id).label("count"),
        func.coalesce(func.sum(WasteRecord.weight_g), 0).label("weight_g")
    ).outerjoin(
        WasteRecord,
        and_(WasteRecord.waste_type_id == WasteType.id, *filters) if filters else WasteRecord.waste_type_id == WasteType.id
    ).group_by(WasteType.id, WasteType.code, WasteType.name).order_by(WasteType.name).all()

    by_waste_type = []
    top_cat_name = "N/A"
    max_cat_g = Decimal("-1")

    for r in q_type:
        g = Decimal(str(r.weight_g))
        kg = (g / Decimal("1000")).quantize(Decimal("0.001"))
        by_waste_type.append({
            "id": str(r.id),
            "code": r.code,
            "name": r.name,
            "count": r.count,
            "total_weight_g": str(g),
            "total_weight_kg": str(kg)
        })
        if g > max_cat_g and r.count > 0:
            max_cat_g = g
            top_cat_name = f"{r.name} ({kg} kg)"

    # 4. By cause
    q_cause = db.query(
        Cause.id,
        Cause.code,
        Cause.name,
        func.count(WasteRecord.id).label("count"),
        func.coalesce(func.sum(WasteRecord.weight_g), 0).label("weight_g")
    ).outerjoin(
        WasteRecord,
        and_(WasteRecord.cause_id == Cause.id, *filters) if filters else WasteRecord.cause_id == Cause.id
    ).group_by(Cause.id, Cause.code, Cause.name).order_by(Cause.name).all()

    by_cause = [
        {
            "id": str(r.id),
            "code": r.code,
            "name": r.name,
            "count": r.count,
            "total_weight_g": str(Decimal(str(r.weight_g))),
            "total_weight_kg": str((Decimal(str(r.weight_g)) / Decimal("1000")).quantize(Decimal("0.001")))
        }
        for r in q_cause
    ]

    # 5. By machine
    q_machine = db.query(
        Machine.id,
        Machine.code,
        Machine.name,
        func.count(WasteRecord.id).label("count"),
        func.coalesce(func.sum(WasteRecord.weight_g), 0).label("weight_g")
    ).outerjoin(
        WasteRecord,
        and_(WasteRecord.machine_id == Machine.id, *filters) if filters else WasteRecord.machine_id == Machine.id
    ).group_by(Machine.id, Machine.code, Machine.name).order_by(Machine.name).all()

    by_machine = [
        {
            "id": str(r.id),
            "code": r.code,
            "name": r.name,
            "count": r.count,
            "total_weight_g": str(Decimal(str(r.weight_g))),
            "total_weight_kg": str((Decimal(str(r.weight_g)) / Decimal("1000")).quantize(Decimal("0.001")))
        }
        for r in q_machine
    ]

    # 6. By material
    q_material = db.query(
        Material.id,
        Material.code,
        Material.name,
        func.count(WasteRecord.id).label("count"),
        func.coalesce(func.sum(WasteRecord.weight_g), 0).label("weight_g")
    ).outerjoin(
        WasteRecord,
        and_(WasteRecord.material_id == Material.id, *filters) if filters else WasteRecord.material_id == Material.id
    ).group_by(Material.id, Material.code, Material.name).order_by(Material.name).all()

    by_material = [
        {
            "id": str(r.id),
            "code": r.code,
            "name": r.name,
            "count": r.count,
            "total_weight_g": str(Decimal(str(r.weight_g))),
            "total_weight_kg": str((Decimal(str(r.weight_g)) / Decimal("1000")).quantize(Decimal("0.001")))
        }
        for r in q_material
    ]

    # 7. Monthly series (chronological, zero-filled, labels with year)
    # Determine span of months to display (at least the last 6 months or based on records)
    records_range = db.query(
        func.min(WasteRecord.recorded_at),
        func.max(WasteRecord.recorded_at)
    ).first()

    first_rec = records_range[0] if records_range and records_range[0] else None
    if first_rec:
        first_local = first_rec.astimezone(tz)
        series_start = date(first_local.year, first_local.month, 1)
    else:
        series_start = date(now_local.year, now_local.month, 1) - relativedelta(months=5)

    series_end = date(now_local.year, now_local.month, 1)
    if series_start > series_end - relativedelta(months=5):
        series_start = series_end - relativedelta(months=5)

    if start_date:
        series_start = start_date.replace(day=1)
    if end_date:
        series_end = end_date.replace(day=1)

    month_names = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    monthly_series = []

    curr_m = series_start
    while curr_m <= series_end:
        m_start_utc, m_end_utc = get_month_utc_range(curr_m.year, curr_m.month, tz)
        m_filters = [*filters, WasteRecord.recorded_at >= m_start_utc, WasteRecord.recorded_at < m_end_utc]
        if waste_type_id:
            m_filters.append(WasteRecord.waste_type_id == waste_type_id)
        if material_id:
            m_filters.append(WasteRecord.material_id == material_id)
        if machine_id:
            m_filters.append(WasteRecord.machine_id == machine_id)
        if cause_id:
            m_filters.append(WasteRecord.cause_id == cause_id)

        m_q = db.query(
            func.count(WasteRecord.id).label("cnt"),
            func.coalesce(func.sum(WasteRecord.weight_g), 0).label("sum_g")
        ).filter(and_(*m_filters)).first()

        m_cnt = m_q.cnt if m_q else 0
        m_g = Decimal(str(m_q.sum_g)) if m_q else Decimal("0")
        m_kg = (m_g / Decimal("1000")).quantize(Decimal("0.001"))

        period_str = f"{curr_m.year:04d}-{curr_m.month:02d}"
        label = f"{month_names[curr_m.month - 1]} {curr_m.year}"

        monthly_series.append({
            "period": period_str,
            "label": label,
            "count": m_cnt,
            "total_weight_g": str(m_g),
            "total_weight_kg": str(m_kg)
        })

        curr_m += relativedelta(months=1)

    return {
        "total_records": total_records,
        "total_weight_g": str(total_weight_g),
        "total_weight_kg": str(total_weight_kg),
        "current_month_records": cur_m_count,
        "top_category_by_mass": top_cat_name,
        "by_waste_type": by_waste_type,
        "by_cause": by_cause,
        "by_machine": by_machine,
        "by_material": by_material,
        "monthly_series": monthly_series
    }

