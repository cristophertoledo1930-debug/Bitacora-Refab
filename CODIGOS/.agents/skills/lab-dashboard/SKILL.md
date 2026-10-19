---
name: lab-dashboard
description: Construye y verifica el dashboard Dash oscuro verde de QR Lab Hub, con filtros, categorías y barras mensuales; se usa en F3 y correcciones visuales.
---

# Dashboard de laboratorio

Lee F3 en `PLAN_ORQUESTACION.md` y las reglas de agregación en `docs/CONTRATOS.md`.

Implementa lateral izquierdo con navegación y filtros, indicadores arriba, categorías al centro y barras mensuales abajo. Usa la paleta definida, tipografía clara y etiquetas de unidades. Mantén cantidad de registros separada de masa y de cantidad de piezas.

- Consume API autenticada y consultas comunes; no mantengas un segundo registro de residuos en memoria.
- Todos los componentes deben aplicar los mismos filtros. Valida fechas y muestra rango activo.
- Completa meses vacíos con cero, ordena por fecha real y muestra el año.
- Actualiza dentro de 15 segundos después de registrar. Si falla la consulta, muestra error y última actualización; no sustituyas el fallo por ceros.
- Comprueba nombres largos, meses vacíos, empates, categorías inactivas y volúmenes que requieran paginación.
- Verifica en navegador móvil/escritorio, teclado y contraste. Usa capturas para evidencia y corrige recortes.

Puerta de salida: T09–T12 y T20. Compara totales con fixture independiente, no con otra visualización de la misma función defectuosa.
