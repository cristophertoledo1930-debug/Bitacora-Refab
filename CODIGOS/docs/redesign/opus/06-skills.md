# 06 · Skills recomendadas para Codex (cargar en este orden)

Máximo 6, cada una ligada a hallazgos de `03` / casos de `04`. No sustituir: si una falla, anotar en `STATUS.md > preguntas`.

| # | Skill | Origen | Resuelve | Cómo verificar que se aplicó |
|---|---|---|---|---|
| 1 | `lab-dashboard` | repo: `CODIGOS/.agents/skills/lab-dashboard/SKILL.md` | Reglas propias del proyecto (filtros comunes, ceros mensuales, refresh 15 s, error ≠ ceros) · H03, CB05, CB16 | Tests T09–T12/T20 de `docs/PRUEBAS.md` siguen en verde |
| 2 | `dashboard-design` | repo: `CODIGOS/.agents/skills/dashboard-design/SKILL.md` (copiada 2026-11-09) | KPIs con delta, comparaciones, rangos/presets, vacíos, layout móvil · H02, H04, H06, H12, CB01-CB04, CB19 | KPIs muestran delta vs periodo anterior; presets de fecha; QA de capturas 1440/390 px en `codex/implementacion.md` |
| 3 | `dataviz` | repo: `CODIGOS/.agents/skills/dataviz/SKILL.md` (copiada 2026-11-09; validar paleta con `scripts/validate_palette.py`) | Color con significado, orden de barras, etiquetas, top-N + Otros · H05, H07, CB13, CB21 | Gráficos de ranking con un solo color, orden desc, etiquetas "x,x kg (y %)" |
| 4 | `lab-datos-api` | repo: `CODIGOS/.agents/skills/lab-datos-api/SKILL.md` | Cambios en `aggregations.py`: serie mensual en 1 query, periodo anterior, Decimal, zona horaria · I02, CB07, CB10, CB22 | Nº de queries por tick ≤ 4 (test con contador de eventos SQLAlchemy) |
| 5 | `lab-depuracion` | repo: `CODIGOS/.agents/skills/lab-depuracion/SKILL.md` | Estados de error/BD caída y verificación con evidencia · CB05, CB16, CB17 | Test simula excepción de sesión → banner visible, sin ceros |
| 6 | Playwright (ya en `pyproject.toml`) | dependencia dev existente, no instalar nada nuevo | Pruebas de accesibilidad/responsive: foco, tamaños ≥44 px, sin overflow · H11, CB19 | `tests/` con prueba a 390 y 1440 px sin overflow horizontal |

Notas
- Las 5 skills de archivo están en `CODIGOS/.agents/skills/`.
- No se recomiendan librerías UI nuevas (dash-bootstrap, mantine): el tema `static/theme.css` ya cubre tokens.
