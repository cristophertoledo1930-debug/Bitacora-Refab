# Archivo semanal automático

## Corrección de actualización mensual

El circuito mensual reutilizaba un PDF completado sin comparar los datos nuevos. Ahora genera el snapshot actual bajo lectura repetible y lo compara con la revisión más reciente bajo bloqueo por periodo. Cambios producen una nueva revisión; reintentos sin cambios recuperan la misma. Incluye copia de registros operativos sin información personal.

El supervisor revisa también mes actual, meses con registros y meses archivados cada 15 segundos. Este refresco usa `send_email=False`; no invoca SMTP. La recuperación programada de entregas consulta la revisión más reciente. La tabla mensual muestra cantidad y masa de cada revisión.

Validación ejecutada: 66 pruebas pasan, 6 avisos de deprecación, Ruff sin errores. Nueva prueba reproduce PDF vacío, alta posterior desde Google Forms, actualización automática, masa exacta, preservación de revisión anterior, reintento estable y baja posterior; falla si se intenta enviar correo. Se usó PostgreSQL desechable, periodo inicial de pruebas 2026-01 y temporales `.tools/pytest-monthly-refresh`.

Supervisor reiniciado. Informe real de noviembre 2026, revisión 2: 3 registros y 90.000 g, iguales al dashboard. Descarga HTTP 200. PDF de dos páginas renderizado e inspeccionado visualmente: título mensual, totales, tablas y gráfico legibles.

## Cambio

La sección `/reports` tenía solo informes mensuales generados bajo demanda o por recuperación mensual. Ahora incorpora archivo semanal automático, actualizado con la misma fuente PostgreSQL que utiliza el dashboard. Conserva informes mensuales, protección administrativa y descargas.

El supervisor independiente revisa cambios cada 15 segundos. Cada semana ISO usa límites de lunes a lunes en America/Santiago. Guarda snapshot consistente de agregaciones y registros operativos sin información personal. Cada cambio crea una revisión PDF; reintentos sin cambios recuperan la existente. Las bajas también actualizan semanas ya archivadas. No envía correo semanal.

`report_runs` reutiliza su clave de siete caracteres con periodo `YYYYWww`; el snapshot indica `report_kind=weekly`. Los periodos mensuales conservan su formato. No se requirió migración.

## Validación ejecutada

- Suite completa con `REPORT_INITIAL_MONTH=2026-01`, `.venv/Scripts/python.exe -m pytest -q --basetemp .tools/pytest-weekly`: 65 passed, 6 warnings. PostgreSQL desechable mediante fixture existente.
- Ruff: `src tests probar.py` sin errores.
- Pruebas nuevas: cambio domingo/lunes, cruce de año ISO, semana vacía, altas manuales y Google Forms, masa exacta, idempotencia de revisiones, borrado de registros, actualización de la página y descarga protegida.
- Supervisor reiniciado con los lanzadores locales. Semana real `2026W45`: 3 registros, 90.000 g, iguales a agregaciones del dashboard.
- `/reports`: HTTP 200, cabecera Refresh 15, sección semanal presente. Descarga PDF por endpoint protegido: HTTP 200 y cabecera binaria PDF válida.
- PDF semanal real de dos páginas renderizado e inspeccionado visualmente: título semanal, rango 02/11/2026–08/11/2026, totales, tablas y gráfico legibles, sin cortes de texto.
- Dependencias de uso compatibles (`uv pip check`). Se instaló PyMuPDF como herramienta local de revisión visual.

## Operación

Los archivos se guardan bajo `REPORT_OUTPUT_DIR`, y snapshots/revisiones en PostgreSQL. La página muestra todas las revisiones, con la más reciente primero dentro de la semana. Tras reiniciar Windows abrir `Iniciar QR Lab.cmd`. Sheets mantiene su intervalo de 60 segundos; el archivo semanal refleja el dato tras su importación y la siguiente comprobación de 15 segundos.
