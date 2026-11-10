from datetime import date
from decimal import Decimal

from sqlalchemy import event

from lab_hub.db.session import SessionLocal, engine
from lab_hub.services.aggregations import get_aggregations, previous_period
from tests.test_f3_dashboard import clean_control_fixture  # noqa: F401


def test_previous_period_calendar_days():
    assert previous_period(date(2026, 3, 1), date(2026, 3, 9)) == (date(2026, 2, 20), date(2026, 2, 28))


def test_one_statement_for_five_years_and_previous_totals(clean_control_fixture):  # noqa: F811
    statements = []
    def count(conn, cursor, statement, parameters, context, many):
        statements.append(statement)
    event.listen(engine, "before_cursor_execute", count)
    try:
        with SessionLocal() as db:
            result = get_aggregations(db, start_date=date(2022, 1, 1), end_date=date(2026, 12, 31))
        assert len(statements) == 1
        assert len(result["monthly_series"]) == 60
        assert result["total_records"] == 3
        assert Decimal(result["total_weight_g"]) == 1500
    finally:
        event.remove(engine, "before_cursor_execute", count)
    with SessionLocal() as db:
        result = get_aggregations(db, start_date=date(2026, 2, 1), end_date=date(2026, 2, 28))
    assert result["total_records"] == 1
    # Jan 4–31 is the immediately preceding 28-day period.
    assert result["previous_period"]["total_records"] == 2
    assert Decimal(result["previous_period"]["total_weight_g"]) == 500
