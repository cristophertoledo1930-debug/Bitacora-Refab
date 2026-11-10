# QR Lab Hub — Sistema de Registro y Reportería de Residuos

## Importación local de Google Sheets

Los datos ya importados también se archivan automáticamente en [informes semanales](http://localhost:8071/reports). Cada semana abarca lunes a domingo en hora de Chile. El supervisor revisa cambios cada 15 segundos, genera una nueva revisión PDF cuando cambian los datos y conserva el historial. La página se refresca sola; la semana en curso es provisional. No se envía correo semanal. Funciona mientras el lanzador local permanezca activo.

Configurar `GOOGLE_SHEETS_ID`, `GOOGLE_SHEETS_TAB` y `GOOGLE_SHEETS_CREDENTIALS` en `.env`. Colocar la clave privada local en `credenciales.json` (excluido de Git). Habilitar Google Sheets API y compartir la hoja como Lector con la cuenta de servicio.

El lanzador local consulta Sheets cada 60 segundos e importa filas válidas a PostgreSQL; el dashboard actualiza cada 15 segundos. No requiere URL pública. No guarda nombre ni correo. Selecciones múltiples se muestran como categorías conjuntas: se conserva un registro y su peso total g/kg, sin repartirlo entre componentes. No reordenar ni borrar filas importadas. No combinar con entrega directa Apps Script del mismo formulario.

El dashboard muestra sincronización pendiente si hay errores. Detalles operativos en [plan vigente](plan.md) y [evidencia](docs/evidencias/sheets_local.md). Ejecución manual: `.venv/Scripts/python.exe -m lab_hub.services.sheets`.

Sistema Python para registro de residuos de laboratorio universitario mediante formulario abierto desde código QR, persistencia en PostgreSQL, dashboard estadístico en Dash (tema oscuro verde) e informe mensual en PDF despachado por correo.

---

## Arranque local verificado (2026-10-19)

**Puerto actual: http://localhost:8071/dashboard/**. SmartAgro ocupa 8070.
El lanzador usa 8071 y, si pertenece a otra aplicación, elige el siguiente puerto libre hasta 8090.
Abre automáticamente la dirección correcta y guarda el puerto en `storage/local.port`.

Abra `Iniciar QR Lab.cmd`, o ejecute desde esta carpeta:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-local.ps1
```

Inicia PostgreSQL portable, aplica migraciones, verifica catálogos y deja API/Dash en segundo plano en **http://localhost:8070/dashboard/**.
También inicia SMTP en `127.0.0.1:1025` y un proceso independiente de recuperación de informes cada cinco minutos.
El primer día del mes no procesa el nuevo periodo cerrado antes de las 08:00 de Santiago.

- Registro: http://localhost:8070/r/token-general
- Informes y descargas: http://localhost:8070/reports
- API: http://localhost:8070/docs
- Correo capturado: `storage/mail/*.eml`, sin entrega externa.
- Logs: `storage/logs/app-error.log` y `storage/logs/postgres.log`.
- Detener API, SMTP y job: `powershell -NoProfile -ExecutionPolicy Bypass -File .\stop-local.ps1`.
- PostgreSQL se conserva activo; detenerlo si corresponde con `.\.tools\pgsql\bin\pg_ctl.exe -D pgdata -m fast -w stop`.

`LOCAL_DESKTOP_ACCESS=true` permite administrar desde este equipo en modo desarrollo. El servidor escucha solamente en loopback.
Otros clientes requieren `X-Admin-Key` o `admin_session`. No es un despliegue en red ni configura acceso desde teléfonos externos.
`LOCAL_SMTP_ENABLED=true` exige SMTP loopback; `EMAIL_ENABLED=false` mantiene deshabilitado el correo externo.

El entorno reparado utiliza Python 3.12.14 del runtime disponible en este equipo. `.venv` no se puede trasladar entre equipos.
Para reconstruirlo con un Python 3.12 instalado:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock.txt
.\.venv\Scripts\python -m pip install --no-deps -e .
```

`requirements.lock.txt` contiene las versiones instaladas y probadas. PostgreSQL 16.3 requiere sus DLL de Visual C++:
en este entorno se copiaron `vcruntime140.dll`, `vcruntime140_1.dll` y `msvcp140.dll` desde el runtime local a `.tools/pgsql/bin`.
En otro equipo se puede instalar el [runtime oficial de Microsoft](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).
La configuración de prefijos de Dash sigue su [referencia oficial](https://dash.plotly.com/reference).

Ejecute pruebas con `.\.venv\Scripts\python -m pytest -q`. El fixture crea una base PostgreSQL nueva por ejecución,
aplica migraciones y la elimina al terminar. Nunca ejecuta los borrados de pruebas sobre `qrlabhub_dev`.
Los informes de pruebas se guardan separadamente en `storage/test-reports`.
Existe un respaldo previo a esta reparación en `.tools/backup_before_local.dump`.

Los enlaces absolutos de informes trasladados se recuperan solamente si su archivo local coincide con el SHA-256 registrado.
El supervisor funciona mientras esté iniciado; tras reiniciar Windows, abra nuevamente `Iniciar QR Lab.cmd`.

---

## 1. Arquitectura y Tecnologías

- **API y Formulario Móvil:** FastAPI, Pydantic, Jinja2, CSS responsive móvil-primero.
- **Persistencia:** PostgreSQL 16, SQLAlchemy 2, Alembic (migraciones versionadas).
- **Dashboard Estadístico:** Dash, Plotly, motor de agregaciones compartido con Reportes.
- **Informes Mensuales:** ReportLab con gráficos estáticos de alta resolución mediante Matplotlib.
- **Correo (SMTP):** Biblioteca estándar `smtplib` con seguimiento por destinatario y estado `uncertain`.
- **Huso Horario:** `America/Santiago` con conversión consciente a UTC y soporte de horario de verano.
- **Pesos:** Manejo exacto con `Decimal` en gramos (`NUMERIC(12, 3)` con `CHECK (weight_g > 0)`).

---

## 2. Requisitos y Entorno Local

- **Python:** 3.12 (o >= 3.11).
- **PostgreSQL:** Versión 16 (incluye binarios portables en `.tools/pgsql` para Windows o conexión local estándar).
- **Variables de Entorno:** Archivo `.env` (basado en `.env.example`).

---

## 3. Guía Rápida de Arranque (Quickstart)

### Paso 1: Configurar entorno virtual y dependencias
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### Paso 2: Iniciar PostgreSQL
Si usa el clúster local portable de Windows:
```powershell
.\.tools\pgsql\bin\postgres.exe -D pgdata
```
*(O ejecute su servicio habitual de PostgreSQL en el puerto 5432).*

### Paso 3: Aplicar migraciones y cargar catálogos sintéticos
```powershell
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python -c "from lab_hub.db.session import SessionLocal; from lab_hub.services.seeds import seed_catalogs; db = SessionLocal(); seed_catalogs(db); db.close()"
```

### Paso 4: Iniciar la aplicación (API + Dashboard)
```powershell
.\.venv\Scripts\uvicorn lab_hub.api.app:app --host 127.0.0.1 --port 8070
```

---

## 4. Recorridos y Enlaces del Sistema

- **Formulario QR Estación Láser 1:**  
  `http://localhost:8070/r/token-laser-01`
- **Formulario QR Estación SLA 1:**  
  `http://localhost:8070/r/token-sla-01`
- **Formulario QR General:**  
  `http://localhost:8070/r/token-general`
- **Dashboard Oscuro Verde:**  
  `http://localhost:8070/dashboard/`
- **Healthchecks:**  
  - Liveness: `http://localhost:8070/health/live`  
  - Readiness: `http://localhost:8070/health/ready`
- **Documentación OpenAPI interactiva:**  
  `http://localhost:8070/docs`

---

## 5. Tarea Programada (Informe Mensual)

Para ejecutar la verificación diaria y generación del informe del mes anterior:
```powershell
.\.venv\Scripts\python -c "from lab_hub.db.session import SessionLocal; from lab_hub.jobs.monthly_report import run_daily_check; db = SessionLocal(); runs = run_daily_check(db); print('Procesados:', len(runs)); db.close()"
```
Los PDFs generados se almacenan en `storage/reports/`. Existe una muestra de informe en `docs/evidencias/informe_muestra_2026_01.pdf`.

---

## 6. Procedimiento de Respaldo y Restauración (T21)

### Respaldo:
```powershell
.\.tools\pgsql\bin\pg_dump.exe -U postgres -d qrlabhub_dev -F c -f backup_qrlabhub.dump
```

### Restauración:
```powershell
.\.tools\pgsql\bin\createdb.exe -U postgres qrlabhub_restaurada
.\.tools\pgsql\bin\pg_restore.exe -U postgres -d qrlabhub_restaurada backup_qrlabhub.dump
```

---

## 7. Ejecución de Pruebas

Para ejecutar la suite completa de 37 pruebas automatizadas:
```powershell
.\.venv\Scripts\pytest -v
```

---

## 8. Pendientes Externos para Producción

1. **Catálogos Reales:** Validar con los encargados de laboratorio los nombres de máquinas, tipos y causas definitivas.
2. **Infraestructura SMTP:** Proveer servidor SMTP institucional, usuario, contraseña y remitente autorizado antes de habilitar `EMAIL_ENABLED=true`.
3. **Balanza ESP32 (Fase F7 opcional):** Protocolo de comunicación, autenticación de dispositivo y calibración de hardware.
4. **Política de Acceso y Red:** Integración con Single Sign-On (SSO) o autenticación universitaria para administradores y despliegue bajo HTTPS.



## Google Forms, QR y nueva UI

Integración local implementada siguiendo [PLAN_GOOGLE_FORMS_UIUX](PLAN_GOOGLE_FORMS_UIUX.md).
Configuración de cuenta, preguntas, triggers y QR: [guía Google Forms](integrations/google_forms/README.md).
La API usa GOOGLE_FORMS_SECRET y GOOGLE_FORM_URL (ver .env.example); sin secreto devuelve 503.
No se ha creado ni publicado un formulario en una cuenta externa.

Pruebas y límites: [evidencia G0–G6](docs/evidencias/g_google_forms.md).
Diseño, accesibilidad y capturas antes/después: [auditoría UI/UX](docs/UIUX_AUDITORIA.md).

La suite requiere PostgreSQL y crea una base desechable desde TEST_DATABASE_URL.
Ejemplo PowerShell, usando una instancia de pruebas propia:

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:55432/postgres'
.venv/Scripts/python.exe -m pytest -q --basetemp .tools/pytest-local
.venv/Scripts/python.exe -m ruff check src tests scripts
node tests/google_forms_script.cjs
uv pip check --python .venv/Scripts/python.exe
```

Para repetir revisión visual instale Chromium con `.venv/Scripts/python.exe -m playwright install chromium`;
ejecute después `scripts/capture_ui.py after`. El script usa loopback y bases temporales sintéticas.
Forms necesita HTTPS público para enviar a la API; activación y escaneo real siguen pendientes.
# Envío mensual automático

Copie `.env.example` a `.env` si aún no tiene configuración. Conserve su archivo privado existente y edite solo las claves necesarias. No guarde contraseñas en Git ni en evidencia.

El archivo mensual usa `REPORT_SOURCE=google_forms`: coincide con el dashboard filtrado por Google Forms. PDF y correo indican Formularios. Un mes vacío también produce correo. Cambios tardíos crean otra revisión en `/reports`; los destinatarios enviados no reciben otro correo automático. Los snapshots antiguos generan una revisión al incorporar el origen y la comparación mensual, sin repetir entregas exitosas.

Configure `REPORT_SEND_DAY=1` (1–28), `REPORT_SEND_HOUR=8` (0–23, America/Santiago). `REPORT_AUTO_SEND_FROM` debe indicar el primer **periodo cerrado** enviable, en formato YYYY-MM; vacío impide todo envío automático. `REPORT_INITIAL_MONTH` solo define el inicio del archivo. Al activar un periodo anterior, todos los periodos elegibles pendientes pueden recuperarse: elija deliberadamente el primer mes. Cada periodo queda habilitado en su día/hora del mes siguiente. Un arranque posterior recupera los pendientes.

Para SMTP institucional solicite host, puerto y política de autenticación al administrador. Use STARTTLS con `SMTP_TLS=true` (habitualmente 587), o `SMTP_SSL=true` con `SMTP_TLS=false` (habitualmente 465). No active ambos. Defina `SMTP_USERNAME`, `SMTP_PASSWORD`, `REPORT_FROM` y `REPORT_TO` separados por comas. Si el proveedor exige contraseña de aplicación, créela en la cuenta autorizada siguiendo sus instrucciones; no use una contraseña de sesión cuando el proveedor la prohíba. Login sin cifrado se rechaza, salvo SMTP local explícito en loopback. Desactive `LOCAL_SMTP_ENABLED` para SMTP institucional.

Mantenga `EMAIL_ENABLED=false` hasta que el propietario apruebe credenciales y destinatarios. Para prueba local use `SMTP_HOST=127.0.0.1`, `SMTP_PORT=1025`, `SMTP_TLS=false`, `SMTP_SSL=false`, `LOCAL_SMTP_ENABLED=true`, sin usuario/contraseña. El supervisor captura estos mensajes en `storage/mail`; una tarea independiente requiere un receptor SMTP local ya iniciado para esa prueba. Nunca use destinatarios reales durante pruebas.

`/reports` y dashboard muestran estado por periodo, próxima comprobación y aviso de correo deshabilitado. Los errores se reintentan hasta tres veces, con espera. `uncertain` nunca se reenvía automáticamente: concilie el Message-ID con el proveedor y use **Confirmar enviado** o **Reenviar correo** desde `/reports`, con acceso administrativo y CSRF. La generación manual de PDF no envía correo.

Una pasada manual desde `CODIGOS/`:

```powershell
.\.venv\Scripts\python.exe -m lab_hub.jobs.monthly_report
```

El comando devuelve 1 ante error o entregas fallidas/inciertas. Configuración sin activación registra el motivo y archiva sin correo. Logs de ejecución no contienen destinatarios ni secretos.

Para funcionar sin abrir el lanzador, el propietario instala la tarea desde PowerShell con los permisos que Windows solicite:

```powershell
.\scripts\instalar_tarea_mensual.ps1
# Para retirarla:
.\scripts\desinstalar_tarea_mensual.ps1
```

La tarea diaria usa la hora configurada al instalarla; reinstálela si cambia esa hora. El job relee `.env` y aplica día/hora en cada pasada. `StartWhenAvailable` recupera ejecuciones omitidas. Usa la identidad Windows actual mediante S4U, sin guardar su contraseña; accede a recursos locales. El runner inicia el PostgreSQL local existente si falta, no crea bases ni ejecuta migraciones. Logs de la última pasada: `storage/logs/monthly.log` y `storage/logs/monthly-error.log` (incluye el resumen estructurado). El bloqueo PostgreSQL evita carreras con el supervisor. Con equipo apagado no hay envío hasta el siguiente encendido; puntualidad garantizada requiere servidor. La instalación de la tarea y recepción institucional no están verificadas durante desarrollo.
