# Evidencia F1 — Datos

- **Fecha:** 2026-10-18
- **Estado:** Superada

## Entregables
- Modelos SQLAlchemy 2 en `src/lab_hub/db/models.py`:
  - `WasteType`, `Material`, `Machine`, `Cause`
  - `QRContext` (con `token_hash` SHA-256)
  - `WasteRecord` (con `NUMERIC(12,3)` y `CHECK (weight_g > 0)`)
  - `ReportRun`, `ReportDelivery`
- Migración Alembic `migrations/versions/c33319fc0990_initial_schema.py`
- Servicio de semillas sintéticas `src/lab_hub/services/seeds.py`

## Verificaciones ejecutadas
Comando:
```powershell
.\.venv\Scripts\pytest tests\test_f1_data.py
```
Resultado:
- `test_t01_catalogs_seeded_and_idempotent`: PASSED
- `test_t01_positive_weight_constraint`: PASSED (IntegrityError en <= 0)
- `test_t01_exact_decimal_weight_storage`: PASSED (Decimal exacto 125.456)
- `test_t01_qr_token_hash_lookup`: PASSED (Resolución contextual por SHA-256)
- 4/4 pasadas en 0.71s.

