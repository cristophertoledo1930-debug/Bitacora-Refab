from datetime import date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from lab_hub.api.app import app
from lab_hub.config import get_settings
from lab_hub.db.models import WasteRecord
from lab_hub.db.session import SessionLocal
from lab_hub.jobs.weekly_report import update_week, week_key
from lab_hub.services.seeds import seed_catalogs
from lab_hub.services.records import create_waste_record


def test_week_boundaries():
    assert week_key(date(2026, 11, 8)) == "2026W45"
    assert week_key(date(2026, 11, 9)) == "2026W46"
    assert week_key(date(2027, 1, 1)) == "2026W53"


def test_weekly_versions_include_all_sources_and_deletions():
    with SessionLocal() as db:
        cats = seed_catalogs(db)
        ids = {field + "_id": next(iter(cats[group].values())).id for field, group in
               (("waste_type", "waste_types"), ("material", "materials"), ("machine", "machines"), ("cause", "causes"))}
        period = "2030W01"
        first = update_week(db, period)
        assert first.snapshot["total_records"] == 0
        assert update_week(db, period).id == first.id
        for source in ("manual", "google_forms"):
            create_waste_record(db, idempotency_key="weekly-test-" + source, qr_token=None,
                                **ids, source=source, weight_str="12.5",
                                recorded_at=datetime(2030, 1, 2, 12, tzinfo=get_settings().timezone))
        second = update_week(db, period)
        assert second.revision == first.revision + 1
        assert second.snapshot["total_records"] == 2
        assert Decimal(second.snapshot["total_weight_g"]) == Decimal("25")
        assert len(second.snapshot["records"]) == 2
        assert update_week(db, period).id == second.id
        db.query(WasteRecord).filter(WasteRecord.idempotency_key.like("weekly-test-%")).delete(synchronize_session=False)
        db.commit()
        third = update_week(db, period)
        assert third.snapshot["total_records"] == 0
        assert third.revision == second.revision + 1
        client = TestClient(app)
        response = client.get("/reports", headers={"X-Admin-Key": get_settings().ADMIN_API_KEY})
        assert response.status_code == 200
        assert response.headers["refresh"] == "15"
        assert "2030W01" in response.text
        assert client.get(f"/api/v1/reports/{second.id}/pdf", headers={"X-Admin-Key": get_settings().ADMIN_API_KEY}).status_code == 200
