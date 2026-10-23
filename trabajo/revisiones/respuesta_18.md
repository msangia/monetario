# Respuesta al dictamen 18 (APROBADO, 84/100) — vuelta final, cambios mínimos en el núcleo

El dictamen no tenía cambios obligatorios para el núcleo; se aplicaron las siete mejoras sugeridas. Anexos y `codigo/` no se tocaron (a cargo de otro agente).

| # | Mejora sugerida | Qué se hizo (proyecto.tex) |
|---|---|---|
| 1 | Método de la posición de efectivo mínimo | E1, "Qué": oración nueva (exigencia frente a integración acumulada en el período de cómputo, por grupo de entidades, con datos internos; se pronostica la integración diaria necesaria para cerrarlo). |
| 2 | Regla "en paralelo sin alcanzar la meta" | E1, "Cómo se mide": si no corre en paralelo a los 9 meses, o corre sin alcanzar la meta, rige el proceso vigente y se informa a Operaciones el error observado; el sesgo por día del mes se evalúa aparte y, si persiste, se corrige con un ajuste de fin de mes. |
| 3 | Definir "ingenuo" y "ensamble"; aligerar tasas | Definiciones entre paréntesis en la primera aparición (E1); Intro dice "pronóstico de liquidez". Frase del diferencial de tasas reescrita y acortada (se quitó la evaluación "cuánto del diferencial y de su dispersión..."). |
| 4 | Pregunta analítica para medios de pago y FCI | E3: "¿cuánto de la demanda transaccional de dinero migra a billeteras y FCI de mercado de dinero y cómo cambia la velocidad del M2?" (reemplaza "como canal de transmisión y medida de la liquidez que migra..."). |
| 5 | Ampliar F8 | E6: registro de recomendaciones priorizadas por riesgo; informe trimestral a la Gerencia Principal. |
| 6 | Área de modelos (IPOM) y rol del MCE | E4: "acuerdo los escenarios con el área de modelos, cuyos DSGE y semiestructurales conozco"; MCE: "no ancla, sirve de contraste y de señal de cambio estructural". |
| 7 | Alinear M2 (dictamen, anexos punto 2) | E4: "el informe diario ya muestra el M2 con una banda..." y "(base y M2 a 1--3 meses; los anexos prueban el M2 total y la base)". |

**Recortes para compensar**: "Primero a un día; luego, semanal y mensual" (E1; el horizonte de un día queda en el indicador i); regla de los 9 meses fusionada en una oración; explicación de Divisia condensada (E2); ECC "sin crear otra encuesta" (E3); frase "El paso al trabajo desde el código se hace con formación en servicio y pilotos en paralelo" (E6; formación y pilotos siguen en la tabla de riesgos).

**Control formal**: pdflatex x2 sin errores ni *overfull*/*underfull*; `pdfinfo`: 4 páginas; espacio libre medido al final de la página 4: 40,5 pt (unas 3 líneas). Preámbulo sin cambios. Sin cifras ni datos biográficos nuevos.
