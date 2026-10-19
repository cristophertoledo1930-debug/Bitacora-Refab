# QR Lab Hub — instrucciones del proyecto

## CodeGraph

Si existe `.codegraph/` en la raíz, consultar CodeGraph antes de localizar o entender código: MCP `codegraph_explore`, o `codegraph explore "símbolo o pregunta"`. Pedir símbolos/archivos concretos y sus llamadas. Si no existe, omitir CodeGraph y usar `rg`. La indexación la decide el usuario.

## Trabajo

- Leer `docs/ESTADO.md` y la habilidad de la fase activa en `.agents/skills/`.
- `PLAN_ORQUESTACION.md` define alcance y fases; `docs/CONTRATOS.md` define datos; `docs/PRUEBAS.md` define aceptación.
- No duplicar estas especificaciones en cada respuesta. Consultar solo el fragmento necesario.
- Mantener PostgreSQL como fuente de verdad. Usar Decimal, transacciones, fechas conscientes de zona e idempotencia.
- Probar con datos sintéticos y SMTP local. No habilitar envíos reales ni publicar durante implementación local.
- No guardar secretos ni datos personales en Markdown, capturas, prompts o logs.
- No cambiar archivos ajenos al proyecto. No declarar verificaciones sin ejecutarlas.
- Cerrar cada fase con evidencia y actualizar `docs/ESTADO.md`. Continuar cuando su puerta de salida esté satisfecha.
