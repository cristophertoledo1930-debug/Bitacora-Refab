# Auditoría UI/UX y estética · Re-Fab / Lab881

Fecha: 2026-11-03. Alcance: formulario QR, confirmación, error, informes y dashboard.
Datos: tres registros sintéticos (125 g, 375 g de Google Forms y 1000 g), total 1.500 kg.
No se consultó la base de uso existente. Cada captura usa una base nueva y eliminada al terminar.

## Hallazgos y cambios

| Prioridad | Hallazgo antes | Mejora aplicada | Estado |
|---|---|---|---|
| Alta | Controles táctiles pequeños, unidad sin nombre accesible | Campos y botón ≥48 px; unidad con aria-label; teclado decimal | Implementado y comprobado en navegador |
| Alta | Doble envío sin estado visible | Botón deshabilitado, indicador de progreso, aria-busy y protección contra segundo submit; idempotencia servidor | Implementado |
| Alta | Error genérico sin vínculo al campo | Mensaje junto al peso/catálogo, aria-invalid y aria-describedby; valores preservados | Implementado y envío inválido/recuperación comprobados |
| Alta | Filtros ocupan toda la primera pantalla móvil | Navegación nativa plegable, conserva filtros; KPIs visibles al abrir | Implementado y comprobado a 390 px |
| Alta | Texto de métrica oscuro sobre panel oscuro | Texto claro explícito y foco visible | Corregido y revisado visualmente |
| Media | CSS repetido y distinta identidad entre páginas | Tema común static/theme.css, variables, fuentes de sistema, favicon y Re-Fab / Lab881 | Implementado |
| Media | Causas, máquinas y materiales con etiquetas superpuestas | Barras horizontales, etiquetas envueltas y márgenes automáticos | Implementado y revisado |
| Media | Jerarquía de indicadores incompleta | Seis KPIs; masa mensual, registros y principal causa por masa; tres columnas escritorio, dos móvil | Implementado |
| Media | Carga confundida con ceros | Mensaje inicial Cargando, spinner en origen, vacíos explicados y errores conservan valores | Implementado; callbacks de vacío/error comprobados |
| Media | Colores sin estabilidad por categoría | Paleta determinista por código; nombres y ejes kg/registros visibles | Implementado |
| Media | Informes con estructura mínima y acciones poco visibles | Tabla semántica con revisión, estado y descarga; tarjetas en móvil; generación con estado | Implementado y revisado |
| Media | Confirmación con resumen escaso y error sin recuperación | Resumen de siete datos, registrar otro y orientación para QR activo | Implementado |
| Baja | No hay logotipo institucional oficial | Favicon tipográfico provisional; sustituir cuando el laboratorio entregue identidad oficial | Pendiente opcional |
| Baja | Recorrido con lector de pantalla y navegadores alternativos | Añadir NVDA/VoiceOver, Safari y teléfonos físicos | Pendiente; no se declara conformidad WCAG completa |
| Baja | Tabla envía todas las filas al cliente | Considerar paginación de servidor al crecer el volumen | Pendiente opcional |

## Antes y después

Capturas completas: `docs/evidencias/google_forms_ui/`. “Antes” corresponde a la entrada de G5,
con G4 ya implementada. “Después” incluye las mejoras finales, siempre con el mismo fixture.

| Vista | Antes | Después |
|---|---|---|
| Dashboard escritorio 1440×1050 | [Antes](evidencias/google_forms_ui/before-dashboard-desktop.png) | [Después](evidencias/google_forms_ui/after-dashboard-desktop.png) |
| Dashboard móvil 390×844 | [Antes](evidencias/google_forms_ui/before-dashboard-mobile.png) | [Después](evidencias/google_forms_ui/after-dashboard-mobile.png) |
| Formulario móvil | [Antes](evidencias/google_forms_ui/before-form-mobile.png) | [Después](evidencias/google_forms_ui/after-form-mobile.png) |
| Error de peso | [Antes](evidencias/google_forms_ui/before-form-validation-mobile.png) | [Después](evidencias/google_forms_ui/after-form-validation-mobile.png) |
| Confirmación | [Antes](evidencias/google_forms_ui/before-success-mobile.png) | [Después](evidencias/google_forms_ui/after-success-mobile.png) |
| QR inválido | [Antes](evidencias/google_forms_ui/before-error-mobile.png) | [Después](evidencias/google_forms_ui/after-error-mobile.png) |
| Informes móvil | [Antes](evidencias/google_forms_ui/before-reports-mobile.png) | [Después](evidencias/google_forms_ui/after-reports-mobile.png) |
| Informes escritorio | [Antes](evidencias/google_forms_ui/before-reports-desktop.png) | [Después](evidencias/google_forms_ui/after-reports-desktop.png) |

También se conserva [dashboard filtrado por Google Forms](evidencias/google_forms_ui/after-dashboard-filtered-mobile.png).
Las páginas se inspeccionaron visualmente; capturas no equivalen a pruebas con lectores de pantalla.

## Accesibilidad y evidencia ejecutada

Chromium / Playwright: sin overflow horizontal global en cuatro páginas, a 1440 y 390 px;
sin errores JavaScript. Registro inválido conserva -1 y muestra error; posterior 125 g confirma guardado.
Filtro Google Forms cambia cuatro registros (tras el nuevo ingreso) a uno. Foco por Tab visible,
inputmode decimal y altura de cuatro controles ≥44 px comprobados mediante DOM.
Idioma español, labels asociados, estados accesibles y movimiento reducido definidos en código.

Ratios calculados según luminancia relativa sRGB (AA texto normal ≥4.5:1, controles ≥3:1):

| Par | Ratio |
|---|---|
| Texto #F4F8F5 / panel #14231D | 15.21:1 |
| Secundario #BCCEC3 / panel | 9.90:1 |
| Enlace/foco #64D6A0 / panel | 9.06:1 |
| Botón #07120D / #64D6A0 | 10.59:1 |
| Error #FF9090 / panel | 7.49:1 |
| Borde #809D8C / campo #1B2D26 | 4.91:1 |

[Resultados DOM](evidencias/google_forms_ui/after-checks.json) y
[contrastes](evidencias/google_forms_ui/contrast.json). No se afirma certificación WCAG global;
los estilos internos de bibliotecas y tecnologías de asistencia requieren revisión adicional.

Reproducir: `.venv/Scripts/python.exe scripts/capture_ui.py after --postgres-dsn DSN_A_INSTANCIA_DE_PRUEBAS`.
El script crea y elimina su propia base, usa solo loopback y deshabilita correos.
No use `before` para regenerar las imágenes históricas sobre la UI modificada.
