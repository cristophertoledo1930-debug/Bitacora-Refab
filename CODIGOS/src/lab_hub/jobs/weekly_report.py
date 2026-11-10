"""Versioned weekly reports from the same PostgreSQL records as the dashboard."""
from datetime import date, datetime, timedelta, time
from pathlib import Path

from sqlalchemy.orm import Session

from lab_hub.config import get_settings
from lab_hub.db.models import ReportRun, WasteRecord
from lab_hub.reports.generator import build_monthly_pdf
from lab_hub.services.aggregations import get_aggregations
from lab_hub.services.locks import report_lock


def week_key(day):
    year, week, _ = day.isocalendar()
    return f"{year}W{week:02d}"


def update_week(db, period):
    settings = get_settings()
    start = date.fromisocalendar(int(period[:4]), int(period[5:]), 1)
    end = start + timedelta(days=6)
    with report_lock(db, "weekly:" + period):
        with db.get_bind().connect().execution_options(isolation_level="REPEATABLE READ") as connection:
            with Session(bind=connection) as snapshot_db:
                snapshot = get_aggregations(snapshot_db, start_date=start, end_date=end)
                # Exclude global/current-month values that change outside this week.
                for key in ("last_google_forms_received_at", "current_month_weight_kg", "current_month_records"):
                    snapshot.pop(key, None)
                rows = snapshot_db.query(WasteRecord).filter(
                    WasteRecord.recorded_at >= datetime.combine(start, time.min, tzinfo=settings.timezone),
                    WasteRecord.recorded_at < datetime.combine(end + timedelta(days=1), time.min, tzinfo=settings.timezone),
                ).order_by(WasteRecord.id).all()
                snapshot["records"] = [{"id": str(row.id), "recorded_at": row.recorded_at.astimezone(settings.timezone).isoformat(),
                                        "weight_g": str(row.weight_g), "source": row.source,
                                        "waste_type": row.waste_type.name, "material": row.material.name,
                                        "machine": row.machine.name, "cause": row.cause.name} for row in rows]
        snapshot.update(report_kind="weekly", start_date=start.isoformat(), end_date=end.isoformat())
        latest = db.query(ReportRun).filter_by(period=period).order_by(ReportRun.revision.desc()).first()
        if latest and latest.snapshot == snapshot and latest.pdf_path and Path(latest.pdf_path).is_file():
            return latest
        revision = latest.revision + 1 if latest else 1
        path = Path(settings.REPORT_OUTPUT_DIR).resolve() / f"semanal_{period}_rev{revision}.pdf"
        pdf_path, digest = build_monthly_pdf(snapshot, str(path), f"{start:%d/%m/%Y} - {end:%d/%m/%Y}", revision)
        run = ReportRun(period=period, revision=revision, status="completed", snapshot=snapshot,
                        pdf_path=pdf_path, content_hash=digest, generated_at=datetime.now(settings.timezone))
        db.add(run)
        db.commit()
        return run


def refresh_weekly_reports(db):
    settings = get_settings()
    periods = {week_key(datetime.now(settings.timezone).date())}
    periods.update(week_key(value.astimezone(settings.timezone).date())
                   for value, in db.query(WasteRecord.recorded_at).all())
    periods.update(period for period, in db.query(ReportRun.period).filter(ReportRun.period.like("____W__")).distinct())
    return [update_week(db, period) for period in sorted(periods)]
