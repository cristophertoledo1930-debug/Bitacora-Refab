# Google Forms ? Re-Fab / Lab881

Los scripts crean un borrador privado con siete preguntas: tipo de residuo, material,
máquina, causa, peso, unidad y estación (única opcional). Los desplegables usan nombres
de los catálogos activos de la API, no listas inventadas. No se crea ninguna hoja Sheets.

## Configuración por el propietario

1. Abra Apps Script en su cuenta Google y cree un proyecto. Pegue `create_form.gs` y
   `on_submit.gs` como archivos del mismo proyecto. No use un trigger de Sheets.
2. En Configuración del proyecto ? Propiedades del script agregue:
   `API_BASE_URL` (origen HTTPS público sin barra final), `GOOGLE_FORMS_SECRET`
   (secreto aleatorio compartido con la API) y `STATION_CODE` (label de estación).
   No coloque secretos en archivos, capturas ni consola. Configure el mismo secreto
   en `.env` del servidor y reinicie la API. Puede generar uno con
   `python -c "import secrets; print(secrets.token_hex(32))"` en su terminal privada.
3. Ejecute `createForm` y autorice Forms y acceso HTTP. Crea borrador sin publicar;
   guarda FORM_ID, FORM_ITEM_IDS y GOOGLE_FORM_URL. Abra la URL de edición indicada.
   Si la creación se interrumpe, inspeccione ese borrador antes de quitar FORM_ID.
4. Revise las preguntas, mantenga desactivada recopilación de correo y no vincule Sheets.
   Ejecute `installTriggers` una vez: instala envío y recuperación cada cinco minutos.
   Repetir no crea duplicados. `syncFormOptions` actualiza catálogos sin recrear preguntas.
5. Cuando apruebe el formulario y disponga de API HTTPS operativa, publíquelo desde Forms
   y revise permisos de los encuestados. Esta implementación no publica nada.
6. Ejecute `stationPrefilledUrl`. Copie el enlace obtenido: contiene el `entry.<id>` real.
   No confunda ID de pregunta con entry ID. Guarde la URL base en GOOGLE_FORM_URL del servidor.
7. Genere el QR desde CODIGOS:

   ```powershell
   .venv/Scripts/python.exe scripts/make_form_qr.py --url 'ENLACE_PREFIJADO_REAL' --station-code 'ESTACION_REAL'
   ```

   Si usa URL sin prefijar, añada `--entry-id NUMERO_REAL`. El script escribe PNG, SVG y TXT.
   Escanee el PNG y confirme estación y enlace con un teléfono.
8. Envíe una respuesta sintética desde el formulario publicado. Confirme en dashboard el
   origen Google Forms y peso esperado; compruebe que desaparezca de Respuestas en Forms.
   El mensaje de Forms solo confirma recepción en Google, no el commit del dashboard.

## Entrega, recuperación y almacenamiento

Cada envío firma el JSON UTF-8 con HMAC-SHA256 y usa responseId como Idempotency-Key.
Tres intentos con espera de 1 y 2 segundos para errores de red/408/429/5xx.
200/201 con ACK válido elimina la respuesta en Forms; 401/409/422 la conserva.
`retryPending` recupera hasta 20 por ejecución. Revise fallos de triggers en Apps Script;
una opción de catálogo eliminada requiere corrección antes de reenviar.
No edite respuestas pendientes: conservan el mismo ID para impedir duplicados.

PostgreSQL es la única fuente de verdad del dashboard. Forms guarda temporalmente cada
respuesta: no es posible prometer que los datos jamás pasen por almacenamiento de Google.
El borrado posterior no acredita borrado de backups de Google. Para exclusividad estricta
use el formulario local `/r/{token}` que ya guarda directamente en PostgreSQL.

Apps Script no puede alcanzar localhost. Hace falta HTTPS público por túnel o despliegue,
fuera del alcance de esta implementación local. No exponga modo LOCAL_DESKTOP_ACCESS.
No publique ni abra túneles sin decisión del propietario. Prueba real Google y escaneo móvil
quedan pendientes hasta contar con URL y cuenta reales.

Referencias oficiales consultadas: [Form](https://developers.google.com/apps-script/reference/forms/form),
[FormResponse](https://developers.google.com/apps-script/reference/forms/form-response),
[Utilities](https://developers.google.com/apps-script/reference/utilities/utilities),
[eventos de Forms](https://developers.google.com/apps-script/guides/triggers/events).
