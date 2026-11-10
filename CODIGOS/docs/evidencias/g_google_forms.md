# Evidencia Google Forms + QR + UI/UX

## G0 ? Contrato

2026-11-03: leídos AGENTS, estado, contratos, pruebas y habilidades locales.
CodeGraph consultado con `codegraph explore "create_waste_record get_aggregations routes dashboard"`.
Contrato y D11 actualizados antes de código. Sin cambio de esquema.
Revisión documental: nueve campos, códigos HTTP, HMAC, almacenamiento y límites externos definidos.
Pruebas de ejecución no aplican a esta fase documental.

## G1 ? Backend

Python 3.12.15 y entorno .venv creado con uv; dependencias lock instaladas.
PostgreSQL 16 aislado inicializado en `.tools/pg-google-verify`, solo 127.0.0.1:55432.
La instancia de 5432 usa otras credenciales: no se modific? ni se utiliz?.
Comando: `TEST_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:55432/postgres .venv/Scripts/python.exe -m pytest tests/test_g_google_forms.py -q` (variable de entorno PowerShell).
Resultado: **16 passed, 3 warnings**, 6.13 s. Base temporal creada y eliminada por conftest.
Incluye concurrencia, firma, secreto ausente, conflictos de estación/fecha/peso, validaciones,
125.000 g exactos y consulta del registro en API y agregaciones. Sin migración.

## G2 ? Scripts de Google Forms

`node` comprob? sintaxis de ambos archivos `.gs`. `node tests/google_forms_script.cjs`:
8 escenarios pasan con servicios simulados: HMAC UTF-8, ACK, 200/201, retry 503/429/red,
retención ante 401/409/422 y no borrado con ACK incorrecto. No prueba servicios de Google.
Borrador privado, siete preguntas, catálogos API, propiedades privadas y triggers sin Sheets.
Guía de cuenta, publicación manual, URL prefijada y recuperación en integrations/google_forms/README.md.
Creación en cuenta y envío real pendientes de propietario y HTTPS; no se declararon ejecutados.

## G3 ? QR

Generador PNG/SVG/TXT con corrección M, margen 4, leyenda y URL en metadatos.
Prueba `pytest tests/test_g_google_forms.py -k qr_assets -q --basetemp .tools/pytest-g3`:
**1 passed**, 16 deselected. Antes fall? fixture tmp_path por permisos en Temp de Windows;
se resolvi? con basetemp dentro de .tools. No se alteraron permisos externos.
URL, Unicode, rutas seguras distintas por estación y archivos comprobados.
QR definitivo y escaneo físico pendientes de URL/entry ID del formulario real.

## G4 ? Dashboard y consultas

Filtro source en API, agregaciones, todos los gráficos y tabla. Desglose por origen e indicador
operativo global de Última recepción con America/Santiago. Informes conservan consulta común sin
excluir google_forms. Comando: pytest tests/test_g_google_forms.py tests/test_f3_dashboard.py
-q --basetemp .tools/pytest-g4 con TEST_DATABASE_URL aislada.
Resultado: **23 passed, 3 warnings**, 5.05 s. Incluye callbacks reales del dashboard y filtros.

## G5 — Auditoría y UI

Entregable: [UIUX_AUDITORIA](../UIUX_AUDITORIA.md). Se conservaron 10 capturas antes y 11 después,
con PostgreSQL sintético eliminado tras cada ejecución. Chromium: cero errores JavaScript,
cuatro páginas sin overflow global en escritorio/móvil. Teclado, controles ≥44 px, validación,
confirmación y filtro Google Forms comprobados. Contrastes de texto revisados superan 4.5:1.
Capturas inspeccionadas visualmente y refinadas (KPIs, radio métrica, etiquetas y descargas móviles).

`pytest tests/test_g_google_forms.py tests/test_f2_records.py tests/test_f3_dashboard.py -q
--basetemp .tools/pytest-g5`: 32 passed y un fallo del nuevo test PDF por nombre de función
incorrecto en el test; corregido a build_monthly_pdf. Repetición focal `-k forms_in_monthly`:
1 passed, 20 deselected. No defecto de producto en ese fallo.

Dos fallos previos del capturador (filtro dentro de navegación cerrada y selector de texto ambiguo)
se corrigieron en el script; ejecución final `capture_ui.py after`: 11 capturas, cero errores JS.
También se corrigió codificación de textos nuevos producida por el pipe ASCII de PowerShell.
Ningún hallazgo alto/medio abierto en el alcance revisado; pendientes de accesibilidad externos
se detallan sin certificar conformidad total. G6 ejecuta la suite acumulada final.

## G6 — Verificación acumulada y cierre local

2026-11-03, Python 3.12.15, PostgreSQL 16, dependencias bloqueadas.
Comando PowerShell ejecutado en CODIGOS:

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:55432/postgres'
.venv/Scripts/python.exe -m pytest -q --basetemp .tools/pytest-g6
.venv/Scripts/python.exe -m ruff check src tests scripts
node tests/google_forms_script.cjs
uv pip check --python .venv/Scripts/python.exe
```

Resultados: **58 passed, 6 warnings**, 7.70 s. Incluye las 37 pruebas anteriores y 21 nuevas.
[Salida pytest](g_pytest.txt). Ruff: **All checks passed**. Sender JS: **8 escenarios pasan**,
incluido contenido UTF-8. `uv pip check`: **77 paquetes compatibles**. Reinstalación editable
comprobada tras actualizar pyproject y dependencias. `python -m pip check` no se ejecuta en
este venv de uv porque no instala pip; se utilizó su equivalente `uv pip check`.

Ruff incorpora configuración propia E4/E7/E9/F; se limpiaron imports/variables no usados
preexistentes para pasar el chequeo acumulado. Import de fixtures sigue posterior a configurar
la base temporal, con justificación E402. Sin cambio de esquema ni migraciones nuevas.
Avisos pendientes: deprecaciones de TestClient/httpx, WSGIMiddleware, Dash DataTable y constante 422.
No impiden las pruebas actuales. No se actualizó ninguna biblioteca para ocultarlos.

La revisión visual final generó 21 capturas en total y las inspeccionó; no se exponen secretos
ni datos personales. Los únicos datos persistidos durante pruebas son sintéticos en bases
creadas específicamente y eliminadas al terminar. PostgreSQL de uso existente en 5432 intacto.
No se publicó, abrió túnel ni envió correo externo.

### Puertas pendientes del propietario

- Ejecutar createForm/installTriggers en su cuenta Google, revisar y publicar el borrador.
- Proporcionar API HTTPS operativa y secreto compartido en propiedades privadas.
- Generar el QR definitivo con URL/entry ID reales y escanearlo en teléfono.
- Enviar respuesta desde Forms y confirmar registro/origen en dashboard y eliminación en Forms.

Estas puertas NO se marcan aprobadas. La implementación local G0–G6 queda entregada;
la aceptación extremo a extremo real está pendiente. PostgreSQL es la fuente del dashboard;
Forms almacena temporalmente hasta confirmar recepción, sin Sheets, como documenta D11.


## Arranque local solicitado por el usuario

Servidor dejado en ejecución en http://localhost:8071/dashboard/.
Se creó configuración privada .env y una base persistente nueva qrlabhub_dev en pgdata,
con contraseña aleatoria y escucha exclusiva 127.0.0.1:55432. La instancia 5432 y la app 8070
no se tocaron. Se corrigió start-local.ps1 para uv y PostgreSQL 16 instalado.

Verificación ejecutada: start-local.ps1 -NoBrowser terminó correctamente; /health/ready
respondió ready/database connected; /dashboard/ devolvió HTTP 200; /api/v1/stats devolvió
cero registros (base nueva, sin datos de pruebas). API 8071, PostgreSQL 55432 y SMTP 1025
escuchan solo en 127.0.0.1. Proceso de aplicación independiente, guardado en storage/local.pid.
Correos externos deshabilitados; Google Forms sin configurar hasta activar cuenta y HTTPS.
Reabrir mediante Iniciar QR Lab.cmd; detener app mediante stop-local.ps1.
