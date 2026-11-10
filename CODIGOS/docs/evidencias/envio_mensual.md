# Evidencia de envío mensual

M0: contratos y decisión actualizados antes del código. Revisión contra B1–B8; sin cambios de esquema. Prueba documental: claves y reglas presentes.

## Fases M1–M7

- M1: validación directa con `Settings(_env_file=None)`: valores por defecto y cinco configuraciones inválidas, seis comprobaciones correctas.
- M2–M5: `.venv\Scripts\python.exe -m pytest tests/test_f4_reports.py tests/test_monthly_refresh.py tests/test_local_runtime.py -q --basetemp=storage/pytest-monthly-phase3`: 17 passed. Comprueba archivo, revisión tardía sin correo durante refresco, entregas y SMTP local con PDF.
- M6–M7: `.venv\Scripts\python.exe -m pytest tests/test_monthly_send.py -q --basetemp=storage/pytest-monthly-new2`: 24 passed. Reloj, activación sin historial, filtro e igualdad con API del dashboard, datos tardíos y snapshot antiguo sin reenvío, PDF ausente/vacío, fallo parcial, incertidumbre, CSRF, SSL, mes vacío y calendario.
- Concurrencia: dos intérpretes Python independientes con PostgreSQL desechable y un servidor SMTP local. Una sola entrega y un solo mensaje capturado.
- Puerto 1025 ocupado por supervisor existente: captura adicional mediante su buzón `storage/mail`, solo mensaje sintético y base desechable. No se detuvo supervisor.
- `.venv\Scripts\python.exe -m ruff check src tests scripts`: All checks passed.
- No se instaló ni eliminó ninguna tarea real. Los tres scripts operativos pasan el parser PowerShell. `tests/verify_monthly_task.ps1` ejecuta instalación/desinstalación con todos los cmdlets de tareas reemplazados por dobles: valida programación diaria, StartWhenAvailable, exclusión, identidad S4U y proceso oculto. El runner operativo no se ejecutó contra la instancia de uso. El punto de entrada Python se verificó en subprocess contra la base desechable.

## Fallos encontrados y corregidos

- Primer intento de pytest: directorio temporal Windows sin acceso. Reintento con `--basetemp` dentro de storage.
- Variable de etiqueta del correo sin definir tras primera edición: corregida y regresión de asunto Forms añadida.
- Prueba histórica dependía del REPORT_INITIAL_MONTH privado: fixture fija 2026-01 y desactiva envío automático.
- Primera captura intentaba abrir 1025 ya ocupado: concurrencia utiliza puerto libre y aceptación 1025 reutiliza buzón local.
- Reintento histórico sin report_source podía adjuntar PDF antiguo mezclado: ahora vincula la entrega no exitosa a revisión filtrada conservando presupuesto/plazo. Regresión comprueba 0.125 kg Forms, excluye 0.900 kg manuales y conserva segundo intento.
- Prueba PowerShell inicial no compartía sus indicadores entre ámbitos: estado del doble corregido y verificado. Ningún cmdlet real de tareas se ejecutó.
- `ruff check .` detecta dos E402 preexistentes en `migrations/env.py`; no se modifica migración ajena. Alcance habitual `src tests scripts` limpio.

## Seguridad y límites

Todas las pruebas PostgreSQL usan `qrlabhub_verify_*`, creada y eliminada por conftest. No se cambió `.env`, base de uso ni registros reales. No se enviaron correos externos. Los artefactos `monthly_send/` contienen solo datos y direcciones sintéticas.

Credenciales institucionales, EMAIL_ENABLED=true, REPORT_AUTO_SEND_FROM, instalación de tarea y recepción externa corresponden al propietario. Ninguna prueba local acredita recepción externa.

## M8: cierre local (2026-11-08)

Comando final:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=storage/pytest-monthly-final2
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\tests\verify_monthly_task.ps1
```

Resultado: **103 passed, 6 warnings in 32.94s**; 37 casos nuevos de envío mensual. Avisos existentes de Starlette/Dash y alias HTTP 422. Ruff: **All checks passed!** en src/tests/scripts. Ruff global mantiene únicamente dos E402 preexistentes en migrations/env.py, fuera del alcance de esta implementación. `git diff --check` sobre archivos del cambio pasó.

Salidas: [pytest](monthly_send/pytest.txt), [Ruff](monthly_send/ruff.txt), [PowerShell con dobles](monthly_send/powershell.txt).

La suite incluye SMTP 127.0.0.1:1025 real y concurrencia entre dos intérpretes con SMTP en puerto local libre: una entrega por destinatario. [Correo capturado](monthly_send/correo_sintetico.eml) adjunta [PDF sintético](monthly_send/formularios_sintetico.pdf): 1 respuesta, 125.000 g / 0.125 kg, idénticos al agregador/API del dashboard filtrado por google_forms. La comparación mensual usa exclusivamente snapshot; STARTTLS y SSL verifican cifrado antes del login mediante dobles.

PDF final renderizado con PyMuPDF (Poppler no disponible), dos páginas inspeccionadas visualmente: título Formularios, acentos, totales, tablas con cabecera repetida y gráfico legibles, sin recortes. Imágenes: [página 1](monthly_send/pdf-page-1.png), [página 2](monthly_send/pdf-page-2.png).

Chromium mediante Playwright y TestClient sobre la base desechable: `/reports` y dashboard a 1440 y 390 px, sin desbordamiento horizontal del documento ni errores JavaScript. Inspección visual de controles, avisos y conciliación. Capturas: [informes escritorio](monthly_send/reports-desktop.png), [informes móvil](monthly_send/reports-mobile.png), [dashboard escritorio](monthly_send/dashboard-desktop.png), [dashboard móvil](monthly_send/dashboard-mobile.png).

M0–M8 implementados; aceptación local satisfecha con el límite de lint global indicado. No se instaló tarea, no se activó correo externo, no se cambió .env ni base de uso, no se hizo commit. La puntualidad con el equipo apagado y la recepción institucional quedan fuera de esta verificación. Instrucciones de activación en README.md.
