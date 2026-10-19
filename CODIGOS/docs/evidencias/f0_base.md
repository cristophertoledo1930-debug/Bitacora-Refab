# Evidencia F0 — Base y Entorno

- **Fecha:** 2026-10-18
- **Estado:** Superada

## Inventario
- Python: 3.12.10
- Entorno virtual: `.venv`
- PostgreSQL: 16.3 (binarios x64 portables en `.tools/pgsql`), puerto 5432
- Bases de datos creadas: `qrlabhub_dev`, `qrlabhub_test`
- Dependencias instaladas: FastAPI, SQLAlchemy, Alembic, psycopg, Dash, Plotly, Pandas, ReportLab, Matplotlib, tzdata, pytest

## Verificaciones ejecutadas
Comando:
```powershell
.\.venv\Scripts\pytest tests\test_f0_base.py
```
Resultado:
- `test_timezone_santiago`: PASSED (America/Santiago disponible en Python 3.12 con paquete tzdata)
- `test_health_live`: PASSED (HTTP 200 `{"status": "ok", "service": "qr-lab-hub"}`)
- `test_health_ready`: PASSED (HTTP 200 `{"status": "ready", "database": "connected"}`)
- Duración: 0.87s, 3 passed.

