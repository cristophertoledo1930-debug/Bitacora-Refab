# 02 · Mantener / Rediseñar / Eliminar / Agregar

Prioridad: P1 = bloquea lectura correcta · P2 = mejora clara · P3 = deseable.

| ID | Elemento | Veredicto | Razón (una línea) | Prio |
|---|---|---|---|---|
| E01 | Marca sidebar | Mantener | Identidad Re-Fab/Lab881 consistente con resto de páginas | P3 |
| E02 | Estado Sheets | Rediseñar | Mover a barra de estado superior como chip (OK / pendiente / error) | P2 |
| E03 | Estado correo mensual | Rediseñar | Expone variables de entorno y lista todos los periodos; resumir a 1 chip + link a Informes | P1 |
| E04 | Nuevo registro | Rediseñar | Botón primario visible; token desde config, no hardcode | P2 |
| E05 | Anclas con emoji | Eliminar | Página única; emojis ruido; reemplazar por header con acciones | P3 |
| E06 | Informes PDF | Mantener | Acción útil; pasar a header como botón secundario | P2 |
| E07 | `<details>` por mutación | Rediseñar | Construir layout declarativo; filtros en barra superior plegable | P2 |
| E08 | Última actualización / error al pie | Rediseñar | Errores invisibles en móvil; mover a barra de estado arriba | P1 |
| E09 | Header | Mantener | Agregar rango activo como subtítulo dinámico | P2 |
| F01 | Radio métrica | Mantener | Útil; convertir a control segmentado | P3 |
| F02 | Fechas | Rediseñar | Sin presets ni valor por defecto; agregar presets (Este mes, Mes anterior, 3 m, 12 m, Todo) | P1 |
| F03-F07 | Dropdowns catálogo | Rediseñar | Catálogo cargado al importar (no refresca); 5 dropdowns apilados; agrupar + "Limpiar filtros" + contador de filtros activos | P1 |
| K01 | Total registros | Mantener | Formato es-CL `1.234` | P1 |
| K02 | Masa total "acumulada" | Rediseñar | "1.500 kg" se lee como mil quinientos en es-CL; y no es acumulada sino del periodo | P1 |
| K03 | Registros este mes | Eliminar | Redundante con presets de periodo; contradice filtro de fechas | P2 |
| K04 | Mayor categoría | Rediseñar | Fusionar en ranking (G02); KPI muestra % del total | P2 |
| K05 | Masa este mes | Eliminar | Reemplazado por KPI masa periodo + delta vs periodo anterior | P2 |
| K06 | Principal causa | Mantener | Pregunta clave del lab; mostrar con % | P2 |
| — | Delta vs periodo anterior | Agregar | Sin comparación los números no dicen si mejora o empeora | P1 |
| — | Promedio por registro (kg) | Agregar | Detecta registros anómalos/ escala | P3 |
| G01 | Origen | Rediseñar | Gráfico grande para 2-3 valores; pasar a barra apilada 100 % fina o mini-tabla | P2 |
| G02 | Tipo | Rediseñar | Barras horizontales ordenadas desc, un solo color, etiqueta con unidad, ocultar ceros | P1 |
| G03 | Causa | Rediseñar | Ordenar desc (hoy alfabético), un color, % | P1 |
| G04 | Máquinas | Rediseñar | Igual a G03; sin etiquetas valor, mucho vacío | P2 |
| G05 | Materiales | Rediseñar | Igual a G03 | P2 |
| G06 | Evolución mensual | Rediseñar | Primer gráfico tras KPIs; destacar mes actual parcial; título corto | P1 |
| T01 | Tabla | Rediseñar | Paginación/orden en servidor, origen legible, g sin decimales, exportar CSV | P1 |
| M01 | Recepción Forms | Rediseñar | Unificar en chip de estado de fuentes | P3 |
| M02/M03 | Vacíos | Rediseñar | Un único estado vacío con acción "Limpiar filtros" | P2 |
| I01/I02 | Refresh 15 s × 4 consultas | Rediseñar | Una sola agregación por tick (`dcc.Store`) y serie mensual en 1 query GROUP BY | P1 |
| I03 | Colores por hash | Eliminar | Color sin significado + colisiones; usar 1 color + acento para destacado | P1 |
| I04 | Estilos inline + `!important` | Rediseñar | Tokens en CSS (`theme.css`), sin inline | P2 |
