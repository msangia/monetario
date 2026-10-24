# Benchmark internacional (confianza: A alto / M medio / V a verificar)

Consulta: 22-10-2026. Red al sitio del BCRA no disponible desde el entorno (ENOTFOUND); sólo resúmenes de búsqueda.

| Banco | Práctica | Fuente | Conf. | Uso en proyecto |
|---|---|---|---|---|
| BCE | Bank Lending Survey trimestral (ene/abr/jul/oct), insumo de la evaluación de política | ecb.europa.eu/stats/ecb_surveys/bank_lending_survey | A | E3 encuesta cualitativa de crédito |
| BCE | Análisis monetario y financiero (M3, préstamos); MMSR/€STR | conocimiento general | M | E1, E2 |
| BoE | Fan charts; Money and Credit; Credit Conditions Survey; ML (Chakraborty y Joseph 2017) | conocimiento general / ejemplos del repo | M-A | E2, E4, E5 |
| NY Fed | Proyecciones de reservas del Desk; Staff Nowcast; Consumer Credit Panel | conocimiento general | M | E1, E3 |
| Fed St. Louis | FRED/ALFRED con vintages; agregados Divisia (MSI, hoy discontinuados: se redactan en pasado) | conocimiento general; https://fred.stlouisfed.org/series/MSIM3P (DISCONTINUED), consulta 2026-10-22 | M-A | E2, E5 |
| Banco de Canadá | Senior Loan Officer Survey, Business Outlook Survey | conocimiento general | M | E3 |
| BCRA | Publica Informe Monetario Mensual e IPOM trimestral (IPOM 1T26 el 13/5/2026, 2T26 el 6/8/2026) | bcra.gob.ar (resultados de búsqueda) | M | No proponer "crear" el IMM: proponer evolucionarlo |
| BCRA | Encuesta de Condiciones Crediticias trimestral publicada desde 2016 (2T26 el 23/7/2026), cobertura ~90 % del crédito privado | bcra.gob.ar (búsqueda) | M-A | Integrar y explotar, no duplicar |
| BCRA | Esquema vigente centrado en control de agregados monetarios (“fase 4”), banda cambiaria indexada a inflación desde 1/1/2026 | bcra.gob.ar (búsqueda) | M | Redactar de forma robusta al régimen |
| BCRA | Comunicado de política monetaria "Profundización del esquema de agregados monetarios: fase de re-monetización 2026", 15/12/2025: esquema de agregados monetarios; desde 1/1/2026 banda de flotación ajustada por inflación (T-2) y programa de acumulación de reservas | https://www.bcra.gob.ar/politica-monetaria/profundizacion-del-esquema-de-agregados-monetarios-fase-de-re-monetizacion-2026/ (WebFetch ENOTFOUND; verificado en resultados de WebSearch, que también listan la fecha en bcra.gob.ar/PoliticaMonetaria/comunicados.asp y una reproducción en cda.org.ar), consulta 22-10-2026 | M | Intro, Punto de partida: "Según su comunicado de política monetaria del 15 de diciembre de 2025, el BCRA enmarca su política en un esquema de agregados monetarios con banda de flotación cambiaria" |
| BCRA | Informe monetario diario: gráfico del M2 privado transaccional con banda de dos desvíos de los modelos | material compartido por el usuario (uso cualitativo, sin cifras ni fechas); citado como "BCRA, Informe monetario diario" en Referencias (respuesta 16) | M | E4, Referencias |

## Agregado respuesta 20 (consulta 23-10-2026)

| Banco | Práctica | Fuente | Conf. | Uso en proyecto |
|---|---|---|---|---|
| BCE / Eurosistema | Pronóstico de los factores autónomos de liquidez (billetes, depósitos del gobierno, activos externos netos, otros); el BCE publica desde junio de 2000 el pronóstico promedio de factores autónomos al anunciar cada operación principal de financiación (MRO) y, desde el 8-3-2004, una actualización el día de adjudicación, junto con la "benchmark allotment" (avisos de MRO de 2015 y 2017 lo siguen mostrando). Los boxes "Liquidity conditions and monetary policy operations" del Economic Bulletin revisan ex post esos factores. | Comunicado BCE "Weekly publication of estimates of average liquidity factors", https://www.ecb.europa.eu/press/pr/date/2004/html/pr040305.en.html ; Monthly Bulletin jul-2001, Box 2 (lista de factores), https://www.ecb.europa.eu/pub/pdf/other/mb200107_focus02.en.pdf ; avisos de MRO, p. ej. https://www.ecb.europa.eu/mopo/implement/omo/html/20170086.de.html ; Economic Bulletin 4/2026, https://www.ecb.europa.eu/press/economic-bulletin/focus/2026/html/ecb.ebbox202604_07~e257cabcc5.de.html | M (textos de fuentes oficiales vía WebSearch; WebFetch/curl al sitio del BCE bloqueados: ENOTFOUND / proxy 403). No verificado si la publicación sigue vigente hoy: se redacta como "empezó a publicar en 2000". | E1: "Del Eurosistema tomo pronosticar por separado cada factor autónomo (...), pronóstico que el BCE empezó a publicar en 2000. Aquí será interno y sumará el efectivo mínimo, para ver qué factor explica cada error." |

## Agregado respuesta 21 (consulta 23-10-2026; PDFs públicos del repo, `pdftotext -layout`)

| Banco | Práctica | Fuente | Conf. | Uso en proyecto |
|---|---|---|---|---|
| BCRA | IPOM "Junio de 2026" (2T26), sección III.2/III.3: Gráfico III.2.9 "M2 privado transaccional", sin estacionalidad, % del PIB, observado vs. "Escenario Base de simulación de modelo VECM" con bandas ±1 y ±2 desvíos standard (abr–jul-26); Gráfico III.3.1, mismo concepto ene-25 a oct-26 | `informe-politica-monetaria-2026-T2.pdf` (pp. 27-28), BCRA, Subgerencia General de Investigaciones Económicas | A | E4 Contraste; Referencias. Reemplaza la atribución al "Informe monetario diario" (sale del núcleo y de Referencias) |
| BCRA | Informe Monetario Mensual, agosto de 2026, Gráfico 3.1.2 "Base Monetaria – variación entre saldos a fines de mes" por factores: Base monetaria, Fiscal, C/V USD priv., REPO y OMAs, Otros | `informe-monetario-mensual-2026-08.pdf` (p. 3-4, sección 3. Creación de dinero) | A | E4 Ancla; Referencias |
| BCRA | (retirado) Informe monetario diario como fuente de la banda de dos desvíos | Material compartido por el usuario; el jurado (dictamen 21) indica que el informe diario público no lo muestra | — | No se cita |
