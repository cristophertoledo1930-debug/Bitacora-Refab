# Integración local Sheets — 2026-11-08

## Confirmación de importación automática

Se detectó una segunda respuesta pendiente por tipo `Pieza fallida`, ausente del catálogo. Se añadió la opción real como `failed_part` en los catálogos reproducibles; prueba de idempotencia de semillas actualizada para comprobar códigos e identidad.

Tras reiniciar mediante el lanzador, el supervisor importó automáticamente la respuesta: estado `created=1`, `existing=1`, `rejected=[]`. No se invocó `sync_once` manualmente para esa respuesta. Callback del dashboard confirma dos filas de origen Google Forms y KPI 0.060 kg. Suite completa: 63 passed, 6 warnings con periodo inicial de pruebas 2026-01; Ruff sin errores.

La automatización funciona mientras el supervisor local permanece activo. Consulta cada 60 segundos y Dash refresca cada 15 segundos. Tras reiniciar Windows hay que abrir `Iniciar QR Lab.cmd`. Opciones nuevas ajenas al catálogo requieren incorporarlas; no se inventan categorías a partir de texto desconocido.

## Actualización: selecciones múltiples y limpieza

El propietario solicitó retirar el dato ficticio y normalizar la respuesta existente para los gráficos. Se reconocen opciones múltiples conocidas como categoría conjunta; no se reparte ni se duplica el peso. Se incorporaron alias explícitos para causas, además de normalización de acentos y espacios.

- Importación real: un registro creado, sin rechazos. Peso 30.000 g. Segundo intento: cero creados, uno existente.
- Eliminado exclusivamente el registro manual ficticio identificado de 200.000 g. Copia recuperable en `storage/uploads/removed_fictitious_200g.json`, excluida de Git.
- Base de uso tras limpieza: un registro de Sheets, 30.000 g.
- Callback real del dashboard: KPI 1 registro, 0.030 kg; tabla con una fila de 30.000 g. Gráficos por máquina y material suman 0.03 kg cada uno, agrupado por combinación.
- Supervisor reiniciado: estado `Sheets sincronizado`; dashboard HTTP 200 y health ready con base conectada.
- Suite completa: 62 passed, 6 warnings, con `REPORT_INITIAL_MONTH=2026-01` y temporales `.tools/pytest-joint-full`. Ruff sobre src/tests/probar.py sin errores.
- Prueba nueva verifica aliases, categorías conjuntas, masa total invariable y reenvío sin duplicados.

Las secciones siguientes describen la primera implementación; el rechazo de selecciones múltiples queda superado por esta actualización. Las respuestas de Google no se modificaron.

## Implementación

`services/sheets.py` lee Sheets sin permisos de escritura. El supervisor local importa a PostgreSQL cada 60 segundos. El dashboard conserva sus consultas y refresco de 15 segundos, y muestra estado de sincronización. No se almacenan nombre ni correo, ni se imprimen respuestas completas. No se cambió el esquema de base de datos.

Cada fila válida se confirma individualmente. Clave idempotente derivada de hoja, pestaña y posición; cambio posterior de payload produce rechazo. Requiere hoja acumulativa sin reordenar. Fechas locales se convierten a UTC; pesos usan Decimal. Valores desconocidos no crean catálogos.

## Verificación ejecutada

- Cuenta de servicio: lectura real correcta mediante Google Sheets API.
- Importación real: cero creados, cero existentes, fila 2 rechazada por material. La respuesta incluye múltiples opciones para dimensiones con un solo peso; no se repartió ni duplicó el peso.
- `uv pip check --python .venv/Scripts/python.exe`: 87 paquetes compatibles.
- `REPORT_INITIAL_MONTH=2026-01` en el proceso de pruebas; `.venv/Scripts/python.exe -m pytest -q --basetemp .tools/pytest-sheets-verified`: 61 passed, 6 warnings. Base PostgreSQL nueva y desechable mediante fixture existente.
- Sin ese ajuste inicial se detectó un fallo en prueba histórica de informes dependiente del periodo inicial configurado localmente. Sin `--basetemp` local, Temp de Windows rechazó acceso. Segunda ejecución usa configuración y temporales de pruebas explícitos; no cambió el periodo del entorno de uso.
- `.venv/Scripts/python.exe -m ruff check src tests probar.py`: correcto.
- Nuevas pruebas: gramos exactos desde kg con coma decimal, fecha UTC, reenvío sin duplicados incluso al cambiar información personal, conflicto tras editar peso, fila inválida seguida de válida, catálogo desconocido y encabezados incompletos.
- Reinicio con `stop-local.ps1` y `start-local.ps1 -NoBrowser`; health ready con base conectada y dashboard HTTP 200 en 8071.
- Estado local escrito por supervisor: fila 2 pendiente por material. Callback del dashboard devuelve aviso de una fila pendiente con hora local.

## Pendiente de aceptación

Cambiar preguntas de material, máquina y causa a selección única. Alinear sus opciones con catálogos activos. Enviar una respuesta nueva compatible y comprobarla en tabla, métricas y gráficos tras un máximo aproximado de 75 segundos con la app abierta.

No se modificaron preguntas ni respuestas de Google. No se publicó, abrió túnel, habilitó correo externo ni activó el envío directo Apps Script. No se declara completada la prueba real hasta recibir una respuesta compatible.
