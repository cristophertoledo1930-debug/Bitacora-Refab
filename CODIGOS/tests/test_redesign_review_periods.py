from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from lab_hub.dashboard.components import kpis
from lab_hub.dashboard.data import load_snapshot, parse_filters
from lab_hub.db.models import WasteRecord
from lab_hub.db.session import SessionLocal
from tests.test_f3_dashboard import clean_control_fixture  # noqa: F401


@pytest.mark.parametrize("preset,start,end,label", [
    ("month", "2026-10-01", "2026-10-09", "oct 2026"),
    ("previous", "2026-09-01", "2026-09-30", "sep 2026"),
    ("three", "2026-06-01", "2026-08-09", "jun–ago 2026"),
    ("year", "2024-12-01", "2025-11-09", "dic 2024–nov 2025"),
    ("custom", "2026-10-23", "2026-10-31", "23-10-2026 – 31-10-2026"),
    ("all", None, None, "periodo anterior"),
])
def test_review_calendar_comparisons(preset, start, end, label):
    filters = parse_filters(preset, "2026-11-01", "2026-11-09", today=date(2026, 11, 9))
    assert filters["comparison_start_date"] == start
    assert filters["comparison_end_date"] == end
    assert filters["comparison_label"] == label


@pytest.mark.parametrize("today,end", [(date(2026, 3, 31), "2026-02-28"), (date(2024, 3, 31), "2024-02-29")])
def test_previous_month_shorter_and_leap_year(today, end):
    filters = parse_filters("month", today=today)
    assert filters["comparison_start_date"] == end[:8] + "01"
    assert filters["comparison_end_date"] == end


def test_january_compares_with_previous_december():
    filters = parse_filters("previous", today=date(2026, 2, 9))
    assert (filters["comparison_start_date"], filters["comparison_end_date"]) == ("2025-12-01", "2025-12-31")


def test_calendar_query_and_rendered_delta(clean_control_fixture):  # noqa: F811
    with SessionLocal() as db:
        seed = db.query(WasteRecord).first()
        db.add(WasteRecord(**{key: getattr(seed, key) for key in ("waste_type_id", "material_id", "machine_id", "cause_id")},
            weight_g=100, recorded_at=datetime(2026, 1, 1, 15, tzinfo=timezone.utc),
            idempotency_key="review-calendar", payload_hash="synthetic"))
        db.commit()
    filters = parse_filters("month", today=date(2026, 2, 10))
    with SessionLocal() as db:
        snapshot = load_snapshot(db, filters)
    assert Decimal(snapshot["agg"]["previous_period"]["total_weight_g"]) == 100
    assert snapshot["agg"]["previous_period"]["total_records"] == 1
    cards = kpis(snapshot["agg"]).children
    assert cards[0].children[2].children == "▲ 900 % vs ene 2026"
