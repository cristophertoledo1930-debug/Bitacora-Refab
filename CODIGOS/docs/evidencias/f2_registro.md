# Evidencia F2 — Registro e Ingreso

- **Fecha:** 2026-10-18
- **Estado:** Superada

## Entregables
- Formulario móvil en Jinja2/CSS tema oscuro verde (`src/lab_hub/templates/form.html`, `success.html`, `error.html`).
- Servicio de registros con idempotencia y hash de payload (`src/lab_hub/services/records.py`).
- Endpoints en `src/lab_hub/api/routes.py`:
  - `GET /r/{token}`: renderiza formulario contextualizado con clave idempotente.
  - `POST /r/{token}`: valida y guarda, preservando campos en caso de error.
  - `GET /api/v1/catalogs`: lista opciones activas.
  - `POST /api/v1/records`: POST con header `Idempotency-Key` (201 en creación, 200 en reintento, 409 en conflicto).

## Verificaciones ejecutadas
Comando:
```powershell
.\.venv\Scripts\pytest tests\test_f2_records.py
```
Resultado:
- `test_t02_valid_qr_and_mobile_form`: PASSED
- `test_t03_invalid_qr_returns_404`: PASSED
- `test_t04_weight_validation_and_rejections`: PASSED (0, negativos, NaN, Infinity, exceso)
- `test_t04_html_form_preserves_values_on_error`: PASSED (preserva campos corregibles)
- `test_t05_exact_weight_kg_and_g_both_save_125g`: PASSED (0.125 kg y 125 g guardan 125.000 g)
- `test_t06_missing_catalog_rejection`: PASSED (422 sin fila parcial)
- `test_t07_idempotency_retry_and_conflict`: PASSED (retry devuelve 200 sin duplicar; payload diferente devuelve 409)
- 7/7 pasadas en 1.41s.

