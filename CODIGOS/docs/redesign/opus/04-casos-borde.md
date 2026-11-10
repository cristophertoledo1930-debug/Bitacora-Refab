# 04 · Casos borde

Comportamiento actual deducido del código (referencias en `01-inventario.md`). Severidad: crítico / alto / medio / bajo.

| ID | Caso | Comportamiento actual | Esperado | Sev. |
|---|---|---|---|---|
| CB01 | BD vacía (0 registros) | KPIs "0", "0.000 kg", "N/A"; gráficos con todas las categorías en 0 + anotación; 6 meses vacíos | Un estado vacío único con texto + botón "Nuevo registro"; KPIs "—" | Medio |
| CB02 | Filtros sin resultados | Anotación en cada gráfico + mensaje M02; K03/K05 pueden ser 0 | Estado vacío único con "Limpiar filtros" y filtros activos listados | Medio |
| CB03 | Un solo registro | Funciona; % = 100 %; delta no calculable | Delta "sin periodo anterior" en vez de ∞ % | Medio |
| CB04 | Periodo anterior = 0 | (no existe delta) | Mostrar "nuevo" / "—", nunca división por cero | Alto |
| CB05 | Fecha desde > hasta | Callback principal: error al pie sidebar; otros 3 callbacks fallan en silencio y conservan datos viejos → mezcla de estados | Validación inmediata junto al campo; ningún gráfico se actualiza; mensaje en barra de estado | Crítico |
| CB06 | Solo fecha "desde" en el futuro | `series_start > series_end` → serie mensual vacía sin aviso | Serie limitada a hoy; aviso "rango posterior a hoy" | Medio |
| CB07 | Rango de 5 años | Serie: 60 queries por callback ×1 + barras ilegibles | 1 query GROUP BY; si > 24 meses agrupar por trimestre o scroll | Medio |
| CB08 | Peso enorme (p.ej. 500 000 g) | `1,234`/`500.000 kg` mezcla de locales; barras aplastan al resto | Formato es-CL único; eje automático; tooltip exacto | Alto |
| CB09 | Peso con decimales (0,5 g) | Tabla "0.500"; kg 3 decimales | g: hasta 1 decimal; kg: 1-2 decimales según magnitud | Medio |
| CB10 | Peso nulo / negativo | Validación en ingreso (`records.py`); dashboard asume no nulo, `str(None)` si `sum` None | Tratar None como 0 y registrar warning; nunca "None" en pantalla | Medio |
| CB11 | Catálogo nuevo o desactivado | Dropdown no se actualiza hasta reiniciar; gráficos incluyen inactivos con 0 | Opciones cargadas por callback; ocultar categorías con 0 (toggle "mostrar todas") | Alto |
| CB12 | Nombres largos (> 40 car.) | Envueltos a 22 car.; K04 ellipsis | Truncar con tooltip completo; tabla con wrap | Bajo |
| CB13 | > 12 categorías en un gráfico | Todas mostradas, alto fijo 260 px → barras ilegibles | Top 8 + "Otros"; altura proporcional | Alto |
| CB14 | Empates en top categoría/causa | Gana el primero alfabético en silencio | Mostrar "A y B (empate)" | Bajo |
| CB15 | 10 000+ registros | Todas las filas al cliente cada 15 s | Paginación servidor (`page_action="custom"`), 25 filas | Alto |
| CB16 | Base de datos caída | Callback principal: "Error: Base de datos no disponible" al pie; otros silencio | Banner de estado arriba, valores marcados "desactualizados desde HH:MM" | Crítico |
| CB17 | `sheets-status.json` faltante/corrupto | "Sheets: esperando primera sincronización" | Igual, pero como chip "sin datos" | Bajo |
| CB18 | Muchos periodos de correo | Texto crece sin límite en sidebar | Solo último periodo + link a Informes | Medio |
| CB19 | Pantalla 320-390 px | Sidebar plegable; KPIs 2 col; gráficos 300 px min; tabla scroll horizontal | KPIs 2 col, filtros en hoja plegable, gráficos 100 % ancho, tabla en tarjetas o columnas reducidas | Alto |
| CB20 | Datos cambian en caliente durante filtrado | Interval reemplaza datos; página de tabla puede volver a 1 | Conservar página y orden; indicador discreto "actualizado HH:MM:SS" | Medio |
| CB21 | Mes actual parcial | Se compara visualmente con meses completos | Barra del mes actual con patrón/opacidad + etiqueta "en curso" | Medio |
| CB22 | Zona horaria / DST Santiago | Correcto en agregaciones; tabla OK | Mantener (test existente) | Bajo |
| CB23 | Origen nuevo no listado (p.ej. `api`) | Dropdown hardcode no lo ofrece; G01 lo muestra crudo | Opciones desde `by_source`; etiqueta fallback legible | Bajo |
