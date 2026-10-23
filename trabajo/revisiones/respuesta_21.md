# Respuesta al dictamen 21 (APROBADO, 81,5/100)

Núcleo: `proyecto.tex` / `proyecto.pdf`, 4 páginas, sin *overfull*, ≈ 37,7 pt libres al pie de la página 4 (≈ 2,8 líneas). Formato sin cambios. No se tocó `anexos.tex` ni `codigo/`.

## Correcciones antes de presentar
1. **Atribución de fuentes**: verificado con `pdftotext -layout` en los PDFs públicos. IPOM de junio de 2026, Gráficos III.2.9 y III.3.1: M2 privado transaccional s.e., % del PIB, escenario base de un VECM con bandas de ±1 y ±2 desvíos estándar. Informe Monetario Mensual de agosto de 2026, Gráfico 3.1.2: variación de la base entre fines de mes por factores (fiscal, C/V USD privado, REPO y OMAs, otros). El núcleo cita sólo esas publicaciones (E4, Contraste y Ancla); se agrega la frase sobre el Anexo B (otra especificación: M2 total, IPC observado) y el contraste del VECM vigente con datos internos antes de cambiar su rol; el MCE queda como contraste y señal de cambio estructural. Referencias: sale "Informe monetario diario", entran IPOM (junio de 2026) e IMM (agosto de 2026). Registrado en `trabajo/benchmark_internacional.md`.
2. **Efectivo mínimo, indicador (i)**: validación con *backtest* sobre datos internos históricos (p. ej. 24 períodos de cómputo) más la prueba en paralelo; umbral a fijar con la línea de base. Sale "≥ 80 % de los períodos".
3. **Paralelo**: E1 dice "si no se reúnen las observaciones de la prueba, se extiende el paralelo; no se pasa a producción". (La regla de A.3 y el Anexo C corresponden a `anexos.tex`, a cargo del analista.)
4. **Anexo C**: fuera del alcance de esta tarea (anexos); citar las mismas dos fuentes.

## Recomendados aplicados
- "Seguimiento de desvíos" en tres oraciones, con "ver Anexo C" y sin resultados intermedios.
- Frase llana de efectivo mínimo; ARIMAX → "ARIMA con variables de calendario"; TAMAR definida; MCE definido.
- "Liquidez (pronóstico a un día; meta al mes 12)"; "Ancla: la consistencia de fuentes. Proyecta…".
- IA: −20 % como hipótesis a medir con la línea de base de 90 días; laboratorio financiado con las horas que libere la IA si se confirma y, mientras tanto, con la prioridad del diagnóstico (techo 10 %).
- E6: línea de dotación y horas (diagnóstico de 90 días; porcentajes como supuestos a validar) y de resistencia o bajo desempeño (conversación individual, plan de mejora y acompañamiento; escalamiento a la Gerencia Principal sólo si persiste).

## Recortes compensatorios (menor valor)
Resultado de billetes del Anexo A.1 en E1; propuesta de publicar *vintages*; "generada desde el código" (E2); notas firmadas y sesión mensual del tablero (E6); "cada prototipo tiene un analista líder" (queda en indicador iv); calendario con Estadísticas y "canales formales"; fila de microdatos de crédito en riesgos; números de gráficos en Referencias (quedan en el cuerpo); compresión de frases en E1, E3, E4 e indicador (i).

## Pendientes fuera del núcleo
"--reales" en el PDF de anexos, ejes de la Figura 1, explicación 1,65 vs 1,66 y regla de A.3: corresponden a `anexos.tex`.
