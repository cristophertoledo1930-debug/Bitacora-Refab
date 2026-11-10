"""Read-only Sheets ingestion; no personal answers are persisted or logged."""
import hashlib
import json
import unicodedata
from datetime import datetime, timezone

import gspread
from sqlalchemy.dialects.postgresql import insert

from lab_hub.config import get_settings
from lab_hub.db.models import WasteRecord, WasteType, Material, Machine, Cause
from lab_hub.db.session import SessionLocal
from lab_hub.services.records import create_waste_record, ConflictError, ValidationError

HEADERS = {
    "marca temporal": "date", "tipo de residuo": "waste_type",
    "material": "material", "maquina": "machine", "causa del descarte": "cause",
    "peso medido": "weight", "unidad de medida": "unit",
}


def normalized(value):
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", value)
                            if not unicodedata.combining(c)).casefold().split())


def resolve_selection(db, model, value, field):
    aliases = {"cause": {"defecto del material": "defecto de material",
                         "error del diseno": "error de diseno"}}
    options = db.query(model).filter(model.is_active.is_(True)).all()
    selected = {}
    for part in value.split(","):
        name = normalized(part)
        name = aliases.get(field, {}).get(name, name)
        matches = [item for item in options
                   if name in {normalized(item.name), normalized(item.code)}]
        if len(matches) != 1:
            raise ValidationError("Catálogo desconocido o ambiguo.", field)
        selected[matches[0].code] = matches[0]
    if len(selected) == 1:
        return next(iter(selected.values())).id
    # A joint category retains the whole measured weight without assuming a split.
    codes = sorted(selected)
    code = "joint_" + hashlib.sha256("|".join(codes).encode()).hexdigest()[:40]
    name = " + ".join(selected[item].name for item in codes) + " (conjunto)"
    if len(name) > 100:
        raise ValidationError("Selección conjunta demasiado larga.", field)
    db.execute(insert(model).values(code=code, name=name, is_active=True)
               .on_conflict_do_nothing(index_elements=["code"]))
    combined = db.query(model).filter_by(code=code, is_active=True).one_or_none()
    if combined is None:
        raise ValidationError("Selección conjunta inactiva.", field)
    return combined.id


def parse_date(value, zone):
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            local = datetime.strptime(value.strip(), fmt)
            # Reject ambiguous/nonexistent local times instead of silently changing them.
            first = local.replace(tzinfo=zone, fold=0)
            second = local.replace(tzinfo=zone, fold=1)
            if first.utcoffset() != second.utcoffset():
                raise ValidationError("Fecha ambigua o inexistente.", "date")
            return first.astimezone(timezone.utc)
        except ValueError:
            continue
    raise ValidationError("Fecha inválida.", "date")


def import_values(db, values, sheet_id, tab_id):
    result = {"created": 0, "existing": 0, "rejected": []}
    if not values:
        return result
    columns = {}
    for index, header in enumerate(values[0]):
        field = HEADERS.get(normalized(header))
        if field:
            if field in columns:
                raise ValidationError("Encabezado duplicado.", field)
            columns[field] = index
    if set(columns) != set(HEADERS.values()):
        raise ValidationError("Faltan columnas requeridas.", "headers")
    for number, row in enumerate(values[1:], 2):
        if not any(cell.strip() for cell in row):
            continue
        field = "row"
        try:
            data = {name: row[index].strip() if index < len(row) else ""
                    for name, index in columns.items()}
            date = parse_date(data.pop("date"), get_settings().timezone)
            data["unit"] = {"gramos": "g", "gramos (g)": "g", "kilogramos": "kg",
                            "kilogramos (kg)": "kg"}.get(normalized(data["unit"]), data["unit"].lower())
            canonical = json.dumps({**data, "date": date.isoformat()}, sort_keys=True, ensure_ascii=False)
            digest = hashlib.sha256(canonical.encode()).hexdigest()
            key = "sheets:" + hashlib.sha256(f"{sheet_id}:{tab_id}:{number}".encode()).hexdigest()
            previous = db.query(WasteRecord).filter_by(idempotency_key=key).first()
            if previous:
                if previous.payload_hash != digest:
                    raise ConflictError("Fila modificada tras importar.")
                result["existing"] += 1
                continue
            ids = {}
            for field, model in (("waste_type", WasteType), ("material", Material),
                                 ("machine", Machine), ("cause", Cause)):
                ids[field + "_id"] = resolve_selection(db, model, data[field], field)
            _, created = create_waste_record(
                db, idempotency_key=key, qr_token=None, **ids, weight_str=data["weight"],
                unit=data["unit"], source="google_forms", integration_payload_hash=digest,
                recorded_at=date,
            )
            result["created" if created else "existing"] += 1
        except (ValidationError, ConflictError) as error:
            db.rollback()
            result["rejected"].append({"row": number, "field": getattr(error, "field", None) or field})
    return result


def sync_once():
    settings = get_settings()
    client = gspread.service_account(filename=settings.GOOGLE_SHEETS_CREDENTIALS,
                                    scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    client.set_timeout(20)
    worksheet = client.open_by_key(settings.GOOGLE_SHEETS_ID).worksheet(settings.GOOGLE_SHEETS_TAB)
    values = worksheet.get_all_values()
    with SessionLocal() as db:
        return import_values(db, values, settings.GOOGLE_SHEETS_ID, worksheet.id)


if __name__ == "__main__":
    print(json.dumps(sync_once()))
