---
name: dataviz
description: Método para cualquier gráfico/dashboard - forma, color por función, validación de paleta (scripts/validate_palette.js|.py), marcas, hover, accesibilidad. Leer antes de escribir código de gráficos.
---

# Data Visualization

Copia de la skill integrada `dataviz` de Claude Code (2026-11-09) para uso de Codex en el rediseño.

## Procedimiento (en orden; el color va AL FINAL)
1. **Elegir la forma.** ¿Magnitud, identidad, polaridad, titular único, cambio en el tiempo? A veces no es un gráfico (stat tile). -> `references/choosing-a-form.md`
2. **Asignar color por función.** Categórico (identidad), secuencial (magnitud), divergente (polaridad), estado. Hues categóricos en orden fijo, nunca ciclados. -> `references/color-formula.md`
3. **VALIDAR la paleta con el script**, no a ojo: `node scripts/validate_palette.js "<hex,...>" --mode dark` (o `python scripts/validate_palette.py`). Corregir todo FAIL. Validar contra la superficie del modo usado.
4. **Specs de marcas.** Marcas finas, extremos redondeados 4px anclados a la base, líneas 2px, marcadores >=8px, separación 2px entre rellenos, etiquetas directas selectivas. -> `references/marks-and-anatomy.md`
5. **Capa hover por defecto.** Tooltip por marca en barras; crosshair en líneas. Filtros en una fila sobre los gráficos. -> `references/interaction.md`
6. **Accesibilidad final.** >=2 series: leyenda siempre (y <=4 con etiqueta directa); una serie: sin leyenda, el título la nombra. Vista de tabla disponible. Modo oscuro validado, no invertido automáticamente.
7. **Renderizar y mirar** (captura): colisiones de etiquetas, geometría, overflow.

Luego revisar `references/anti-patterns.md`: si el gráfico coincide con una entrada, está mal.

## No negociables
- Hues categóricos en orden fijo; la serie 9 se pliega en "Otros" o small multiples.
- Un solo eje Y; nunca doble eje.
- El color sigue a la entidad, no a su rango; filtrar no repinta las sobrevivientes.
- Secuencial = un hue claro->oscuro. Divergente = dos hues + gris neutro al medio. Nunca arcoíris.
- Ejecutar el validador antes de publicar una paleta categórica (CVD ΔE >= 8 objetivo; 6-8 solo con codificación secundaria; visión normal < 15 = FAIL). Un WARN de contraste obliga a etiquetas visibles o tabla.
- Marcas finas, grid/ejes recesivos, nunca un número en cada punto.
- El texto usa tokens de texto, nunca el color de la serie.
- Colores de estado (bien/advertencia/serio/crítico) reservados, siempre con icono + etiqueta.

## Referencias
| Archivo | Responde |
|---|---|
| references/choosing-a-form.md | ¿Qué tipo de gráfico? |
| references/color-formula.md | Las 4 funciones, los 6 checks |
| references/marks-and-anatomy.md | Marcas, separadores, etiquetas, hero number |
| references/interaction.md | Tooltips, filtros, rangos de tiempo |
| references/components.md | Piezas de un gráfico |
| references/anti-patterns.md | Qué sale mal |
| references/palette.md | Paleta de referencia (sustituir por la de Re-Fab: tokens de 05-spec-diseno.md §6) |
| scripts/validate_palette.js / .py | Validador ejecutable |
