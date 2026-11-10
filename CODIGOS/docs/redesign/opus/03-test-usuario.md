# 03 · Prueba de usuario simulada

Método: recorrido cognitivo sobre código + captura escritorio 1440 px y móvil 390 px. Tiempos estimados (no medidos). Validación real pendiente: ver tabla final.

## Personas
| ID | Persona | Nivel técnico | Dispositivo | Urgencia |
|---|---|---|---|---|
| P1 | Técnica de máquinas (registra residuos con QR) | Bajo | Móvil, de pie junto a la máquina | Alta, < 30 s |
| P2 | Coordinador del laboratorio | Medio | Laptop | Media, revisión semanal/mensual |
| P3 | Responsable de informes / dirección | Medio-bajo | Laptop o proyector en reunión | Baja, pero necesita cifras exactas |

## Tareas
| ID | Tarea |
|---|---|
| T1 | ¿Cuántos kg de residuo se generaron este mes? |
| T2 | ¿Este mes es mejor o peor que el anterior? |
| T3 | ¿Qué causa genera más residuo y cuánto % representa? |
| T4 | ¿Qué máquina genera más residuo en los últimos 3 meses? |
| T5 | Ver los registros de Google Forms de ayer |
| T6 | ¿Mi registro recién hecho aparece? |
| T7 | ¿Se envió el informe mensual? |
| T8 | Exportar los registros del mes para Excel |

## Recorridos
| Tarea | Persona | Pasos actuales | Tiempo est. | Dónde se confunde |
|---|---|---|---|---|
| T1 | P2 | Ver K05 "MASA ESTE MES" (fila 2 de KPIs) | 10 s | "1.500 kg": ¿1,5 o 1500? Confunde con K02 "acumulada" |
| T1 | P1 | Móvil: plegable cerrado → scroll a KPIs | 15 s | Igual ambigüedad decimal |
| T2 | P2 | No hay comparación; leer barras G06 al fondo de la página | 40 s+ | Barras sin delta; mes actual parcial se compara con mes completo |
| T3 | P3 | G03: buscar barra más larga (orden alfabético), K06 no da % | 25 s | No hay %; debe calcular a mano |
| T4 | P2 | Fijar 2 fechas manualmente → G04 | 45 s | Sin presets; si pone fecha inválida, G04 no cambia y error aparece al pie del sidebar |
| T5 | P2 | Origen=Google Forms + 2 fechas → tabla al final | 50 s | Tabla muestra `google_forms` crudo; todo el resto del dashboard también cambia |
| T6 | P1 | Esperar hasta 15 s; buscar en tabla al final | 30 s | No sabe si refrescó; carga de "Origen" parpadea cada 15 s |
| T7 | P3 | Leer texto sidebar E03 | 20 s | Texto técnico ("EMAIL_ENABLED=false", ISO con zona), lista creciente de periodos |
| T8 | P2 | No es posible | — | Sin exportación; debe ir a Informes PDF |

## Hallazgos (Nielsen + jerarquía + legibilidad)
| ID | Hallazgo | Heurística | Severidad |
|---|---|---|---|
| H01 | Masa con 3 decimales y punto ("1.500 kg") ambigua en es-CL | Coincidencia con mundo real | Crítico |
| H02 | Sin comparación con periodo anterior | Visibilidad del estado | Alto |
| H03 | Errores de consulta solo al pie del sidebar (oculto en móvil) | Visibilidad / recuperación de errores | Alto |
| H04 | Sin presets de periodo ni rango activo visible | Reconocer antes que recordar | Alto |
| H05 | Rankings ordenados alfabéticamente, sin % | Estética/minimalismo, jerarquía | Alto |
| H06 | 6 KPIs redundantes (acumulada vs este mes) en 2 filas | Minimalismo | Medio |
| H07 | Colores por hash sin significado y con colisiones (Retazo láser = Acrílico = morado) | Consistencia | Medio |
| H08 | Estado de correo con jerga técnica | Lenguaje del usuario | Medio |
| H09 | Tabla: origen crudo, g con decimales, todas las filas al cliente, sin export | Flexibilidad/eficiencia | Medio |
| H10 | Catálogos de filtros no se actualizan sin reiniciar | Consistencia | Medio |
| H11 | Placeholder de fecha casi invisible (texto claro sobre input blanco), dropdown "Origen" con otra tipografía | Consistencia / contraste | Medio |
| H12 | Evolución mensual al fondo, título largo | Jerarquía visual | Medio |
| H13 | Spinner de G01 parpadea cada 15 s | Estado del sistema | Bajo |
| H14 | Emojis en navegación, anclas innecesarias | Minimalismo | Bajo |

## Contraste (valores existentes, `docs/UIUX_AUDITORIA.md`)
Texto/panel 15.2:1, secundario 9.9:1, primario 9.1:1 → OK. Riesgo: placeholder de `input[type=date]` (H11) y texto de anotación Plotly por defecto.

## Validación con personas reales (pendiente — usuario)
| Hallazgo crítico | Persona real | Resultado |
|---|---|---|
| H01 | ¿Qué cifra lees en "1.500 kg"? | _pendiente_ |
| H03 | Provocar fecha desde > hasta en móvil: ¿ve el error? | _pendiente_ |
