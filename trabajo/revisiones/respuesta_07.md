# Respuesta 07 — dictamen 07 (APROBADO CON OBSERVACIONES, 79/100)

## Cambios obligatorios
1. **Trazabilidad de la hoja de ruta.** "Tablero de alerta" eliminado (no tenía eje). "Perímetro del dinero" definido en el Eje 3 (condicionado): cuadro mensual que elabora Coyuntura con los datos de FCI, billeteras, caución y títulos cortos, que estima qué parte funciona como reserva de liquidez frente a M2. El "piloto de normativa" se eliminó (Eje 5 y hoja de ruta). Cada condicionado de 12-24 meses lleva entre paréntesis su eje (Eje 2: nota quincenal, Divisia, vintages; Eje 3: panel de crédito, perímetro del dinero).
2. **Indicadores.** (i) Umbral explícito: test de Diebold y Mariano (1995) al 10 % con al menos 60 observaciones diarias en paralelo; si aún no se reúnen, reducción del error medio con intervalo de confianza que excluya el cero. (vi) Ahora tiene meta: base y M2 dentro de la banda en al menos tres de cada cuatro trimestres, y cada desvío explicado en nota a las autoridades en diez días hábiles.
3. **Riesgos.** Tabla de 5 filas (riesgo / señal / mitigación / responsable). Gerente: cambio de régimen o de autoridades, y resistencia al cambio. Subg. de Liquidez: falla o ausencia en liquidez (incluye aviso inmediato y análisis de causas en 48 h, que se retiró de Articulación). Subg. de Coyuntura: datos y Sistemas. Ambos subgerentes: sobrecarga. El riesgo de accesos pasó a Confidencialidad (Eje 6).
4. **Ética, confidencialidad y Auditoría (Eje 6).** Nuevo ítem: la información de liquidez y de política tiene impacto de mercado; acceso según necesidad de la función, perfiles segregados, registro de accesos revisado semestralmente con Seguridad de la Información, período de restricción de difusión antes de cada decisión y publicación, salida sólo por canales formales, declaración de conflictos de interés. Auditoría (F8): tablero de observaciones con responsable, plazo y evidencia de cierre; revisión trimestral con informe a la Gerencia Principal; seguimiento hasta que la Auditoría General da por cerrada cada observación.
5. **Citas.** Se quitó la mención al *Stata Journal* del Eje 2. En el Eje 1 queda sólo Hamilton (1996): "se toma el peso del calendario en la demanda diaria de reservas, adaptado al período de cómputo del efectivo mínimo".

## Mejoras opcionales aplicadas
- Briefing semanal "elevado por la Gerencia Principal" (línea jerárquica).
- Eje 4: los escenarios usan los modelos DSGE y semiestructurales "por acuerdo con el área de modelos y sin duplicar funciones".
- Eje 4 (b): bloque crediticio de la programación (préstamos y depósitos privados por segmento, moneda y grupo de entidades, con su concentración) consistente con los encajes.
- Eje 1: firma conjunta con el/la Subgerente de Liquidez de las decisiones técnicas de liquidez durante los primeros seis meses.
- Trayectoria: "más de veinte años en el BCRA" (feb/2006–oct/2026, según CV).

## Recortes para compensar
Intro (frase de brechas resumida), Principios, Divisia, Eje 3 (paréntesis sobre retorno de fondos; aporte abreviado), Eje 4 (plazos de consultas y cronograma del IPOM abreviados), Eje 5 (bosques aleatorios), Eje 6 (ítem Aporte fusionado en Desarrollo de colaboradores y en \trayectoria), hoja de ruta 0-3, capacidad.

## Control formal
pdflatex x2; pdfinfo = 4 páginas; 0 overfull/underfull; 6 líneas libres en la página 4 (con 6 líneas de prueba sigue en 4 páginas). Preámbulo sin cambios (la tabla de riesgos usa `array`, ya cargado).
