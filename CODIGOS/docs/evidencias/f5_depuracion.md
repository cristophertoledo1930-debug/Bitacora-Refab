# Evidencia F5 — Depuración e Integración

- **Fecha:** 2026-10-18
- **Estado:** Superada

## Entregables
- Prueba de recorrido completo de extremo a extremo T22 (`tests/test_f5_integration.py`):
  1. Resolución de QR `/r/token-laser-01`.
  2. Envío de formulario web con validación y normalización a gramos exactos.
  3. Inserción persistida y comprobada en PostgreSQL.
  4. Consulta de estadísticas en `/api/v1/stats`.
  5. Generación de snapshot y PDF mensual con ReportLab/Matplotlib.
  6. Entrega por correo local SMTP con PDF adjunto y Message-ID.
  7. Descarga autorizada del PDF desde `/api/v1/reports/{id}/pdf`.
- Prueba de concurrencia de inserción simultánea con misma clave idempotente (ThreadPoolExecutor con 4 hilos concurrentes):
  - Resultado: exactamente 1 fila en base de datos, respuestas coherentes con ID único.
- Suite acumulada completa (27 pruebas en total).

## Verificaciones ejecutadas
Comando:
```powershell
.\.venv\Scripts\pytest -v
```
Resultado:
- `tests/test_f0_base.py`: 3/3 PASSED
- `tests/test_f1_data.py`: 4/4 PASSED
- `tests/test_f2_records.py`: 7/7 PASSED
- `tests/test_f3_dashboard.py`: 5/5 PASSED
- `tests/test_f4_reports.py`: 6/6 PASSED
- `tests/test_f5_integration.py`: 2/2 PASSED
- **Total:** 27 passed en 4.31s. Defectos críticos o altos abiertos: 0.

