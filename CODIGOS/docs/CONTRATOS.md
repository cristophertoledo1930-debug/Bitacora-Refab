# Contratos del MVP

Estado: propuesta para F1. Modificar aquí antes de cambiar API, esquema o consumidores.

## Datos

| Entidad | Campos y restricciones |
|---|---|
| `waste_types`, `materials`, `machines`, `causes` | UUID, código único, nombre, activo; catálogos independientes |
| `qr_contexts` | UUID, hash de token aleatorio único, IDs de catálogos opcionales, activo, fecha de creación; contexto versionado o revocable |
| `waste_records` | UUID, tipo/material/máquina/causa obligatorios, `weight_g NUMERIC(12,3) CHECK (weight_g > 0)`, `recorded_at TIMESTAMPTZ` generado por servidor, QR opcional, origen manual/ESP32, clave idempotente única, hash del payload |
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

Una función de consulta recibe rango, zona, filtros y métrica. Devuelve cantidad de registros y suma exacta en gramos. Solo convertir a kg para presentación. Dashboard, tabla e informe usan iguales reglas de inclusión.

Serie mensual: orden cronológico, meses ausentes con cero, etiquetas con año, rango visible. Distinguir valores vacíos de fallos de consulta. Mantener dimensiones con nombres históricos aunque estén inactivas.

## Envío mensual y concurrencia

Un proceso independiente adquiere bloqueo o reclama trabajo de forma atómica en PostgreSQL. Crear snapshot consistente antes de PDF. Registrar entrega por destinatario para no repetir destinatarios exitosos al fallar otros.

SMTP no ofrece garantía de exactamente una vez. Si el servidor acepta el mensaje y el proceso cae antes de guardar `sent`, el resultado es incierto. Guardar Message-ID estable, marcar `uncertain` y requerir conciliación antes de reenviar automáticamente. Reintentar con límite y espera los errores inequívocamente transitorios; conservar fallo final visible. Nunca describir un timeout ambiguo como prueba de que no se envió.

La ejecución diaria procesa periodos cerrados desde el mes inicial configurado. Febrero, cambio de año, horario de verano y meses vacíos deben funcionar. Para pruebas inyectar reloj y transporte SMTP.

## ESP32, fuera del MVP

No aceptar el peso de la última lectura global. Cada medición futura requiere ID de dispositivo, ID de medición, fecha, unidad, calibración y vínculo con sesión/registro. Rechazar lectura antigua o ya consumida. Autenticar dispositivo. Usuario confirma antes de guardar. No simular hardware probado.
