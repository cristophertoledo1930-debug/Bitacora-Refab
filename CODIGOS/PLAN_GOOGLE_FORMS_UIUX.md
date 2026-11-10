# Plan Codex: Google Forms + QR + Dashboard + UI/UX

Orquestador: Claude. Implementador: Codex. Leer antes: `AGENTS.md`, `docs/ESTADO.md`, `docs/CONTRATOS.md`, `docs/PRUEBAS.md`.

## Objetivo

1. Formulario Google Forms listo, con las mismas preguntas que `templates/form.html`.
2. Cada respuesta del Form se guarda en PostgreSQL (`waste_records`) y aparece en el dashboard. PostgreSQL es la única fuente de verdad; Google Sheets no se usa como almacenamiento.
3. Código QR único (PNG + SVG) que abre el Form.
4. Auditoría UI/UX y estética del sitio (formulario `/r/{token}`, páginas de éxito/error, `/reports`, dashboard Dash) con mejoras implementadas.

## Arquitectura

```
QR (PNG/SVG) -> URL Google Form (prefill: código de estación)
Google Form -> Apps Script onFormSubmit -> POST HTTPS /api/v1/integrations/google-forms
          (cabecera X-Forms-Signature = HMAC-SHA256(secreto, cuerpo); Idempotency-Key = responseId)
API -> valida, mapea nombres a IDs de catálogo -> waste_records (source="google_forms") -> dashboard
```

Restricción: Apps Script corre en servidores de Google y no alcanza `localhost`. Para pruebas reales hace falta URL pública HTTPS (túnel `cloudflared` o despliegue). Documentar esto; no publicar nada sin aprobación del usuario.

## Fases

### G0. Contrato (docs)
- Agregar a `docs/CONTRATOS.md` el endpoint `POST /api/v1/integrations/google-forms`: cuerpo JSON `{response_id, submitted_at, station_code, waste_type, material, machine, cause, weight, unit}`.
- Respuestas: 201 creado; 200 repetido (mismo `response_id` y payload); 409 mismo `response_id`, payload distinto; 401 firma inválida; 422 validación (valor fuera de catálogo, peso inválido).
- Agregar `google_forms` a valores permitidos de `source`. Agregar decisión en `docs/DECISIONES.md`.

### G1. Backend
- `config.py`: `GOOGLE_FORMS_SECRET` (obligatorio para habilitar el endpoint; ausente = 503), `GOOGLE_FORM_URL`.
- Nuevo módulo `src/lab_hub/api/integrations.py`: verificación HMAC con `hmac.compare_digest`, límite de tamaño de cuerpo, reutilizar `services/records.py` (idempotencia, Decimal, conversión g/kg). Mapear por `name` o `code` de catálogo activo, sin distinguir mayúsculas.
- `station_code` resuelve `qr_contexts.label`; desconocido = registro sin QR, no error. No registrar el secreto ni cuerpos completos en logs.
- Migración Alembic solo si cambia esquema (p. ej. columna `external_id`); si basta `idempotency_key = "gform:" + response_id`, no migrar.

### G2. Google Form (código en repo, ejecución por el usuario)
Carpeta `integrations/google_forms/`:
- `create_form.gs`: crea el Form con `FormApp`. Preguntas: tipo de residuo, material, máquina, causa (listas desplegables con valores de `GET /api/v1/catalogs` o de `seeds.py`), peso (respuesta corta con validación numérica > 0), unidad (g/kg), código de estación (respuesta corta, prefijada por QR). Todas obligatorias excepto estación.
- `on_submit.gs`: disparador instalable `onFormSubmit`; arma JSON, firma HMAC (`Utilities.computeHmacSha256Signature`), `UrlFetchApp.fetch` con reintento exponencial (3 intentos) y `Idempotency-Key`. Secreto y URL en `PropertiesService`, nunca en el código.
- `README.md`: pasos para el usuario (crear proyecto Apps Script, pegar scripts, definir propiedades, ejecutar `createForm`, instalar disparador, copiar URL del Form).
- Script Python `scripts/sync_form_options.py` opcional: imprime opciones de catálogo para pegar o mantener sincronizado el Form.

### G3. QR único
- `scripts/make_form_qr.py` (dependencia `qrcode[pil]` en `pyproject.toml` y lock): recibe URL del Form y `station_code`, arma URL prefijada (`usp=pp_url&entry.<id>=<code>`), genera `storage/qr/form_<station>.png` y `.svg`, corrección de errores M, margen 4, etiqueta legible debajo.
- Test: decodificar no es necesario; validar que la URL incluida en el PNG sea la esperada (guardar URL en metadatos/archivo `.txt`).

### G4. Dashboard
- Filtro y desglose por `source` (manual, google_forms, esp32).
- Indicador "última respuesta recibida de Google Forms" con hora America/Santiago.
- Confirmar que agregaciones, tabla e informe PDF incluyen los registros nuevos con las mismas reglas.

### G5. Auditoría UI/UX y estética
Entregable: `docs/UIUX_AUDITORIA.md` con capturas antes/después (datos sintéticos) y lista priorizada (alto/medio/bajo).
Revisar:
- Formulario móvil `/r/{token}`: tamaño de toque mínimo 44 px, orden de campos, teclado numérico para peso (`inputmode="decimal"`), mensajes de error junto al campo, estado de envío (botón deshabilitado + spinner) para evitar duplicados.
- Accesibilidad WCAG 2.1 AA: contraste 4.5:1, `label` asociado, foco visible, `lang="es"`, navegación por teclado.
- Consistencia visual: una paleta, tipografía y espaciado comunes entre FastAPI templates y Dash (extraer CSS compartido `static/theme.css` con variables).
- Dashboard: jerarquía (KPIs arriba: total kg mes, registros, top causa), gráficos con unidad en ejes, colores por categoría consistentes, estado vacío explicado, carga y error diferenciados, responsive bajo 768 px.
- `/reports`: hoy 11 líneas; dar tabla con estado, revisión, descarga y acción generar.
- Páginas éxito/error: resumen de lo registrado, acción "registrar otro", texto claro.
- Identidad: nombre Re-Fab / Lab881 en encabezado y favicon.
Implementar mejoras de prioridad alta y media; dejar bajas listadas.

### G6. Pruebas y evidencia
Nuevo `tests/test_g_google_forms.py`:
- firma válida 201; firma inválida 401; secreto ausente 503;
- reenvío igual 200 sin fila nueva; payload distinto 409; concurrencia mismo `response_id` = una fila;
- catálogo desconocido 422; peso `0`, negativo, `NaN`, texto = 422; kg a g exacto con Decimal;
- registro aparece en `get_aggregations()` y `/api/v1/records`.
- Test de `make_form_qr.py` (archivos creados, URL correcta).
Ejecutar suite completa (`pytest`) y `ruff`; guardar salida en `docs/evidencias/g_google_forms.md`. Actualizar `docs/ESTADO.md`.

## Puertas de salida
- Suite verde, sin regresiones F0–F6.
- Respuesta enviada desde Google Form real (vía túnel) visible en dashboard: la verifica el usuario; Codex no la declara sin ejecutarla.
- QR escaneado con teléfono abre el Form con estación prefijada.
- Auditoría con mejoras altas implementadas y capturas.

## Fuera de alcance
- Publicar/desplegar, envíos SMTP reales, guardar respuestas en Sheets como fuente, ESP32.

## Prompt para Codex

> Implementa `PLAN_GOOGLE_FORMS_UIUX.md` fase por fase (G0 a G6) en `CODIGOS/`. Respeta `AGENTS.md` y `docs/CONTRATOS.md`. Al cerrar cada fase, ejecuta pruebas, registra evidencia y actualiza `docs/ESTADO.md`. No guardes secretos, no publiques, no declares verificaciones no ejecutadas. Si una decisión cambia el contrato, actualiza docs primero.
