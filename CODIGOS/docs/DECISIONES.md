# Decisiones

| ID | Fecha | Decisión | Motivo / condición de cambio |
|---|---|---|---|
| D01 | 2026-10-18 | FastAPI + Dash + PostgreSQL | Sistema Python con formulario móvil y dashboard personalizable |
| D02 | 2026-10-18 | Gramos exactos, UTC y periodos America/Santiago | Consistencia de pesos e informes mensuales |
| D03 | 2026-10-18 | QR resuelto por servidor; causa inicial editable | Conciliar pedido escrito con formulario del diagrama |
| D04 | 2026-10-18 | Peso manual en MVP; ESP32 posterior | Diagrama identifica balanza como prototipo |
| D05 | 2026-10-18 | SMTP local antes de producción | Faltan configuración y destinatarios reales |
| D06 | 2026-10-18 | Habilidades locales en `.agents/skills` | Formato documentado por Antigravity; lectura explícita como alternativa |
| D07 | 2026-10-18 | PostgreSQL 16 portable local en `.tools/pgsql` | Entorno Windows sin Docker; ejecución verificable nativa |
| D08 | 2026-10-18 | Acceso admin vía `X-Admin-Key` / cookie `admin_session` | Proteger estadísticas y descargas sin restringir formulario QR público |

Registrar solo cambios relevantes: contexto, decisión, motivo y consecuencias. No duplicar el plan completo.

## D09 — Operación de escritorio local (2026-10-19)

El pedido actual exige dashboard local en puerto 8070. `LOCAL_DESKTOP_ACCESS` permite administración
solo desde loopback, con Host local, en desarrollo. Está deshabilitado por defecto en código y activado
explícitamente en el entorno local. Otros clientes requieren clave/cookie. Uvicorn ignora cabeceras proxy.
No habilitar esta opción en un despliegue compartido.

## D10 — SMTP local y pruebas aisladas (2026-10-19)

`LOCAL_SMTP_ENABLED` permite transporte exclusivamente a loopback; `EMAIL_ENABLED=false` mantiene bloqueada
la entrega externa. Captura en `storage/mail`. Las pruebas usan una base nueva desechable porque las fixtures
originales borraban filas y antes utilizaban la base de desarrollo.
