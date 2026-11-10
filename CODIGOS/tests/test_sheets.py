from decimal import Decimal
from datetime import timezone
import hashlib
from uuid import uuid4

import pytest

from lab_hub.db.session import SessionLocal
from lab_hub.db.models import WasteRecord
from lab_hub.services.sheets import import_values
from lab_hub.services.records import ValidationError
from lab_hub.services.aggregations import get_aggregations


def fixture_rows():
    return [
        ["Marca temporal", "Nombre (completo)", "Correo electrónico ", "Tipo de residuo",
         "Material ", "Maquina", "Causa del descarte", "Peso medido", "Unidad de medida"],
        ["08/11/2026 12:30:00", "Synthetic", "synthetic@example.invalid", "Resina",
         "PLA", "Impresora FDM #1", "Error de diseño", "0,125", "Kilogramos (kg)"],
    ]


def test_ingestion_retries_edits_date_and_privacy():
    sheet = uuid4().hex
    rows = fixture_rows()
    with SessionLocal() as db:
        assert import_values(db, rows, sheet, 1)["created"] == 1
        rows[1][1:3] = ["Changed personal answer", "changed@example.invalid"]
        assert import_values(db, rows, sheet, 1)["existing"] == 1
        key = "sheets:" + hashlib.sha256(f"{sheet}:1:2".encode()).hexdigest()
        record = db.query(WasteRecord).filter_by(idempotency_key=key).one()
        assert record.weight_g == Decimal("125.000")
        assert record.recorded_at.astimezone(timezone.utc).isoformat() == "2026-11-08T15:30:00+00:00"
        rows[1][7] = "0.5"
        assert import_values(db, rows, sheet, 1)["rejected"] == [{"row": 2, "field": "row"}]


def test_invalid_row_does_not_block_valid_row():
    rows = fixture_rows()
    rows.append(rows[1].copy())
    rows[1][7] = "NaN"
    with SessionLocal() as db:
        result = import_values(db, rows, uuid4().hex, 1)
        assert result["created"] == 1
        assert result["rejected"] == [{"row": 2, "field": "weight"}]


def test_missing_headers_and_unknown_catalog():
    with SessionLocal() as db:
        with pytest.raises(ValidationError):
            import_values(db, [["Material"]], uuid4().hex, 1)
        rows = fixture_rows()
        rows[1][5] = "unknown synthetic machine"
        result = import_values(db, rows, uuid4().hex, 1)
        assert result["created"] == 0
        assert result["rejected"] == [{"row": 2, "field": "machine"}]


def test_multiple_choices_conserve_total_and_normalize_aliases():
    rows = fixture_rows()
    rows[1][3:] = ["Retazo laser", "ABS, Acrilico", "Cortadora laser #1, Impresora FDM #1",
                   "Defecto del material, Error del diseño", "30", "g"]
    sheet = uuid4().hex
    with SessionLocal() as db:
        before = get_aggregations(db)
        assert import_values(db, rows, sheet, 1)["created"] == 1
        assert import_values(db, rows, sheet, 1)["existing"] == 1
        after = get_aggregations(db)
        key = "sheets:" + hashlib.sha256(f"{sheet}:1:2".encode()).hexdigest()
        record = db.query(WasteRecord).filter_by(idempotency_key=key).one()
        assert record.weight_g == Decimal("30.000")
        assert "ABS" in record.material.name and "Acrílico" in record.material.name
        assert record.material.name.endswith("(conjunto)")
        assert Decimal(after["total_weight_g"]) - Decimal(before["total_weight_g"]) == Decimal("30")


def test_form_failed_part_option_imports():
    rows = fixture_rows()
    rows[1][3:] = ["Pieza fallida", "ABS, Acrilico", "Cortadora laser #1, Cortadora laser #2",
                   "Defecto del material, Error del diseño, Margen de corte", "30", "g"]
    with SessionLocal() as db:
        result = import_values(db, rows, uuid4().hex, 1)
        assert result == {"created": 1, "existing": 0, "rejected": []}
