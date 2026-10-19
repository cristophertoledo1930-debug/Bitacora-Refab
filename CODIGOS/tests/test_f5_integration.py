import os
import uuid
import concurrent.futures
from decimal import Decimal
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from lab_hub.api.app import app
from lab_hub.db.session import SessionLocal
from lab_hub.db.models import WasteRecord, ReportRun, ReportDelivery
from lab_hub.services.seeds import seed_catalogs
from lab_hub.jobs.monthly_report import process_monthly_report
from tests.test_f4_reports import MockSMTPClient

client = TestClient(app)
ADMIN_KEY = "labhub-dev-admin-key-2026"


def test_t22_end_to_end_journey():
    """
    Scenario T22: Full journey:
    1. Resolve QR and load HTML form
    2. Submit form via HTTP POST
    3. Verify record saved in PostgreSQL
    4. Query admin stats and verify metrics increased
    5. Generate monthly report PDF from snapshot
    6. Deliver via SMTP with PDF attachment
    7. Download PDF from admin API
    """
    db = SessionLocal()
    seed_catalogs(db)

    # 1. Resolve QR token
    res_qr = client.get("/r/token-laser-01")
    assert res_qr.status_code == 200
    assert "Estación Cortadora Láser 1" in res_qr.text

    # 2. Submit form
    cats = client.get("/api/v1/catalogs").json()
    wt_id = cats["waste_types"][0]["id"]
    mat_id = cats["materials"][0]["id"]
    mach_id = cats["machines"][0]["id"]
    cause_id = cats["causes"][0]["id"]

    idemp_key = f"t22-key-{uuid.uuid4()}"
    res_post = client.post(
        "/r/token-laser-01",
        data={
            "waste_type_id": wt_id,
            "material_id": mat_id,
            "machine_id": mach_id,
            "cause_id": cause_id,
            "weight": "0.450",
            "unit": "kg",
            "idempotency_key": idemp_key
        }
    )
    assert res_post.status_code == 200
    assert "Registro Guardado" in res_post.text
    assert "450.000 g" in res_post.text

    # 3. Verify record in PostgreSQL
    saved = db.query(WasteRecord).filter_by(idempotency_key=idemp_key).first()
    assert saved is not None
    assert saved.weight_g == Decimal("450.000")

    # 4. Query admin stats
    res_stats = client.get("/api/v1/stats", headers={"X-Admin-Key": ADMIN_KEY})
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["total_records"] >= 1
    assert Decimal(stats["total_weight_g"]) >= Decimal("450.000")

    # 5 & 6. Generate monthly report PDF and deliver
    mock_smtp = MockSMTPClient()
    current_period = datetime.now(timezone.utc).strftime("%Y-%m")
    run = process_monthly_report(
        db,
        period=current_period,
        recipients=["coordinador@qrlabhub.local"],
        smtp_client=mock_smtp,
        force_new_revision=True
    )
    assert run.status == "completed"
    assert os.path.exists(run.pdf_path)
    assert len(mock_smtp.sent_messages) == 1

    # 7. Download PDF via API
    res_pdf = client.get(f"/api/v1/reports/{run.id}/pdf", headers={"X-Admin-Key": ADMIN_KEY})
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 1000

    db.close()


def test_concurrent_idempotency_race_condition():
    """
    Simulates concurrent requests hitting POST /api/v1/records at the same instant
    with the exact same Idempotency-Key.
    Expected: exactly one record created in database; all callers receive successful response.
    """
    cats = client.get("/api/v1/catalogs").json()
    wt_id = cats["waste_types"][0]["id"]
    mat_id = cats["materials"][0]["id"]
    mach_id = cats["machines"][0]["id"]
    cause_id = cats["causes"][0]["id"]

    shared_key = f"concurrent-race-{uuid.uuid4()}"
    payload = {
        "waste_type_id": wt_id,
        "material_id": mat_id,
        "machine_id": mach_id,
        "cause_id": cause_id,
        "weight": "150.0",
        "unit": "g"
    }

    def do_post():
        c = TestClient(app)
        return c.post("/api/v1/records", headers={"Idempotency-Key": shared_key}, json=payload)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(do_post) for _ in range(4)]
        responses = [f.result() for f in futures]

    status_codes = [r.status_code for r in responses]
    assert all(code in (200, 201) for code in status_codes)

    # Verify returned ID is identical across all responses
    returned_ids = {r.json()["id"] for r in responses}
    assert len(returned_ids) == 1

    # Verify exactly ONE row exists in database
    db = SessionLocal()
    count = db.query(WasteRecord).filter_by(idempotency_key=shared_key).count()
    db.close()
    assert count == 1

