# Checklist de aceptación

Spec v2 implementada; R-01–R-04 del ciclo 1 corregidos. P-01 cerrada. Ver `implementacion.md` para decisiones, comandos y límites. Regresión PostgreSQL completa: 138 pruebas aprobadas; Ruff limpio. Pendiente de revisión de Opus.

- [x] CA-01: `test_redesign_data.py`, diez casos de masa con Decimal, cero, gramos y valores grandes; conteos y porcentajes es-CL.
- [x] CA-02: formatos centralizados y ejes Plotly con separadores es-CL; capturas escritorio/móvil revisadas.
- [x] CA-03: `parse_filters` selecciona Este mes; Playwright verifica preset activo y encabezado.
- [x] CA-04: R-01 corregido conforme a la revisión: presets comparados por calendario; personalizado por días contiguos. `test_redesign_review_periods.py` cubre cada preset, febrero corto/bisiesto, cruce de año y delta contra datos PostgreSQL.
- [x] CA-05: Playwright exige exactamente cuatro KPIs y verifica masa/conteo independientes del agregado.
- [x] CA-06: prueba de 13 categorías positivas, top 8 + Otros (5), ceros ocultos, color único y etiquetas de masa/porcentaje.
- [x] CA-07: serie inmediatamente después de KPIs en layout; prueba de opacidad 0,45 y texto en curso.
- [x] CA-08: prueba de fechas inválidas sin abrir sesión; Playwright verifica mensaje junto al campo, `aria-describedby` y valores anteriores intactos.
- [x] CA-09: fallo sintético de sesión; store `no_update`, banner `role=alert`, hora anterior y clase stale. Captura `evidencias/database-error.png`.
- [x] CA-10: Playwright verifica vacío único, ausencia de KPIs y botón Limpiar filtros funcional. Captura `evidencias/empty.png`.
- [x] CA-11: prueba PostgreSQL crea/desactiva causa y comprueba nuevas opciones sin reinicio.
- [x] CA-12: R-02 reinicia al cambiar periodo, fechas, dimensiones u orden; limita páginas fuera de rango. Prueba Chromium: página 3, filtro ESP32 de una fila, resultado `1 / 1` con fila visible. Conservación entre ticks cubierta por la prueba UI general.
- [x] CA-13: prueba CSV completo de 63 filas y filtro api de 60 filas; navegador descarga 56 filas actuales más cabecera.
- [x] CA-14: una llamada de agregación en `load_snapshot`; contador SQLAlchemy verifica una sentencia para cinco años y ≤4 consultas para snapshot + tabla (real: 3).
- [x] CA-15: chips actualizados desde snapshot; prueba mensual sin nombres de variables, último periodo; Sheets faltante/corrupto cubierto.
- [x] CA-16: Playwright sin overflow a 320, 390, 768 y 1440 px; `evidencias/responsive.json` y capturas.
- [x] CA-17: Playwright mide controles visibles ≥44 px, verifica foco, labels asociados, `lang=es` y fechas descritas. CSS agrega foco al dropdown y paginación.
- [x] CA-18: `test_redesign_palette.py` exige ≥4,5:1 en tokens de texto. Navegador verifica ambos placeholders reales: muted sobre input, 8,8:1. Evidencia `input-styles.json` y `contrast.json`.
- [x] CA-19: revisión de layout sin props style, CSS nuevo sin !important; Plotly resuelve colores desde tokens CSS.
- [x] CA-20: regresión completa del ciclo 1: 138 aprobadas, incluidos F3 y F5/T22. Adaptaciones justificadas en `implementacion.md`; log `evidencias/review-pytest.txt`.
- [x] CA-21: `app.layout` se asigna una sola vez, sin mutaciones posteriores; layout declarativo.
- [x] CA-22: enlace desde `Settings.DASHBOARD_NEW_RECORD_URL` y `.env.example`, sin token en layout/componentes.
- [x] CA-23: paleta exacta v2 verificada en prueba; ALL CHECKS PASS en `evidencias/palette.txt` y salida pegada en `implementacion.md`.

## Revisión Opus · ciclo 1

- [x] R-01: comparación por calendario y etiquetas es-CL; 26 pruebas focalizadas aprobadas.
- [x] R-02: reinicio y límite de página; tres pruebas focalizadas aprobadas, incluida regresión real en Chromium.
- [x] R-03: barra de Origen de 18 px medida en Chromium a 320/390/768/1440 px, hover verificado en móvil/escritorio; tres pruebas UI aprobadas.
- [x] R-04: `lru_cache(maxsize=1)`; nueve figuras consecutivas leen solo dos archivos CSS en total. Prueba de caché y paleta: dos aprobadas.
