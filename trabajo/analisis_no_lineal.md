# Análisis: no linealidades y medios de pago en la demanda de efectivo (material de trabajo)

> Material de trabajo, **no se entrega**. Analiza una nota técnica preliminar de un tercero
> (`Non_linear_money_2.pdf`, nov-2025, "versión preliminar en elaboración") y prueba la idea
> con un prototipo propio sobre datos públicos. **Confidencialidad:** aquí no se copian texto,
> cifras, tablas ni resultados de esa nota; se describen en forma cualitativa. Las cifras de
> este archivo son **cálculo propio** con datos públicos (`codigo/salidas/exploratorio_no_lineal.txt`).

## 1. Resumen ejecutivo

- La nota plantea una buena pregunta para la Gerencia: si la demanda de efectivo responde distinto
  a la tasa según su nivel, y si los pagos electrónicos están cambiando la demanda de largo plazo.
  Usa un MCE mensual con dos compuertas logísticas, una en la tasa y otra en un indicador de
  adopción de pagos, estimado con métodos bayesianos (Stan).
- Es una nota exploratoria valiosa, pero **no muestra que la no linealidad mejore el pronóstico**:
  no tiene prueba de linealidad ni evaluación fuera de muestra contra el MCE lineal, y el régimen
  tecnológico apenas se observa en la muestra (es, sobre todo, extrapolación guiada por los *priors*).
- Prototipo propio (LSTR en la tasa + tendencia logística de pagos; billetes 17, circulación 16,
  M2 109; IPC oficial desde 2016-12; ventana expansiva; 64 orígenes desde 2021-01): **ningún
  modelo no lineal supera al MCE lineal** a 1-3 meses (MAE relativo 0,99-1,27; DM-HLN p ≥ 0,45).
  La linealidad se rechaza en la muestra completa, pero **no** con la información del primer
  origen (p ≥ 0,12), y para billetes con la tasa de plazo fijo deja de rechazarse si se corta en
  2023-06: el rechazo lo produce casi solo el episodio de tasas > 100 % de fines de 2023.
- Hallazgo útil lateral: el **MCE lineal de billetes (17) y circulación (16)** con ventana expansiva
  supera a la deriva estacional a 1 mes (p 0,03 y 0,04; DM-HLN al 10 %), con cobertura de banda
  del 79-88 % (nominal 90 %). Eso sirve para la rutina C, no para el núcleo tal como está.
- Recomendación: **no** incorporar el LSTR al núcleo ni a los anexos como resultado. Una mención
  breve como línea de trabajo del Eje 4 (con literatura pública) es defendible. No citar la nota.

## 2. Análisis del documento

**Pregunta.** Dos fuentes de incertidumbre *de modelo* en la demanda de billetes y monedas en
poder del público: (i) efecto no lineal de la tasa según su nivel; (ii) efecto de mediano plazo
de la adopción de medios de pago alternativos (billeteras) sobre la demanda de largo plazo.

**Datos y variables.** Mensual, desde 2017 hasta el último dato de 2025 (la muestra se elige por
la disponibilidad del indicador de pagos). Dinero real desestacionalizado (circulante en público
deflactado), tasa de plazo fijo de corto plazo (TNA), PIB mensual desestacionalizado y, como
indicador de adopción, saldos reales en proveedores de servicios de pago.

**Especificación.**
- *Largo plazo:* demanda convencional (semielasticidad a la tasa, elasticidad al producto). Una
  compuerta logística decreciente en el indicador de pagos pondera entre ese régimen
  "convencional" y uno "terminal" en el que la tasa deja de importar y la elasticidad al
  producto es menor. Es decir, la tecnología no desplaza un intercepto: cambia pendientes.
- *Corto plazo:* MCE con inercia (Δx rezagado), Δy, Δr contemporánea y rezagada, y el término
  de corrección; los coeficientes de Δr, Δr₋₁ y del término de corrección son mezclas de un
  régimen "tasa baja" y otro "tasa alta" según una logística en el **nivel rezagado** de la tasa.
- Errores normales (y una variante con t de Student).

**Estimación y pruebas.** Bayesiana (HMC/NUTS en Stan, varias cadenas), *priors* débilmente
informativos pero **truncados en el signo** de varios coeficientes (todos los coeficientes de
régimen negativos, pendientes positivas). Diagnósticos de convergencia (R̂, tamaño efectivo).
**No** hay prueba de linealidad (tipo Luukkonen-Saikkonen-Teräsvirta), ni selección de la
variable de transición, ni comparación formal (verosimilitud marginal, LOO, pseudo fuera de
muestra) con el MCE lineal: la "comparación de ajuste" es un gráfico de pelos recursivo y una
proyección comparada visualmente con otro modelo interno.

**Resultados (cualitativo).** La elasticidad producto de largo plazo cae hacia un valor terminal
claramente menor y el rol de largo plazo de la tasa se apaga con la adopción de pagos; en el corto
plazo, la tasa contrae más el efectivo cuando su nivel es bajo, y la corrección al equilibrio es
algo más rápida con tasas altas. La transición en la tasa es suave. La compuerta tecnológica está
prácticamente en el régimen convencional durante casi toda la muestra y sólo empieza a moverse al
final; el régimen terminal surge de extrapolarla. Los intervalos de credibilidad de los
parámetros de la compuerta tecnológica y de la elasticidad terminal son muy amplios, y los
regímenes de tasa "baja" y "alta" se superponen.

**Hipótesis fuertes.**
1. Que el **nivel de la tasa nominal** sea la variable de estado. En Argentina el nivel de la tasa
   nominal acompaña al régimen de inflación, a la brecha cambiaria y a los episodios de crisis;
   el "régimen de tasa alta" puede ser un régimen de inflación o de incertidumbre.
2. Que el indicador de pagos sea **exógeno**: los saldos en billeteras dependen de la
   remuneración (fondos *money market*, cuentas remuneradas), es decir, de la propia tasa, y de la
   menor tenencia de efectivo (causalidad inversa).
3. Que la tecnología cambie **pendientes** (elasticidades) y no sólo el nivel: con un régimen
   terminal casi no observado, esto se identifica por los *priors*.
4. Signos impuestos por truncamiento: el resultado "todos negativos" es en parte supuesto.
5. Relación de largo plazo sin prueba de cointegración; velocidades de ajuste chicas, compatibles
   con ausencia de cointegración.

**Debilidades.**
- *Look-ahead:* dinero y PIB desestacionalizados con filtros de muestra completa y datos
  revisados; no queda claro si el gráfico "recursivo" reestima en cada origen o usa la posterior
  de muestra completa (en ese caso, hay información futura en los parámetros).
- *Muestra corta:* unos cien meses, más de quince parámetros y dos compuertas no lineales; la posición de los
  umbrales la determinan uno o dos episodios (2019, fines de 2023).
- *Endogeneidad:* Δr contemporánea, tasa de política que responde al dinero y al tipo de cambio;
  indicador de pagos determinado en conjunto con el efectivo.
- *Identificación de la tendencia de pagos:* sin variación exógena (normativa: interoperabilidad
  QR, transferencias inmediatas; denominaciones), la compuerta absorbe cualquier factor lento
  omitido (informalidad, estructura de denominaciones —que la propia nota menciona pero no
  modela—, dolarización, pandemia).
- No se informan errores fuera de muestra, cobertura de intervalos ni pruebas DM.

**Qué no se puede replicar con datos públicos (de `datos/`).** El indicador de saldos en
proveedores de pago no está en el catálogo de la API v4.0 ni en `datos/`; la serie
desestacionalizada exacta del dinero; la tasa de plazo fijo del tramo que usa la nota (usamos 1189,
promedio de plazo fijo); la estimación bayesiana (Stan no está en nuestras dependencias). Sí se replica la
estructura del MCE con compuerta logística en la tasa.

## 3. Diagnóstico para nuestros modelos

**¿Explica la no linealidad la inestabilidad del MCE lineal (rutina B)?** En parte, y no por la
vía que propone la nota:
- El **largo plazo lineal tiene signo equivocado** en la elasticidad producto (b_y < 0 en billetes,
  circulación y M2, muestra 2017-2026). Agregar una tendencia logística de "sustitución" lo vuelve
  positivo y más plausible (billetes: de −1,24 a 0,79; circulación: de −1,42 a 1,00; M2: de −0,83
  a 0,29). Es un síntoma de **variable omitida lenta** (pagos digitales u otra), que hace no
  estacionario el residuo y explica parte del fracaso de Engle-Granger.
- La no linealidad en la tasa **es un episodio**, no un régimen recurrente: la prueba LM3 rechaza
  en muestra completa pero no con información hasta 2023-06 (billetes con plazo fijo, p 0,23;
  con BAIBAR como variable de transición sí rechaza al 5 %, p 0,04, lo que vuelve a apuntar a
  que la variable de estado no está bien definida).
  Con un solo episodio de tasa > 100 %, el umbral no está identificado (en los orígenes, c varía
  entre 22 y 69 % anual para billetes y γ cae en el borde inferior de la grilla en la mitad de
  los orígenes: la "transición" es casi una interacción lineal con el nivel de la tasa).
- La secuencia de Teräsvirta no es estable entre variables de transición (ESTR con plazo fijo,
  LSTR con BAIBAR y pases para billetes), señal adicional de identificación débil.

**Modelo A (liquidez diaria, billetes 17).** La no linealidad en tasa no aporta a un día; manda el
calendario. Sí es relevante la tendencia tecnológica para la **amplitud** de los efectos de
calendario (aguinaldo, inicio de mes): conviene estimarlos en ventana móvil o con interacción
con una tendencia, y verificar si se achican desde 2020.

**Modelo B (demanda).** Lo aprovechable: (i) incluir un término de tendencia/quiebre suave en el
largo plazo como **control de especificación** (no como "efecto tecnológico" identificado);
(ii) probar como variable de estado la inflación o la tasa real esperada (REM) además de la tasa
nominal; (iii) reportar LM3 con la información disponible en cada origen.

**Modelo C (bandas).** La lección más útil es de **varianza**, no de media: los errores son mucho
mayores en el episodio de tasas e inflación altas. Bandas condicionadas al régimen (cuantiles
escalados por volatilidad reciente o por el nivel de la variable de estado) deberían mejorar la
cobertura, que hoy está bajo el 90 % nominal. Además, el MCE lineal de billetes y circulación
con ventana expansiva supera a la deriva estacional a 1 mes: es candidato a programa de efectivo.

## 4. Resultados del prototipo (`codigo/monetario_demo/no_lineal.py`)

Implementación propia: MCE con dummies mensuales; largo plazo por MCO (con o sin tendencia
logística en el tiempo, elegida por grilla); corto plazo con S_t = (u₋₁, Δi, Δi₋₁) cuyos
coeficientes cambian con F = logística(i₋₁; γ, c), estimada por NLS concentrado en grilla (γ en
unidades del desvío de la tasa, c entre los percentiles 15 y 85). Prueba LM3 y secuencia
H04-H03-H02. Pronóstico condicional (IPC, EMAE y tasa observados) a 1-3 meses, ventana
expansiva desde 2017 (mínimo 48 meses), 64 orígenes comunes desde 2021-01, errores en % simple,
DM-HLN unilateral con pérdida absoluta, banda del 90 % por cuantiles empíricos previos.
Datos reales; cálculo propio, no oficial. Salida: `codigo/salidas/exploratorio_no_lineal.txt`.

MAE (%) fuera de muestra, h = 1 / 2 / 3:

| Serie | MCE lineal | LSTR | Tendencia | LSTR + tendencia | Deriva estacional |
|---|---|---|---|---|---|
| Billetes (17) | 2,06 / 4,48 / 6,45 | 2,36 / 5,02 / 6,82 | 2,19 / 4,58 / 6,83 | 2,62 / 5,36 / 7,40 | 2,65 / 5,23 / 7,60 |
| Circulación (16) | 2,07 / 4,27 / 6,08 | 2,29 / 4,70 / 6,33 | 2,12 / 4,24 / 6,22 | 2,54 / 5,20 / 7,03 | 2,60 / 5,18 / 7,56 |
| M2 total (109) | 2,83 / 4,90 / 6,42 | 3,42 / 5,39 / 7,47 | 2,83 / 4,83 / 6,58 | 3,24 / 5,52 / 7,68 | 3,11 / 5,50 / 8,09 |

- Ningún modelo no lineal mejora al lineal con significancia (DM-HLN p entre 0,45 y 0,97). La
  tendencia sola empata (MAE relativo 0,99-1,06); la combinación es la peor (sobreajuste).
- El lineal supera a la deriva estacional a h = 1 en billetes (p 0,03) y circulación (p 0,04);
  no en M2 (p 0,25), ni a 2-3 meses.
- Cobertura de la banda del 90 % (38-40 orígenes): lineal 78-88 %; no lineales 63-87 %, con
  bandas más anchas; deriva estacional 37-65 %.
- Submuestra **elegida ex post** (orígenes desde 2024-07, 23, ya con el episodio en la
  estimación): el LSTR iguala o mejora levemente al lineal a 2-3 meses en billetes y circulación
  (h = 3: 4,45 contra 4,86 en billetes). Sin DM por su tamaño; es una pista, no una conclusión.
- Riesgos de sobreajuste: 25-28 parámetros con ~110 observaciones; grilla de (γ, c), cuatro
  variables de transición y cuatro modelos (búsqueda de especificación); un solo episodio que
  define el régimen alto; IPC oficial sólo desde 2016-12; datos de EMAE revisados (no en tiempo
  real). Los p-valores LM3 son aproximados (u₋₁ es regresor generado).
- Datos sintéticos (`--demo`, rotulados): el procedimiento recupera umbral y tendencia
  conocidos y mejora al lineal; o sea, el resultado negativo con datos reales no es un defecto
  del código.

## 5. Recomendación

**Núcleo (`proyecto.tex`).** No agregar el LSTR como resultado ni citar la nota. Si hay espacio en
el Eje 4, una línea: "evaluar no linealidades en la demanda de efectivo (transición suave según
el nivel de tasa o inflación) y el efecto de los nuevos medios de pago, con prueba de linealidad
y evaluación fuera de muestra contra el MCE lineal". Citas seguras: Granger y Teräsvirta (1993),
*Modelling Nonlinear Economic Relationships*, Oxford University Press; Teräsvirta (1994), *JASA*
89(425), 208-218; van Dijk, Teräsvirta y Franses (2002), *Econometric Reviews* 21(1), 1-47;
Luukkonen, Saikkonen y Teräsvirta (1988), *Biometrika* 75(3), 491-499. **No** citar Kapetanios,
Shin y Snell (2006) como *Journal of Econometrics*: el trabajo que recuerdo sobre cointegración
con corrección de errores no lineal de esos autores es de *Econometric Theory* 22 (2006) y el de
raíz unitaria en ESTAR es *Journal of Econometrics* 112 (2003); verificar antes de usar.

**Anexos (`anexos.tex`).** No incorporar el prototipo (los anexos ya están en su límite y el
resultado es negativo). Opcional, si el usuario quiere mostrar honestidad metodológica: una frase
en la rutina C ("un MCE con transición logística en la tasa no mejoró fuera de muestra al MCE
lineal; ver `codigo/`"). Más valioso: evaluar el MCE lineal de billetes como programa de efectivo
en `programa.py` (supera a la deriva estacional a 1 mes).

**Cómo referirse a la nota sin infringir confidencialidad.** No nombrarla, no citar al autor ni
sus resultados; presentar la idea como práctica estándar de la literatura pública citada arriba.
Si el usuario quiere reconocerla, pedir antes autorización al autor. **Aviso:**
`Non_linear_money_2.pdf` está **versionado en git** (`git ls-files`); si el repositorio es o será
público, conviene sacarlo del control de versiones (decisión del usuario).

**Datos que conviene bajar** (IDs de `datos/catalogo_monetarias.csv`, con `descargar_bcra.py`):
- `1608` billetes y monedas en poder del público, `1618` M2 y `1624` M3 en moneda local
  (mensuales desde 1940): historia larga para probar la no linealidad con más de un episodio
  (requiere un deflactor previo a 2016 documentado).
- `1239` M2 privado (desde 2017), `1241` depósitos a la vista y `1242` a plazo del sector privado:
  composición efectivo/depósitos (proxy de sustitución, endógena: usar con rezago y como control).
- `115` préstamos con tarjeta de crédito al sector privado: proxy de uso de medios electrónicos.
- `153` pases pasivos con fondos comunes de inversión (hasta su eliminación): actividad de FCI
  *money market*.
- Fuera de la API (verificar disponibilidad y formato antes): patrimonio de FCI *money market*
  (CAFCI/CNV), estadísticas de pagos minoristas del BCRA (transferencias inmediatas, pagos con QR)
  y expectativas de inflación del REM (para una tasa real esperada como variable de transición).

## 6. Próximos pasos (prioridad)

1. **Programa de efectivo en C:** agregar el MCE lineal expansivo de billetes (17) a
   `programa.py` y repetir la comparación con la banda; ver si la ventaja a 1 mes persiste.
2. **Bandas condicionadas al régimen:** escalar los cuantiles por volatilidad reciente o por la
   variable de estado; medir cobertura fuera de muestra (objetivo: acercarse al 90 %).
3. **Largo plazo con control de tendencia/quiebre** en la rutina B (billetes y M2), con la
   prueba LM3 reportada en tiempo real (en cada origen) y Engle-Granger sobre el residuo.
4. **Proxy de pagos observable** con los IDs anteriores (rezagado, como control), y comparar con
   la tendencia determinística; documentar la identificación.
5. **Historia larga** (1608/1618 con deflactor documentado) para que el régimen de tasa alta
   tenga más de un episodio; recién entonces reevaluar el LSTR.
6. Benchmarks adicionales: regresión regularizada (ridge/LASSO sobre rezagos y calendario) y
   versión en tiempo real del EMAE; LSTR con NLS completo y *priors* vía penalización sólo si 1-5
   muestran ganancia.
