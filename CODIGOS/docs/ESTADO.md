# Estado de QR Lab Hub

- Actualizado: 2026-10-19.
- Corrección posterior: 8070 ocupado por SmartAgro. QR Lab verificado en http://localhost:8071/dashboard/.
- Lanzador detecta puertos ocupados y busca hasta 8090; puerto actual guardado en `storage/local.port`.
- Operación local reparada: http://localhost:8070/dashboard/; lanzador `Iniciar QR Lab.cmd`.
- Entorno: Python 3.12.14, PostgreSQL 16.3, dependencias bloqueadas en `requirements.lock.txt`.
- Verificación actual: 37 pruebas pasan; pip check sin incompatibilidades; cinco registros originales conservados (2.100 kg).
- 15 PDF descargables y 10 mensajes capturados por SMTP local; sin envío externo.
- Arranque/parada comprobados; puertos 8070, 5432 y 1025 escuchan solamente en 127.0.0.1.
- Backup restaurado en base temporal: cinco registros; base temporal eliminada.
- Evidencia actual y límites: [operación local](evidencias/local_2026_10_19.md).
- UI revisada mediante DOM; captura visual del navegador no disponible por fallo del proveedor. PDF de dos páginas revisado visualmente.
- Tras reiniciar Windows, abrir nuevamente el lanzador. No se configuró inicio automático.
- Fase activa: MVP Completado (F0 a F6 superadas). F7 opcional pendiente para hardware real.
- Implementador: Antigravity.
- F0 superada: entorno reproducible, PostgreSQL 16 portable local, tzdata, FastAPI y salud en [evidencia](evidencias/f0_base.md).
- F1 superada: modelos SQLAlchemy, migraciones Alembic, catálogos sintéticos en [evidencia](evidencias/f1_datos.md).
- F2 superada: formulario QR móvil, validación y POST idempotente en [evidencia](evidencias/f2_registro.md).
- F3 superada: agregación centralizada, API administrativa y dashboard Dash oscuro verde en [evidencia](evidencias/f3_dashboard.md).
- F4 superada: snapshot mensual, PDF con ReportLab/Matplotlib, despacho SMTP local y recuperación en [evidencia](evidencias/f4_informes.md).
- F5 superada: suite completa 27/27, recorrido completo T22 y concurrencia sin defectos en [evidencia](evidencias/f5_depuracion.md).
- F6 superada: documentación operativa, arranque, backup/restore comprobado (T21) y PDF de muestra en [evidencia](evidencias/f6_entrega.md).
- Decisiones registradas: D01 a D08 en [decisiones](DECISIONES.md).
- CodeGraph: no existía `.codegraph/`. Sin índice. Búsquedas directas.
- Pruebas acumuladas actuales: 37 pruebas pasadas, seis avisos de deprecación.
- Pendientes externos para producción: catálogos reales del laboratorio, credenciales SMTP institucionales, autenticación universitaria / SSO y balanza ESP32 (F7).
- Bloqueos: ninguno. Sistema MVP funcional y verificable localmente.

Actualizar al terminar cada fase. Mantener menos de 100 líneas. Guardar decisiones en su documento y evidencia extensa fuera de esta nota.
