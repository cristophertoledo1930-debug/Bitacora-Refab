"""Monthly scheduling and transport acceptance on the disposable PostgreSQL database."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from email import policy
from email.parser import BytesParser
from pathlib import Path
import json
import os
import subprocess
import sys
import socket

from aiosmtpd.controller import Controller
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from lab_hub.api.app import app
from lab_hub.config import Settings, get_settings
from lab_hub.db.models import ReportDelivery, ReportRun, WasteRecord
from lab_hub.db.session import SessionLocal
from lab_hub.jobs.monthly_report import process_monthly_report, run_daily_check, next_scheduled_at
from lab_hub.reports.mailer import send_report_email, safe_error
from lab_hub.services.aggregations import get_aggregations
from lab_hub.services.records import create_waste_record
from lab_hub.services.report_status import csrf_token
from lab_hub.services.seeds import seed_catalogs
from tests.test_f4_reports import MockSMTPClient


@pytest.fixture
def context(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "REPORT_INITIAL_MONTH", "2035-01")
    monkeypatch.setattr(settings, "REPORT_AUTO_SEND_FROM", "2035-01")
    monkeypatch.setattr(settings, "REPORT_SEND_DAY", 1)
    monkeypatch.setattr(settings, "REPORT_SEND_HOUR", 8)
    monkeypatch.setattr(settings, "REPORT_TO", "one@qrlabhub.local,two@qrlabhub.local")
    smtp = MockSMTPClient()
    with SessionLocal() as db:
        assert db.get_bind().url.database.startswith("qrlabhub_verify_")
        runs = db.query(ReportRun.id).filter(ReportRun.period.like("2035-%"))
        db.query(ReportDelivery).filter(ReportDelivery.report_run_id.in_(runs)).delete(synchronize_session=False)
        db.query(ReportRun).filter(ReportRun.period.like("2035-%")).delete(synchronize_session=False)
        db.query(WasteRecord).filter(WasteRecord.idempotency_key.like("monthly-send:%")).delete(synchronize_session=False)
        db.commit()
        yield db, settings, smtp


def instant(settings, month=2, day=1, hour=8, minute=0):
    return datetime(2035, month, day, hour, minute, tzinfo=settings.timezone)


def add_record(db, settings, source, grams="125", month=1):
    cats = seed_catalogs(db)
    ids = {field + "_id": next(iter(cats[group].values())).id for field, group in
           (("waste_type", "waste_types"), ("material", "materials"), ("machine", "machines"), ("cause", "causes"))}
    import uuid
    return create_waste_record(db, idempotency_key="monthly-send:" + uuid.uuid4().hex,
                              qr_token=None, **ids, source=source, weight_str=grams,
                              recorded_at=datetime(2035, month, 15, 12, tzinfo=settings.timezone))[0]


def test_schedule_exact_time_late_start_and_repeat(context):
    db, settings, smtp = context
    run_daily_check(db, now=instant(settings, hour=7, minute=59), smtp_client=smtp)
    assert not smtp.sent_messages
    run_daily_check(db, now=instant(settings), smtp_client=smtp)
    assert len(smtp.sent_messages) == 2
    run_daily_check(db, now=instant(settings, day=5), smtp_client=smtp)
    assert len(smtp.sent_messages) == 2


def test_missed_day_and_configured_schedule(context, monkeypatch):
    db, settings, smtp = context
    monkeypatch.setattr(settings, "REPORT_SEND_DAY", 3)
    monkeypatch.setattr(settings, "REPORT_SEND_HOUR", 10)
    run_daily_check(db, now=instant(settings, day=3, hour=9), smtp_client=smtp)
    assert not smtp.sent_messages
    run_daily_check(db, now=instant(settings, day=5, hour=9), smtp_client=smtp)
    assert len(smtp.sent_messages) == 2
    assert next_scheduled_at(instant(settings, day=5)).month == 3


@pytest.mark.parametrize("activation,expected", [("", 0), ("2035-02", 2)])
def test_activation_does_not_send_history(context, monkeypatch, activation, expected):
    db, settings, smtp = context
    monkeypatch.setattr(settings, "REPORT_AUTO_SEND_FROM", activation)
    run_daily_check(db, now=instant(settings, month=3, day=5), smtp_client=smtp)
    assert len(smtp.sent_messages) == expected
    assert db.query(ReportRun).filter_by(period="2035-01").count() == 1
    assert all("2035-02" in m["Subject"] for m in smtp.sent_messages)


def test_forms_match_dashboard_and_late_data_never_resends(context):
    db, settings, smtp = context
    add_record(db, settings, "google_forms")
    manual = add_record(db, settings, "manual", "900")
    runs = run_daily_check(db, now=instant(settings), smtp_client=smtp)
    first = runs[0]
    expected = get_aggregations(db, start_date=date(2035, 1, 1), end_date=date(2035, 1, 31), source="google_forms")
    response = TestClient(app).get("/api/v1/stats", params={"start_date": "2035-01-01", "end_date": "2035-01-31", "source": "google_forms"}, headers={"X-Admin-Key": settings.ADMIN_API_KEY})
    assert response.status_code == 200
    for key in ("total_records", "total_weight_g", "total_weight_kg", "by_material", "by_machine"):
        assert first.snapshot[key] == expected[key] == response.json()[key]
    assert Decimal(first.snapshot["total_weight_g"]) == Decimal("125")
    assert first.snapshot["report_source"] == "google_forms"
    assert all(row["source"] == "google_forms" for row in first.snapshot["records"])
    manual.weight_g = Decimal("999")
    db.commit()
    assert process_monthly_report(db, "2035-01", send_email=False).id == first.id
    add_record(db, settings, "google_forms", "50")
    second = process_monthly_report(db, "2035-01", send_email=False)
    assert second.revision == first.revision + 1
    run_daily_check(db, now=instant(settings, day=5), smtp_client=smtp)
    assert len(smtp.sent_messages) == 2
    assert not second.deliveries


def test_old_snapshot_migrates_without_resend(context):
    db, settings, smtp = context
    first = run_daily_check(db, now=instant(settings), smtp_client=smtp)[0]
    snapshot = dict(first.snapshot)
    snapshot.pop("report_source")
    first.snapshot = snapshot
    db.commit()
    second = run_daily_check(db, now=instant(settings, day=5), smtp_client=smtp)[0]
    assert second.revision == first.revision + 1
    assert len(smtp.sent_messages) == 2


def test_legacy_pending_delivery_uses_scoped_pdf(context):
    db, settings, smtp = context
    add_record(db, settings, "google_forms", "125")
    add_record(db, settings, "manual", "900")
    old = process_monthly_report(db, "2035-01", send_email=False)
    snapshot = dict(old.snapshot)
    snapshot.pop("report_source")
    snapshot["total_weight_kg"] = "1.025"
    old.snapshot = snapshot
    db.add(ReportDelivery(report_run_id=old.id, recipient="one@qrlabhub.local", status="failed", attempts=1))
    db.commit()
    latest = run_daily_check(db, now=instant(settings), smtp_client=smtp)[0]
    assert latest.revision == old.revision + 1
    assert len(smtp.sent_messages) == 2
    assert all("Masa total: 0.125 kg" in m.get_body().get_content() for m in smtp.sent_messages)
    retried = next(d for d in latest.deliveries if d.recipient.startswith("one"))
    assert retried.attempts == 2


@pytest.mark.parametrize("missing", [True, False])
def test_pdf_required(context, tmp_path, missing):
    db, settings, smtp = context
    run = process_monthly_report(db, "2035-01", send_email=False)
    path = tmp_path / "absent.pdf"
    if not missing:
        path.write_bytes(b"")
    run.pdf_path = str(path)
    db.commit()
    delivery = send_report_email(db, run, "pdf@qrlabhub.local", smtp)
    assert delivery.status == "failed"
    assert "PDF obligatorio" in delivery.error_summary
    assert not smtp.sent_messages


def test_failed_recipient_retry_keeps_original_revision_and_limit(context):
    db, settings, smtp = context
    class SelectiveSMTP:
        def send_message(self, message):
            if message["To"].startswith("two"):
                raise ConnectionRefusedError("synthetic failure")
            smtp.sent_messages.append(message)
    first = run_daily_check(db, now=instant(settings), smtp_client=SelectiveSMTP())[0]
    failed = next(d for d in first.deliveries if d.status == "failed")
    failed.next_attempt_at = None
    db.commit()
    add_record(db, settings, "google_forms")
    run_daily_check(db, now=instant(settings, day=5), smtp_client=smtp)
    assert len(smtp.sent_messages) == 2
    db.refresh(failed)
    assert failed.status == "sent" and failed.attempts == 2
    assert failed.report_run_id == first.id
    run_daily_check(db, now=instant(settings, day=6), smtp_client=smtp)
    assert len(smtp.sent_messages) == 2


def test_uncertain_blocks_all_revisions_and_manual_csrf(context):
    db, settings, smtp = context
    run = run_daily_check(db, now=instant(settings), smtp_client=MockSMTPClient(should_be_uncertain=True))[0]
    delivery = run.deliveries[0]
    add_record(db, settings, "google_forms")
    run_daily_check(db, now=instant(settings, day=5), smtp_client=smtp)
    assert not smtp.sent_messages
    client = TestClient(app)
    url = f"/reports/deliveries/{delivery.id}/confirm"
    assert client.post(url, data={"csrf": csrf_token(delivery.id)}).status_code == 401
    headers = {"X-Admin-Key": settings.ADMIN_API_KEY}
    assert client.post(url, data={"csrf": "bad"}, headers=headers).status_code == 403
    assert client.post(url, data={"csrf": csrf_token(delivery.id, 1)}, headers=headers).status_code == 403
    assert client.post(url, data={"csrf": csrf_token(delivery.id)}, headers=headers, follow_redirects=False).status_code == 303
    db.refresh(delivery)
    assert delivery.status == "sent"
    assert client.post(url, data={"csrf": csrf_token(delivery.id)}, headers=headers).status_code == 409


def test_disabled_email_and_status_visible(context):
    db, settings, smtp = context
    run_daily_check(db, now=instant(settings))
    assert all(d.attempts == 0 and d.status == "pending" for d in db.query(ReportDelivery).join(ReportRun).filter(ReportRun.period == "2035-01"))
    client = TestClient(app)
    headers = {"X-Admin-Key": settings.ADMIN_API_KEY}
    response = client.get("/reports", headers=headers)
    assert "EMAIL_ENABLED=false" in response.text
    state = client.get("/api/v1/reports/monthly-status", headers=headers).json()
    assert any(p["period"] == "2035-01" and p["status"] == "pending" for p in state["periods"])
    from lab_hub.dashboard.data import catalog_and_mail
    _, chip = catalog_and_mail(db)
    assert chip["text"] == "Informe 2035-01: pendiente"
    assert "EMAIL_ENABLED" not in chip["text"]


@pytest.mark.parametrize("values", [{"REPORT_SEND_DAY": 0}, {"REPORT_SEND_DAY": 29},
    {"REPORT_SEND_HOUR": 24}, {"REPORT_SOURCE": "bad"}, {"REPORT_AUTO_SEND_FROM": "2035-13"},
    {"SMTP_USERNAME": "synthetic", "SMTP_TLS": False, "SMTP_SSL": False}])
def test_invalid_config(values):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


@pytest.mark.parametrize("ssl_mode", [True, False])
def test_smtp_ssl_and_redaction(context, monkeypatch, ssl_mode):
    db, settings, smtp = context
    monkeypatch.setattr(settings, "EMAIL_ENABLED", True)
    monkeypatch.setattr(settings, "SMTP_SSL", ssl_mode)
    monkeypatch.setattr(settings, "SMTP_TLS", not ssl_mode)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "synthetic-user")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "synthetic-password")
    class SSLClient:
        def __init__(self, host, port, **kwargs):
            assert ("context" in kwargs) == ssl_mode
            self.encrypted = ssl_mode
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def login(self, username, password):
            assert username == "synthetic-user"
            assert self.encrypted
        def starttls(self, context):
            assert context is not None
            self.encrypted = True
        def send_message(self, message):
            smtp.sent_messages.append(message)
    monkeypatch.setattr("smtplib.SMTP_SSL", SSLClient)
    monkeypatch.setattr("smtplib.SMTP", SSLClient)
    run_daily_check(db, now=instant(settings))
    assert len(smtp.sent_messages) == 2
    assert "synthetic-password" not in safe_error(Exception("synthetic-password recipient@example.test"))
    assert "recipient@example.test" not in safe_error(Exception("recipient@example.test"))


@pytest.mark.parametrize("month", [1, 3, 5, 10])
def test_empty_february_year_and_chile_dst(context, monkeypatch, month):
    db, settings, smtp = context
    local = instant(settings, month=month, day=5)
    previous = local.date().replace(day=1) - timedelta(days=1)
    period = previous.strftime("%Y-%m")
    monkeypatch.setattr(settings, "REPORT_INITIAL_MONTH", period)
    monkeypatch.setattr(settings, "REPORT_AUTO_SEND_FROM", period)
    runs = run_daily_check(db, now=local, smtp_client=smtp)
    assert runs[0].period == period
    assert runs[0].snapshot["end_date"] == previous.isoformat()
    assert len(smtp.sent_messages) == 2
    assert "No hubo respuestas" in smtp.sent_messages[0].get_body().get_content()


def test_local_smtp_two_processes_pdf_and_no_personal_data(context, monkeypatch):
    db, settings, smtp = context
    add_record(db, settings, "google_forms", "125")
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
    env = os.environ.copy()
    env.update(REPORT_INITIAL_MONTH="2035-01", REPORT_AUTO_SEND_FROM="2035-01", REPORT_SOURCE="google_forms",
               REPORT_TO="capture@qrlabhub.local", LOCAL_SMTP_ENABLED="true", EMAIL_ENABLED="false",
               SMTP_HOST="127.0.0.1", SMTP_PORT=str(port), SMTP_USERNAME="", SMTP_PASSWORD="", SMTP_TLS="false", SMTP_SSL="false")
    code = "from datetime import datetime; from lab_hub.config import get_settings; from lab_hub.db.session import SessionLocal; from lab_hub.jobs.monthly_report import run_daily_check; db=SessionLocal(); run_daily_check(db, now=datetime(2035,2,5,12,tzinfo=get_settings().timezone)); db.close()"
    try:
        processes = [subprocess.Popen([sys.executable, "-c", code], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        for process in processes:
            _, error = process.communicate(timeout=60)
            assert process.returncode == 0, error.decode(errors="replace")
    finally:
        controller.stop()
    assert len(messages) == 1
    message = BytesParser(policy=policy.default).parsebytes(messages[0])
    assert "Formularios" in message["Subject"]
    assert "0.125 kg" in message.get_body().get_content()
    attachment = next(message.iter_attachments()).get_payload(decode=True)
    assert attachment.startswith(b"%PDF")
    run = db.query(ReportRun).filter_by(period="2035-01").one()
    assert run.snapshot["total_records"] == 1
    assert "@" not in json.dumps(run.snapshot)
    evidence = Path("docs/evidencias/monthly_send")
    evidence.mkdir(exist_ok=True)
    (evidence / "formularios_sintetico.pdf").write_bytes(attachment)
    (evidence / "correo_sintetico.eml").write_bytes(messages[0])


def test_smtp_1025_capture(context, monkeypatch):
    db, settings, smtp = context
    messages = []
    class Inbox:
        async def handle_DATA(self, server, session, envelope):
            messages.append(envelope.original_content)
            return "250 Stored"
    controller = Controller(Inbox(), hostname="127.0.0.1", port=1025)
    existing = set(Path("storage/mail").glob("*.eml"))
    try:
        controller.start()
    except OSError:
        # A running local supervisor already owns 1025 and captures in storage/mail.
        controller = None
    monkeypatch.setattr(settings, "LOCAL_SMTP_ENABLED", True)
    monkeypatch.setattr(settings, "SMTP_HOST", "127.0.0.1")
    monkeypatch.setattr(settings, "SMTP_PORT", 1025)
    monkeypatch.setattr(settings, "REPORT_TO", "acceptance@qrlabhub.local")
    try:
        run = run_daily_check(db, now=instant(settings))[0]
        assert run.deliveries[0].status == "sent"
        message_id = run.deliveries[0].message_id
        if controller is None:
            messages.extend(p.read_bytes() for p in set(Path("storage/mail").glob("*.eml")) - existing)
        captured = [BytesParser(policy=policy.default).parsebytes(raw) for raw in messages]
        message = next(m for m in captured if m["Message-ID"] == message_id)
        assert next(message.iter_attachments()).get_payload(decode=True).startswith(b"%PDF")
        assert "No hubo respuestas" in message.get_body().get_content()
    finally:
        if controller:
            controller.stop()


def test_retry_limit_survives_new_revision(context):
    db, settings, smtp = context
    run = run_daily_check(db, now=instant(settings), smtp_client=MockSMTPClient(should_fail=True))[0]
    for delivery in run.deliveries:
        delivery.attempts = 3
        delivery.next_attempt_at = None
    db.commit()
    add_record(db, settings, "google_forms")
    run_daily_check(db, now=instant(settings, day=5), smtp_client=smtp)
    assert not smtp.sent_messages
    assert all(d.attempts == 3 for d in run.deliveries)


def test_previous_month_comparison_uses_filtered_snapshot(context):
    db, settings, smtp = context
    add_record(db, settings, "google_forms", "125", month=1)
    add_record(db, settings, "manual", "900", month=1)
    add_record(db, settings, "google_forms", "250", month=2)
    runs = run_daily_check(db, now=instant(settings, month=3), smtp_client=smtp)
    february = next(run for run in runs if run.period == "2035-02")
    assert february.snapshot["previous_month"]["total_weight_kg"] == "0.125"
    assert february.snapshot["previous_month"]["total_records"] == 1
    message = next(m for m in smtp.sent_messages if "2035-02" in m["Subject"])
    assert "+0.125 kg" in message.get_body().get_content()


@pytest.mark.parametrize("source,expected", [("", 2), ("manual", 1), ("esp32", 0)])
def test_alternative_source_and_all_sources_stay_consistent(context, monkeypatch, source, expected):
    db, settings, smtp = context
    add_record(db, settings, "google_forms")
    add_record(db, settings, "manual")
    monkeypatch.setattr(settings, "REPORT_SOURCE", source)
    run = process_monthly_report(db, "2035-01", send_email=False)
    assert run.snapshot["report_source"] == source
    assert run.snapshot["total_records"] == len(run.snapshot["records"]) == expected
    assert process_monthly_report(db, "2035-01", send_email=False).id == run.id


def test_login_without_tls_rejected_before_connect(context, monkeypatch):
    db, settings, smtp = context
    monkeypatch.setattr(settings, "EMAIL_ENABLED", True)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "synthetic")
    monkeypatch.setattr(settings, "SMTP_TLS", False)
    monkeypatch.setattr(settings, "SMTP_SSL", False)
    def forbidden(*args, **kwargs):
        raise AssertionError("Must reject configuration before connecting")
    monkeypatch.setattr("smtplib.SMTP", forbidden)
    run = run_daily_check(db, now=instant(settings))[0]
    assert all(d.status == "failed" and "requiere TLS" in d.error_summary for d in run.deliveries)


def test_manual_resend_requires_csrf_and_sends_once(context, monkeypatch):
    db, settings, smtp = context
    run = run_daily_check(db, now=instant(settings), smtp_client=MockSMTPClient(should_be_uncertain=True))[0]
    delivery = run.deliveries[0]
    monkeypatch.setattr("lab_hub.reports.mailer.send_report_email",
                        lambda db, run, recipient: send_report_email(db, run, recipient, smtp))
    client = TestClient(app)
    url = f"/reports/deliveries/{delivery.id}/resend"
    headers = {"X-Admin-Key": settings.ADMIN_API_KEY}
    data = {"csrf": csrf_token(delivery.id)}
    assert client.post(url, data=data, headers={**headers, "Origin": "https://other.test"}).status_code == 403
    assert client.post(url, data=data, headers=headers, follow_redirects=False).status_code == 303
    assert len(smtp.sent_messages) == 1
    assert client.post(url, data=data, headers=headers).status_code == 409


def test_cli_errors_nonzero_and_no_secrets(context, monkeypatch, caplog):
    from lab_hub.jobs import monthly_report
    def fail(*args, **kwargs):
        raise RuntimeError("synthetic-password")
    monkeypatch.setattr(monthly_report, "run_daily_check", fail)
    assert monthly_report.main() == 1
    assert "synthetic-password" not in caplog.text


def test_cli_entrypoint_uses_isolated_database(context):
    env = os.environ.copy()
    env.update(REPORT_INITIAL_MONTH="2035-01", REPORT_AUTO_SEND_FROM="", EMAIL_ENABLED="false", LOCAL_SMTP_ENABLED="false")
    result = subprocess.run([sys.executable, "-m", "lab_hub.jobs.monthly_report"], env=env, capture_output=True, timeout=30)
    assert result.returncode == 0
    assert b'"auto_send_configured": false' in result.stderr


def test_config_validation_hides_password():
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, SMTP_USERNAME="synthetic", SMTP_PASSWORD="never-print-this",
                 SMTP_TLS=False, SMTP_SSL=False, LOCAL_SMTP_ENABLED=False)
    assert "never-print-this" not in str(error.value)


def test_ui_browser_synthetic_status(context):
    from playwright.sync_api import sync_playwright
    from urllib.parse import urlsplit
    db, settings, smtp = context
    run_daily_check(db, now=instant(settings), smtp_client=MockSMTPClient(should_be_uncertain=True))
    client = TestClient(app, base_url="http://monthly.test")
    output = Path("docs/evidencias/monthly_send")
    output.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(extra_http_headers={"X-Admin-Key": settings.ADMIN_API_KEY})
        def proxy(route):
            request = route.request
            parsed = urlsplit(request.url)
            response = client.request(request.method, parsed.path + ("?" + parsed.query if parsed.query else ""),
                                      content=request.post_data_buffer, headers=request.headers)
            headers = {k: v for k, v in response.headers.items() if k not in {"content-encoding", "content-length"}}
            route.fulfill(status=response.status_code, headers=headers, body=response.content)
        page.route("http://monthly.test/**", proxy)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        for width, device in ((1440, "desktop"), (390, "mobile")):
            page.set_viewport_size({"width": width, "height": 1000})
            for path, label in (("/reports", "reports"), ("/dashboard/", "dashboard")):
                page.goto("http://monthly.test" + path, wait_until="networkidle")
                if label == "dashboard":
                    page.wait_for_function("document.querySelector('#system-chips')?.textContent.includes('Correo') || document.querySelector('#system-chips')?.textContent.includes('Informe')")
                else:
                    assert page.get_by_role("button", name="Confirmar enviado").count() > 0
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
                page.screenshot(path=str(output / f"{label}-{device}.png"), full_page=True)
        browser.close()
        assert not errors
