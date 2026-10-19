from decimal import Decimal
import pytest
from sqlalchemy.exc import IntegrityError
from lab_hub.db.session import SessionLocal
from lab_hub.db.models import (
    WasteType,
    Material,
    Machine,
    Cause,
    QRContext,
    WasteRecord,
)
from lab_hub.services.seeds import seed_catalogs, hash_token


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_t01_catalogs_seeded_and_idempotent(db):
    cats1 = seed_catalogs(db)
    assert len(cats1["waste_types"]) == 2
    assert len(cats1["materials"]) == 5
    assert len(cats1["machines"]) == 4
    assert len(cats1["causes"]) == 6
    assert len(cats1["qr_contexts"]) == 3

    # Idempotent re-run
    cats2 = seed_catalogs(db)
    assert len(cats2["waste_types"]) == 2


def test_t01_positive_weight_constraint(db):
    cats = seed_catalogs(db)
    wt = list(cats["waste_types"].values())[0]
    mat = list(cats["materials"].values())[0]
    mach = list(cats["machines"].values())[0]
    cause = list(cats["causes"].values())[0]

    # Test weight = 0 fails
    rec_zero = WasteRecord(
        waste_type_id=wt.id,
        material_id=mat.id,
        machine_id=mach.id,
        cause_id=cause.id,
        weight_g=Decimal("0.000"),
        idempotency_key="key-test-zero-weight",
        payload_hash="dummyhash0"
    )
    db.add(rec_zero)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    # Test negative weight fails
    rec_neg = WasteRecord(
        waste_type_id=wt.id,
        material_id=mat.id,
        machine_id=mach.id,
        cause_id=cause.id,
        weight_g=Decimal("-10.500"),
        idempotency_key="key-test-neg-weight",
        payload_hash="dummyhashneg"
    )
    db.add(rec_neg)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_t01_exact_decimal_weight_storage(db):
    cats = seed_catalogs(db)
    wt = list(cats["waste_types"].values())[0]
    mat = list(cats["materials"].values())[0]
    mach = list(cats["machines"].values())[0]
    cause = list(cats["causes"].values())[0]

    weight = Decimal("125.456")
    rec = WasteRecord(
        waste_type_id=wt.id,
        material_id=mat.id,
        machine_id=mach.id,
        cause_id=cause.id,
        weight_g=weight,
        idempotency_key="key-test-exact-weight",
        payload_hash="dummyhashexact"
    )
    db.add(rec)
    db.commit()

    saved = db.query(WasteRecord).filter_by(idempotency_key="key-test-exact-weight").first()
    assert saved is not None
    assert saved.weight_g == Decimal("125.456")

    # Clean up
    db.delete(saved)
    db.commit()


def test_t01_qr_token_hash_lookup(db):
    token = "token-laser-01"
    th = hash_token(token)
    qr = db.query(QRContext).filter_by(token_hash=th).first()
    assert qr is not None
    assert qr.label == "Estación Cortadora Láser 1"
    assert qr.machine.code == "laser_cutter_1"
    assert qr.waste_type.code == "laser_cut"
    assert qr.cause.code == "cut_margin"

