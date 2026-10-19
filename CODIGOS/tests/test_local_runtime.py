from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from email import policy
from email.parser import BytesParser
import socket
import uuid

import pytest
from aiosmtpd.controller import Controller
from fastapi.testclient import TestClient
from lab_hub.api.app import app
from lab_hub.config import get_settings
from lab_hub.db.models import ReportRun, ReportDelivery
from lab_hub.db.session import SessionLocal
from lab_hub.jobs.monthly_report import process_monthly_report
from lab_hub.reports.mailer import send_report_email
from lab_hub.services.records import normalize_weight, ValidationError
from lab_hub.services.aggregations import get_aggregations
from tests.test_f4_reports import MockSMTPClient


@pytest.mark.parametrize("weight", ["0.0001", "1.1234", "1e100", "0.000000001"])
def test_weight_precision_and_extreme_values(weight):
    with pytest.raises(ValidationError):
        normalize_weight(weight, "g")


def test_mounted_dashboard_and_protection():
    client = TestClient(app)
    assert client.get("/dashboard/").status_code == 401
    headers = {"X-Admin-Key": get_settings().ADMIN_API_KEY}
    assert client.get("/dashboard/", headers=headers).status_code == 200
    response = client.get("/dashboard/_dash-layout", headers=headers)
    assert response.status_code == 200
    assert response.json()["type"] == "Div"
    assert client.get("/reports", headers=headers).status_code == 200
    assert client.get("/r/token-general").status_code == 200


def test_local_access_requires_loopback_host_and_explicit_mode(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "LOCAL_DESKTOP_ACCESS", True)
    client = TestClient(app, client=("127.0.0.1", 12345), base_url="http://localhost")
    assert client.get("/dashboard/_dash-layout").status_code == 200
    assert client.get("/dashboard/", headers={"Host": "untrusted.example"}).status_code == 401
    assert client.get("/dashboard/", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 401


def test_date_filtered_series_matches_totals():
    with SessionLocal() as db:
        agg = get_aggregations(db, start_date=date(2026, 1, 1), end_date=date(2026, 1, 31))
    assert [r["period"] for r in agg["monthly_series"]] == ["2026-01"]
    assert sum(r["count"] for r in agg["monthly_series"]) == agg["total_records"]
    assert sum(Decimal(r["total_weight_g"]) for r in agg["monthly_series"]) == Decimal(agg["total_weight_g"])


def test_disabled_mail_stays_pending_and_uncertain_never_resends():
    with SessionLocal() as db:
        run = process_monthly_report(db, "2025-12", recipients=["disabled@qrlabhub.local"])
        delivery = db.query(ReportDelivery).filter_by(report_run_id=run.id).one()
        assert delivery.status == "pending"
        assert delivery.attempts == 0
        delivery.status = "uncertain"
        db.commit()
        smtp = MockSMTPClient()
        assert send_report_email(db, run, delivery.recipient, smtp).status == "uncertain"
        assert smtp.sent_messages == []


def test_concurrent_report_is_single_revision_and_delivery():
    smtp = MockSMTPClient()
    def run():
        with SessionLocal() as db:
            return process_monthly_report(db, "2025-11", recipients=["race@qrlabhub.local"], smtp_client=smtp).id
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(lambda _: run(), range(2)))
    assert len(set(ids)) == 1
    assert len(smtp.sent_messages) == 1


def test_real_local_smtp_and_pdf_attachment(monkeypatch):
    messages = []
    class Inbox:
        async def handle_DATA(self, server, session, envelope):
            messages.append(envelope.original_content)
            return "250 Stored"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    controller = Controller(Inbox(), hostname="127.0.0.1", port=port)
    controller.start()
    settings = get_settings()
    monkeypatch.setattr(settings, "LOCAL_SMTP_ENABLED", True)
    monkeypatch.setattr(settings, "SMTP_HOST", "127.0.0.1")
    monkeypatch.setattr(settings, "SMTP_PORT", port)
    try:
        with SessionLocal() as db:
            run = process_monthly_report(db, "2025-10", recipients=["smtp@qrlabhub.local"])
            assert run.deliveries[0].status == "sent"
        assert len(messages) == 1
        message = BytesParser(policy=policy.default).parsebytes(messages[0])
        attachment = next(message.iter_attachments())
        assert attachment.get_content_type() == "application/pdf"
        assert attachment.get_payload(decode=True).startswith(b"%PDF")
    finally:
        controller.stop()
