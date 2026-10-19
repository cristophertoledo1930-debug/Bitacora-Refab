---
name: lab-datos-api
description: Implementa esquema PostgreSQL, API FastAPI y formulario QR de QR Lab Hub en F1/F2; prepara la integración ESP32 únicamente si se encarga F7.
---

# Datos y registro

Lee `docs/CONTRATOS.md` y la fase activa del plan. Mantén modelos, validación, transacciones y consultas en capas pequeñas compartidas.

- Implementa primero migraciones y restricciones PostgreSQL. Valida sobre una instancia desechable real.
- Conserva tipo, material, máquina y causa como dimensiones distintas. Catálogos inactivos conservan historia.
- Normaliza gramos con Decimal. Rechaza peso inválido antes de persistir y aplica CHECK en BD.
- Resuelve el token QR en servidor. Precarga contexto y valida cada selección; no concedas acceso administrativo con el QR.
- El formulario preserva valores al corregir errores y confirma solo después del commit.
- Clave idempotente y hash de payload evitan duplicados. Prueba la carrera de inserciones simultáneas; conflicto de payload devuelve 409.
- Protege consultas administrativas y descargas con sesión. No filtrar tokens, contraseñas ni SQL al navegador o logs.
- Extrae consultas de agregación reutilizables para Dash e informes, con periodos locales convertidos a UTC.
- ESP32 queda fuera del MVP. Si se encarga, vincula medición a dispositivo/sesión y rechaza lectura antigua o consumida.

Puerta de salida: pruebas relevantes T01–T08 y T19 de `docs/PRUEBAS.md`, según la fase. Entrega migración, contrato actualizado si cambió y evidencia. No implementar módulos ajenos para aparentar avance.
