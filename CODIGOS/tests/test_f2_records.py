import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from lab_hub.api.app import app
from lab_hub.db.session import SessionLocal
from lab_hub.db.models import WasteRecord
from lab_hub.services.seeds import seed_catalogs

client = TestClient(app)


@pytest.fixture(autouse=True)
def init_catalogs():
    db = SessionLocal()
    seed_catalogs(db)
    db.close()


def test_t02_valid_qr_and_mobile_form():
    res = client.get("/r/token-laser-01")
    assert res.status_code == 200
    assert "Estación Cortadora Láser 1" in res.text
    assert "selected" in res.text
    assert "name=\"idempotency_key\"" in res.text


def test_t03_invalid_qr_returns_404():
    res = client.get("/r/token-non-existent-xyz")
    assert res.status_code == 404
    assert "Acceso No Autorizado" in res.text


def test_t04_weight_validation_and_rejections():
    cats_res = client.get("/api/v1/catalogs")
    assert cats_res.status_code == 200
    cats = cats_res.json()

    wt_id = cats["waste_types"][0]["id"]
    mat_id = cats["materials"][0]["id"]
    mach_id = cats["machines"][0]["id"]
    cause_id = cats["causes"][0]["id"]

    invalid_weights = ["0", "-5", "abc", "NaN", "Infinity", "1000001"]
    for w in invalid_weights:
        res = client.post(
            "/api/v1/records",
            headers={"Idempotency-Key": f"key-invalid-{w}-{uuid.uuid4()}"},
            json={
                "waste_type_id": wt_id,
                "material_id": mat_id,
                "machine_id": mach_id,
                "cause_id": cause_id,
                "weight": w,
                "unit": "g"
            }
        )
        assert res.status_code == 422


def test_t04_html_form_preserves_values_on_error():
    cats_res = client.get("/api/v1/catalogs")
    cats = cats_res.json()

    wt_id = cats["waste_types"][0]["id"]
    mat_id = cats["materials"][0]["id"]
    mach_id = cats["machines"][0]["id"]
    cause_id = cats["causes"][0]["id"]

    res = client.post(
        "/r/token-laser-01",
        data={
            "waste_type_id": wt_id,
            "material_id": mat_id,
            "machine_id": mach_id,
            "cause_id": cause_id,
            "weight": "-10",
            "unit": "g",
            "idempotency_key": str(uuid.uuid4())
        }
    )
    assert res.status_code == 422
    assert "El peso debe ser mayor a cero" in res.text
    assert "-10" in res.text  # Preserved field value


def test_t05_exact_weight_kg_and_g_both_save_125g():
    cats_res = client.get("/api/v1/catalogs")
    cats = cats_res.json()

    wt_id = cats["waste_types"][0]["id"]
    mat_id = cats["materials"][0]["id"]
    mach_id = cats["machines"][0]["id"]
    cause_id = cats["causes"][0]["id"]

    # Post 1: 0.125 kg
    key1 = f"key-t05-kg-{uuid.uuid4()}"
    res1 = client.post(
        "/api/v1/records",
        headers={"Idempotency-Key": key1},
        json={
            "waste_type_id": wt_id,
            "material_id": mat_id,
            "machine_id": mach_id,
            "cause_id": cause_id,
            "weight": "0.125",
            "unit": "kg"
        }
    )
    assert res1.status_code == 201
    assert res1.json()["weight_g"] == "125.000"

    # Post 2: 125 g
    key2 = f"key-t05-g-{uuid.uuid4()}"
    res2 = client.post(
        "/api/v1/records",
        headers={"Idempotency-Key": key2},
        json={
            "waste_type_id": wt_id,
            "material_id": mat_id,
            "machine_id": mach_id,
            "cause_id": cause_id,
            "weight": "125",
            "unit": "g"
        }
    )
    assert res2.status_code == 201
    assert res2.json()["weight_g"] == "125.000"


def test_t06_missing_catalog_rejection():
    fake_id = str(uuid.uuid4())
    cats = client.get("/api/v1/catalogs").json()

    res = client.post(
        "/api/v1/records",
        headers={"Idempotency-Key": f"key-t06-{uuid.uuid4()}"},
        json={
            "waste_type_id": fake_id,
            "material_id": cats["materials"][0]["id"],
            "machine_id": cats["machines"][0]["id"],
            "cause_id": cats["causes"][0]["id"],
            "weight": "50",
            "unit": "g"
        }
    )
    assert res.status_code == 422


def test_t07_idempotency_retry_and_conflict():
    cats = client.get("/api/v1/catalogs").json()
    wt_id = cats["waste_types"][0]["id"]
    mat_id = cats["materials"][0]["id"]
    mach_id = cats["machines"][0]["id"]
    cause_id = cats["causes"][0]["id"]

    same_key = f"key-idempotent-{uuid.uuid4()}"

    payload1 = {
        "waste_type_id": wt_id,
        "material_id": mat_id,
        "machine_id": mach_id,
        "cause_id": cause_id,
        "weight": "250.5",
        "unit": "g"
    }

    # Initial POST -> 201 Created
    res1 = client.post("/api/v1/records", headers={"Idempotency-Key": same_key}, json=payload1)
    assert res1.status_code == 201
    id1 = res1.json()["id"]

    # Retry same key & same payload -> 200 OK, returns same ID without duplicate row
    res2 = client.post("/api/v1/records", headers={"Idempotency-Key": same_key}, json=payload1)
    assert res2.status_code == 200
    assert res2.json()["id"] == id1

    # Retry same key with DIFFERENT payload -> 409 Conflict
    payload_diff = dict(payload1, weight="300.0")
    res3 = client.post("/api/v1/records", headers={"Idempotency-Key": same_key}, json=payload_diff)
    assert res3.status_code == 409

