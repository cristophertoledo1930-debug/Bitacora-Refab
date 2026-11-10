"""Monthly delivery visibility and signed, expiring reconciliation forms."""
import hashlib
import hmac
import time

from lab_hub.config import get_settings
from lab_hub.db.models import ReportDelivery, ReportRun
from lab_hub.jobs.monthly_report import next_scheduled_at


def csrf_token(delivery_id, issued=None):
    issued = int(time.time()) if issued is None else issued
    payload = f"monthly:{delivery_id}:{issued}"
    signature = hmac.new(get_settings().SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{issued}:{signature}"


def valid_csrf(delivery_id, token):
    try:
        issued = int(token.split(":", 1)[0])
        return 0 <= time.time() - issued <= 3600 and hmac.compare_digest(token, csrf_token(delivery_id, issued))
    except (ValueError, TypeError):
        return False


def monthly_delivery_status(db):
    periods = {}
    deliveries = db.query(ReportDelivery).join(ReportRun).filter(
        ReportRun.period.like("____-__")
    ).order_by(ReportRun.period.desc(), ReportRun.revision.desc()).all()
    for delivery in deliveries:
        period = db.get(ReportRun, delivery.report_run_id).period
        recipients = periods.setdefault(period, {})
        # A successful or ambiguous historical delivery takes precedence over newer pending ones.
        current = recipients.get(delivery.recipient)
        priority = {"sent": 6, "uncertain": 5, "sending": 4, "failed": 3, "pending": 2}
        if current is None or priority[delivery.status] > priority[current.status]:
            recipients[delivery.recipient] = delivery
    result = []
    for period, recipients in periods.items():
        states = {d.status for d in recipients.values()}
        state = next(s for s in ("uncertain", "sending", "failed", "pending", "sent") if s in states)
        result.append({"period": period, "status": state, "deliveries": [
            {"id": str(d.id), "recipient": d.recipient, "status": d.status, "attempts": d.attempts,
             "error": d.error_summary, "csrf": csrf_token(d.id)} for d in recipients.values()
        ]})
    settings = get_settings()
    return {"email_enabled": settings.EMAIL_ENABLED,
            "auto_send_from": settings.REPORT_AUTO_SEND_FROM,
            "next_scheduled_at": next_scheduled_at().isoformat(), "periods": result}
