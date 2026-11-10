import os
import smtplib
import ssl
from decimal import Decimal
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
    source_label = " — Formularios" if report_run.snapshot.get("report_source") == "google_forms" else ""
    msg["Subject"] = f"QR Lab Hub — Informe Mensual{source_label} {report_run.period} (Rev {report_run.revision})"
    msg["From"] = settings.REPORT_FROM
    msg["To"] = recipient
    msg["Message-ID"] = msg_id
    snapshot = report_run.snapshot
    lines = [f"Resumen mensual {report_run.period}{source_label}",
             f"Respuestas: {snapshot.get('total_records', 0)}",
             f"Masa total: {snapshot.get('total_weight_kg', '0.000')} kg"]
    if not snapshot.get("total_records"):
        lines.append("No hubo respuestas durante este periodo.")
    for key, label in (("by_waste_type", "Tipo"), ("by_material", "Material"),
                       ("by_machine", "Máquina"), ("by_cause", "Causa")):
        rows = [row for row in snapshot.get(key, []) if row["count"]]
        top = max(rows, key=lambda row: Decimal(row["total_weight_g"]), default=None)
        lines.append(f"{label} principal por masa: {top['name'] if top else 'Sin respuestas'}")
    previous = snapshot.get("previous_month")
    if previous:
        delta = (Decimal(snapshot["total_weight_g"]) - Decimal(previous["total_weight_g"])) / Decimal("1000")
        lines.append(f"Mes anterior ({previous['period']}): {previous['total_records']} respuestas, "
                     f"{previous['total_weight_kg']} kg. Diferencia: {delta:+f} kg.")
    else:
        lines.append("Comparación con mes anterior no disponible en este snapshot histórico.")
    lines.append("Informe PDF adjunto. Cifras del snapshot de esta revisión.")
    msg.set_content("\n".join(lines))

    # Attach PDF
    try:
        if not report_run.pdf_path:
            raise ValueError("PDF obligatorio: ruta ausente.")
        with open(report_run.pdf_path, "rb") as f:
            pdf_bytes = f.read()
        if not pdf_bytes:
            raise ValueError("PDF obligatorio: archivo vacío.")
        msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf",
                           filename=os.path.basename(report_run.pdf_path))
    except (OSError, ValueError):
        delivery.status = "failed"
        delivery.error_summary = "PDF obligatorio ausente, vacío o no legible. No se envió correo."
        db.commit()
        return delivery

    # Dispatch via SMTP
    try:
        if smtp_client is not None:
            # Injectable client (for tests / mocks)
            smtp_client.send_message(msg)
        else:
            settings.validate_smtp_security()
            transport = smtplib.SMTP_SSL if settings.SMTP_SSL else smtplib.SMTP
            options = {"context": ssl.create_default_context()} if settings.SMTP_SSL else {}
            with transport(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10, **options) as s:
                if settings.SMTP_TLS:
                    s.starttls(context=ssl.create_default_context())
                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    s.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                s.send_message(msg)

        delivery.status = "sent"
        delivery.next_attempt_at = None
        delivery.error_summary = None
        db.commit()
    except (SMTPUncertainError, smtplib.SMTPServerDisconnected, TimeoutError) as exc:
        delivery.status = "uncertain"
        delivery.error_summary = safe_error(exc)
        db.commit()
    except Exception as exc:
        from datetime import timedelta
        delivery.status = "failed"
        delivery.next_attempt_at = datetime.now(timezone.utc) + timedelta(minutes=5 * delivery.attempts)
        delivery.error_summary = safe_error(exc)
        db.commit()

    return delivery



def safe_error(exc: Exception) -> str:
    text = str(exc)
    for secret in (settings.SMTP_PASSWORD, settings.SMTP_USERNAME):
        if secret:
            text = text.replace(secret, "[redacted]")
    # SMTP exceptions can echo a refused recipient; persist no full addresses.
    import re
    return re.sub(r"[\w.+-]+@[\w.-]+", "[recipient]", text)[:300]
