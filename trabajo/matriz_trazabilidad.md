# Matriz de trazabilidad (perfil / manual → propuesta)

| Origen | Requisito / función | Eje del proyecto |
|---|---|---|
| Manual F1 | Pronóstico de liquidez, posición de efectivo mínimo, tasas → SG Operaciones | E1 (cuadro diario de tasas de corto plazo: call, caución, tasa de referencia, letras cortas del Tesoro y diferenciales frente al excedente proyectado, enviado con el pronóstico a Operaciones y al briefing/informe; holgura: si a los 9 meses no corre en paralelo, sigue el proceso vigente, se extiende el plazo, se reevalúa el umbral con Operaciones y se posterga lo condicionado; Hamilton 1996 como única fuente del peso del calendario; firma conjunta con Subg. de Liquidez los primeros 6 meses); indicador (i) con criterio DM al 10 % sobre ≥60 obs. diarias o IC del error medio que excluya cero |
| Manual F2 | Agregados monetarios y componentes | E2 |
| Manual F3 | Estructura de mercados de crédito | E3 (ECC, panel de crédito, perímetro del dinero: cuadro mensual de Coyuntura sobre FCI, billeteras, caución y títulos cortos frente a M2); E4 bloque crediticio de la programación (préstamos y depósitos por segmento, moneda y grupo de entidades, con concentración) |
| Manual F4 | Programación monetaria y crediticia | E4 (bloques: demanda de dinero con corrección de errores y ventanas móviles; consistencia con balance BCRA, programa financiero del Tesoro, balance cambiario y resultado cuasifiscal; banda de tolerancia en base/M2, revisión mensual y nota ante desvíos; bloque crediticio; escenarios con DSGE/semiestructurales del área de modelos sin duplicar funciones); indicador (vi): dentro de banda ≥3 de 4 trimestres, nota en ≤10 días hábiles |
| Manual F5 | Diseño de políticas de intervención | E4 (agenda propia: evaluación ex post anual de encajes/instrumentos, traspaso de tasas semestral, protocolo de consultas con plazos diferenciados: urgente en horas con lectura cualitativa y rango, estándar en días, completo según complejidad); E1 (datos de efectivo mínimo) |
| Manual F6 | Presentaciones, estudios, notas técnicas, documentos de trabajo, discursos | E2 (presentaciones y discursos: banco de gráficos desde el código, láminas y mensajes clave en 72 h / 24 h urgente, cifras trazables, revisión jefe → subgerente → gerente), E3, E4 (notas técnicas), indicador (iv) |
| Manual F7 | Informe de Política Monetaria | E4 |
| Manual F8 | Respuesta a Auditoría General | E6 (tablero de observaciones con responsable, plazo y evidencia de cierre; revisión trimestral con informe a la Gerencia Principal; seguimiento hasta cierre por Auditoría) |
| Manual F9 | Objetivos, plan anual, control y reporte | E6, hoja de ruta |
| Manual F10 | Normas de procedimiento y capacitación | E5, E6 |
| Manual F11 | Administración de recursos y supervisión de subgerencias | E6 (Planificación y delegación, funciones 9 y 11, fusionadas en un ítem) |
| Perfil | Programación monetaria, agregados, liquidez, crédito | E1–E4 |
| Perfil | Medios de pago electrónicos, FCI, mercados de capitales | E3 (pregunta de política: migración de liquidez de depósitos a caución/FCI MM/billeteras y su efecto en agregados y pronóstico de liquidez; alcance declarado: no valuación ni emisores) |
| Perfil | Código abierto e IA | E5 (caso de uso de IA generativa: borrador del informe mensual y revisión de código en entorno interno, medido por horas de producción y defectos detectados en revisión; política de IA al mes 6: datos públicos/agregados sí, datos por entidad, de liquidez o de política nunca fuera del entorno interno, registro de usos, revisión humana) |
| Perfil | Seguimiento de coyuntura e informes | E2 (brecha declarada; plan de 90 días: dos ciclos del informe mensual con subgerente/jefes/analistas, ficha por producto, revisión trimestral), E4 |
| Perfil | Inglés avanzado | Intro (\trayectoria), E6 Aporte (literatura de bancos centrales, CCBS) |
| Perfil | Conducción de personal, desarrollo de colaboradores, trabajo con otras áreas, ética | E6 (briefing semanal elevado por la Gerencia Principal; ética y confidencialidad: acceso por necesidad, perfiles segregados, registro de accesos, restricción de difusión previa a decisiones y publicaciones, canales formales, conflictos de interés); Riesgos (tabla con responsables: Gerente en régimen/autoridades y resistencia; subgerentes en riesgos operativos) |

Régimen BCRA (Intro): comunicado de política monetaria del 15/12/2025 (ver benchmark, confianza M).

Fuente del manual: `manual_organico.docx` (reemplaza al PDF; misión, 11 funciones y 2 subgerencias sin cambios respecto del mapeo anterior).

## Trayectoria del postulante (CV `MSangia_CVeng.pdf`) → requisito / eje

| Requisito / eje | Respaldo en el CV | Dónde se usa |
|---|---|---|
| Licenciatura en Economía; posgrado valorado | Bachelor in Economics UNLP (1995-2001); Master in Finance UTDT (2002-2003; completa, confirmado por el usuario); Data Science Specialization ITBA (2019-2020); PhD in Economics UNLP (2023-present) | Intro (\trayectoria) |
| 5 años en tareas afines | BCRA desde feb/2006: Senior Analyst / Chief of Economic Research (2006-2017), Chief of Macroprudential Monitoring (2017-2020), Assistant Manager of Macroeconomic Models (may/2020-present) | Intro |
| ≥3 años de conducción | Subgerente desde may/2020 (~6 años 5 meses); Jefe de Monitoreo Macroprudencial ene/2017-may/2020 y Jefe de Investigaciones Económicas (fecha de inicio no consta en el CV), con personal a cargo en ambas jefaturas (confirmado por el usuario). Desde la respuesta 08 ya no se escribe la síntesis "casi diez años de conducción"; se dejan las fechas de cada cargo. No se dan tamaños de equipo | Intro, E6 |
| Liquidez / pronóstico (F1) | "Designed macroeconomic forecasting pipelines (time series and ML)"; HEATMAPGRAPH (2018). **Brecha**: sin experiencia operativa en liquidez → inmersión 90 días con Liquidez y Operaciones; aval de subgerente/jefes | E1, hoja de ruta 0-3 |
| Agregados / demanda de dinero (F2) | Stata Journal 2016 (panel time series, con Burdisso); XTCIPS, DFSUMMARY, ROLLSTAT | Ya no se cita en E2 (dictamen 07); los módulos de Stata se mencionan en E5 |
| Crédito (F3) | Credit market analysis 2006-2020; IMF Economic Review 2020; BIS WP 2020 | E3 |
| Programación (F4, F7) | DSGE y semiestructurales; CCBS Economic modelling and forecasting (2021). **Brecha**: programación operativa → sobre ejercicios existentes con subgerentes y jefes | E4 |
| Código abierto e IA | Stata, R, Python; 11 módulos Stata; curso interno de R BCRA (nov/2019, ago/2021); ITBA; Banca d'Italia Big Data & ML (feb/2021) | E5 |
| Desarrollo de colaboradores (F10) | Docente Economic Policy II UNLP (2010-present); 6 cursos CCBS BoE (2007, 2009, 2011, 2021 x3) | E6 |
| Inglés avanzado | CV: "Languages: English"; nivel avanzado confirmado por el usuario (sin certificaciones) | Intro, E6 |
