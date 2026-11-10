# Implementación del rediseño v2

Rama: `redesign/codex`. Spec congelada: `opus/05-spec-diseno.md` v2. P-01 cerrada al pedir el usuario retomar. No existe `opus/07-revision.md`.

## Componentes

- `services/aggregations.py`: contrato anterior conservado, `previous_period` añadido. Periodo anterior inmediatamente contiguo con igual número de días locales. Serie mensual mediante GROUP BY; resumen, dimensiones, orígenes y metadatos se devuelven en una sola sentencia UNION ALL. No se transfieren registros individuales para agregar.
- `dashboard/data.py`: validación anterior a la conexión, fechas futuras limitadas a hoy, formatos es-CL con Decimal hasta la presentación, opciones actualizadas, último periodo de correo, Sheets y consultas paginadas con joins. Lectura de agregados y catálogos en una transacción REPEATABLE READ nueva. La tabla consulta como máximo 25 filas. CSV completo filtrado, UTF-8 con BOM y protección de fórmulas de hoja de cálculo.
- `dashboard/components.py`: cuatro KPIs, deltas neutros, empates, rankings descendentes de una sola serie, top 8 + Otros, tablas accesibles de gráficos, origen con etiquetas y paleta fija, vacío único.
- `dashboard/layout.py` y `assets/dashboard.css`: layout declarativo sin sidebar ni mutaciones; barra de filtros y presets, móvil plegable, dos columnas de KPIs y tarjetas de registros. CSS con tokens; sin estilos inline de layout ni `!important` nuevo.
- `dashboard/callbacks.py`: una sola llamada de agregación por actualización, en `agg-store`; renderizadores sin agregaciones. Fechas inválidas conservan el store completo. Caída de BD conserva valores y marca `.stale`, con banner `role="alert"` y hora anterior. Tabla y descarga con errores propios.
- `dashboard/app.py`: solo instancia, layout y registro de callbacks. Conserva `app` y `server`. Assets con ruta absoluta, `lang="es"`, CSS compartido y acceso protegido por el montaje FastAPI existente.
- `DASHBOARD_NEW_RECORD_URL`: configuración del enlace de registro; documentada en `.env.example`. No se modificó el `.env` privado.

## Decisiones de implementación y límites

No se modificaron archivos de `opus/` ni se cambió la spec. Su incorporación al commit base conservó exactamente los archivos existentes.

El commit base preserva cambios previos del proyecto, fuentes, pruebas y documentación de rediseño. No incorpora eliminaciones ajenas al proyecto ni almacenamiento privado/credenciales. Se conserva el respaldo previo de Opus.

Los colores de Plotly se resuelven leyendo los tokens CSS: Plotly requiere colores concretos y no acepta `var(...)` en sus propiedades. La fuente de valores sigue siendo CSS. No se añaden colores por hash ni nuevas dependencias.

La altura de ranking incluye 32 px por fila + 40 px de área de trazado, más 100 px para título y ejes. Se documenta esta interpretación de la altura de la spec para evitar recortar títulos y unidades en rankings de una fila. Un contenedor con altura CSS fija por número de filas evita que Dash comprima el gráfico tras actualizarlo. JavaScript limita marcas a 24 px y conserva extremos redondeados.

Para CB11 se aplica la regla congelada de §8: catálogo actualizado y categorías con cero ocultas. No se agrega un control independiente de “mostrar todas” mencionado en 04, ya que no figura en la especificación final de componentes.

En “Todo” no hay un periodo anterior finito equivalente: los KPIs indican “Sin datos del periodo anterior”. La serie compartida mantiene todos los meses por compatibilidad con informes; solo la vista limita a 24 meses con aviso, y a seis en móvil.

La tabla conserva página y orden durante ticks. Una nueva entrada puede desplazar filas dentro de esa página por el orden cronológico; la página no se reinicia. Los datos de la tabla pueden reflejar una inserción ocurrida después del snapshot de agregaciones, y convergen en el siguiente tick; no se guarda una segunda base de registros en el navegador.

## Pruebas existentes adaptadas

- F3/T20 usa `refresh_data`, `render_records` y componentes puros en lugar del callback monolítico retirado. Masa esperada cambia de `1.500 kg` a `1,50 kg` por CA-01/02.
- Google Forms verifica el mismo filtro mediante el store y tabla paginada; origen se comprueba como barra 100 % y nombres legibles. Vacío único sustituye anotaciones en cada gráfico; error verifica store conservado y `.stale`.
- Estado mensual verifica un chip del último periodo sin variables de entorno, según CA-15. La página Informes conserva sus pruebas previas.
- Prueba del montaje verifica el elemento semántico `Main` del layout. Autenticación y protección conservadas.
- `scripts/capture_ui.py` espera el KPI nuevo; el ID del KPI antiguo ya no existe.

## Validación de paleta CA-23

Comando ejecutado:

```text
python -X utf8 .agents/skills/dataviz/scripts/validate_palette.py "#199e70,#3987e5,#d95926" --mode dark --surface "#14231D" --pairs all
```

Salida completa:

```text
Palette (dark, surface #14231D, categorical): 3 slots
  [PASS] Lightness band         all 3 inside L 0.48–0.67
  [PASS] Chroma floor           all 3 >= 0.1
  [PASS] CVD separation         worst all-pairs #d95926↔#199e70 ΔE 9.4 (deutan) · tritan 4.0
  [PASS] Normal-vision floor    worst all-pairs #3987e5↔#199e70 ΔE 20.9 (normal)
  [PASS] Contrast vs surface    all 3 >= 3:1

  → ALL CHECKS PASS  (CVD in the 6–8 floor band is legal ONLY with secondary encoding: direct labels, gaps, or texture)
  scope: categorical palettes only. For a lone status/text color check text contrast with this script's apca() or contrast(); for a sequential ramp, lightness monotonicity.
```

También se ejecuta en `test_redesign_palette.py`, que exige los tres colores exactos. Salida: `evidencias/palette.txt`. Contrastes de texto verificados en `evidencias/contrast.json`: todos ≥ 4,5:1; muted sobre input 8,8:1.

## Evidencia y QA

Fixture visual independiente: 55 registros actuales × 100 g = 5.500 g, 5,50 kg; promedio 0,10 kg; causa principal 100 %. Tres registros históricos: enero 500 g y febrero 1.000 g. Durante la prueba de actualización se agrega un registro de 500 g: resultado esperado 56 registros actuales y 6,00 kg, visible en el siguiente tick conservando la página 2. El CSV contiene las 56 filas filtradas y una cabecera. No son datos personales ni registros de la base de uso.

Playwright usa Chromium con TestClient sobre PostgreSQL desechable. Capturas en `evidencias/dashboard-{320,390,768,1440}.png`, más fechas inválidas, error de BD, estado vacío y filtros. Se revisan las imágenes generadas, no solo el DOM. Se comprueba la conservación de página tras un tick real de 15 s, descarga completa, foco y controles de 44 px, labels asociados, idioma y ausencia de overflow.

Primer intento con Python global no encontró pytest: se usó el Python existente de `.venv`. El temporal global de pytest devolvió acceso denegado; se usa un directorio nuevo bajo `.tools/` mediante `--basetemp`, sin borrar temporales ajenos. Se corrigieron fallos encontrados en alturas de gráficos, asociaciones de labels de Dash 4 y validación de fechas sin debounce.

Comando de suite completa: `.venv/Scripts/python.exe -X utf8 -m pytest -q --basetemp=.tools/pytest-redesign-full-02`.

Comando de análisis: `.venv/Scripts/python.exe -X utf8 -m ruff check src tests scripts`.

Resultados finales se registran en `evidencias/pytest.txt`, `evidencias/ruff.txt` y `checklist.md`. Las capturas incluyen filtros abiertos; `evidencias/input-styles.json` registra los colores reales del buscador y paginación: placeholder muted sobre input, contraste 8,8:1. No se declaran verificaciones de producción ni se activan tareas, envíos reales o servicios externos.

Resultado final: **124 passed, 6 warnings in 74.07s**; Ruff: **All checks passed!**. Los seis avisos son de deprecación de Starlette/HTTP 422 y Dash DataTable; no se agregaron dependencias para reemplazarlos. Tras mejorar la toma de capturas, se repitieron las tres pruebas de `test_redesign_ui.py`: **3 passed in 33.67s**. Se revisaron visualmente las capturas finales de escritorio, móvil, fechas inválidas, vacío y BD caída. Versiones instaladas en `evidencias/versions.json`.

## Commits por componente

- Base previa: `f7cf0e6`.
- Agregaciones: `099a9e9`.
- Datos, formatos, filtros y CSV: `f5434a4`.
- Componentes de visualización: `8328abc`.
- Layout, CSS y accesibilidad de navegador: `7b19c94`.
- Callbacks, conexión de aplicación y regresión: `1812ea8`.

Los commits son locales. No se publicó ni desplegó el rediseño.

## Fase 8 · ciclo 1 · correcciones de revisión

Alcance exclusivo: R-01–R-04 de `opus/07-revision.md`. No se modifica la spec ni los archivos de Opus; la revisión autoriza estas correcciones y precisa el comportamiento esperado.

### R-01 · periodos de comparación

La revisión reemplaza, para presets, la interpretación inicial de días contiguos: Este mes compara los mismos días del mes anterior, limitados a su último día; Mes anterior compara con el mes calendario completo anterior; 3 y 12 meses desplazan ambos extremos 3 y 12 meses. Personalizado conserva días contiguos de igual longitud. Todo no tiene comparación finita.

`parse_filters` prepara límites y etiqueta de comparación. `get_aggregations` acepta esos límites opcionales dentro de su misma sentencia SQL; los consumidores anteriores que no los envían mantienen su contrato. Las fechas de comparación no alteran los filtros de registros ni del CSV. Los KPIs reciben etiquetas `oct 2026`, `jun–ago 2026` o fechas `dd-mm-aaaa`, sin fechas ISO visibles en el delta.

Validación ejecutada: `.venv/Scripts/python.exe -X utf8 -m pytest tests/test_redesign_review_periods.py tests/test_redesign_data.py tests/test_redesign_aggregations.py -q --basetemp=.tools/pytest-review-r01`: **26 passed**. Fixture independiente: febrero 1.000 g frente a enero 1–10 de 100 g; delta renderizado `▲ 900 % vs ene 2026`. Pruebas por cada preset, febrero corto/bisiesto y cruce de año.

### R-02 · página coherente con filtros y orden

El callback de tabla concentra datos, página, contador y contexto de filtros/orden en una sola respuesta. `table-context` conserva únicamente el contexto aplicado. Cambios de filtros válidos, fechas, preset u orden reinician a cero; un tick con el mismo contexto conserva la página. Un descenso del total limita la página a la última válida antes de calcular el offset. Fechas inválidas mantienen el store y el contexto anteriores.

Validación ejecutada: `.venv/Scripts/python.exe -X utf8 -m pytest tests/test_redesign_review_paging.py -q --basetemp=.tools/pytest-review-r02-browser`: **3 passed**. Incluye reinicio por cada clase de cambio, conservación, límite por reducción de filas y Chromium en página 3 con filtro ESP32 de una fila: página `1 / 1`, fila presente. Captura: `evidencias/review-r02-paging.png`.

### R-03 · barra de Origen legible

Se fija el dominio vertical de la barra apilada y un grosor de 18 px sobre su área de trazado de 85 px. Se conservan los colores aprobados, separaciones, leyenda, valores y tooltips. La ampliación solicitada por R-03 prevalece sobre la barra fina de la implementación inicial.

Validación: `.venv/Scripts/python.exe -X utf8 -m pytest tests/test_redesign_ui.py -q --basetemp=.tools/pytest-review-r03-final`: **3 passed**. El navegador mide cada segmento entre 16 y 20 px a 320/390/768/1440 px y activa el tooltip apuntando al centro real del segmento a 390 y 1440 px. Capturas `evidencias/origin-390.png` y `origin-1440.png` revisadas visualmente. Los primeros intentos corrigieron la prueba de hover para usar la capa de interacción propia de Plotly y lectura de texto SVG; no se alteró la interacción del producto.

### R-04 · caché de tokens

`components.tokens()` usa `functools.lru_cache(maxsize=1)`. Los colores conservan su fuente CSS y sus valores; no se vuelve a leer CSS en cada figura o tick. Un reinicio del proceso renueva la caché tras cambiar el tema.

Validación ejecutada: `.venv/Scripts/python.exe -X utf8 -m pytest tests/test_redesign_review_tokens.py tests/test_redesign_palette.py -q --basetemp=.tools/pytest-review-r04`: **2 passed**. Se dibujan nueve figuras de ranking, meses y origen, interceptando las lecturas reales: solo `theme.css` y `dashboard.css` una vez cada uno. La paleta exacta y los contrastes siguen aprobados.

### Commits del ciclo 1

- R-01: `b4f0406`.
- R-02: `c395a96`.
- R-03: `e65a6b1`.
- R-04: `e551507`.

Regresión del ciclo: `.venv/Scripts/python.exe -X utf8 -m pytest -q --basetemp=.tools/pytest-review-final-01`, con salida UTF-8 en `evidencias/review-pytest.txt`. Ruff: `.venv/Scripts/python.exe -X utf8 -m ruff check src tests scripts`, en `evidencias/review-ruff.txt`. Las capturas generales se actualizan al ejecutar la prueba UI sobre PostgreSQL desechable. La revisión de `opus/` permanece sin cambios.

Resultado final del ciclo 1: **138 passed, 6 warnings in 87.06s**. Ruff: **All checks passed!**. Los seis avisos de deprecación son los ya presentes en la fase inicial. Se conservan la paginación de 25 filas y el alcance de v2; no se implementó la sugerencia opcional para una futura v3. Se devuelven los cuatro R-xx resueltos a Opus para su comprobación.
