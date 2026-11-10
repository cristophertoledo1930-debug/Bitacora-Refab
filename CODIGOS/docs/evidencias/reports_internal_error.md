# Corrección de Internal Server Error en /reports

Fecha: 2026-11-08.

Causa confirmada en `storage/logs/app-error.log`: `jinja2.exceptions.UndefinedError: 'monthly_delivery' is undefined`. El proceso seguía usando la ruta Python anterior, mientras Jinja cargaba la plantilla nueva desde disco. Las pruebas anteriores arrancaban procesos nuevos y no reproducían esa combinación.

Corrección: sección de correo condicionada a que exista `monthly_delivery`; cuando falta, los PDF siguen disponibles y aparece un aviso. Prueba `test_reports_template_accepts_previous_worker_context` reproduce el contexto anterior. Reinicio controlado del supervisor local para cargar las rutas y estados nuevos; PostgreSQL permaneció disponible. No se ejecutó el lanzador con migraciones ni se activó correo externo.

Validación:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_reports_compatibility.py tests/test_local_runtime.py::test_mounted_dashboard_and_protection tests/test_monthly_send.py::test_disabled_email_and_status_visible -q --basetemp=storage/pytest-reports-compat
.\.venv\Scripts\python.exe -m ruff check tests/test_reports_compatibility.py
```

Tres pruebas pasan en PostgreSQL desechable; Ruff limpio. Antes del reinicio, la plantilla corregida ya devolvió HTTP 200 en la instancia local. Después del reinicio se verificaron `/health/ready`, `/dashboard/`, `/reports` y `/api/v1/reports/monthly-status` mediante GET. Comprobación Chromium: clic real en el enlace Informes PDF del dashboard, apertura de `/reports` y presencia de Informes mensuales sin Internal Server Error. No se guardaron capturas ni contenido de registros reales.
