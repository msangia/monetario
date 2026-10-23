# Respuesta al dictamen 13 (núcleo, `proyecto.tex`)

Veredicto previo: APROBADO, 82/100, sin cambios obligatorios en el núcleo. Se atienden las seis mejoras de mayor impacto dirigidas al núcleo. Los obligatorios menores de anexos corresponden a `anexos.tex` (otro agente); aquí no se tocaron.

| # | Punto del dictamen | Qué se hizo en `proyecto.tex` |
|---|---|---|
| 1 | Indicador (i): meta de precisión propia para cuentas corrientes; simplificar cadena de reemplazos | (i): regla principal (circulación y cuentas corrientes, un día, ≥60 obs. en paralelo con datos internos, DM al 10 %); para cuentas corrientes, además, MAE relativo al ingenuo ≤ 0,95, rotulado como umbral provisorio a fijar con la línea de base; cobertura al 90 % y sin sesgo por día del mes como condiciones adicionales, no sustitutas. Respaldo: si no hay 60 obs., intervalo de la reducción del error que excluya el cero; si las cuentas corrientes no mejoran al ingenuo, reviso el modelo con Operaciones. |
| 2 | Eje 4: banda calibrada y validada antes de activar (vi); demanda como contraste | Bloques reordenados: el ancla es la consistencia de fuentes; el segundo bloque (demanda, MCE en ventanas móviles) se presenta como herramienta de contraste; el tercero calibra la banda con errores fuera de muestra del programa vigente y valida cobertura cercana al 90 % antes de activar la nota; no se usa un programa cuya banda no cubra (con datos públicos la deriva estacional cubre menos; Anexo C). (vi) reformulado: con la banda validada, nota en 10 días hábiles y revisión anual de cobertura. Hoja de ruta: "primera programación con banda validada". |
| 3 | Método para cuentas corrientes | Eje 1: modelo por factores programados (Tesoro, sector externo, operaciones del BCRA) más dinámica de integración del efectivo mínimo dentro del período de cómputo, estimado con Operaciones y Liquidez sobre su información interna y evaluado contra el ingenuo. |
| 4 | Quién firma en la transición | Eje 1: durante seis meses las decisiones técnicas de liquidez las toma el Gerente, con la conformidad técnica del subgerente de Liquidez, y responde por ellas ante Operaciones y las autoridades. Se eliminó "firma conjunta… sin cuyo aval nada cambia". |
| 5 | Jerga ("frente 4", "condicionado") | "Condicionado" → "segunda etapa" en Intro, Ejes 2 y 3, hoja de ruta y riesgos; "frente 4" eliminado de la tabla de riesgos ("Posterga la segunda etapa"); "cuatro frentes" → "cuatro partes". Oraciones de Eje 1 y Eje 4 partidas. |
| 6 | Mercado de capitales más allá de caución | Eje 3, núcleo: curva corta de letras del Tesoro y tasas de pases y caución como canal de transmisión de la política y medida de la sustitución de liquidez. Brecha declarada intacta. |

## Recortes para no pasar de 4 páginas
- Intro: se quitó "En cada eje indico qué aporto…", el principio "Adaptar, no copiar" (la práctica se mantiene en cada eje), "Código e IA… lo hacen posible", "El diagnóstico de 90 días fija líneas de base" y "de política monetaria" en la cita del comunicado.
- Eje 1: "(el de los anexos)".
- Eje 2: frase "El BCRA ya publica…" condensada en "Núcleo (evolución del informe mensual, no uno nuevo)".
- Eje 3: "sin crear otra encuesta"; caución sale de la lista de seguimiento (queda en la línea de mercado de capitales); "y de los títulos cortos" en el perímetro; plan de 90 días más corto.
- Eje 4: frase de consultas condensada.
- Eje 6: recursos no humanos integrados a la frase del plan anual.

## Control formal
`pdflatex` dos veces: 4 páginas, sin *overfull*. Holgura: en la página 4 entran 5 líneas adicionales en tamaño `\small`.
