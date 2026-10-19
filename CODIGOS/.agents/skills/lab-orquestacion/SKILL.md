---
name: lab-orquestacion
description: Coordina las fases de QR Lab Hub y conserva contexto compacto para Antigravity; se usa al iniciar, reanudar o cerrar una fase del proyecto.
---

# Orquestación de QR Lab Hub

1. Lee `AGENTS.md` y `docs/ESTADO.md` desde la raíz del proyecto. Localiza fase y siguiente acción.
2. Lee únicamente la fase necesaria de `PLAN_ORQUESTACION.md`; consulta contratos o pruebas por necesidad.
3. Antes de desarrollar inventaría herramientas disponibles. No confundir una especificación con una capacidad instalada.
4. Descompón la fase en tareas comprobables con entradas, archivos, aceptación y verificación. Un implementador por defecto.
5. Enruta: F1/F2/F7 a `lab-datos-api`; F3 a `lab-dashboard`; F4 a `lab-informes`; F5 a `lab-depuracion`.
6. F0 prepara entorno reproducible y protección del dashboard; F6 entrega arranque, operación y recuperación comprobables.
7. Aplica CodeGraph solo bajo la condición de AGENTS.md. Sin índice, usa búsquedas delimitadas. No copies todo el código al contexto.
8. Verifica la puerta de salida. Si falla, corrige antes de avanzar; registra bloqueos externos sin inventar resultados.
9. Actualiza `docs/ESTADO.md` y solo decisiones que cambiaron. Conserva logs extensos en evidencia, enlazados desde el estado.

Para revisión usa una segunda pasada centrada en comportamiento y datos. No es necesario abrir otro agente. El cierre informa cambios, comandos/resultados, pendientes y siguiente fase en hasta 250 palabras.

Las notas `docs/` son la memoria compatible con Obsidian. No crear otro banco duplicado. No modificar integraciones personales o instalar plugins para ahorrar contexto.
