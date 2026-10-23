# Respuesta al dictamen 12 (núcleo, `proyecto.tex`)

Veredicto previo: APROBADO, 84/100. Esta ronda atiende la corrección obligatoria 1 (la que toca el núcleo) y las recomendaciones dirigidas al núcleo. Las correcciones 2 a 4 y las recomendaciones sobre anexos corresponden a `anexos.tex`, que edita otro agente: aquí no se tocaron.

| # | Punto del dictamen | Qué se hizo en `proyecto.tex` |
|---|---|---|
| Obl. 1 | Eje 1, frase "para billetes y circulación… en los últimos 60 días empata" imprecisa | Ahora dice: en la muestra 2022–2026 con datos públicos el ensamble supera al ingenuo con diferencia significativa en billetes y en circulación; en los últimos 60 días los billetes en poder del público empatan y la circulación conserva la mejora. No se agregaron cifras (0,73; p = 0,001 quedan en el Anexo A). |
| Rec. | Partir el indicador (i) | Dos oraciones: (a) regla principal: circulación y cuentas corrientes en el BCRA, un día, Diebold-Mariano al 10 %, al menos 60 observaciones en paralelo con datos internos; (b) alternativa: si no se reúnen, un intervalo de la reducción del error que excluya el cero; si las cuentas corrientes no superan al ingenuo, cobertura al 90 % cercana a la nominal y sin sesgo por día del mes. |
| Rec. | "Elevado por la Gerencia Principal" y comunicación con autoridades | E6: "briefing semanal de una página que elevo a las autoridades a través de la Gerencia Principal, nota ante cada desvío fuera de banda y presentación trimestral del programa por la línea jerárquica". |
| Rec. | Desdoblar el riesgo "sobrecarga, resistencia o falta de datos" | La tabla tiene cinco filas, cada una con señal, mitigación y responsable propios: régimen o autoridades; falla en liquidez; sobrecarga; rotación o resistencia (pilotos de código y formación; subgerentes); datos de Operaciones (acuerdo de servicio; rige el proceso vigente; Subg. de Liquidez). Para que cada fila entrara en una línea se acortaron los textos de las filas previas. |
| Rec. | Conducción del cambio hacia el trabajo desde el código | E6, Procedimientos y capacitación: formación en servicio, pilotos con voluntarios, reconocimiento en la evaluación y planillas en paralelo hasta validar. |
| Rec. | Línea de base de (vii) y de la IA generativa | Tras los indicadores: "Líneas de base (primeros 90 días): horas actuales del informe, defectos en la revisión actual y encuesta inicial de usuarios, para (vii) y la IA generativa". |
| Rec. | Indicador de estructura del mercado de crédito (F3) | E3, Crédito (núcleo): índice trimestral de concentración (Herfindahl–Hirschman) del crédito por segmento y grupo de entidades, junto con la ECC; el panel condicionado permitiría medirla por tipo de deudor. |
| Rec. | Qué modelo alimenta la banda | E4, bloque 3: la banda sale de los percentiles de los errores fuera de muestra del programa vigente (deriva estacional o bloque de consistencia), con el modelo de demanda como contraste. Bloque 1 redactado así: el MCE "no superó de forma estable a una deriva estacional" en los ejercicios con datos públicos. |
| Rec. | Los anexos cubren sólo h = 1 | E1: "Primero, el horizonte de un día (el de los anexos); el semanal y el mensual, después". |

## Recortes para no pasar de 4 páginas
- E1: el cuadro de tasas queda sin la enumeración de usuarios; la lista de tasas, compactada.
- E2: se sacó la justificación de Divisia ("sus rendimientos divergen cuando cambia la inflación"); quedan la ponderación por costo de uso y los componentes. En presentaciones se sacó "y revisadas".
- E3: se sacó "No cubro valuación de activos ni análisis de emisores"; el plan de 90 días en medios de pago quedó más corto.
- E4: bloque 1 condensado (se sacó "y del transaccional privado"); se quitó la enumeración de tasas del traspaso y de temas de consulta; se quitó "la programación operativa parte de los ejercicios vigentes".
- E5: la frase de aprendizaje automático, condensada.
- E6: se quitó "ningún dato interno sale a herramientas externas de IA" (estaba repetido con la gobernanza de E5); la auditoría, más breve.
- Indicadores: se sacaron "(si no, se recalibra)" en (vi) y "se revisa el modelo" en (i).

## Control formal
`pdflatex` corrido dos veces: 4 páginas, sin *overfull*. Prueba de holgura: en la página 4 entran cerca de 4 líneas de cuerpo libres (4 `\baselineskip` en tamaño `\small` más una línea).
