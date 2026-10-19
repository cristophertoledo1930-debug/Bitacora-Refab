# Evidencia F6 — Entrega y Operación

- **Fecha:** 2026-10-18
- **Estado:** Superada

## Entregables
- Documentación de inicio rápido, arquitectura y comandos en [README.md](../../README.md).
- Procedimiento de respaldo y restauración en PostgreSQL (T21) verificado sobre base desechable `qrlabhub_restore_test`.
- Informe mensual PDF de muestra generado en [docs/evidencias/informe_muestra_2026_01.pdf](informe_muestra_2026_01.pdf).
- Demostración de runner del job diario y recuperación de periodos cerrados.
- Declaración de pendientes externos para producción: catálogos reales de laboratorio, credenciales SMTP institucionales, política de acceso/SSO y balanza ESP32 (F7).

## Verificaciones ejecutadas
Comandos:
```powershell
# Backup & Restore T21
.\.tools\pgsql\bin\pg_dump.exe -U postgres -d qrlabhub_dev -F c -f .tools\backup_test.dump
.\.tools\pgsql\bin\createdb.exe -U postgres qrlabhub_restore_test
.\.tools\pgsql\bin\pg_restore.exe -U postgres -d qrlabhub_restore_test .tools\backup_test.dump
.\.tools\pgsql\bin\psql.exe -U postgres -d qrlabhub_restore_test -t -c "SELECT count(*) FROM waste_records;"
```
Resultado:
- Registros restaurados verificados: 5 filas coincidentes.
- Base temporal eliminada limpiamente.
- Suite completa automatizada: 27/27 pruebas pasadas en pytest.

