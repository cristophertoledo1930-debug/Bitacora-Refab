---
name: lab-informes
description: Implementa PDF mensual, ejecución programada y entregas SMTP de QR Lab Hub; se usa en F4 y al corregir periodos, reintentos o informes.
---

# Informe mensual

Lee F4 del plan y contratos de fechas/entregas. Usa ReportLab, gráficos estáticos y transporte SMTP inyectable. No asumas herramientas PDF de otro agente instaladas.

1. Calcula mes anterior por America/Santiago y consulta límites UTC [inicio, siguiente inicio).
2. Reclama periodo de forma atómica; crea snapshot consistente y genera PDF reproducible desde ese snapshot.
3. Incluye totales, unidades, desgloses, gráfico, fecha de generación y nota de metodología. Mes sin registros produce informe explícito.
4. Renderiza PDF a imágenes con herramienta disponible e inspecciona cortes, tablas, acentos, gráficos y paginación. Extraer texto no basta.
5. Guarda archivo y estado. Entrega por destinatario; no reenviar los ya exitosos.
6. Prueba SMTP local y reintentos limitados. Ante aceptación SMTP ambigua marca `uncertain`; no prometas exactamente una entrega.
7. Programa un único proceso diario; recupera periodos desde el mes inicial configurado. No crear scheduler dentro de cada worker web.

Mantén `EMAIL_ENABLED=false` para correo externo durante desarrollo. Faltan credenciales/destinatarios reales hasta que el usuario los configure. No incluir secretos en evidencia.

Puerta de salida: T12–T18. Registra PDF de muestra y resultados del simulador; no declarar envío real por haber probado SMTP local.
