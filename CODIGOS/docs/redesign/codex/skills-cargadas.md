# Skills cargadas

2026-11-09. Skills de `opus/06-skills.md` leídas en el orden indicado. No se sustituyó ninguna.

1. **lab-dashboard**: `.agents/skills/lab-dashboard/SKILL.md`. Filtros compartidos, meses vacíos, actualización de 15 s y errores con datos conservados.
2. **dashboard-design**: `.agents/skills/dashboard-design/SKILL.md`. Referencias consultadas: components, layout, tokens y qa. Se aplica el diseño oscuro fijado por la spec del proyecto.
3. **dataviz**: `.agents/skills/dataviz/SKILL.md`. Referencias consultadas: choosing-a-form, color-formula, marks-and-anatomy, interaction y anti-patterns. Validador ejecutado sobre v1 y v2.
4. **lab-datos-api**: `.agents/skills/lab-datos-api/SKILL.md`. PostgreSQL real, Decimal, fechas de Santiago y agregación común sin modificar el contrato existente.
5. **lab-depuracion**: `.agents/skills/lab-depuracion/SKILL.md`. Fixtures independientes, fallos sintéticos y evidencia reproducible.
6. **Playwright**: dependencia existente 1.64.1 comprobada; Chromium disponible. No se instalaron dependencias.

La v1 falló la validación de paleta: se registró P-01 y se devolvió turno al usuario. Opus entregó v2. El usuario pidió retomar y Codex verificó nuevamente la paleta: ALL CHECKS PASS. Ningún fallo de carga de skills.

Al retomar, el usuario invocó explícitamente `/caveman`. Se leyó `C:/Users/USER/.codex/skills/caveman/SKILL.md` como instrucción adicional de voz, después de las skills anteriores. No afecta código ni documentación persistida.

Todos los archivos de texto nuevos se escriben en UTF-8. Comandos Python con `-X utf8`; lecturas PowerShell con `-Encoding utf8`. Se corrigieron los caracteres dañados en los registros anteriores de Codex.

## Fase 8 · ciclo 1

STATUS confirmó `turno: codex`. Se releyeron, en orden, lab-dashboard, dashboard-design, dataviz, lab-datos-api y lab-depuracion desde las mismas rutas de la tabla. Después se comprobó Playwright 1.64.1 en `.venv`. Todas las cargas fueron correctas; no se cargaron otras skills ni se instalaron dependencias. Alcance limitado a R-01–R-04 de `opus/07-revision.md`.
