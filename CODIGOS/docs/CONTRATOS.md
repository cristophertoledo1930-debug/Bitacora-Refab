# Contratos del MVP

Estado: propuesta para F1. Modificar aquí antes de cambiar API, esquema o consumidores.

## Datos

| Entidad | Campos y restricciones |
|---|---|
| `waste_types`, `materials`, `machines`, `causes` | UUID, código único, nombre, activo; catálogos independientes |
| `qr_contexts` | UUID, hash de token aleatorio único, IDs de catálogos opcionales, activo, fecha de creación; contexto versionado o revocable |
| `waste_records` | UUID, tipo/material/máquina/causa obligatorios, `weight_g NUMERIC(12,3) CHECK (weight_g > 0)`, `recorded_at TIMESTAMPTZ` generado por servidor, QR opcional, origen manual/google_forms/esp32, clave idempotente única, hash del payload |
| `report_runs` | UUID, periodo local YYYY-MM, revisión, estado, fecha, snapshot, ruta de PDF, hash; unicidad periodo/revisión |
| `report_deliveries` | UUID, informe, destinatario, estado pending/sending/sent/failed/uncertain, intentos, próximo intento, error resumido, Message-ID; unicidad informe/destinatario |

Usar `Decimal` para pesos. Recibir peso decimal como cadena y unidad `g` o `kg`; convertir una sola vez. Validar finitud, positividad, escala y límite de almacenamiento. Definir máximo operativo y precisión reales en F1. No redondear silenciosamente medidas fuera de precisión: explicar el error.

Resina y retazo láser son tipos iniciales. Material es otra dimensión; no convertir ambos conceptos en el mismo campo. Catálogos desactivados conservan referencias históricas y etiquetas interpretables. No borrar registros para corregir un total; diseñar correcciones trazables si el MVP incorpora edición.

Las fechas se guardan como instantes UTC. Para meses locales calcular inicio inclusivo y siguiente inicio exclusivo en America/Santiago, luego convertir ambos a UTC. No usar un desplazamiento fijo: Chile cambia horario. No aceptar fechas libres del cliente en el registro normal.

## API propuesta

| Método y ruta | Comportamiento |
|---|---|
| `GET /r/{token}` | Formulario móvil con contexto autorizado; QR inexistente o revocado muestra error claro |
| `GET /api/v1/catalogs` | Opciones activas válidas para el formulario |
| `POST /api/v1/records` | Valida, guarda y devuelve 201 con ID, fecha y peso normalizado |
| `GET /api/v1/stats` | Resumen, agrupaciones y series con filtros; sesión obligatoria |
| `GET /api/v1/records` | Tabla paginada y filtrada; sesión obligatoria |
| `GET /api/v1/reports` | Lista de informes y estado; sesión obligatoria |
| `GET /api/v1/reports/{id}/pdf` | Descarga autorizada desde almacenamiento controlado |
| `GET /health/live`, `GET /health/ready` | Vida del proceso y disponibilidad de PostgreSQL, respectivamente |

Crear OpenAPI como contrato ejecutable durante implementación. Las rutas administrativas y el mecanismo de sesión se resuelven en F0; no exponer estadísticas o descargas por conocer el QR. Cuando existan cookies de sesión, aplicar protección CSRF a mutaciones y cookies seguras en producción. Consultas parametrizadas; no interpolar SQL desde filtros.

### Ejemplo sintético de ingreso

```json
{
  "qr_token": "token-de-ejemplo-sin-validez",
  "waste_type_id": "<uuid-del-catalogo>",
  "material_id": "<uuid-del-catalogo>",
  "machine_id": "<uuid-del-catalogo>",
  "cause_id": "<uuid-del-catalogo>",
  "weight": "0.125",
  "unit": "kg",
  "source": "manual"
}
```

El cliente envía `Idempotency-Key` aleatoria, conservada durante reintentos del mismo envío. Misma clave y payload: devolver registro existente sin insertar otra fila. Misma clave y payload diferente: 409. Resolver también la carrera entre dos peticiones simultáneas mediante restricción única y transacción; no solo comprobación previa. Error de validación: 422 con campos; QR inválido/revocado: error de acceso, sin guardar. Caída temporal: 503 y reintento seguro. No registrar tokens completos en logs.

## Agregación y consistencia

### Importación local desde Sheets

El supervisor consulta Sheets con alcance de solo lectura cada 60 segundos cuando `GOOGLE_SHEETS_ID` está configurado. Mapea los siete encabezados operativos de la hoja; excluye nombre y correo. Cada fila representa un residuo con peso positivo y unidad g/kg. Los catálogos aceptan nombre o código activo sin distinguir acentos, espacios repetidos o mayúsculas.

Selecciones múltiples separadas por comas se resuelven exclusivamente contra opciones conocidas. Se deduplican y ordenan por código; se crea una categoría conjunta con código `joint_` más hash de componentes y nombre terminado en `(conjunto)`. La medición se registra una sola vez y conserva todo su peso. Los gráficos muestran la combinación, sin atribuir fracciones a sus miembros. Alias de causa admitidos: `Defecto del material` a `Defecto de material`; `Error del diseño` a `Error de diseño`. No se crean categorías para valores desconocidos. La creación de combinaciones y del registro comparte transacción.

Fecha local de respuesta interpretada en America/Santiago y guardada con zona; fechas inválidas, ambiguas o inexistentes se rechazan. Peso usa Decimal y validación compartida. Origen `google_forms`. Clave `sheets:` más SHA-256 de hoja/pestaña/fila; hash de payload operativo incluye fecha, excluye datos personales. Reintento idéntico no duplica; cambios en fila importada quedan pendientes. La hoja debe ser acumulativa y no reordenarse. No combinar este canal con entrega directa Apps Script del mismo formulario.

Cada fila válida confirma su propia transacción; una fila inválida no impide importar las siguientes. Los errores conservan datos anteriores en PostgreSQL. `storage/sheets-status.json` contiene únicamente hora, contadores y números de fila/campos rechazados; el dashboard muestra estado y antigüedad. No se escriben cambios en Google.

Una función de consulta recibe rango, zona, filtros y métrica. Devuelve cantidad de registros y suma exacta en gramos. Solo convertir a kg para presentación. Dashboard, tabla e informe usan iguales reglas de inclusión.

Serie mensual: orden cronológico, meses ausentes con cero, etiquetas con año, rango visible. Distinguir valores vacíos de fallos de consulta. Mantener dimensiones con nombres históricos aunque estén inactivas.

## Envío mensual y concurrencia

### Archivo semanal automático

Los informes mensuales también se mantienen automáticamente cada 15 segundos: mes actual, meses con registros y meses ya archivados. La recuperación compara el snapshot actual con la última revisión antes de reutilizar PDF. Cambios en registros, masa o dimensiones crean una nueva revisión; sin cambios no se genera otro archivo. El refresco automático no llama al transporte de correo. El procesamiento programado de entregas mantiene su circuito existente y consulta la revisión completada más reciente. El mes en curso es provisional.

El supervisor local consulta PostgreSQL cada 15 segundos y archiva todas las semanas que contienen registros, la semana actual y las semanas ya archivadas. Semana ISO de lunes 00:00 a lunes siguiente 00:00 en America/Santiago, con límites conscientes de zona. `report_runs.period` acepta `YYYYWww` para semanas, además de `YYYY-MM` para meses; ambos ocupan siete caracteres. `snapshot.report_kind=weekly` distingue los informes semanales sin migración.

Cada archivo semanal contiene agregaciones comunes del dashboard y copia de registros operativos sin nombre ni correo. Usa snapshot de lectura repetible y bloqueo PostgreSQL por semana. Un cambio de snapshot genera nueva revisión y PDF; si no cambió, recupera la misma revisión. Altas manuales, importaciones, correcciones y bajas se reflejan en la siguiente revisión. Las revisiones previas se conservan como historial. La semana actual es provisional.

La página `/reports` lista semanas con rango, masa, cantidad, revisión y PDF, y se refresca cada 15 segundos. La API y las descargas mantienen protección administrativa. Los informes semanales no generan entregas de correo; el flujo mensual conserva sus reglas existentes. Ante fallo se conservan revisiones anteriores y el supervisor reintenta.

Un proceso independiente adquiere bloqueo o reclama trabajo de forma atómica en PostgreSQL. Crear snapshot consistente antes de PDF. Registrar entrega por destinatario para no repetir destinatarios exitosos al fallar otros.

SMTP no ofrece garantía de exactamente una vez. Si el servidor acepta el mensaje y el proceso cae antes de guardar `sent`, el resultado es incierto. Guardar Message-ID estable, marcar `uncertain` y requerir conciliación antes de reenviar automáticamente. Reintentar con límite y espera los errores inequívocamente transitorios; conservar fallo final visible. Nunca describir un timeout ambiguo como prueba de que no se envió.

La ejecución diaria archiva periodos cerrados desde REPORT_INITIAL_MONTH; solo envía periodos desde REPORT_AUTO_SEND_FROM, cuando está definido. Febrero, cambio de año, horario de verano y meses vacíos deben funcionar. Para pruebas inyectar reloj y transporte SMTP.

## ESP32, fuera del MVP

No aceptar el peso de la última lectura global. Cada medición futura requiere ID de dispositivo, ID de medición, fecha, unidad, calibración y vínculo con sesión/registro. Rechazar lectura antigua o ya consumida. Autenticar dispositivo. Usuario confirma antes de guardar. No simular hardware probado.

## Integración Google Forms (G0, 2026-11-03)

`POST /api/v1/integrations/google-forms` recibe JSON UTF-8:
`{response_id, submitted_at, station_code, waste_type, material, machine, cause, weight, unit}`.
Todos obligatorios salvo `station_code` (cadena vacía por defecto). `submitted_at` exige zona horaria;
se valida pero `recorded_at` sigue siendo la recepción UTC del servidor.
Catálogos activos por nombre o código, sin distinguir mayúsculas; coincidencia ambigua se rechaza.
Estación por `qr_contexts.label` activo; desconocida no vincula QR, duplicada devuelve 422.

Cabeceras: `X-Forms-Signature` = HMAC-SHA256 hexadecimal del cuerpo exacto, con
`GOOGLE_FORMS_SECRET`; `Idempotency-Key` debe coincidir con `response_id` (1–94 caracteres).
Máximo 16 KiB incluso sin Content-Length. Secreto ausente: 503; firma inválida: 401;
201 creado; 200 reenvío; 409 misma respuesta con contenido distinto; 422 datos inválidos;
413 cuerpo excesivo; fallo transitorio de BD: 503.

Se almacena `idempotency_key="gform:" + response_id`, `source="google_forms"` y hash
canónico de todos los campos aceptados, incluidos fecha y estación. Orden JSON no importa;
cambiar un campo s?. Se reutiliza el servicio transaccional y Decimal, sin cambiar esquema.
El endpoint público normal conserva origen manual/esp32; google_forms requiere firma.

`GET /api/v1/stats` y `GET /api/v1/records` aceptan filtro `source` manual/google_forms/esp32.
Agregaciones incluyen `by_source`, masa del mes y Última recepción Google Forms (hora Chile,
global para el indicador operativo). PDF mensual aplica REPORT_SOURCE (google_forms por defecto); PDF semanal incluye todos los orígenes.

PostgreSQL es la fuente de verdad del dashboard. Google Forms retiene respuestas en Google
antes de entregarlas: no puede ofrecerse almacenamiento exclusivamente local durante el envío.
El script elimina cada respuesta en Google solo tras confirmar 200/201, no vincula Sheets,
y conserva pendientes en Forms para reintento. Borrar en Forms no garantiza borrado de backups de Google.


### Envío mensual automático (M0)

Periodo: mes calendario cerrado en America/Santiago. El día REPORT_SEND_DAY (1–28) a REPORT_SEND_HOUR (0–23) habilita el mes anterior; un arranque posterior recupera los periodos elegibles. REPORT_AUTO_SEND_FROM (YYYY-MM) es el primer periodo enviable; vacío deshabilita el envío automático sin impedir el archivo histórico. REPORT_INITIAL_MONTH solo define el archivo.

REPORT_SOURCE=google_forms filtra agregaciones y registros del snapshot; vacío incluye todos. El snapshot guarda report_source y comparación con el mes anterior desde la misma lectura consistente. Los snapshots antiguos generan una revisión al incorporar estas claves. Un cambio tardío genera PDF visible sin repetir correo: cada destinatario con sent en cualquier revisión queda excluido del envío automático. uncertain y sending de cualquier revisión bloquean reenvío automático y requieren conciliación administrativa. Reintentos failed conservan la entrega original y su límite de tres intentos. El bloqueo por periodo cubre selección y envío.

Excepción de migración: una entrega pending/failed de un snapshot sin origen compatible se vincula a la nueva revisión filtrada antes de reintentar. Conserva intentos, Message-ID y plazo; nunca adjunta el PDF antiguo mezclado. Entregas sent/uncertain no se migran ni se reenvían automáticamente.

Mes sin respuestas: enviar igualmente, con aviso explícito. PDF existente y no vacío obligatorio. Las cifras del correo proceden exclusivamente del snapshot. SMTP autenticado exige STARTTLS o SSL, salvo loopback con LOCAL_SMTP_ENABLED. EMAIL_ENABLED=false impide correo externo; el SMTP local explícito y transporte inyectado quedan disponibles para pruebas.

La conciliación ofrece confirmar enviado o reenviar, con require_admin y token CSRF firmado ligado a la entrega. La generación manual de PDF no envía correo. Estado por periodo incluye todas las revisiones y es visible en informes y dashboard, junto con la próxima ejecuci?n y aviso de correo deshabilitado. Nunca se registran destinatarios completos ni secretos.

La tarea Windows se instala exclusivamente por el propietario. Ejecuta una pasada diaria con StartWhenAvailable y arranque de PostgreSQL local si falta. Equipo apagado: entrega tras encender; puntualidad garantizada requiere servidor.
