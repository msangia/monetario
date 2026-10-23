# Respuesta al dictamen 14 (núcleo, `proyecto.tex`)

Veredicto previo: APROBADO, 80/100 (en el umbral). Se atienden las seis causas del descenso que tocan al núcleo y la indicación del usuario de integrar, sólo en forma cualitativa, tres gráficos del informe diario (M2 privado transaccional con banda "2° desvío modelos"; factores de oferta de la base; factores de explicación de las reservas). No se copiaron cifras ni fechas de esos gráficos. Los obligatorios de anexos corresponden a `anexos.tex` (otro agente); aquí no se tocaron.

| # | Punto | Qué se hizo |
|---|---|---|
| 1 | Indicador (i) condicional; exige al ensamble lo que el Eje 1 asigna a otro modelo; sin métrica de efectivo mínimo | (i) reescrito en tres frases, cada una con su modelo: (1) circulación y billetes, ensamble de calendario (regresión, espacio de estado y ARIMAX), DM al 10 % con ≥60 obs. en paralelo con datos internos; (2) cuentas corrientes, modelo por factores programados: error relativo al ingenuo ≤ 0,95 (provisorio, línea de base de 90 días), cobertura al 90 %, sin sesgo por día del mes; (3) posición de efectivo mínimo por entidad y total: MAE menor que el ingenuo y proporción de períodos de cómputo con error dentro de un umbral que alcance una meta (ambos fijados con la línea de base). Respaldo: IC de la reducción del error que excluya el cero. Se quitó "si las cuentas corrientes no mejoran, reviso el modelo". |
| 2 | Transición de liquidez | "Las decisiones técnicas de liquidez las tomo yo" → decisión conjunta con el/la Subgerente de Liquidez durante seis meses; sólo ante desacuerdo decide el Gerente, que responde por el resultado ante Operaciones y las autoridades. |
| 3 | Densidad (Eje 1, Eje 4, indicador (i)) | Oraciones partidas, menos paréntesis y siglas. Eje 1: "dos modelos" explícitos; "Cómo se mide" remite al indicador (i). Eje 4: bloques rotulados *Ancla*, *Contraste*, *Seguimiento de desvíos*. |
| 4 | Funciones 8 y 11 mínimas | F11: criterio explícito de asignación de horas, licencias y acceso a datos (operación diaria y compromisos con Operaciones/IPOM → núcleo → segunda etapa), revisión trimestral. F8: respuesta formal a cada observación en 30 días con responsable, plan y evidencia; seguimiento trimestral hasta el cierre por la Auditoría General. |
| 5 | Riesgos sin confidencialidad/IA ni Central de Deudores | Filas nuevas "Central de Deudores" (acceso demorado → datos agregados mientras tanto; Subg. Coy.) y "Confidencialidad o IA" (uso sin registro → entorno interno, registro, revisión; Gerente). Sobrecarga y rotación fusionadas. |
| 6 | Frase selectiva sobre cobertura (Anexo C) | "Con datos públicos, ninguna banda candidata llega al 90 % en la base; en el M2, sólo la de velocidad, muy ancha (Anexo C)". Se cita el Anexo B: la demanda "no cointegra de forma estable". |
| — | Coherencia con anexo (recomendado) | Ensamble descripto como "regresión con calendario, espacio de estado y ARIMAX" en Eje 1 e indicador (i); el agente de anexos iguala el Anexo A. |
| — | Informe diario (usuario) | Eje 1: los factores programados son los de la descomposición de la base por factores de oferta del informe diario; el aporte es pasar de describirlos a pronosticarlos uno por uno, contra el ingenuo. Eje 4: la banda del M2 ya existe con dos desvíos de los modelos; no se crea otra, se la evoluciona (junto con la del programa) calibrándola por cobertura empírica fuera de muestra. La descomposición de reservas no se mencionó (no agrega a una función sin sumar texto). |

## Recortes para no pasar de 4 páginas
- Eje 1: "por factores autónomos"; frase separada de estimación con Liquidez y Operaciones (integrada en "con información interna").
- Eje 3: mercado de capitales fusionado con el seguimiento mensual del núcleo; plan de 90 días más corto.
- Eje 4: frase de plazos de consultas; "con un rango de calibración"; Aporte y brecha abreviado.
- Eje 5: gobernanza de IA abreviada (el detalle queda en la fila de riesgos).
- Eje 6: briefing abreviado.
- Indicadores: líneas de base en una frase.

## Control formal
`pdflatex` dos veces: 4 páginas, sin *overfull*. Holgura: unas 2-3 líneas libres en la página 4 (las ~12 previas se consumieron en el indicador (i), F8/F11 y las dos filas de riesgo).
