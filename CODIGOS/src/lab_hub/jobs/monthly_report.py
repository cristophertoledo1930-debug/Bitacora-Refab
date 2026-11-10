import os
import json
import logging
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from lab_hub.config import get_settings
from lab_hub.db.models import ReportRun, ReportDelivery, WasteRecord
from lab_hub.services.aggregations import get_aggregations
from lab_hub.reports.generator import build_monthly_pdf
from lab_hub.reports.mailer import send_report_email
from lab_hub.services.locks import report_lock

settings = get_settings()
logger = logging.getLogger(__name__)


def get_closed_months(initial_month_str: str, reference_date: date) -> list[str]:
    """Returns list of YYYY-MM periods that are fully closed relative to reference_date."""
    init_year, init_month = map(int, initial_month_str.split("-"))
    curr = date(init_year, init_month, 1)
    end = date(reference_date.year, reference_date.month, 1)

    closed = []
    while curr < end:
        closed.append(f"{curr.year:04d}-{curr.month:02d}")
        curr += relativedelta(months=1)
    return closed


def process_monthly_report(
    db: Session, period: str, recipients=None, smtp_client=None, force_new_revision=False,
    send_email=True, automatic=False,
) -> ReportRun:
    with report_lock(db, f"report:{period}"):
        return _process_monthly_report(db, period, recipients, smtp_client, force_new_revision, send_email, automatic)


def _process_monthly_report(
    db: Session,
    period: str,
    recipients: list[str] | None = None,
    smtp_client=None,
    force_new_revision: bool = False,
    send_email: bool = True,
    automatic: bool = False,
) -> ReportRun:
    """
    Creates snapshot, generates PDF, records run, and dispatches to recipients.
    Atomically acquires or updates the report run for the given period.
    """
    recipients = recipients if recipients is not None else [r.strip() for r in settings.REPORT_TO.split(",") if r.strip()]
    year, month = map(int, period.split("-"))

    # Compute start date and end date of that calendar month
    start_d = date(year, month, 1)
    # Last day of month
    next_m = start_d + relativedelta(months=1)
    end_d = next_m - relativedelta(days=1)

    # Check existing run
    existing_run = db.query(ReportRun).filter_by(period=period).order_by(ReportRun.revision.desc()).first()

    # Always compare the current month data; a saved PDF can be out of date.
    with db.get_bind().connect().execution_options(isolation_level="REPEATABLE READ") as connection:
        with Session(bind=connection) as snapshot_db:
            snapshot = get_aggregations(snapshot_db, start_date=start_d, end_date=end_d, source=settings.REPORT_SOURCE or None)
            previous_start = start_d - relativedelta(months=1)
            previous = get_aggregations(snapshot_db, start_date=previous_start,
                                        end_date=start_d - relativedelta(days=1), source=settings.REPORT_SOURCE or None)
            snapshot["previous_month"] = {"period": previous_start.strftime("%Y-%m"),
                                          "total_records": previous["total_records"],
                                          "total_weight_g": previous["total_weight_g"],
                                          "total_weight_kg": previous["total_weight_kg"]}
            for key in ("last_google_forms_received_at", "current_month_weight_kg", "current_month_records"):
                snapshot.pop(key, None)
            from datetime import time
            rows = snapshot_db.query(WasteRecord).filter(
                WasteRecord.recorded_at >= datetime.combine(start_d, time.min, tzinfo=settings.timezone),
                WasteRecord.recorded_at < datetime.combine(next_m, time.min, tzinfo=settings.timezone),
            )
            if settings.REPORT_SOURCE:
                rows = rows.filter(WasteRecord.source == settings.REPORT_SOURCE)
            rows = rows.order_by(WasteRecord.id).all()
            snapshot["records"] = [{"id": str(row.id), "recorded_at": row.recorded_at.astimezone(settings.timezone).isoformat(),
                                    "weight_g": str(row.weight_g), "source": row.source,
                                    "waste_type": row.waste_type.name, "material": row.material.name,
                                    "machine": row.machine.name, "cause": row.cause.name} for row in rows]
    snapshot.update(report_source=settings.REPORT_SOURCE, report_kind="monthly", start_date=start_d.isoformat(), end_date=end_d.isoformat())

    if existing_run and existing_run.snapshot == snapshot and existing_run.status == "completed" and existing_run.pdf_path and os.path.exists(existing_run.pdf_path) and not force_new_revision:
        report_run = existing_run
    else:
        revision = existing_run.revision + 1 if existing_run else 1

        # Generate snapshot using common aggregation service
        # Snapshot above already includes a consistent view of the latest records.

        # Build PDF path
        filename = f"informe_{period}_rev{revision}.pdf"
        output_dir = os.path.abspath(settings.REPORT_OUTPUT_DIR)
        output_path = os.path.join(output_dir, filename)

        pdf_path, content_hash = build_monthly_pdf(snapshot, output_path, period, revision)

        report_run = ReportRun(
            period=period,
            revision=revision,
            status="completed",
            snapshot=snapshot,
            pdf_path=pdf_path,
            content_hash=content_hash,
            generated_at=datetime.now(settings.timezone)
        )
        db.add(report_run)
        db.commit()
        db.refresh(report_run)

    # Dispatch to all recipients
    if send_email:
        for recipient in recipients:
            recipient = recipient.strip()
            target = report_run
            if automatic:
                history = db.query(ReportDelivery).join(ReportRun).filter(
                    ReportRun.period == period, ReportDelivery.recipient == recipient
                ).order_by(ReportRun.revision).all()
                if any(d.status in {"sent", "uncertain", "sending"} for d in history):
                    # A process interrupted while sending cannot prove SMTP acceptance.
                    for delivery in history:
                        if delivery.status == "sending":
                            delivery.status = "uncertain"
                    db.commit()
                    continue
                if history:
                    compatible = [delivery for delivery in history if
                                  db.get(ReportRun, delivery.report_run_id).snapshot.get("report_source") == settings.REPORT_SOURCE]
                    if compatible:
                        target = db.get(ReportRun, compatible[0].report_run_id)
                    else:
                        # An old unsent mixed-source PDF must never escape through a retry.
                        # Keep its attempt budget and retry deadline on the scoped revision.
                        history[0].report_run_id = report_run.id
                        db.commit()
            send_report_email(db, target, recipient, smtp_client=smtp_client)

    return report_run


def scheduled_at(now: datetime) -> datetime:
    return now.replace(day=settings.REPORT_SEND_DAY, hour=settings.REPORT_SEND_HOUR,
                       minute=0, second=0, microsecond=0)


def next_scheduled_at(now: datetime | None = None) -> datetime:
    local = (now or datetime.now(settings.timezone)).astimezone(settings.timezone)
    scheduled = scheduled_at(local)
    return scheduled if local < scheduled else scheduled + relativedelta(months=1)


def run_daily_check(
    db: Session,
    reference_date: date | None = None,
    smtp_client=None,
    *, now: datetime | None = None,
) -> list[ReportRun]:
    """Archive closed months and deliver only eligible periods under their locks."""
    if now is not None and now.tzinfo is None:
        raise ValueError("now requiere zona horaria")
    local = (now or datetime.now(settings.timezone)).astimezone(settings.timezone)
    if reference_date is not None:
        # Compatibility for callers supplying a date; scheduling still uses a full instant.
        local = datetime.combine(reference_date, local.timetz())
    cutoff = local.date().replace(day=1)
    if local < scheduled_at(local):
        cutoff -= relativedelta(months=1)
    closed_periods = get_closed_months(settings.REPORT_INITIAL_MONTH, local.date())
    runs = []
    for period in closed_periods:
        eligible = bool(settings.REPORT_AUTO_SEND_FROM and period >= settings.REPORT_AUTO_SEND_FROM
                        and date.fromisoformat(period + "-01") < cutoff)
        runs.append(process_monthly_report(db, period, smtp_client=smtp_client,
                                           send_email=eligible, automatic=True))
    counts = {}
    for state, in db.query(ReportDelivery.status).join(ReportRun).filter(ReportRun.period.in_(closed_periods)):
        counts[state] = counts.get(state, 0) + 1
    logger.info(json.dumps({"event": "monthly_check", "at": local.isoformat(), "periods": len(runs),
                            "auto_send_configured": bool(settings.REPORT_AUTO_SEND_FROM),
                            "email_enabled": settings.EMAIL_ENABLED, "deliveries": counts}))
    return runs


def refresh_monthly_reports(db):
    """Refresh current, populated and archived months without sending email."""
    periods = {datetime.now(settings.timezone).strftime("%Y-%m")}
    periods.update(value.astimezone(settings.timezone).strftime("%Y-%m")
                   for value, in db.query(WasteRecord.recorded_at).all())
    periods.update(period for period, in db.query(ReportRun.period).filter(ReportRun.period.like("____-__")).distinct())
    return [process_monthly_report(db, period, send_email=False) for period in sorted(periods)]



def main() -> int:
    from lab_hub.db.session import SessionLocal
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        with SessionLocal() as db:
            runs = run_daily_check(db)
            incomplete = db.query(ReportDelivery).join(ReportRun).filter(
                ReportRun.period.in_([run.period for run in runs]),
                ReportDelivery.status.in_(["failed", "uncertain", "sending"])
            ).count()
            if incomplete:
                logger.error('{"event":"monthly_check_incomplete"}')
                return 1
        return 0
    except Exception:
        # Exception details may contain credentials from connection strings.
        logger.error('{"event":"monthly_check_failed"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
