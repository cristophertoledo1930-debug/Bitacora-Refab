# QR Lab Hub — Sistema de Registro y Reportería de Residuos

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

