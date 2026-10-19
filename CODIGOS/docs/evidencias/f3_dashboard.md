# Evidencia F3 — Dashboard de Laboratorio

- **Fecha:** 2026-10-18
- **Estado:** Superada

## Entregables
- Motor centralizado de agregación: `src/lab_hub/services/aggregations.py`.
- Endpoints administrativos en `src/lab_hub/api/routes.py`:
  - `GET /api/v1/stats`: métricas y series para el dashboard/informes, protegido por `require_admin`.
  - `GET /api/v1/records`: lista paginada y filtrable de registros, protegido por `require_admin`.
- Aplicación Dash montada en `/dashboard/` (`src/lab_hub/dashboard/app.py`):
  - Paleta oscuro verde: `#0B1411` fondo, `#14231D` paneles, `#64D6A0` verde primario, `#F4F8F5` texto.
  - Lateral izquierdo con navegación y filtros.
  - 4 tarjetas superiores: total registros, masa total acumulada (kg), registros del mes, categoría con mayor masa.
  - Gráficos de barras Plotly (tipo de residuo, causa, evolución mensual cronológica con meses vacíos).
  - Tabla de registros paginada y filtrada.
  - Actualización periódica en vivo (intervalo de 15 segundos).

## Verificaciones ejecutadas
Comando:
```powershell
.\.venv\Scripts\pytest tests\test_f3_dashboard.py
```
Resultado:
- `test_t09_synthetic_control_fixture`: PASSED (Enero: 2 reg 0.500 kg; Feb: 1 reg 1.000 kg; Marzo: 0 kg; Total: 3 reg 1.500 kg)
- `test_t11_empty_month_and_year_labels`: PASSED (meses vacíos con cero y etiquetas con año)
- `test_t12_month_boundaries_and_santiago_dst`: PASSED (límites de mes y DST en America/Santiago)
- `test_t19_admin_protection_and_public_qr`: PASSED (401 denegado sin clave, 200 con header/cookie, QR público activo)
- `test_t20_dashboard_callback_renders_cleanly`: PASSED (renderizado de gráficos y tabla)
- 5/5 pasadas en 1.59s.

