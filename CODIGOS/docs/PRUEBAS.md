# Matriz de aceptación y depuración

Estado: pruebas especificadas, aún no ejecutadas. Cada ejecución debe indicar comando real, resultado y evidencia.

| ID | Escenario | Resultado exigido |
|---|---|---|
| T01 | Migraciones sobre PostgreSQL vacío | Esquema utilizable y catálogos iniciales; repetir upgrade no rompe |
| T02 | QR válido y formulario móvil | Precarga máquina/material/tipo/causa configurados; valores confirmables |
| T03 | QR inexistente, revocado o parámetros alterados | Rechazo claro; ninguna fila creada |
| T04 | Peso cero, negativo, vacío, NaN, infinito, exceso de precisión y límite | Validación de servidor; formulario preserva campos corregibles |
| T05 | 0.125 kg y 125 g | Ambos guardan exactamente 125.000 g |
| T06 | Tipo/material/máquina/causa ausentes o desconocidos | 422; sin fila parcial |
| T07 | Doble clic, retry y dos POST simultáneos con misma clave | Un registro; mismo ID; clave reutilizada con otro payload devuelve 409 |
| T08 | PostgreSQL caído durante guardado | Sin falso éxito; recuperación y retry seguro |
| T09 | Datos sintéticos conocidos y filtros combinados | Cantidades y pesos de dashboard coinciden con valores esperados independientes |
| T10 | Registro nuevo y dashboard abierto | Aparece dentro de 15 segundos; filtros se conservan |
| T11 | Mes vacío y cruce diciembre/enero | Barras cronológicas con cero; etiquetas con año |
| T12 | Límites de mes y cambio horario America/Santiago | Cada registro entra en un único periodo correcto |
| T13 | PDF normal, mes vacío, acentos y tablas extensas | Totales exactos; texto legible, sin recortes y paginación correcta |
| T14 | PDF y dashboard sobre mismo rango y snapshot | Cifras y unidades equivalentes; corte temporal documentado |
| T15 | SMTP local, fallo temporal y destinatario fallido | Adjunto PDF válido; retries limitados; no duplicar entregas exitosas |
| T16 | Dos jobs simultáneos y segunda ejecución mismo mes | Un trabajo reclamado; entregas ya exitosas no se repiten |
| T17 | Caída tras aceptación SMTP y antes de guardar estado | Entrega incierta visible; sin reenvío ciego |
| T18 | Equipo apagado al cambio de mes | Próximo arranque recupera periodos pendientes desde mes inicial |
| T19 | Acceso sin sesión al dashboard/PDF y QR sin privilegios | Consulta administrativa denegada; formulario autorizado sigue funcionando |
| T20 | Escritorio, móvil, teclado y contraste | Sin scroll horizontal del formulario, foco visible y unidades claras |
| T21 | Respaldo y restauración en base desechable | Registros e informes recuperables según guía |
| T22 | Recorrido QR → guardado → dashboard → PDF → correo local | Mismo registro rastreable; evidencia sin secretos |

## Fixture de control

Usar IDs sintéticos y fechas dentro de periodos sin ambigüedad, más casos separados de frontera. Ejemplo: enero, dos entradas de resina de 125 g y 375 g; febrero, un retazo láser de 1000 g; marzo vacío. Esperado enero: 2 registros y 0.500 kg; febrero: 1 y 1.000 kg; marzo: 0 y 0 kg. Total: 3 y 1.500 kg. Asignar causas y máquinas distintas para comprobar filtros. No calcular el esperado llamando la misma función bajo prueba.

## Orden de verificación

1. Ejecutar validadores y pruebas focalizadas de la fase.
2. Ejecutar integración con PostgreSQL real; SQLite no demuestra compatibilidad SQL ni bloqueos.
3. Revisar UI en navegador y PDF renderizado. La extracción de texto del PDF no prueba maquetación.
4. En F5 ejecutar recorrido completo y suite acumulada una vez; repetir por cambios o fallos pertinentes.
5. Registrar comandos, versiones, resumen y rutas en `docs/evidencias/`. No pegar logs gigantes en el chat.

Si existen habilidades de PDF o navegador en Antigravity, usarlas para la revisión correspondiente. No asumir que las habilidades de Codex existen en otro producto. Las pruebas visuales pueden realizarse manualmente con evidencia si falta automatización.

## Fallos y cierre

Crítico: pérdida de datos, acceso no autorizado, secretos expuestos. Alto: totales incorrectos, duplicados, registro bloqueado o envíos repetidos. Medio/bajo: degradación visual o secundaria sin afectar integridad.

Para cada fallo conservar pasos de reproducción, esperado/observado, causa, archivos cambiados y regresión. No cerrar F5 con críticos o altos abiertos. Limitaciones del entorno deben figurar como no verificadas, nunca como aprobadas.
