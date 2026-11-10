from datetime import datetime
from decimal import Decimal

from lab_hub.config import get_settings
from lab_hub.db.models import WasteRecord
from lab_hub.db.session import SessionLocal
from lab_hub.jobs.monthly_report import process_monthly_report, refresh_monthly_reports
from lab_hub.services.records import create_waste_record
from lab_hub.services.seeds import seed_catalogs


def test_monthly_refresh_updates_existing_pdf_without_email(monkeypatch):
    def unexpected_email(*args, **kwargs):
        raise AssertionError("Automatic refresh must not send email")
    monkeypatch.setattr("lab_hub.jobs.monthly_report.send_report_email", unexpected_email)
    with SessionLocal() as db:
        cats = seed_catalogs(db)
        ids = {field + "_id": next(iter(cats[group].values())).id for field, group in
               (("waste_type", "waste_types"), ("material", "materials"), ("machine", "machines"), ("cause", "causes"))}
        first = process_monthly_report(db, "2031-02", send_email=False)
        assert first.snapshot["total_records"] == 0
        assert process_monthly_report(db, "2031-02", send_email=False).id == first.id
        record, _ = create_waste_record(db, idempotency_key="monthly-refresh-synthetic", qr_token=None,
                                        **ids, source="google_forms", weight_str="42.5",
                                        recorded_at=datetime(2031, 2, 28, 23, 59, tzinfo=get_settings().timezone))
        runs = refresh_monthly_reports(db)
        second = next(run for run in runs if run.period == "2031-02")
        assert second.revision == first.revision + 1
        assert second.snapshot["total_records"] == 1
        assert Decimal(second.snapshot["total_weight_g"]) == Decimal("42.5")
        assert second.pdf_path != first.pdf_path
        assert not second.deliveries
        assert process_monthly_report(db, "2031-02", send_email=False).id == second.id
        db.delete(db.get(WasteRecord, record.id))
        db.commit()
        third = process_monthly_report(db, "2031-02", send_email=False)
        assert third.revision == second.revision + 1
        assert third.snapshot["total_records"] == 0
