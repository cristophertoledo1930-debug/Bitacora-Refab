# 05 · Especificación de diseño — v2 (congelada)

## Historial
| Versión | Fecha | Cambio |
|---|---|---|
| v1 | 2026-11-09 | Versión inicial |
| v2 | 2026-11-09 | Respuesta a P-01: paleta de Origen reemplazada por una validada (§5 Origen, §6, CA-23). Nada más cambia. |

Contrato para Codex. Tras aprobar el Gate 1 queda congelada; cambios → `STATUS.md > preguntas`.
Stack fijo: Dash + Plotly + PostgreSQL. Sin dependencias nuevas.

## 1. Arquitectura de código
| Módulo | Responsabilidad |
|---|---|
| `dashboard/data.py` | Parseo de filtros, llamada única a agregaciones, consulta paginada de tabla, formateo es-CL |
| `dashboard/components.py` | KPI card, ranking chart, monthly chart, status chip, empty state (funciones puras → componentes) |
| `dashboard/layout.py` | Layout declarativo (sin mutaciones post-definición) |
| `dashboard/callbacks.py` | Callbacks; 1 callback de datos → `dcc.Store("agg-store")`; render lee del store |
| `dashboard/app.py` | Instancia Dash, registra layout/callbacks (mantiene `app`, `server` exportados) |
| `dashboard/assets/dashboard.css` | Estilos con variables de `static/theme.css`; sin estilos inline ni `!important` |
| `services/aggregations.py` | + `previous_period` (mismo largo inmediatamente anterior) + serie mensual en 1 query GROUP BY; contrato de salida actual se conserva (claves extra permitidas) |

## 2. Layout escritorio (≥ 1024 px)
```
┌────────────────────────────────────────────────────────────────────────┐
│ RE-FAB · LAB881   Residuos del laboratorio      [+ Nuevo registro] [Informes] │
│ Periodo: 1–9 nov 2026 · 2 filtros activos   ● Sheets OK  ● Correo: oct enviado │
│                                         Actualizado 14:32:05 (cada 15 s)│
├────────────────────────────────────────────────────────────────────────┤
│ [Este mes][Mes anterior][3 meses][12 meses][Todo][Personalizado▾]      │
│ Tipo▾  Material▾  Máquina▾  Causa▾  Origen▾   Métrica:(kg|registros) [Limpiar] │
├───────────────┬───────────────┬───────────────┬────────────────────────┤
│ MASA PERIODO  │ REGISTROS     │ PROMEDIO/REG. │ PRINCIPAL CAUSA        │
│ 12,4 kg       │ 37            │ 0,34 kg       │ Margen de corte · 41 % │
│ ▲ 18 % vs oct │ ▼ 5 vs oct    │               │ 5,1 kg                 │
├───────────────┴───────────────┴───────────────┴────────────────────────┤
│ Evolución mensual (kg)                                  barras, mes en curso atenuado │
├───────────────────────────────────┬────────────────────────────────────┤
│ Por causa (ranking)               │ Por tipo de residuo (ranking)      │
├───────────────────────────────────┼────────────────────────────────────┤
│ Por máquina (ranking)             │ Por material (ranking)             │
├───────────────────────────────────┴────────────────────────────────────┤
│ Origen: ███████ Manual 70 % ███ Forms 25 % █ ESP32 5 %  (barra 100 % fina) │
├────────────────────────────────────────────────────────────────────────┤
│ Registros (37)                               [Exportar CSV]            │
│ Fecha/hora | Tipo | Material | Máquina | Causa | Peso | Origen         │
│ … 25 por página, orden por fecha desc, paginación servidor             │
└────────────────────────────────────────────────────────────────────────┘
```
Sin sidebar: la barra de filtros es horizontal y "sticky" bajo el header.

## 3. Layout móvil (< 768 px)
```
RE-FAB · LAB881           [+ Nuevo]
Residuos · 1–9 nov 2026
● Error/estado (solo si no OK)
[Este mes][Mes ant.][3 m][Más ▾]
[Filtros (2) ▾]  ← hoja plegable, cerrada por defecto
┌ MASA 12,4 kg ▲18 % ┐┌ REGISTROS 37 ┐
┌ PROMEDIO 0,34 kg   ┐┌ CAUSA Margen 41 % ┐
Evolución mensual (100 % ancho, últimos 6 meses visibles)
Rankings apilados (causa, tipo, máquina, material)
Origen (barra 100 %)
Registros como lista de tarjetas: fecha · peso grande · tipo/causa
```

## 4. Jerarquía (orden de lectura)
1. Estado del sistema solo si hay problema (banner) · 2. Periodo activo · 3. KPI masa + delta · 4. Evolución mensual · 5. Rankings · 6. Origen · 7. Tabla.

## 5. Componentes
| Componente | Especificación |
|---|---|
| KPI card | Etiqueta (mayúsculas, 0,75 rem, muted), valor (2 rem, texto), delta (0,85 rem). Delta: ▲/▼ + texto, color neutro muted (más residuo no siempre es "malo"); nunca solo color |
| Ranking chart | Barras horizontales, orden desc por métrica, 1 color `--primary`, etiqueta fuera de barra "4,2 kg · 34 %", top 8 + "Otros (n)", altura = 32 px × filas + 40, categorías con 0 ocultas |
| Serie mensual | Barras `--primary`; mes en curso opacidad 0,45 + etiqueta "en curso"; eje y con unidad; tooltip "nov 2026: 12,4 kg (37 reg.)"; >24 meses → últimos 24 + aviso |
| Origen | Barra horizontal 100 % apilada, 3 tonos fijos (v2, validados): Manual `#199E70`, Google Forms `#3987E5`, ESP32 `#D95926`; separación de 2 px entre segmentos; etiqueta directa con nombre, % y valor (codificación secundaria); orígenes adicionales → gris `--muted` como "Otros" |
| Status chip | Punto + texto: OK (primario), Pendiente (`#FFC982`), Error (`--danger`). Correo: "Informe {mes}: enviado/pendiente/falló" + link a `/reports`. Sin nombres de variables de entorno |
| Banner error | Arriba del contenido, `role="alert"`, texto + hora de últimos datos válidos; valores se marcan con clase `.stale` (opacidad 0,6) |
| Estado vacío | Un solo bloque en lugar de KPIs+gráficos: "No hay registros para {periodo}{con filtros}". Botones: [Limpiar filtros] [+ Nuevo registro] |
| Presets periodo | Botones toggle `aria-pressed`; default **Este mes**; "Personalizado" abre las 2 fechas |
| Tabla | `page_action="custom"`, 25 filas, columnas: Fecha/hora (dd-mm-aaaa HH:MM), Tipo, Material, Máquina, Causa, Peso, Origen legible. Peso formateado (ver §7). Exportar CSV del filtro completo (endpoint autenticado existente o `dcc.Download`) |

## 6. Paleta y tipografía
| Token | Valor | Uso |
|---|---|---|
| `--bg` | #0B1411 | fondo |
| `--panel` | #14231D | tarjetas |
| `--primary` | #64D6A0 | datos, acciones |
| `--text` | #F4F8F5 | texto |
| `--muted` | #BCCEC3 | etiquetas |
| `--border` | #2B4237 | bordes de tarjeta |
| `--warn` | #FFC982 | pendiente |
| `--danger` | #FF9090 | error |
Paleta categórica (solo gráfico de Origen, v2): `--series-1` #199E70 · `--series-2` #3987E5 · `--series-3` #D95926. Validación:
`python -X utf8 .agents/skills/dataviz/scripts/validate_palette.py "#199e70,#3987e5,#d95926" --mode dark --surface "#14231D" --pairs all` → ALL CHECKS PASS (luminosidad 0,48–0,67; croma ≥ 0,1; CVD peor ΔE 9,4; visión normal peor ΔE 20,9; contraste ≥ 3:1).
Los rankings y la serie mensual son de una sola serie: usan `--primary` (#64D6A0), no se validan como categóricos. Los textos y etiquetas usan tokens de texto, nunca el color de la serie.

Tipografía: sistema (`Segoe UI, system-ui`), números con `font-variant-numeric: tabular-nums`. Inputs con fondo `--input` (#1B2D26) y texto claro (corrige placeholder invisible). Se elimina `category_colors` por hash.

## 7. Textos y formato
| Dato | Regla | Ejemplo |
|---|---|---|
| Masa ≥ 10 kg | 1 decimal, coma decimal, punto miles | 1.234,5 kg |
| Masa < 10 kg | 2 decimales | 0,38 kg |
| Masa < 0,01 kg | gramos | 5 g |
| Conteo | punto miles | 1.234 |
| % | entero (1 decimal si < 1 %) | 41 % |
| Fecha | dd-mm-aaaa HH:MM, "America/Santiago" solo en tooltip/pie | 03-11-2026 01:53 |
| Delta | "▲ 18 % vs oct 2026" / "Sin datos del periodo anterior" | |
| Origen | manual→Manual, google_forms→Google Forms, esp32→ESP32, otro→Capitalizado | |
Formato centralizado en una función `fmt_*` con tests; Decimal hasta el formateo.

## 8. Comportamiento ante casos borde (`04-casos-borde.md`)
| Caso | Regla |
|---|---|
| CB01, CB02 | Estado vacío único (§5) |
| CB03, CB04 | Delta "—" + "Sin datos del periodo anterior" |
| CB05 | Fechas inválidas: mensaje bajo el campo (`aria-describedby`), ninguna consulta, datos previos intactos |
| CB06 | Fin efectivo = min(hasta, hoy); aviso si desde > hoy |
| CB07 | Serie en 1 query; >24 meses ver §5 |
| CB08-CB10 | §7; None → 0 + log warning |
| CB11 | Opciones de filtros por callback (refresh con interval, cada 5 min o por tick) |
| CB12 | Etiquetas truncadas a 28 car. con tooltip completo |
| CB13 | Top 8 + Otros |
| CB14 | "A y B (empate)" |
| CB15 | Paginación servidor |
| CB16 | Banner error + `.stale` |
| CB17, CB18 | Chips (§5), solo último periodo de correo |
| CB19 | §3; sin overflow horizontal a 320 px |
| CB20 | Mantener `page_current`, filtros y orden entre ticks; sin spinner en refrescos automáticos (solo en cambio de filtro) |
| CB21 | Mes en curso atenuado |
| CB23 | Opciones de origen desde datos |

## 9. Criterios de aceptación
| CA | Criterio | Prioridad |
|---|---|---|
| CA-01 | Todas las masas/conteos siguen §7 (test unitario de `fmt_*` con ≥ 8 casos incl. 0, 0,005, 1,5, 1500, 1 234 567) | Crítico |
| CA-02 | Ningún número visible usa 3 decimales ni punto decimal | Crítico |
| CA-03 | Periodo por defecto "Este mes"; periodo activo visible en header | Alto |
| CA-04 | KPI masa y registros muestran delta vs periodo anterior equivalente; CB04 sin división por cero | Alto |
| CA-05 | 4 KPIs exactos: Masa, Registros, Promedio/registro, Principal causa (con %) | Alto |
| CA-06 | Rankings ordenados desc, 1 color, etiqueta valor+%, top 8 + Otros, ceros ocultos | Alto |
| CA-07 | Serie mensual ubicada inmediatamente después de KPIs, mes en curso diferenciado | Medio |
| CA-08 | Fecha inválida → mensaje junto al campo y ningún componente se actualiza parcialmente | Crítico |
| CA-09 | BD caída → banner `role="alert"` arriba, valores previos marcados `.stale`, nunca ceros | Crítico |
| CA-10 | Filtros/BD vacía → un único estado vacío con "Limpiar filtros" funcional | Alto |
| CA-11 | Opciones de catálogo reflejan altas/bajas sin reiniciar | Medio |
| CA-12 | Tabla con paginación servidor (25), orígenes legibles, peso §7, página conservada tras refresh | Alto |
| CA-13 | Exportar CSV respeta filtros y descarga todas las filas filtradas | Medio |
| CA-14 | Una sola llamada a `get_aggregations` por tick/cambio de filtro; serie mensual en 1 query | Alto |
| CA-15 | Estado correo/Sheets como chips sin nombres de variables de entorno; solo último periodo | Medio |
| CA-16 | Sin overflow horizontal a 320, 390, 768 y 1440 px (Playwright) | Alto |
| CA-17 | Controles ≥ 44 px, foco visible, labels asociados a todos los filtros, `lang="es"` | Alto |
| CA-18 | Contraste texto ≥ 4,5:1 incluido placeholder de inputs | Alto |
| CA-19 | Sin estilos inline en layout ni `!important` en CSS nuevo; colores solo vía tokens | Medio |
| CA-20 | Tests existentes (`tests/test_f3_dashboard.py`, F5) en verde o actualizados con justificación en `codex/implementacion.md` | Crítico |
| CA-21 | Ninguna mutación de `app.layout` después de definirlo | Bajo |
| CA-22 | "Nuevo registro" no usa token hardcodeado (config/env) | Medio |
| CA-23 | La paleta de Origen es exactamente la de §6 v2 y el comando de validación de §6 da ALL CHECKS PASS (salida pegada en `codex/implementacion.md`) | Alto |
