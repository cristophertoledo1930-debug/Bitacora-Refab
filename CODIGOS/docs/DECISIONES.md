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

## D11 ? Google Forms y recepción firmada (2026-11-03)

Forms entrega con HMAC a una API HTTPS. El dashboard consulta únicamente PostgreSQL.
Se reutilizan idempotencia y transacciones con prefijo gform, sin migración. El hash de
integración incluye fecha y estación para detectar cualquier reenvío modificado.
Forms necesariamente guarda temporalmente la respuesta; se elimina tras ACK de la API,
sin crear Sheets. Fallos retienen la respuesta para recuperación manual o periódica.
El QR requiere URL y entry ID reales; no se inventan enlaces funcionales ni se publica.

## D12 — Sheets local y selecciones conjuntas (2026-11-08)

El propietario solicitó integrar Sheets y normalizar sus selecciones múltiples para los gráficos. Sheets se consulta en modo de solo lectura; PostgreSQL mantiene los datos del dashboard. Cada respuesta conserva una medición total y un registro. Varias opciones conocidas dentro de una dimensión se representan como una categoría conjunta canónica, sin repartir peso ni atribuirlo por separado a cada miembro. Se aceptan alias explícitos de causa. Valores desconocidos se rechazan. Se excluyen nombre y correo.

La identidad usa hoja, pestaña y fila; requiere hoja acumulativa sin reordenamientos. No combinar este canal con entrega Apps Script directa para la misma respuesta. La retirada del registro ficticio manual de 200 g fue solicitada por el propietario y conserva respaldo local excluido de Git.


## Envío mensual: elegibilidad y revisiones (M0, 2026-11-08)

Separar archivo histórico de activaci?n del correo mediante REPORT_AUTO_SEND_FROM, vacío por defecto. El origen mensual por defecto es google_forms. Conservar agregador, PDF, tablas y bloqueo existentes. Las entregas se concilian entre todas las revisiones del periodo: un sent no se repite automáticamente; uncertain exige decisión administrativa. Cambios tardíos solo actualizan archivo. Mes vacío se envía. SMTP autenticado requiere cifrado. La tarea Windows queda entregada para instalación voluntaria del propietario; no se activa correo externo durante implementación.
