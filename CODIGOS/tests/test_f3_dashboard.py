import uuid
from decimal import Decimal
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo
import pytest
from fastapi.testclient import TestClient
from lab_hub.api.app import app
from lab_hub.db.session import SessionLocal
from lab_hub.db.models import WasteRecord, WasteType, Material, Machine, Cause
from lab_hub.services.seeds import seed_catalogs
from lab_hub.services.aggregations import get_aggregations, get_month_utc_range
from lab_hub.dashboard.app import update_dashboard

client = TestClient(app)
ADMIN_KEY = "labhub-dev-admin-key-2026"
SANTIAGO_TZ = ZoneInfo("America/Santiago")


@pytest.fixture
def clean_control_fixture():
    """Sets up the exact control fixture specified in docs/PRUEBAS.md"""
    db = SessionLocal()
    seed_catalogs(db)

    # Clean existing records for precise control fixture
    db.query(WasteRecord).delete()
    db.commit()

    cats = seed_catalogs(db)
    wt_resin = cats["waste_types"]["resin"]
    wt_laser = cats["waste_types"]["laser_cut"]
    mat_photo = cats["materials"]["photopolymer"]
    mat_acrylic = cats["materials"]["acrylic"]
    mach_sla = cats["machines"]["sla_printer_1"]
    mach_laser = cats["machines"]["laser_cutter_1"]
    cause_supp = cats["causes"]["support_material"]
    cause_margin = cats["causes"]["cut_margin"]

    # Enero: 2 entradas de resina de 125 g y 375 g
    # 2026-01-15 12:00:00 Santiago (UTC-3)
    dt_jan = datetime(2026, 1, 15, 15, 0, 0, tzinfo=timezone.utc)
    r1 = WasteRecord(
        waste_type_id=wt_resin.id,
        material_id=mat_photo.id,
        machine_id=mach_sla.id,
        cause_id=cause_supp.id,
        weight_g=Decimal("125.000"),
        recorded_at=dt_jan,
        idempotency_key="fixture-jan-1",
        payload_hash="hash-jan-1"
    )
    r2 = WasteRecord(
        waste_type_id=wt_resin.id,
        material_id=mat_photo.id,
        machine_id=mach_sla.id,
        cause_id=cause_supp.id,
        weight_g=Decimal("375.000"),
        recorded_at=dt_jan,
        idempotency_key="fixture-jan-2",
        payload_hash="hash-jan-2"
    )

    # Febrero: 1 retazo láser de 1000 g
    dt_feb = datetime(2026, 2, 10, 15, 0, 0, tzinfo=timezone.utc)
    r3 = WasteRecord(
        waste_type_id=wt_laser.id,
        material_id=mat_acrylic.id,
        machine_id=mach_laser.id,
        cause_id=cause_margin.id,
        weight_g=Decimal("1000.000"),
        recorded_at=dt_feb,
        idempotency_key="fixture-feb-1",
        payload_hash="hash-feb-1"
    )

    db.add_all([r1, r2, r3])
    db.commit()
    db.close()


def test_t09_synthetic_control_fixture(clean_control_fixture):
    """
    PRUEBAS.md fixture:
    Enero: 2 registros y 0.500 kg
    Febrero: 1 registro y 1.000 kg
    Marzo vacío: 0 registros y 0 kg
    Total: 3 registros y 1.500 kg
    """
    db = SessionLocal()
    agg = get_aggregations(db)
    db.close()

    assert agg["total_records"] == 3
    assert Decimal(agg["total_weight_g"]) == Decimal("1500.000")
    assert Decimal(agg["total_weight_kg"]) == Decimal("1.500")

    # Verify series contains months
    series_map = {x["period"]: x for x in agg["monthly_series"]}
    assert "2026-01" in series_map
    assert series_map["2026-01"]["count"] == 2
    assert Decimal(series_map["2026-01"]["total_weight_kg"]) == Decimal("0.500")

    assert "2026-02" in series_map
    assert series_map["2026-02"]["count"] == 1
    assert Decimal(series_map["2026-02"]["total_weight_kg"]) == Decimal("1.000")

    if "2026-03" in series_map:
        assert series_map["2026-03"]["count"] == 0
        assert Decimal(series_map["2026-03"]["total_weight_kg"]) == Decimal("0.000")


def test_t11_empty_month_and_year_labels(clean_control_fixture):
    db = SessionLocal()
    agg = get_aggregations(db)
    db.close()

    for s in agg["monthly_series"]:
        # Verify year is present in label
        assert any(str(yr) in s["label"] for yr in range(2020, 2030))
        # Ensure count is int and weight is valid
        assert isinstance(s["count"], int)
        assert Decimal(s["total_weight_kg"]) >= Decimal("0")


def test_t12_month_boundaries_and_santiago_dst():
    # Chile DST transition test: midnight Santiago crossing
    start_utc, end_utc = get_month_utc_range(2026, 4, SANTIAGO_TZ)
    # Check start is exactly April 1st 00:00:00 local time
    start_local = start_utc.astimezone(SANTIAGO_TZ)
    assert start_local.year == 2026 and start_local.month == 4 and start_local.day == 1
    assert start_local.hour == 0 and start_local.minute == 0

    end_local = end_utc.astimezone(SANTIAGO_TZ)
    assert end_local.year == 2026 and end_local.month == 5 and end_local.day == 1
    assert end_local.hour == 0 and end_local.minute == 0


def test_t19_admin_protection_and_public_qr():
    # 1. Without credentials -> 401 Unauthorized
    res1 = client.get("/api/v1/stats")
    assert res1.status_code == 401

    res2 = client.get("/api/v1/records")
    assert res2.status_code == 401

    # 2. With header X-Admin-Key -> 200 OK
    res3 = client.get("/api/v1/stats", headers={"X-Admin-Key": ADMIN_KEY})
    assert res3.status_code == 200
    assert "total_records" in res3.json()

    # 3. With cookie admin_session -> 200 OK
    client.cookies.set("admin_session", ADMIN_KEY)
    res4 = client.get("/api/v1/records")
    assert res4.status_code == 200
    assert "items" in res4.json()
    client.cookies.clear()

    # 4. Public QR form works without session
    res_qr = client.get("/r/token-laser-01")
    assert res_qr.status_code == 200


def test_t20_dashboard_callback_renders_cleanly(clean_control_fixture):
    # Call Dash callback directly to verify it returns figure objects and table data
    results = update_dashboard(0, "kg", "ALL", "ALL", "ALL", "ALL")
    tot_rec, tot_mass, m_rec, top_cat, fig_type, fig_cause, fig_monthly, table_data, last_upd = results

    assert "3" in tot_rec
    assert "1.500 kg" in tot_mass
    assert len(fig_type.data) == 1
    assert len(fig_cause.data) == 1
    assert len(fig_monthly.data) == 1
    assert len(table_data) == 3
    assert "Última actualización" in last_upd

