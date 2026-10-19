import os
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from lab_hub.config import get_settings
from lab_hub.db.models import ReportRun, ReportDelivery
from lab_hub.services.locks import report_lock

settings = get_settings()


class SMTPDeliveryError(Exception):
    pass


class SMTPUncertainError(Exception):
    pass


def send_report_email(
    db: Session, report_run: ReportRun, recipient: str, smtp_client=None
) -> ReportDelivery:
    with report_lock(db, f"delivery:{report_run.id}:{recipient}"):
        return _send_report_email(db, report_run, recipient, smtp_client)


def _send_report_email(
    db: Session,
    report_run: ReportRun,
    recipient: str,
    smtp_client=None
) -> ReportDelivery:
    """
    Sends monthly report PDF to a single recipient with delivery tracking.
    Skips if recipient is already in 'sent' state.
    """
    delivery = db.query(ReportDelivery).filter_by(
        report_run_id=report_run.id,
        recipient=recipient
    ).first()

    if not delivery:
        delivery = ReportDelivery(
            report_run_id=report_run.id,
            recipient=recipient,
            status="pending",
            attempts=0
        )
        db.add(delivery)
        db.flush()

    if delivery.status in {"sent", "uncertain"}:
        return delivery
    if delivery.status == "sending":
        delivery.status = "uncertain"
        db.commit()
        return delivery
    if not settings.EMAIL_ENABLED and not settings.LOCAL_SMTP_ENABLED and smtp_client is None:
        db.commit()
        return delivery
    if delivery.attempts >= 3:
        return delivery
    if delivery.next_attempt_at and delivery.next_attempt_at > datetime.now(timezone.utc):
        return delivery

    delivery.status = "sending"
    delivery.attempts += 1
    db.commit()

    msg_id = delivery.message_id or make_msgid(domain="qrlabhub.local")
    delivery.message_id = msg_id
    db.commit()

    # Construct email message
    msg = EmailMessage()
    msg["Subject"] = f"QR Lab Hub — Informe Mensual {report_run.period} (Rev {report_run.revision})"
    msg["From"] = settings.REPORT_FROM
    msg["To"] = recipient
    msg["Message-ID"] = msg_id
    msg.set_content(
        f"Estimado(a),\n\n"
        f"Adjunto se encuentra el informe mensual de residuos correspondiente al periodo {report_run.period} "
        f"(Revisión {report_run.revision}), generado automáticamente por QR Lab Hub.\n\n"
        f"Saludos cordiales,\nEquipo QR Lab Hub"
    )

    # Attach PDF
    pdf_filename = os.path.basename(report_run.pdf_path) if report_run.pdf_path else f"informe_{report_run.period}.pdf"
    if report_run.pdf_path and os.path.exists(report_run.pdf_path):
        with open(report_run.pdf_path, "rb") as f:
            pdf_bytes = f.read()
        msg.add_attachment(
            pdf_bytes,
            maintype="application",
            subtype="pdf",
            filename=pdf_filename
        )

    # Dispatch via SMTP
    try:
        if smtp_client is not None:
            # Injectable client (for tests / mocks)
            smtp_client.send_message(msg)
        else:
            if settings.LOCAL_SMTP_ENABLED and settings.SMTP_HOST not in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("El SMTP local requiere un host loopback.")
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as s:
                if settings.SMTP_TLS:
                    s.starttls()
                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    s.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                s.send_message(msg)

        delivery.status = "sent"
        delivery.next_attempt_at = None
        delivery.error_summary = None
        db.commit()
    except (SMTPUncertainError, smtplib.SMTPServerDisconnected, TimeoutError) as exc:
        delivery.status = "uncertain"
        delivery.error_summary = str(exc)
        db.commit()
    except Exception as exc:
        from datetime import timedelta
        delivery.status = "failed"
        delivery.next_attempt_at = datetime.now(timezone.utc) + timedelta(minutes=5 * delivery.attempts)
        delivery.error_summary = str(exc)
        db.commit()

    return delivery

