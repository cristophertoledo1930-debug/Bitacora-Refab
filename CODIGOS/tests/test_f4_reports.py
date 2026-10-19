import os
import uuid
from decimal import Decimal
from datetime import date, datetime, timezone
import pytest
from lab_hub.db.session import SessionLocal
from lab_hub.db.models import ReportRun, ReportDelivery, WasteRecord
from lab_hub.services.seeds import seed_catalogs
from lab_hub.services.aggregations import get_aggregations
from lab_hub.reports.generator import build_monthly_pdf
from lab_hub.reports.mailer import send_report_email, SMTPUncertainError
from lab_hub.jobs.monthly_report import process_monthly_report, run_daily_check, get_closed_months
from lab_hub.api.app import app
from fastapi.testclient import TestClient

client = TestClient(app)
ADMIN_KEY = "labhub-dev-admin-key-2026"


class MockSMTPClient:
    def __init__(self, should_fail=False, should_be_uncertain=False):
        self.sent_messages = []
        self.should_fail = should_fail
        self.should_be_uncertain = should_be_uncertain

    def send_message(self, msg):
        if self.should_fail:
            raise ConnectionRefusedError("Simulated SMTP Connection Refused")
        if self.should_be_uncertain:
            raise SMTPUncertainError("Simulated connection drop after DATA acknowledgement")
        self.sent_messages.append(msg)


@pytest.fixture
def db():
    session = SessionLocal()
    seed_catalogs(session)
    try:
        yield session
    finally:
        session.close()


def test_t13_pdf_normal_and_empty_month(db, tmp_path):
    # Test 1: Normal snapshot with accents
    snapshot_normal = {
        "total_records": 5,
        "total_weight_g": "1500.250",
        "total_weight_kg": "1.500",
        "top_category_by_mass": "Resina (1.500 kg)",
        "by_waste_type": [
            {"name": "Resina", "count": 3, "total_weight_g": "1000.250", "total_weight_kg": "1.000"},
            {"name": "Retazo láser", "count": 2, "total_weight_g": "500.000", "total_weight_kg": "0.500"},
        ],
        "by_cause": [
            {"name": "Soporte desprendido", "count": 3, "total_weight_g": "1000.250", "total_weight_kg": "1.000"},
            {"name": "Margen de corte", "count": 2, "total_weight_g": "500.000", "total_weight_kg": "0.500"},
        ],
        "monthly_series": [
            {"period": "2026-01", "label": "Ene 2026", "count": 5, "total_weight_kg": "1.500"},
            {"period": "2026-02", "label": "Feb 2026", "count": 0, "total_weight_kg": "0.000"},
        ]
    }
    out1 = str(tmp_path / "informe_normal.pdf")
    pdf_path1, hash1 = build_monthly_pdf(snapshot_normal, out1, "2026-01", 1)
    assert os.path.exists(pdf_path1)
    assert os.path.getsize(pdf_path1) > 1000
    assert len(hash1) == 64

    # Test 2: Empty month snapshot (zero records)
    snapshot_empty = {
        "total_records": 0,
        "total_weight_g": "0.000",
        "total_weight_kg": "0.000",
        "top_category_by_mass": "N/A",
        "by_waste_type": [],
        "by_cause": [],
        "monthly_series": [
            {"period": "2026-03", "label": "Mar 2026", "count": 0, "total_weight_kg": "0.000"},
        ]
    }
    out2 = str(tmp_path / "informe_vacio.pdf")
    pdf_path2, hash2 = build_monthly_pdf(snapshot_empty, out2, "2026-03", 1)
    assert os.path.exists(pdf_path2)
    assert os.path.getsize(pdf_path2) > 1000


def test_t14_snapshot_and_dashboard_equivalence(db):
    # Both PDF snapshot generation and API stats use get_aggregations
    agg1 = get_aggregations(db)
    res = client.get("/api/v1/stats", headers={"X-Admin-Key": ADMIN_KEY})
    assert res.status_code == 200
    agg2 = res.json()

    assert agg1["total_records"] == agg2["total_records"]
    assert agg1["total_weight_kg"] == agg2["total_weight_kg"]
    assert agg1["total_weight_g"] == agg2["total_weight_g"]


def test_t15_smtp_delivery_and_failed_recipient(db, tmp_path):
    # Run a report with a mock SMTP client
    mock_smtp = MockSMTPClient(should_fail=False)
    run = process_monthly_report(
        db,
        period="2026-01",
        recipients=["coord@qrlabhub.local"],
        smtp_client=mock_smtp,
        force_new_revision=True
    )
    assert run.status == "completed"
    assert len(mock_smtp.sent_messages) == 1
    assert "informe_2026-01" in str(mock_smtp.sent_messages[0])

    deliv = db.query(ReportDelivery).filter_by(report_run_id=run.id, recipient="coord@qrlabhub.local").first()
    assert deliv.status == "sent"

    # Test failing recipient
    fail_smtp = MockSMTPClient(should_fail=True)
    deliv_fail = send_report_email(db, run, "error@qrlabhub.local", smtp_client=fail_smtp)
    assert deliv_fail.status == "failed"
    assert deliv_fail.attempts == 1
    assert "Simulated SMTP" in deliv_fail.error_summary


def test_t16_idempotent_delivery_skips_already_sent(db):
    mock_smtp = MockSMTPClient()
    run = db.query(ReportRun).filter_by(period="2026-01").order_by(ReportRun.revision.desc()).first()

    # Re-sending to already sent recipient should do nothing
    deliv = send_report_email(db, run, "coord@qrlabhub.local", smtp_client=mock_smtp)
    assert deliv.status == "sent"
    assert len(mock_smtp.sent_messages) == 0  # No message dispatched again!


def test_t17_uncertain_state_on_smtp_drop(db):
    unc_smtp = MockSMTPClient(should_be_uncertain=True)
    run = db.query(ReportRun).filter_by(period="2026-01").order_by(ReportRun.revision.desc()).first()

    deliv = send_report_email(db, run, "drop@qrlabhub.local", smtp_client=unc_smtp)
    assert deliv.status == "uncertain"
    assert "connection drop" in deliv.error_summary


def test_t18_daily_recovery_processes_closed_months(db):
    # Reference date is 2026-03-05 -> closed months from 2026-01 are 2026-01 and 2026-02
    closed = get_closed_months("2026-01", date(2026, 3, 5))
    assert closed == ["2026-01", "2026-02"]

    mock_smtp = MockSMTPClient()
    runs = run_daily_check(db, reference_date=date(2026, 3, 5), smtp_client=mock_smtp)
    # 2026-02 will be generated and processed
    run_feb = db.query(ReportRun).filter_by(period="2026-02").first()
    assert run_feb is not None
    assert run_feb.status == "completed"

