import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from lab_hub.config import get_settings
from lab_hub.db.models import ReportRun, ReportDelivery
from lab_hub.services.aggregations import get_aggregations
from lab_hub.reports.generator import build_monthly_pdf
from lab_hub.reports.mailer import send_report_email
from lab_hub.services.locks import report_lock

settings = get_settings()


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
    db: Session, period: str, recipients=None, smtp_client=None, force_new_revision=False
) -> ReportRun:
    with report_lock(db, f"report:{period}"):
        return _process_monthly_report(db, period, recipients, smtp_client, force_new_revision)


def _process_monthly_report(
    db: Session,
    period: str,
    recipients: list[str] | None = None,
    smtp_client=None,
    force_new_revision: bool = False
) -> ReportRun:
    """
    Creates snapshot, generates PDF, records run, and dispatches to recipients.
    Atomically acquires or updates the report run for the given period.
    """
    recipients = recipients or [r.strip() for r in settings.REPORT_TO.split(",") if r.strip()]
    year, month = map(int, period.split("-"))

    # Compute start date and end date of that calendar month
    start_d = date(year, month, 1)
    # Last day of month
    next_m = start_d + relativedelta(months=1)
    end_d = next_m - relativedelta(days=1)

    # Check existing run
    existing_run = db.query(ReportRun).filter_by(period=period).order_by(ReportRun.revision.desc()).first()

    if existing_run and existing_run.status == "completed" and existing_run.pdf_path and os.path.exists(existing_run.pdf_path) and not force_new_revision:
        report_run = existing_run
    else:
        revision = existing_run.revision + 1 if existing_run else 1

        # Generate snapshot using common aggregation service
        with db.get_bind().connect().execution_options(isolation_level="REPEATABLE READ") as connection:
            with Session(bind=connection) as snapshot_db:
                snapshot = get_aggregations(snapshot_db, start_date=start_d, end_date=end_d)

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
    for recipient in recipients:
        send_report_email(db, report_run, recipient.strip(), smtp_client=smtp_client)

    return report_run


def run_daily_check(
    db: Session,
    reference_date: date | None = None,
    smtp_client=None
) -> list[ReportRun]:
    """
    Daily scheduled job that recovers pending periods from REPORT_INITIAL_MONTH
    and processes closed months.
    """
    ref = reference_date or datetime.now(settings.timezone).date()
    if reference_date is None:
        now = datetime.now(settings.timezone)
        if now.day == 1 and now.hour < 8:
            return []
    closed_periods = get_closed_months(settings.REPORT_INITIAL_MONTH, ref)

    runs = []
    for period in closed_periods:
        # Check if deliveries are needed
        run = db.query(ReportRun).filter_by(period=period, status="completed").first()
        if not run:
            # Need to create report and deliver
            r = process_monthly_report(db, period, smtp_client=smtp_client)
            runs.append(r)
        else:
            # Check if any recipient is pending or failed
            pending = db.query(ReportDelivery).filter(
                ReportDelivery.report_run_id == run.id,
                ReportDelivery.status.in_(["pending", "failed"])
            ).count()
            if pending > 0 or not run.pdf_path or not os.path.exists(run.pdf_path) or not run.deliveries:
                r = process_monthly_report(db, period, smtp_client=smtp_client)
                runs.append(r)

    return runs

