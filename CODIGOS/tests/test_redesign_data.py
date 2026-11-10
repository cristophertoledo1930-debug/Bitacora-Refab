from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import event

from lab_hub.dashboard.data import (export_csv, fmt_count, fmt_delta, fmt_mass, fmt_percent,
                                   load_snapshot, parse_filters, record_rows, sheets_state)
from lab_hub.db.models import Cause, WasteRecord
from lab_hub.db.session import SessionLocal, engine
from tests.test_f3_dashboard import clean_control_fixture  # noqa: F401


@pytest.mark.parametrize("grams,expected", [(0, "0 g"), (5, "5 g"), (Decimal("0.5"), "0,5 g"),
    (1500, "1,50 kg"), (1500000, "1.500,0 kg"), (1234567000, "1.234.567,0 kg"),
    (10000, "10,0 kg"), (380, "0,38 kg"), (10, "0,01 kg"), (None, "0 g")])
def test_mass(grams, expected):
    assert fmt_mass(grams) == expected


def test_count_percent_delta():
    assert fmt_count(1234567) == "1.234.567"
    assert fmt_percent(Decimal("0.4")) == "0,4 %"
    assert fmt_percent(41) == "41 %"
    assert fmt_delta(10, 0, "oct 2026") == "— · Sin datos del periodo anterior"
    assert fmt_delta(15, 10, "oct 2026") == "▲ 50 % vs oct 2026"


def test_filters_clamp_and_validate_before_query():
    today = date(2026, 11, 9)
    assert parse_filters(today=today)["start_date"] == "2026-11-01"
    assert parse_filters("custom", "2026-10-01", "2027-01-01", today=today)["end_date"] == "2026-11-09"
    for start, end in (("bad", None), ("2026-12-01", None), ("2026-11-03", "2026-11-01")):
        with pytest.raises(ValueError):
            parse_filters("custom", start, end, today=today)


def test_missing_corrupt_sheets(tmp_path):
    path = tmp_path / "status.json"
    assert sheets_state(path)["text"] == "Sheets: sin datos"
    path.write_text("[]", encoding="utf-8")
    assert sheets_state(path)["state"] == "pending"


def test_snapshot_paging_export_and_catalog_refresh(clean_control_fixture):  # noqa: F811
    filters = parse_filters("all")
    statements = []
    def count(*args):
        statements.append(args[2])
    event.listen(engine, "before_cursor_execute", count)
    try:
        with SessionLocal() as db:
            snapshot = load_snapshot(db, filters)
            rows = list(record_rows(db, filters))
        assert len(statements) <= 4
        assert snapshot["agg"]["total_records"] == 3
        assert len(rows) == 3
    finally:
        event.remove(engine, "before_cursor_execute", count)
    with SessionLocal() as db:
        seed = db.query(WasteRecord).first()
        for i in range(60):
            db.add(WasteRecord(waste_type_id=seed.waste_type_id, material_id=seed.material_id,
                machine_id=seed.machine_id, cause_id=seed.cause_id, weight_g=1,
                recorded_at=seed.recorded_at, source="api", idempotency_key=f"paging-{i}", payload_hash="synthetic"))
        cause = Cause(code="redesign-new", name="Causa recién creada")
        db.add(cause)
        db.commit()
        cause_id = str(cause.id)
    with SessionLocal() as db:
        assert len(list(record_rows(db, filters, page=1))) == 25
        assert len(export_csv(db, filters).splitlines()) == 64
        assert len(export_csv(db, {**filters, "source": "api"}).splitlines()) == 61
        snapshot = load_snapshot(db, filters)
        assert any(r["value"] == cause_id for r in snapshot["options"]["cause_id"])
        assert any(r["value"] == "api" for r in snapshot["options"]["source"])
    with SessionLocal() as db:
        db.query(Cause).filter(Cause.id == cause_id).update({"is_active": False})
        db.commit()
    with SessionLocal() as db:
        snapshot = load_snapshot(db, filters)
        assert not any(r["value"] == cause_id for r in snapshot["options"]["cause_id"])
