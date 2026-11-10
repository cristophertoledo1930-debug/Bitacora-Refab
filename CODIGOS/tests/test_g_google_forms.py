"""Google Forms contract verified against disposable PostgreSQL."""
import hashlib
import hmac
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from lab_hub.api.app import app
from lab_hub.config import get_settings
from lab_hub.db.models import WasteRecord
from lab_hub.db.session import SessionLocal
from lab_hub.services.aggregations import get_aggregations

client = TestClient(app)
ENDPOINT = "/api/v1/integrations/google-forms"
SECRET = "synthetic-test-secret"


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setattr(get_settings(), "GOOGLE_FORMS_SECRET", SECRET)


def submission(**changes):
    cats = client.get("/api/v1/catalogs").json()
    data = {"response_id": uuid.uuid4().hex, "submitted_at": "2026-11-03T12:00:00Z",
            "station_code": "unknown-synthetic-station", "weight": "0.125", "unit": "kg"}
    for field, catalog in (("waste_type", "waste_types"), ("material", "materials"),
                           ("machine", "machines"), ("cause", "causes")):
        data[field] = cats[catalog][0]["code"].lower()
    return data | changes


def send(data, signature=None):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return client.post(ENDPOINT, content=body, headers={
        "Content-Type": "application/json", "Idempotency-Key": data["response_id"],
        "X-Forms-Signature": signature or hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()})


def test_valid_and_exact_decimal_and_unknown_station():
    data = submission()
    res = send(data)
    assert res.status_code == 201, res.text
    assert res.json()["weight_g"] == "125.000"
    assert res.json()["source"] == "google_forms"
    with SessionLocal() as db:
        record = db.get(WasteRecord, uuid.UUID(res.json()["id"]))
        assert record.qr_context_id is None
        assert record.weight_g == Decimal("125.000")


def test_bad_signature_and_disabled(monkeypatch):
    data = submission()
    assert send(data, "wrong").status_code == 401
    assert send(data, "?").status_code == 401
    monkeypatch.setattr(get_settings(), "GOOGLE_FORMS_SECRET", "")
    assert send(data).status_code == 503


def test_retry_and_conflicting_all_fields():
    data = submission()
    first = send(data)
    assert first.status_code == 201
    again = send(data)
    assert again.status_code == 200
    assert first.json()["id"] == again.json()["id"]
    for changed in ({"weight": "1"}, {"station_code": "other"},
                    {"submitted_at": "2026-11-03T12:01:00Z"}):
        assert send(data | changed).status_code == 409
    with SessionLocal() as db:
        assert db.query(WasteRecord).filter_by(idempotency_key="gform:" + data["response_id"]).count() == 1


def test_concurrent_same_response():
    data = submission()
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(send, [data, data]))
    assert sorted(r.status_code for r in responses) == [200, 201]
    assert len({r.json()["id"] for r in responses}) == 1


@pytest.mark.parametrize("weight", ["0", "-1", "NaN", "Infinity", "text", "0.0000001", "1000001"])
def test_invalid_weights(weight):
    assert send(submission(weight=weight, unit="g")).status_code == 422


def test_unknown_catalog():
    assert send(submission(material="unknown")).status_code == 422


def test_timestamp_and_idempotency_validation():
    assert send(submission(submitted_at="2026-11-03T12:00:00")).status_code == 422
    data = submission()
    body = json.dumps(data).encode()
    assert client.post(ENDPOINT, content=body, headers={"X-Forms-Signature":
        hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()}).status_code == 422


def test_body_limit():
    assert client.post(ENDPOINT, content=b"x" * 16385).status_code == 413


def test_visible_in_records_and_aggregation():
    data = submission()
    with SessionLocal() as db:
        before = get_aggregations(db)
    response = send(data)
    assert response.status_code == 201
    with SessionLocal() as db:
        after = get_aggregations(db)
    assert after["total_records"] == before["total_records"] + 1
    assert Decimal(after["total_weight_g"]) - Decimal(before["total_weight_g"]) == Decimal("125.000")
    records = client.get("/api/v1/records?page_size=500", headers={"X-Admin-Key": get_settings().ADMIN_API_KEY})
    assert response.json()["id"] in [r["id"] for r in records.json()["items"]]


def test_public_route_cannot_impersonate_forms():
    assert client.post("/api/v1/records", headers={"Idempotency-Key": "gform:reserved"}, json={
        "waste_type_id": str(uuid.uuid4()), "material_id": str(uuid.uuid4()),
        "machine_id": str(uuid.uuid4()), "cause_id": str(uuid.uuid4()),
        "weight": "1", "source": "google_forms"}).status_code == 422


def test_qr_assets_and_url(tmp_path):
    import importlib.util
    from pathlib import Path
    from PIL import Image
    from urllib.parse import parse_qs, urlsplit
    spec = importlib.util.spec_from_file_location("make_form_qr", Path("scripts/make_form_qr.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    station = "Estación láser / 1"
    assets = module.make_form_qr("https://docs.google.com/forms/d/e/synthetic/viewform?entry.5=keep", station, "42", tmp_path)
    assert all(assets[ext].exists() for ext in ("png", "svg", "txt"))
    assert Image.open(assets["png"]).info["form_url"] == assets["url"]
    query = parse_qs(urlsplit(assets["txt"].read_text().strip()).query)
    assert query == {"usp": ["pp_url"], "entry.42": [station], "entry.5": ["keep"]}
    assert station in assets["svg"].read_text(encoding="utf-8")
    assert module.prefilled_url(assets["url"], station) == assets["url"]
    with pytest.raises(ValueError):
        module.prefilled_url("https://example.com/form", station, "42")
    with pytest.raises(ValueError):
        module.prefilled_url("https://docs.google.com/forms/d/e/synthetic/viewform", station)
    other = module.make_form_qr("https://docs.google.com/forms/d/e/synthetic/viewform", "Estación láser _ 1", "42", tmp_path)
    assert other["png"] != assets["png"]


def test_source_filters_and_dashboard_callbacks():
    from lab_hub.dashboard.callbacks import refresh_data, render_records
    from lab_hub.dashboard.components import origin, ranking_chart
    data = submission()
    response = send(data)
    assert response.status_code == 201
    with SessionLocal() as db:
        agg = get_aggregations(db, source="google_forms")
        assert agg["last_google_forms_received_at"] is not None
        assert {r["source"] for r in agg["by_source"]} == {"google_forms"}
    result = client.get("/api/v1/records?source=google_forms&page_size=500",
                        headers={"X-Admin-Key": get_settings().ADMIN_API_KEY}).json()
    assert all(r["source"] == "google_forms" for r in result["items"])
    snapshot = refresh_data(0, "all", None, None, "ALL", "ALL", "ALL", "ALL", "google_forms", None)[0]
    assert snapshot["agg"]["total_records"] == agg["total_records"]
    assert all(r["source"] == "Google Forms" for r in render_records(snapshot, 0, None)[0])
    figures = [ranking_chart(agg[key], key) for key in ("by_machine", "by_material")]
    assert len(figures) == 2
    figure = origin(agg, "kg").children[0].children.figure
    assert figure.data[0].name == "Google Forms"
    assert list(figure.data[0].x) == [100]


def test_station_and_catalog_names_casefold():
    from lab_hub.db.models import QRContext
    data = submission(station_code="ESTACIÓN CORTADORA LÁSER 1")
    cats = client.get("/api/v1/catalogs").json()
    for field, catalog in (("waste_type", "waste_types"), ("material", "materials"),
                           ("machine", "machines"), ("cause", "causes")):
        data[field] = cats[catalog][0]["name"].upper()
    response = send(data)
    assert response.status_code == 201, response.text
    with SessionLocal() as db:
        record = db.get(WasteRecord, uuid.UUID(response.json()["id"]))
        assert db.get(QRContext, record.qr_context_id).label == "Estación Cortadora Láser 1"


def test_dashboard_empty_and_error_states(monkeypatch):
    import dash
    from lab_hub.dashboard import callbacks as dashboard
    values = dashboard.refresh_data(0, "custom", None, "2000-01-31", "ALL", "ALL", "ALL", "ALL", "ALL", None)
    assert values[0]["agg"]["total_records"] == 0
    assert dashboard.render_records(values[0], 0, None)[0] == []
    def unavailable():
        raise RuntimeError("synthetic failure")
    # Context KPIs catches connection creation failures and never fabricates zeros.
    monkeypatch.setattr(dashboard, "SessionLocal", unavailable)
    result = dashboard.refresh_data(0, "all", None, None, "ALL", "ALL", "ALL", "ALL", "ALL", values[0])
    assert result[0] is dash.no_update
    assert "Base de datos no disponible" in result[1]
    assert "stale" in result[3]


def test_forms_in_monthly_snapshot_and_pdf(tmp_path):
    from datetime import datetime
    from lab_hub.reports.generator import build_monthly_pdf
    data = submission()
    assert send(data).status_code == 201
    today = datetime.now(get_settings().timezone).date()
    with SessionLocal() as db:
        agg = get_aggregations(db, start_date=today.replace(day=1), end_date=today)
        assert any(row["source"] == "google_forms" for row in agg["by_source"])
        path = tmp_path / "forms-synthetic.pdf"
        build_monthly_pdf(agg, str(path), today.strftime("%Y-%m"))
        assert path.read_bytes().startswith(b"%PDF-")
