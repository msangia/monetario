# Respuesta 10 — cambio obligatorio 1 del dictamen 10 (alinear el núcleo con los anexos)

Los obligatorios 2 a 5 corresponden a `anexos.tex` y quedan a cargo del agente de anexos. Aquí se atiende el 1 y las opcionales que cupieron.

## Obligatorio 1

**Eje 1.**
- El ensamble (regresión con calendario, espacio de estado y ARIMAX, con intervalos) queda como base para **billetes y circulación**: "en mis ejercicios con datos públicos supera al pronóstico ingenuo con diferencia significativa" (Anexo A, `real_liquidez.txt`: circulación MAE rel. 0,58, p DM < 0,001; billetes 0,73, p < 0,001).
- Para las **cuentas corrientes de las entidades en el BCRA** ("cerca del 98 % de la varianza diaria de la base" en esos ejercicios) se dice que el calendario no alcanza: se suman los factores programados (Tesoro, sector externo, operaciones del BCRA) y la exigencia e integración de efectivo mínimo por entidad en el período de cómputo, que es información interna y se incorpora con Operaciones y la Subgerencia de Liquidez.
- "Cómo se mide" aclara que se evalúa con datos internos.
- **Indicador (i)**: serie = variación diaria de la circulación monetaria y de las cuentas corrientes de las entidades en el BCRA; horizonte = un día; DM al 10 % con al menos 60 observaciones en paralelo con datos internos; alternativa: intervalo de confianza de la reducción del error que excluya el cero. No se afirma que hoy se cumpla para la base.

**Eje 4.**
- La demanda se estima para la base y el **M2 total** (el del Anexo B, id 109), y para el M2 transaccional privado cuando su serie lo permita (id 197, desde 2021).
- El benchmark pasa a ser la **deriva estacional** (crecimiento reciente más el efecto típico de cada mes), en lugar de la velocidad simple.
- Contingencia: si la demanda no resulta estable ("como en mis ejercicios con datos públicos, sin cointegración estable"), el programa se apoya en el bloque de consistencia de fuentes y en reglas de seguimiento, y la demanda queda como contraste.
- Banda: base y M2 a 1–3 meses, construida con los percentiles del error fuera de muestra del programa y calibrada para que cubra la tasa nominal (90 %); se revisa cada mes.
- **Indicador (vi)**: tiene ahora frecuencia mensual, coherente con la revisión. Mide la proporción de meses con el desvío dentro de la banda, que debe rondar el 90 % (si no, se recalibra), y exige que cada desvío fuera de banda se explique en una nota dentro de diez días hábiles.

## Opcionales aplicadas
- **Riesgos**: se agregaron dos filas, "Datos y acceso a la Central de Deudores" (sin acuerdo, se posterga el panel de crédito) y "Fuga de información o mal uso de IA" (entorno interno, política de IA, perfiles segregados y revisión semestral). "Sobrecarga" y "Resistencia" quedaron en una sola fila.
- **Función 10**: nuevo ítem "Procedimientos y capacitación" en el Eje 6, con revisión anual de los manuales de pronóstico de liquidez y de elaboración del informe junto con los subgerentes y, cuando corresponda, con Operaciones.
- **Siglas**: se sacó "(BoE)" y se escribe Bank of England; se sacaron SHAP, "(Python y R)" en infraestructura y "(flujos, transiciones de situación)".

## Recortes para compensar
- Eje 1: el "Qué" quedó más corto (horizontes a un día, una semana y un mes), igual que el cuadro de tasas y el aval ("ningún cambio en producción va sin su aval").
- Eje 4: se sacó "además de responder consultas, propongo una agenda propia" y se acortó la frase de respuestas a consultas.
- Eje 3: el "Aporte" quedó sin los temas de cada artículo, pero siguen los medios y el año.
- Eje 6: el diagnóstico de dotación de 90 días ya figura en la hoja de ruta ("capacidad"). La confidencialidad se condensó y los resguardos técnicos pasaron a la tabla de riesgos.
- Indicador (vii): pasó a "≥ 4/5".

## Control formal
- pdflatex dos veces: 4 páginas, sin overfull ni underfull.
- Margen libre en la página 4: unos 76 pt (≈ 5,5 líneas).
- Márgenes, fuente e interlineado sin cambios.
