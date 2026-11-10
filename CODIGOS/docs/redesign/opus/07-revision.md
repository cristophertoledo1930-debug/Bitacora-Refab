# 07 · Revisión de la implementación (ciclo 1)

Fecha: 2026-11-09 · Rama `redesign/codex` @ `2099b65` · Spec `05-spec-diseno.md` v2 · Opus en solo lectura.

## Evidencia ejecutada por Opus
| Verificación | Resultado |
|---|---|
| Suite completa `.venv/Scripts/python.exe -X utf8 -m pytest -q --basetemp=.tools/pytest-opus-review` | **124 passed, 6 warnings** (71,8 s). Incluye `test_redesign_ui.py`: dashboard real en Chromium sobre PostgreSQL desechable, viewports 320/390/768/1440 px |
| Lectura de código `dashboard/{data,callbacks,components,layout}.py`, `assets/navigation.js`, `services/aggregations.py` | Ver hallazgos |
| Script de periodos (`parse_filters` + `previous_period`, hoy = 09-11-2026) | month → anterior 23-10…31-10 · previous (oct) → anterior **31-08…30-09** · three → 23-06…31-08 · year → 22-12-2024…30-11-2025 |
| Formatos `fmt_mass` | 1500 g → "1,50 kg" · 5 g → "5 g" · 1.234.567 kg → "1.234.567,0 kg" ✔ |
| Capturas `codex/evidencias/dashboard-1440.png`, `dashboard-390.png` | Revisadas visualmente |

Nota: la prueba UI reescribe las capturas de `codex/evidencias/` al ejecutarse; Opus las restauró con `git checkout -- docs/redesign/codex/` tras la ejecución (sin cambios netos en la carpeta de Codex).

## Tareas de `03-test-usuario.md` repetidas
| Tarea | Antes | Ahora | Resultado |
|---|---|---|---|
| T1 kg este mes | ambiguo "1.500 kg" | KPI "5,50 kg", periodo "Este mes" por defecto | ✔ |
| T2 mejor/peor que antes | imposible | delta existe, pero compara con un periodo incorrecto y etiqueta ISO (R-01) | ✘ |
| T3 causa principal + % | cálculo manual | KPI "Soporte desprendido · 100 %" + ranking desc | ✔ |
| T4 máquina últimos 3 meses | 2 fechas manuales | preset "3 meses" + ranking | ✔ |
| T5 Forms de ayer | origen crudo | filtro Origen + "Personalizado"; orígenes legibles | ✔ (si el usuario está en la página 1, ver R-02) |
| T6 mi registro aparece | sin señal | "Actualizado HH:MM:SS (cada 15 s)", página conservada | ✔ |
| T7 informe enviado | jerga env | chip "Informe AAAA-MM: estado" enlazado a /reports | ✔ |
| T8 exportar | imposible | CSV filtrado completo | ✔ |

## Casos de `04-casos-borde.md`
| Caso | Resultado | Evidencia |
|---|---|---|
| CB01/CB02 vacío | ✔ estado único + Limpiar filtros | test UI, `empty.png` |
| CB03/CB04 sin periodo anterior | ✔ "— · Sin datos del periodo anterior" | `fmt_delta`, captura 1440 |
| CB05 fechas invertidas | ✔ sin consulta, store intacto, mensaje junto al campo | `test_invalid_dates_and_database_failure_are_atomic` |
| CB06 desde > hoy | ✔ "El rango es posterior a hoy" | `parse_filters` |
| CB07 rango largo | ✔ 1 sentencia, vista 24 meses + aviso | test contador SQL |
| CB08-CB10 magnitudes / None | ✔ | `fmt_*`, `number()` |
| CB11 catálogo en caliente | ✔ | test PostgreSQL |
| CB12 nombres largos | ✔ truncado 28 + tooltip | `ranking_chart`, `kpis` |
| CB13 > 8 categorías | ✔ top 8 + Otros | test 13 categorías |
| CB14 empates | ✔ "A y B (empate)" | `top_name` |
| CB15 volumen | ✔ 25 filas servidor | `record_rows` |
| CB16 BD caída | ✔ banner `role=alert`, `.stale` | `database-error.png` |
| CB17/CB18 Sheets / correo | ✔ chips, último periodo | `sheets_state`, `catalog_and_mail` |
| CB19 pantallas pequeñas | ✔ sin overflow 320-1440 | `responsive.json` |
| CB20 refresco en caliente | ✔ página conservada entre ticks · ✘ **no se reinicia al cambiar filtros** | R-02 |
| CB21 mes en curso | ✔ opacidad 0,45 + "en curso" | captura 1440 |
| CB22 DST | ✔ | tests existentes |
| CB23 origen nuevo | ✔ opciones desde datos | `catalog_and_mail` |

## Criterios de aceptación
| CA | Veredicto | Evidencia / motivo |
|---|---|---|
| CA-01 | Cumple | `test_redesign_data.py`; verificado con script |
| CA-02 | Cumple en números | Pero la etiqueta del delta muestra fechas ISO "2026-10-23 – 2026-10-31" (§7 exige "vs oct 2026") → R-01 |
| CA-03 | Cumple | preset activo + header "01-11-2026 – 09-11-2026" |
| CA-04 | **No cumple** | "Mes anterior" (oct) se compara con 31-ago…30-sep; "Este mes" (1-9 nov) con 23-31 oct en vez de 1-9 oct; spec §2/§7 dice "vs oct 2026" → R-01 |
| CA-05 | Cumple | 4 KPIs en test UI y captura |
| CA-06 | Cumple | test 13 categorías; captura |
| CA-07 | Cumple | layout + captura |
| CA-08 | Cumple | test atómico |
| CA-09 | Cumple | test + `database-error.png` |
| CA-10 | Cumple | test UI |
| CA-11 | Cumple | test PostgreSQL |
| CA-12 | **No cumple (parcial)** | Página conservada entre ticks ✔, pero `page_current` solo lo escribe `paginate` (`callbacks.py:92-95`): al filtrar desde la página 3 hacia un resultado de 1 página, `record_rows` hace offset 50 → tabla vacía con "3 / 1" → R-02 |
| CA-13 | Cumple | test CSV 63/60 filas |
| CA-14 | Cumple | 1 sentencia de agregación (UNION ALL) |
| CA-15 | Cumple | chips sin nombres de variables |
| CA-16 | Cumple | `responsive.json` |
| CA-17 | Cumple | test UI (≥44 px, foco, labels, `lang=es`) |
| CA-18 | Cumple | `contrast.json`, 8,8:1 placeholder |
| CA-19 | Cumple | sin `style=` en layout; sin `!important` nuevo |
| CA-20 | Cumple | 124 passed reproducido por Opus |
| CA-21 | Cumple | `app.layout` asignado una vez |
| CA-22 | Cumple | `DASHBOARD_NEW_RECORD_URL` |
| CA-23 | Cumple | paleta exacta + validador PASS |

Resumen: 21/23 cumplen; 2 altos no cumplen (CA-04, CA-12).

## Correcciones
| ID | Severidad | Corrección | CA |
|---|---|---|---|
| R-01 | **Alto** | Periodo anterior calendario para presets: `month` → mismos días del mes anterior (1-9 oct; si el mes anterior es más corto, hasta su último día); `previous` → mes calendario anterior completo (sep); `three`/`year` → mismos meses desplazados 3/12 meses; `custom` → igual número de días inmediatamente antes (comportamiento actual). Etiqueta del delta: "vs oct 2026" para presets de mes, "vs jun–ago 2026" para rangos de meses, "vs dd-mm-aaaa – dd-mm-aaaa" para personalizado. Test por preset con fecha fija. | CA-04, CA-02 |
| R-02 | **Alto** | Reiniciar `records-table.page_current` a 0 cuando cambien periodo, fechas, filtros o orden (no en los ticks del intervalo). Además, si `page_current ≥ page_count`, limitarlo a la última página válida. Test: página 3 → filtrar a 1 página → muestra filas y "1 / 1". | CA-12 |
| R-03 | Bajo | Barra de Origen se ve como una línea de ~2 px (`width=.06` en 140 px de alto, captura 1440): subir a ~16-20 px de alto para que sea legible y apuntable con hover. Leyenda actual se mantiene. | — (§5 Origen) |
| R-04 | Bajo | `components.tokens()` lee 2 archivos CSS por cada figura (≈10 lecturas por render cada 15 s): cachear con `functools.lru_cache`. | — |

Opcional, no bloquea: en móvil, 25 tarjetas de registros generan una página de ~7.400 px; considerar 10 tarjetas por página en móvil en una futura v3 (requiere cambio de spec, no hacer ahora).

## Decisión
Quedan R-xx de severidad alta → `turno: codex` (Fase 8, ciclo 1 de 2). Resolver solo R-01…R-04, un commit por corrección, marcar en `codex/checklist.md`.

---

# Ciclo 2 — revisión de R-01…R-04 (2026-11-09)

Rama `redesign/codex` @ `d7d7412`. Commits revisados: `b4f0406` (R-01), `c395a96` (R-02), `e65a6b1` (R-03), `e551507` (R-04).

## Evidencia ejecutada por Opus
| Verificación | Resultado |
|---|---|
| Suite completa (`--basetemp=.tools/pytest-opus-review-2`) | **138 passed, 6 warnings** (75,4 s), incluye Chromium a 320-1440 px; evidencias de Codex restauradas con `git checkout` tras la ejecución |
| Script `parse_filters` en 3 fechas (09-11-2026, 31-03-2026, 15-01-2026) × 5 presets + personalizado | Ver tabla R-01 |
| Diff `2099b65..d7d7412` en `src/` | Leído completo |
| Captura `codex/evidencias/review-r02-paging.png` (390 px) | Revisada |

## Correcciones
| R | Veredicto | Evidencia |
|---|---|---|
| R-01 | **Corregida** | Este mes 1-9 nov → 1-9 oct "oct 2026"; Mes anterior oct → 1-30 sep "sep 2026"; 31-03 → feb 1-28 (limita fin de mes); cruces de año correctos ("dic 2025", "ago–oct 2025", "feb 2024–ene 2025"); Todo → "periodo anterior" sin delta; personalizado 1-5 nov → 27-31 oct en dd-mm-aaaa. `test_redesign_review_periods.py` |
| R-02 | **Corregida** | `table_page` reinicia a 0 cuando cambian filtros u orden (clave `table-context`), conserva página en ticks y la limita a la última válida. Captura: ESP32 → "Registros (1)", "1 / 1". `test_redesign_review_paging.py` |
| R-03 | **Corregida** | Barra 18 px visible en captura 390 px, eje fijo; hover en test UI |
| R-04 | **Corregida** | `@lru_cache(maxsize=1)` en `tokens()`; `test_redesign_review_tokens.py` |

## Criterios de aceptación (estado final)
| CA | Veredicto |
|---|---|
| CA-01 … CA-03 | Cumple |
| CA-04 | **Cumple** (antes no cumplía; R-01) |
| CA-05 … CA-11 | Cumple |
| CA-12 | **Cumple** (antes parcial; R-02) |
| CA-13 … CA-23 | Cumple |

**23/23 cumplen.** Tareas T1-T8 de `03` y casos CB01-CB23 de `04` resueltos (T2 y CB20 ahora OK).

## Observaciones no bloqueantes (no requieren ciclo)
- Texto "1 filtros activos" en singular debería ser "1 filtro activo" (cosmético, `data.period_label`).
- Validación con personas reales de H01/H03 sigue pendiente del usuario.
- Móvil: 25 tarjetas por página (propuesta para una v3, ya anotada).

## Decisión
Todos los CA cumplen y no hay casos borde críticos sin manejar → **`turno: usuario`** (Gate 2).
