# Evidencia F4 — Informes y Entregas Mensuales

- **Fecha:** 2026-10-18
- **Estado:** Superada

## Entregables
- Generador de PDF en `src/lab_hub/reports/generator.py`:
  - Maquetación con ReportLab: título, subtítulo con zona horaria, resumen ejecutivo en tabla, desgloses por tipo y causa, nota metodológica.
  - Gráfico de barras mensual estático generado con Matplotlib embebido como imagen de alta resolución.
  - Manejo explícito de meses sin registros ("Durante este periodo calendario no se registraron residuos").
  - Hashing SHA-256 del contenido generado.
- Despacho SMTP en `src/lab_hub/reports/mailer.py`:
  - Registro de entrega por destinatario en `report_deliveries`.
  - Estados: `pending`, `sending`, `sent`, `failed`, `uncertain`.
  - Prevención de reenvíos a destinatarios ya completados.
  - Message-ID único y PDF adjunto (`application/pdf`).
- Tarea programada en `src/lab_hub/jobs/monthly_report.py`:
  - `process_monthly_report`: crea snapshot inmutable, PDF, y dispara despachos.
  - `run_daily_check`: recupera periodos cerrados desde `REPORT_INITIAL_MONTH`.
- Endpoints en `src/lab_hub/api/routes.py`:
  - `GET /api/v1/reports`: listado de ejecuciones y entregas.
  - `GET /api/v1/reports/{id}/pdf`: descarga autorizada de archivo PDF.

## Verificaciones ejecutadas
Comando:
```powershell
.\.venv\Scripts\pytest tests\test_f4_reports.py
```
Resultado:
- `test_t13_pdf_normal_and_empty_month`: PASSED (PDF normal y mes vacío generados correctamente)
- `test_t14_snapshot_and_dashboard_equivalence`: PASSED (mismo snapshot e igualdad de cifras)
- `test_t15_smtp_delivery_and_failed_recipient`: PASSED (adjunto PDF y registro de fallos)
- `test_t16_idempotent_delivery_skips_already_sent`: PASSED (destinatarios sent no se reenvían)
- `test_t17_uncertain_state_on_smtp_drop`: PASSED (estado `uncertain` visible ante corte)
- `test_t18_daily_recovery_processes_closed_months`: PASSED (recuperación de periodos pendientes)
- 6/6 pasadas en 4.86s.

