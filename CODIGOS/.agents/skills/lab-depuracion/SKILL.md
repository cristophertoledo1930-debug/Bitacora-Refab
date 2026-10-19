---
name: lab-depuracion
description: Depura y revisa el flujo integrado de QR Lab Hub con PostgreSQL, dashboard, PDF y correo local; se usa en F5 o ante un fallo reproducible.
---

# Depuración y aceptación

Lee `docs/PRUEBAS.md` y el estado. Primero verifica qué está implementado y qué sigue simulado. No cierres integraciones sin evidencia.

Para cada fallo: reproduce con fixture mínimo, identifica causa, aplica parche acotado, añade regresión de comportamiento cuando corresponda y ejecuta pruebas afectadas. Conserva datos ajenos y configuración del usuario.

Revisa especialmente: inserción concurrente, exactitud Decimal, restricciones PostgreSQL, validación de QR, permisos administrativos, fronteras horarias, filtros consistentes, periodo vacío, PDF largo y entrega SMTP incierta.

Ejecuta T22 al integrar. Revisa UI y PDF visualmente. Para cantidades/masas usa expectativas calculadas independientemente. Pruebas con SQLite no reemplazan PostgreSQL ni prueban bloqueos.

Guarda comandos reales, resultados, versiones y capturas pertinentes en `docs/evidencias/`. Clasifica defectos según la matriz y actualiza `docs/ESTADO.md`. No registrar secretos ni inventar resultados cuando falte infraestructura.

F5 termina con pruebas críticas aprobadas y sin defectos críticos/altos abiertos. Explica qué falta probar en producción. Tras cambios, repite la regresión pertinente; no ejecutes suites repetidamente sin motivo.
