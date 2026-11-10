# Estado de QR Lab Hub

- 2026-11-09, revisión de rediseño ciclo 1: R-01–R-04 corregidos en cuatro commits; comparaciones por calendario, página reiniciada/limitada correctamente, Origen de 18 px y caché de tokens. 138 pruebas PostgreSQL aprobadas; Ruff limpio; Chromium verifica filtrado desde página 3, hover y cuatro tamaños. Turno Opus; sin cambios de spec, despliegue ni envíos reales. Evidencia: `redesign/codex/evidencias/review-pytest.txt`.

- 2026-11-09: rediseño de dashboard v2 implementado en `redesign/codex`, CA-01–CA-23 verificados. 124 pruebas PostgreSQL aprobadas; Ruff limpio; Chromium 320/390/768/1440 px sin overflow. CSV, paginación de 25 filas, deltas y errores con datos conservados. Paleta validada, textos UTF-8. Turno Opus para revisión; commits locales sin despliegue ni envíos reales. Evidencia: `redesign/codex/implementacion.md`.

- 2026-11-09: prueba externa autorizada por el propietario enviada por Gmail STARTTLS al destinatario configurado. Informe noviembre revisión 3, 3 respuestas, 0.090 kg; entrega `sent`, un intento. Mensaje creado 17:35 UTC. Aceptación SMTP confirmada; llegada a bandeja pendiente de comprobación del propietario. Corregidos booleano LOCAL_SMTP_ENABLED y transporte Gmail 587/TLS en .env privado sin imprimir secretos. No se instaló tarea ni reinició el supervisor; se preservó configuración de automatización existente.

- 2026-11-09, Gmail: credenciales presentes y autenticación SMTP 235 confirmada con STARTTLS. Corregidos booleano y transporte en .env (Gmail 587/TLS); secretos conservados y archivo ignorado por Git. 38 pruebas locales pasan, Ruff focalizado limpio. No se envió correo externo ni se reinició aplicación. REPORT_AUTO_SEND_FROM continúa vacío; recepción real y automatización pendientes. Evidencia: `evidencias/gmail_autenticacion_2026_11_09.md`.

- 2026-11-09: envío local revalidado, 53 pruebas pasan y Ruff focalizado limpio. Captura SMTP 1025 con PDF y concurrencia correctas. El .env efectivo sigue en SMTP local: sin usuario/contraseña Gmail, EMAIL_ENABLED=false y REPORT_AUTO_SEND_FROM vacío. Autenticación/recepción Gmail sin verificar; configuración privada y base de uso intactas. Evidencia: `evidencias/gmail_local_2026_11_09.md`.

- Corrección `/reports`: plantilla nueva fallaba con worker antiguo por `monthly_delivery` ausente. Añadida compatibilidad y prueba de regresión; tres pruebas focalizadas pasan, Ruff limpio. Aplicación local reiniciada sin parar PostgreSQL ni activar correo externo. HTTP 200 y clic desde dashboard verificados en Chromium. Evidencia: `evidencias/reports_internal_error.md`.

- Envío mensual M0–M8 implementado y validado localmente: 103 pruebas pasan (37 nuevas), seis avisos de deprecación. Ruff limpio en src/tests/scripts; dos E402 previos en migrations/env.py fuera del cambio. SMTP 1025, dos procesos, PDF de dos páginas y Chromium escritorio/móvil verificados con PostgreSQL desechable. Activación explícita, filtro Forms, revisión sin reenvío, PDF obligatorio, SSL/TLS y conciliación CSRF. Reintentos históricos sin origen usan PDF filtrado conservando intentos. Tarea sin instalar; correo externo sin activar; .env y base de uso sin modificar. Pendiente del propietario: SMTP, REPORT_AUTO_SEND_FROM, EMAIL_ENABLED=true, instalar tarea y recepción real. Evidencia: `evidencias/envio_mensual.md`.

- Mensuales corregidos: comparan snapshot actual antes de reutilizar PDF y crean nueva revisión si cambia. Supervisor actualiza meses con registros, mes actual y meses archivados cada 15 s, sin correo durante refresco. Noviembre 2026 revisión 2: 3 registros, 90 g, igual al dashboard; PDF revisado visualmente y descarga HTTP 200. 66 pruebas pasan; Ruff limpio.

- Archivo semanal automático activo en `/reports`: semanas ISO lunes-domingo, refresco 15 s, snapshots PostgreSQL y PDF versionado solo cuando cambian datos. Incluye Forms/Sheets y registros manuales; mantiene historial y mensuales. Semana 2026W45 verificada contra dashboard: 3 registros, 90 g. PDF de dos páginas revisado visualmente, descarga HTTP 200. 65 pruebas pasan, Ruff limpio. Evidencia: `evidencias/weekly_reports.md`.

- Importación automática confirmada: supervisor importó la segunda respuesta sin ejecutar importación manual. Añadida opción real `Pieza fallida` (`failed_part`) al catálogo reproducible. Estado: 1 creado, 1 existente, cero rechazos; dashboard 2 respuestas y 0.060 kg. 63 pruebas pasan; Ruff limpio. Respuestas compatibles aparecen en aproximadamente 75 s mientras el lanzador siga abierto en segundo plano.

- Normalización Sheets actualizada: selecciones múltiples de opciones conocidas se muestran como categorías conjuntas; un peso y un registro por respuesta. Alias de causa normalizados. Respuesta real importada: 1 registro, 30 g; reintento sin duplicados. Retirado registro ficticio manual de 200 g con respaldo local en storage/uploads. 62 pruebas pasan y Ruff limpio. Este avance supera el rechazo de fila descrito en notas anteriores.

- 2026-11-08: importador Sheets local activo, lectura cada 60 s, PostgreSQL como fuente del dashboard (refresco 15 s). Excluye nombre/correo. Idempotencia y fecha de respuesta conservadas. 61 pruebas pasan con periodo inicial de pruebas 2026-01; Ruff limpio. HTTP ready y dashboard 200 tras reinicio.
- Aceptación real pendiente: fila 2 tiene selección múltiple para un peso único y se rechaza por material. Configurar una opción por dimensión y nombres compatibles con catálogos, enviar respuesta nueva. No se modificó Forms ni Sheets. Evidencia: `evidencias/sheets_local.md`; plan vigente: `../plan.md`.

- Sheets: último reintento correcto, acceso de solo lectura y nueve encabezados detectados. Cero respuestas; pendiente respuesta sintética y mapeo para integración. Superado bloqueo `SERVICE_DISABLED`. Ver `../plan.md`.

- Diagnóstico Sheets actualizado: credenciales cargan; apertura por URL devuelve HTTP 403 `SERVICE_DISABLED` para `sheets.googleapis.com`. Habilitar Google Sheets API en el proyecto de la cuenta de servicio y repetir prueba. No es un fallo de permisos del JSON local.

- 2026-11-08, Sheets: gspread 6.2.1 instalado; 87 paquetes compatibles. `probar.py` comprueba acceso de solo lectura sin mostrar respuestas. Credenciales renombradas a nombre esperado y excluidas de Git. Prueba bloqueada por PermissionError al autenticar; falta URL de Sheets y encabezados. Dashboard sin cambios. Avance en `../plan.md`.

- Actualizado: 2026-11-03.
- Corrección posterior: 8070 ocupado por SmartAgro. QR Lab verificado en http://localhost:8071/dashboard/.
- Lanzador detecta puertos ocupados y busca hasta 8090; puerto actual guardado en `storage/local.port`.
- Operación local reparada: http://localhost:8070/dashboard/; lanzador `Iniciar QR Lab.cmd`.
- Entorno: Python 3.12.14, PostgreSQL 16.3, dependencias bloqueadas en `requirements.lock.txt`.
- Verificación anterior (2026-10-19): 37 pruebas pasan; pip check sin incompatibilidades; cinco registros originales conservados (2.100 kg).
- 15 PDF descargables y 10 mensajes capturados por SMTP local; sin envío externo.
- Arranque/parada comprobados; puertos 8070, 5432 y 1025 escuchan solamente en 127.0.0.1.
- Backup restaurado en base temporal: cinco registros; base temporal eliminada.
- Evidencia actual y límites: [operación local](evidencias/local_2026_10_19.md).
- UI revisada mediante DOM; captura visual del navegador no disponible por fallo del proveedor. PDF de dos páginas revisado visualmente.
- Tras reiniciar Windows, abrir nuevamente el lanzador. No se configuró inicio automático.
- Fase activa: MVP Completado (F0 a F6 superadas). F7 opcional pendiente para hardware real.
- Implementador: Antigravity.
- F0 superada: entorno reproducible, PostgreSQL 16 portable local, tzdata, FastAPI y salud en [evidencia](evidencias/f0_base.md).
- F1 superada: modelos SQLAlchemy, migraciones Alembic, catálogos sintéticos en [evidencia](evidencias/f1_datos.md).
- F2 superada: formulario QR móvil, validación y POST idempotente en [evidencia](evidencias/f2_registro.md).
- F3 superada: agregación centralizada, API administrativa y dashboard Dash oscuro verde en [evidencia](evidencias/f3_dashboard.md).
- F4 superada: snapshot mensual, PDF con ReportLab/Matplotlib, despacho SMTP local y recuperación en [evidencia](evidencias/f4_informes.md).
- F5 superada: suite completa 27/27, recorrido completo T22 y concurrencia sin defectos en [evidencia](evidencias/f5_depuracion.md).
- F6 superada: documentación operativa, arranque, backup/restore comprobado (T21) y PDF de muestra en [evidencia](evidencias/f6_entrega.md).
- Decisiones registradas: D01 a D08 en [decisiones](DECISIONES.md).
- CodeGraph: no existía `.codegraph/`. Sin índice. Búsquedas directas.
- Pruebas acumuladas actuales: 58 pruebas pasadas, seis avisos de deprecación (G6).
- Pendientes externos para producción: catálogos reales del laboratorio, credenciales SMTP institucionales, autenticación universitaria / SSO y balanza ESP32 (F7).
- Bloqueos: ninguno. Sistema MVP funcional y verificable localmente.

Actualizar al terminar cada fase. Mantener menos de 100 líneas. Guardar decisiones en su documento y evidencia extensa fuera de esta nota.

## Extensión Google Forms + UI/UX (2026-11-03)

- Implementación local G0–G6 entregada en orden. Sin migración; HMAC, Decimal e idempotencia reutilizados.
- 58 pruebas pasan en PostgreSQL aislado; Ruff limpio; 8 escenarios JS; 77 paquetes compatibles.
- G5: auditoría y mejoras altas/medias implementadas; 21 capturas antes/después, Chromium sin errores JS.
- Cuenta Google, HTTPS, envío real y QR definitivo/escaneo pendientes; aceptación externa sin cerrar.
- Forms retiene temporalmente respuestas hasta ACK; dashboard consulta solo PostgreSQL. Sin Sheets.
- Instancia de uso 5432 sin modificar; pruebas en loopback 55432 y bases temporales eliminadas.
- Evidencia: [Google Forms](evidencias/g_google_forms.md); [auditoría](UIUX_AUDITORIA.md).
- Siguiente paso del propietario: [activar integración](../integrations/google_forms/README.md).

- Arranque actual: http://localhost:8071/dashboard/ en ejecución; salud y HTTP 200 verificados.
- Base local persistente nueva en pgdata, puerto 55432, cero registros; .env privado creado.
- Lanzador compatible con uv/PostgreSQL instalado; correo externo deshabilitado.
