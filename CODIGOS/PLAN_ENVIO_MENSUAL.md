# Plan Codex: envío automático mensual del resumen de formularios

Orquestador: Claude. Implementador: Codex. Leer antes: `AGENTS.md`, `docs/ESTADO.md`, `docs/CONTRATOS.md` (sección "Envío mensual y concurrencia"), `docs/PRUEBAS.md`.

## Objetivo

Una vez al mes, sin intervención, enviar por correo a los destinatarios configurados el resumen del mes calendario cerrado anterior, solo con registros de formularios (`source="google_forms"`), con cifras iguales a las del dashboard filtrado por ese origen.

## Punto de partida: reutilizar, no reescribir

Ya existen y se conservan:
- `jobs/monthly_report.py`: `process_monthly_report`, `run_daily_check`, `refresh_monthly_reports`.
- `reports/mailer.py`: entrega por destinatario, estados `pending/sending/sent/failed/uncertain`, Message-ID, inyección de `smtp_client`.
- `reports/generator.py`: `build_monthly_pdf`.
- `services/aggregations.py`: `get_aggregations(..., source=...)`.
- `local_runtime.py`: supervisor que llama `run_daily_check` y `refresh_monthly_reports`.
- `services/locks.py`: `report_lock`.

No crear un segundo generador, otra tabla de envíos ni un cálculo de agregación paralelo.

## Brechas a resolver

| # | Brecha actual | Consecuencia si no se corrige |
|---|---|---|
| B1 | `run_daily_check` procesa todos los meses cerrados desde `REPORT_INITIAL_MONTH` (2026-01) | Al activar correo real se envían de golpe todos los meses atrasados |
| B2 | `process_monthly_report` no filtra por origen (agregación y `records`) | El resumen mezcla registros manuales con formularios |
| B3 | `refresh_monthly_reports` crea revisión nueva si cambia el snapshot, y `run_daily_check` reenvía si la última revisión no tiene entregas | Un dato tardío en un mes cerrado provoca un correo no planificado |
| B4 | Día y hora fijos en código (`now.day == 1 and now.hour < 8`) | No configurable |
| B5 | `_send_report_email` envía el correo aunque falte el PDF | Correo sin adjunto marcado `sent` |
| B6 | `failed` con 3 intentos y `uncertain` quedan sin aviso; `EMAIL_ENABLED=false` deja `pending` en silencio | Mes no entregado sin que nadie lo note |
| B7 | Supervisor solo corre con el lanzador abierto; no hay inicio automático | Sin envío si el equipo está apagado o nadie abrió el lanzador |
| B8 | Solo `smtplib.SMTP` con STARTTLS opcional; login sin exigir TLS | Credenciales podrían viajar sin cifrar |

## Fases

### M0. Contrato
Actualizar `docs/CONTRATOS.md` y `docs/DECISIONES.md` antes de tocar código:
- Periodo enviado: mes calendario cerrado anterior, en `America/Santiago`.
- Regla "una vez por periodo": un periodo con al menos una entrega `sent` a un destinatario no se reenvía a ese destinatario, aunque aparezca una revisión nueva.
- Dato tardío: crea revisión visible en `/reports`, sin correo automático. Reenvío solo manual.
- Mes sin respuestas: se envía igualmente, indicando que no hubo respuestas.

### M1. Configuración (`config.py`, `.env.example`)
- `REPORT_SEND_DAY: int = 1` (validar 1 a 28, así existe en todos los meses).
- `REPORT_SEND_HOUR: int = 8` (hora local, validar 0 a 23).
- `REPORT_SOURCE: str = "google_forms"` (validar contra `manual`, `google_forms`, `esp32`; vacío = todos).
- `REPORT_AUTO_SEND_FROM: str` (YYYY-MM, primer periodo elegible para envío automático; sin valor, el envío automático no envía nada y lo registra). Resuelve B1. No reutilizar `REPORT_INITIAL_MONTH`, que sigue definiendo el archivo histórico.
- Sin secretos en `.env.example` ni en Markdown.

### M2. Programación y selección de periodos (`jobs/monthly_report.py`)
- `run_daily_check`: solo enviar a partir de `REPORT_SEND_DAY` y `REPORT_SEND_HOUR` locales, comparando fecha y hora completas: si el equipo estuvo apagado ese día, el envío ocurre en la primera ejecución posterior.
- Periodos elegibles para envío: cerrados y `>= REPORT_AUTO_SEND_FROM`. Los anteriores se archivan sin correo.
- Aplicar regla "una vez por periodo" consultando entregas de todas las revisiones del periodo. Resuelve B3.
- Inyectar reloj (`now`) para pruebas, en lugar de la rama `reference_date is None`.
- Conservar `report_lock`: dos procesos simultáneos producen un solo envío.

### M3. Filtro por origen
- Pasar `source=settings.REPORT_SOURCE` a `get_aggregations` y filtrar igual la consulta `rows` en `_process_monthly_report`.
- Guardar `report_source` en el snapshot. Título del PDF y asunto del correo indican "Formularios".
- Los snapshots antiguos no llevan esa clave: al comparar, la diferencia genera una revisión nueva sin correo. Verificar que no dispare envíos (M2) y documentarlo.
- `refresh_monthly_reports` y `/reports` deben quedar coherentes con el mismo filtro; no debe alternar revisiones entre dos variantes cada 15 s.

### M4. Contenido del correo (`reports/mailer.py`)
- Cuerpo con resumen en texto: periodo, cantidad de respuestas, kg totales, principal tipo, material, máquina y causa, y comparación con el mes anterior. Los valores salen del snapshot; no recalcular.
- PDF adjunto obligatorio: si falta o está vacío, estado `failed` con error claro y sin enviar. Resuelve B5.
- Sin datos personales: el importador ya excluye nombre y correo; verificarlo en una prueba.

### M5. Transporte y seguridad SMTP
- Agregar `SMTP_SSL: bool = False` para puerto 465 (`smtplib.SMTP_SSL`).
- Con `SMTP_USERNAME` definido, exigir TLS o SSL; si no, error de configuración antes de conectar. Excepción: loopback con `LOCAL_SMTP_ENABLED`. Resuelve B8.
- No registrar contraseña; revisar que `error_summary` no la incluya.
- Documentar en `README.md` cómo crear `.env` con SMTP institucional o contraseña de aplicación. Correo real solo con `EMAIL_ENABLED=true`, activado por el propietario.

### M6. Visibilidad de fallos
- `/reports` y dashboard: estado del último envío por periodo (`sent`, `pending`, `failed`, `uncertain`), próxima fecha programada, y aviso visible si `EMAIL_ENABLED=false`.
- `uncertain`: acción manual "confirmar enviado" o "reenviar", protegida con `require_admin` y CSRF según contrato. Nunca reenvío automático.
- Log estructurado por ejecución, sin destinatarios completos ni secretos. Resuelve B6.

### M7. Ejecución sin lanzador abierto
- `scripts/instalar_tarea_mensual.ps1`: registra una tarea de Windows diaria con "ejecutar lo antes posible si se omitió" (`-StartWhenAvailable`), que levanta PostgreSQL si hace falta y ejecuta una sola pasada de `run_daily_check`. Incluir `scripts/desinstalar_tarea_mensual.ps1`.
- Nuevo punto de entrada `python -m lab_hub.jobs.monthly_report` con código de salida distinto de 0 ante error.
- El script no se ejecuta durante la implementación: lo instala el propietario. Documentar el límite: con el equipo apagado no hay envío hasta el siguiente encendido; para puntualidad garantizada hace falta un servidor. Resuelve B7.

### M8. Pruebas y evidencia
`tests/test_monthly_send.py`, con reloj y `smtp_client` inyectados, usando la base de pruebas aislada:
- Antes del día y hora: no envía. En el momento exacto: envía. Equipo apagado el día 1 y encendido el 5: envía una vez.
- Ejecuciones repetidas en el mismo mes: un solo correo por destinatario. Dos procesos simultáneos: un solo correo.
- Activación con historial: nada anterior a `REPORT_AUTO_SEND_FROM` se envía; sin ese valor, no se envía nada.
- Solo incluye `google_forms`; registros manuales no alteran cifras. Igualdad exacta con `get_aggregations(source="google_forms")` y dashboard.
- Dato tardío: nueva revisión, sin correo.
- Mes vacío, febrero, cambio de año y cambio de horario de Chile.
- Sin PDF: `failed`, nada enviado. Fallo de un destinatario: los demás reciben y solo ese se reintenta. Corte SMTP: `uncertain`, sin reenvío.
- Login sin TLS rechazado. `EMAIL_ENABLED=false`: sin envío y aviso visible.

Ejecutar suite completa y `ruff`. Prueba de extremo a extremo con el SMTP local (`127.0.0.1:1025`) y revisión visual del PDF. Guardar salida en `docs/evidencias/envio_mensual.md`; actualizar `docs/ESTADO.md`.

## Puertas de salida
- Suite verde, sin regresiones. Correo capturado en SMTP local con PDF correcto y cifras iguales al dashboard.
- Pendiente del propietario, no declarable por Codex: credenciales SMTP, `EMAIL_ENABLED=true`, instalar tarea y confirmar recepción real.

## Reglas para Codex
- El árbol de trabajo tiene cambios sin commit y PDF de `BITACORA/` figuran borrados: no revertir, restaurar, limpiar ni hacer commit de nada ajeno a este plan.
- No enviar correo externo. Solo SMTP local o `smtp_client` simulado.
- Probar solo con la base de pruebas; no modificar la base de uso ni registros reales.
- No declarar verificaciones sin ejecutarlas.

## Fuera de alcance
Despliegue en servidor, SSO, ESP32, cambios en Forms o Sheets, informes semanales por correo.

## Prompt para Codex

> Implementa `PLAN_ENVIO_MENSUAL.md` fase por fase (M0 a M8) en `CODIGOS/`. Respeta `AGENTS.md` y las reglas del plan. Reutiliza los módulos existentes. Actualiza contratos antes del código. Al cerrar cada fase, ejecuta pruebas, registra evidencia y actualiza `docs/ESTADO.md`. No envíes correo externo, no instales la tarea programada, no hagas commit y no toques archivos ajenos. Si algo del plan contradice el código actual, detente en ese punto e infórmalo.
