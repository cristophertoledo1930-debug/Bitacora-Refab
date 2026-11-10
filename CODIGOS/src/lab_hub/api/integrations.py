"""Signed Google Forms ingestion. Never log bodies or credentials."""

import hashlib
import hmac
import json
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from lab_hub.api.schemas import WasteRecordResponse
from lab_hub.config import get_settings
from lab_hub.db.models import Cause, Machine, Material, QRContext, WasteRecord, WasteType
from lab_hub.db.session import get_db
from lab_hub.services.records import ConflictError, create_waste_record
from lab_hub.services.records import ValidationError as RecordValidationError

router = APIRouter()
MAX_BODY_BYTES = 16 * 1024


class GoogleFormsSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    response_id: str = Field(min_length=1, max_length=94, pattern=r"^\S+$")
    submitted_at: AwareDatetime
    station_code: str = Field(default="", max_length=100)
    waste_type: str = Field(min_length=1, max_length=100)
    material: str = Field(min_length=1, max_length=100)
    machine: str = Field(min_length=1, max_length=100)
    cause: str = Field(min_length=1, max_length=100)
    weight: str = Field(min_length=1, max_length=100)
    unit: Literal["g", "kg"]


def resolve_catalog(db, model, value, field):
    value = value.strip().casefold()
    matches = [row for row in db.query(model).filter(model.is_active.is_(True)).all()
               if value in {row.code.casefold(), row.name.casefold()}]
    if len(matches) != 1:
        raise HTTPException(422, detail={"field": field, "message": "Opción desconocida, inactiva o ambigua."})
    return matches[0].id


@router.post("/api/v1/integrations/google-forms", response_model=WasteRecordResponse,
             status_code=201,
             openapi_extra={"requestBody": {"required": True, "content": {
                 "application/json": {"schema": GoogleFormsSubmission.model_json_schema()}}}},
             responses={200: {"description": "Reenvío"}, 201: {"description": "Creado"},
                        401: {"description": "Firma inválida"}, 409: {"description": "Conflicto"},
                        413: {"description": "Cuerpo excesivo"}, 503: {"description": "No disponible"}})
async def ingest_google_form(
    request: Request,
    signature: str = Header(default="", alias="X-Forms-Signature"),
    idempotency_key: str = Header(default="", alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    secret = get_settings().GOOGLE_FORMS_SECRET
    if not secret:
        raise HTTPException(503, detail="Integración Google Forms no configurada.")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BODY_BYTES:
            raise HTTPException(413, detail="Cuerpo demasiado grande.")
        body.extend(chunk)
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected.encode("ascii"), signature.encode("utf-8")):
        raise HTTPException(401, detail="Firma inválida.")
    try:
        payload = GoogleFormsSubmission.model_validate_json(bytes(body))
    except ValidationError as exc:
        # Avoid echoing the untrusted submitted body or answers in validation errors.
        raise HTTPException(422, detail=[{"field": ".".join(map(str, e["loc"])),
                                         "message": e["msg"]} for e in exc.errors()]) from None
    if idempotency_key != payload.response_id:
        raise HTTPException(422, detail="Idempotency-Key debe coincidir con response_id.")
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True,
                           separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    key = "gform:" + payload.response_id
    existing = db.query(WasteRecord).filter(WasteRecord.idempotency_key == key).first()
    if existing:
        if existing.payload_hash != digest:
            raise HTTPException(409, detail="response_id ya utilizado con datos diferentes.")
        return JSONResponse(status_code=200, content=WasteRecordResponse.model_validate(existing).model_dump(mode="json"))

    ids = {field + "_id": resolve_catalog(db, model, getattr(payload, field), field)
           for field, model in (("waste_type", WasteType), ("material", Material),
                                ("machine", Machine), ("cause", Cause))}
    stations = [row for row in db.query(QRContext).filter(QRContext.is_active.is_(True)).all()
                if row.label and row.label.casefold() == payload.station_code.strip().casefold()
                ] if payload.station_code.strip() else []
    if len(stations) > 1:
        raise HTTPException(422, detail={"field": "station_code", "message": "Estación ambigua."})
    try:
        record, created = create_waste_record(
            db, idempotency_key=key, qr_token=None, **ids,
            weight_str=payload.weight, unit=payload.unit, source="google_forms",
            qr_context_id=stations[0].id if stations else None,
            integration_payload_hash=digest,
        )
    except RecordValidationError as exc:
        raise HTTPException(422, detail={"field": exc.field, "message": exc.message}) from None
    except ConflictError as exc:
        raise HTTPException(409, detail=exc.message) from None
    return JSONResponse(status_code=201 if created else 200,
                        content=WasteRecordResponse.model_validate(record).model_dump(mode="json"))
