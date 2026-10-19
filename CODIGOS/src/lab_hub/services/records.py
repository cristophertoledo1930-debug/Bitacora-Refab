import hashlib
import json
from decimal import Decimal, InvalidOperation
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from lab_hub.db.models import (
    WasteRecord,
    WasteType,
    Material,
    Machine,
    Cause,
    QRContext,
)
from lab_hub.services.seeds import hash_token


class ValidationError(Exception):
    def __init__(self, message: str, field: str | None = None):
        self.message = message
        self.field = field
        super().__init__(message)


class ConflictError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def normalize_weight(weight_str: str, unit: str) -> Decimal:
    """
    Parses and normalizes weight to grams with 3 decimal places using Decimal.
    Rejects <= 0, NaN, Inf, excessively large weights, or invalid formats.
    """
    if not weight_str or not isinstance(weight_str, str):
        raise ValidationError("El peso es obligatorio y debe especificarse como texto decimal.", "weight")

    unit_clean = (unit or "g").strip().lower()
    if unit_clean not in ("g", "kg"):
        raise ValidationError("La unidad debe ser 'g' o 'kg'.", "unit")

    try:
        val = Decimal(weight_str.strip().replace(",", "."))
    except InvalidOperation:
        raise ValidationError("Formato numérico de peso inválido.", "weight")

    if not val.is_finite():
        raise ValidationError("El peso debe ser un número finito.", "weight")

    if val <= Decimal("0"):
        raise ValidationError("El peso debe ser mayor a cero.", "weight")

    if unit_clean == "kg":
        grams = val * Decimal("1000")
    else:
        grams = val

    # Operational limit: max 1,000,000 grams (1,000 kg)
    if grams > Decimal("1000000.000"):
        raise ValidationError("El peso excede el límite operativo máximo (1,000 kg).", "weight")

    # Quantize to 3 decimal places
    normalized = grams.quantize(Decimal("0.001"))
    if normalized != grams:
        raise ValidationError("El peso admite hasta tres decimales en gramos.", "weight")
    grams = normalized

    return grams


def compute_payload_hash(
    waste_type_id: str,
    material_id: str,
    machine_id: str,
    cause_id: str,
    weight_g: Decimal,
    source: str
) -> str:
    payload = {
        "waste_type_id": str(waste_type_id),
        "material_id": str(material_id),
        "machine_id": str(machine_id),
        "cause_id": str(cause_id),
        "weight_g": str(weight_g),
        "source": source
    }
    dumped = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def resolve_qr_token(db: Session, token: str) -> QRContext | None:
    if not token:
        return None
    th = hash_token(token.strip())
    return db.query(QRContext).filter(
        QRContext.token_hash == th,
        QRContext.is_active.is_(True)
    ).first()


def create_waste_record(
    db: Session,
    *,
    idempotency_key: str,
    qr_token: str | None,
    waste_type_id: str | UUID,
    material_id: str | UUID,
    machine_id: str | UUID,
    cause_id: str | UUID,
    weight_str: str,
    unit: str = "g",
    source: str = "manual"
) -> tuple[WasteRecord, bool]:
    """
    Creates a waste record with idempotency and transaction safety.
    Returns (record, was_created: bool).
    """
    if not idempotency_key or not idempotency_key.strip():
        raise ValidationError("La cabecera 'Idempotency-Key' es obligatoria.", "idempotency_key")
    key = idempotency_key.strip()

    # Normalize weight
    weight_g = normalize_weight(weight_str, unit)

    # Validate catalog existences and active status
    wt = db.query(WasteType).filter(WasteType.id == waste_type_id, WasteType.is_active.is_(True)).first()
    if not wt:
        raise ValidationError(f"Tipo de residuo no encontrado o inactivo: {waste_type_id}", "waste_type_id")

    mat = db.query(Material).filter(Material.id == material_id, Material.is_active.is_(True)).first()
    if not mat:
        raise ValidationError(f"Material no encontrado o inactivo: {material_id}", "material_id")

    mach = db.query(Machine).filter(Machine.id == machine_id, Machine.is_active.is_(True)).first()
    if not mach:
        raise ValidationError(f"Máquina no encontrada o inactiva: {machine_id}", "machine_id")

    c = db.query(Cause).filter(Cause.id == cause_id, Cause.is_active.is_(True)).first()
    if not c:
        raise ValidationError(f"Causa no encontrada o inactiva: {cause_id}", "cause_id")

    # Validate QR context if provided
    qr_ctx = None
    if qr_token:
        qr_ctx = resolve_qr_token(db, qr_token)
        if not qr_ctx:
            raise ValidationError("Código QR inválido o revocado.", "qr_token")

    payload_hash = compute_payload_hash(
        str(wt.id), str(mat.id), str(mach.id), str(c.id), weight_g, source
    )

    # Check for existing idempotency key
    existing = db.query(WasteRecord).filter(WasteRecord.idempotency_key == key).first()
    if existing:
        if existing.payload_hash == payload_hash:
            return existing, False
        else:
            raise ConflictError("Idempotency-Key ya utilizada con un payload diferente.")

    # Create new record
    new_record = WasteRecord(
        waste_type_id=wt.id,
        material_id=mat.id,
        machine_id=mach.id,
        cause_id=c.id,
        weight_g=weight_g,
        qr_context_id=qr_ctx.id if qr_ctx else None,
        source=source,
        idempotency_key=key,
        payload_hash=payload_hash,
        recorded_at=datetime.now(timezone.utc)
    )

    db.add(new_record)
    try:
        db.commit()
        db.refresh(new_record)
        return new_record, True
    except IntegrityError:
        db.rollback()
        # Handle concurrent race condition
        race_existing = db.query(WasteRecord).filter(WasteRecord.idempotency_key == key).first()
        if race_existing:
            if race_existing.payload_hash == payload_hash:
                return race_existing, False
            else:
                raise ConflictError("Idempotency-Key ya utilizada con un payload diferente.")
        raise

