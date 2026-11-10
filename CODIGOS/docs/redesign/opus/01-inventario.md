# 01 · Inventario del dashboard actual

Fuente: lectura de `src/lab_hub/dashboard/app.py` (645 líneas), `assets/local.css`, `assets/navigation.js`, `services/aggregations.py`, captura `docs/evidencias/google_forms_ui/after-dashboard-desktop.png` (fixture 3 registros).
No se ejecutó en vivo (requiere PostgreSQL); el comportamiento se deduce del código + captura.

## Dashboard objetivo
| Campo | Valor |
|---|---|
| Ruta | `CODIGOS/src/lab_hub/dashboard/` |
| Entrada | `dashboard/app.py` (Dash), montado en FastAPI `api/app.py:79` en `/dashboard` |
| Datos | PostgreSQL vía SQLAlchemy (`WasteRecord` + catálogos), agregados en `services/aggregations.py:get_aggregations` |
| UI | Dash + Plotly `graph_objects` + `dash_table` |
| Público | Personal Lab881/Re-Fab (técnicos de máquinas), coordinación del laboratorio, responsables de informes mensuales |

## Estructura / navegación
| ID | Elemento | Qué muestra | Fuente | Código |
|---|---|---|---|---|
| E01 | Sidebar marca | "Re-Fab · Lab881 / Panel de Residuos" | estático | app.py:139-142 |
| E02 | Estado Sheets | Sincronización Google Sheets (texto) | `storage/sheets-status.json` | app.py:56-72, 144 |
| E03 | Estado correo mensual | Flags env (`EMAIL_ENABLED`, `REPORT_AUTO_SEND_FROM`), próxima comprobación ISO, estado de **todos** los periodos | `report_status.monthly_delivery_status` | app.py:38-53, 145 |
| E04 | Link "Nuevo registro" | `/r/token-general` (token fijo) | estático | app.py:150 |
| E05 | Links ancla 📊 Resumen / 📋 Registros | Saltos internos | estático | app.py:151-152 |
| E06 | Link 📄 Informes PDF | `/reports` en pestaña nueva | estático | app.py:153 |
| E07 | `<details>` plegable móvil | Envuelve todo el sidebar | mutación post-layout + navigation.js | app.py:615-618, navigation.js |
| E08 | Texto "Última actualización" / errores | Timestamp o "Error: …" al pie del sidebar | callback principal | app.py:220-223, 526-542 |
| E09 | Header main | "Residuos del laboratorio" + subtítulo | estático | app.py:239-241 |

## Filtros
| ID | Elemento | Valores | Código |
|---|---|---|---|
| F01 | Radio métrica | Masa (kg) / Registros | app.py:161-171 |
| F02 | Fecha desde / hasta | `input type=date`, sin presets, sin default | app.py:173-176 |
| F03 | Tipo de residuo | catálogo activo (cargado **al importar**) | app.py:85-109, 177-184 |
| F04 | Material | idem | app.py:186-193 |
| F05 | Máquina | idem (label sin `htmlFor`) | app.py:195-202 |
| F06 | Origen | Manual / Google Forms / ESP32 (hardcode) | app.py:204-210 |
| F07 | Causa | catálogo activo | app.py:211-218 |

## KPIs
| ID | Elemento | Qué muestra | Fuente | Código |
|---|---|---|---|---|
| K01 | TOTAL REGISTROS | count filtrado, formato `1,234` (en-US) | `total_records` | app.py:251-257, 413 |
| K02 | MASA TOTAL ACUMULADA | kg filtrado con 3 decimales "1.500 kg" | `total_weight_kg` | app.py:258-264 |
| K03 | REGISTROS ESTE MES | count mes calendario actual ∩ filtros | `current_month_records` | app.py:265-271 |
| K04 | MAYOR CATEGORÍA EN MASA | "Nombre (x kg)" o "N/A" | `top_category_by_mass` | app.py:272-278 |
| K05 | MASA ESTE MES | kg mes actual ∩ filtros | `current_month_weight_kg` | app.py:621, 643 |
| K06 | PRINCIPAL CAUSA POR MASA | nombre o "Sin registros" | `top_cause_by_mass` | app.py:622, 643 |

## Gráficos
| ID | Elemento | Tipo | Fuente | Código |
|---|---|---|---|---|
| G01 | Origen de los registros | barras verticales por source, color fijo por origen, con `dcc.Loading` | `by_source` | app.py:284-285, 581-612 |
| G02 | Desglose por Tipo | barras verticales, color hash, etiqueta valor crudo | `by_waste_type` (incluye tipos con 0) | app.py:293-294, 419-439 |
| G03 | Desglose por Causa | barras horizontales, color hash, orden alfabético | `by_cause` | app.py:300-301, 442-463 |
| G04 | Máquinas | barras horizontales, sin etiquetas valor, fondo panel | `by_machine` | app.py:308, 548-578 |
| G05 | Materiales | idem | `by_material` | app.py:309, 548-578 |
| G06 | Evolución mensual | barras por mes, ≥6 meses, ceros incluidos | `monthly_series` | app.py:316-317, 466-486 |

## Tabla y mensajes
| ID | Elemento | Qué muestra | Código |
|---|---|---|---|
| T01 | Registros Individuales | 8 columnas, `page_size=10`, **todas** las filas enviadas al cliente, source crudo (`google_forms`), g con 3 decimales | app.py:322-360, 494-524 |
| M01 | Recepción Google Forms | "Última respuesta recibida…" (ignora filtros) | app.py:282, 597-599 |
| M02 | Estado vacío | "Sin registros para estos filtros…" | app.py:283, 642 |
| M03 | Anotación vacía en gráficos | "Sin registros para estos filtros" | app.py:488-491, 573, 608 |

## Interacciones / técnica
| ID | Elemento | Detalle | Código |
|---|---|---|---|
| I01 | Auto-refresh | `dcc.Interval` 15 s dispara 6 callbacks | app.py:123 |
| I02 | Consultas | 4× `get_aggregations` por tick + query de tabla + correo + sheets; serie mensual = 1 query por mes | app.py:404, 559, 592, 637 |
| I03 | Colores | 6 tonos asignados por hash del código → colisiones y sin significado | app.py:75-77 |
| I04 | Paleta / tipografía | fondo #0B1411, panel #14231D, primario #64D6A0, Segoe UI; estilos inline + CSS con `!important` duplicados | app.py:17-23, local.css |
| I05 | Chatbot | No existe | — |
