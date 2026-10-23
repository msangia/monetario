# Rutinas ilustrativas – Gerencia de Análisis Monetario (426 05)

Código que acompaña a `anexos.tex`. Ilustra cómo se aplicarían cuatro propuestas del
proyecto (`proyecto.tex`). **No forma parte del límite de 4 páginas del proyecto.**

> Con `--demo` todo corre con **datos sintéticos de demostración, no oficiales**:
> las cifras no son del BCRA y sólo sirven para verificar que el código funciona.

## Contenido

| Archivo | Eje del proyecto | Qué hace |
|---|---|---|
| `monetario_demo/liquidez.py` | Eje 1 (funciones 1 y 5) | Pronóstico diario a un día de la variación de la base o la liquidez con efectos de calendario (inicio y fin de mes, quincena, aguinaldo, diciembre, lunes). Usa regresión con calendario, espacio de estado (nivel local + calendario, `UnobservedComponents`) y ARIMAX, y su ensamble (promedio de los tres, como en el núcleo), contra un benchmark ingenuo. Evalúa fuera de muestra con ventana expansiva y reporta MAE relativo, sesgo por posición y por día del mes, cobertura de intervalos del 90 % y Diebold-Mariano con corrección HLN al 10 % (`--ultimos 60` reproduce el mínimo de 60 días en paralelo) |
| `monetario_demo/demanda_dinero.py` | Eje 4 (función 4) | Demanda de dinero real (base o M2 privado) por Engle-Granger en dos pasos con corrección de errores, en ventanas móviles. Da una alerta de inestabilidad de los coeficientes de largo plazo con un umbral simulado bajo estabilidad, y agrega CUSUM |
| `monetario_demo/bandas.py` | Eje 4 (función 4) | Banda de tolerancia para base o M2 a 1–3 meses, a partir de cuantiles empíricos del error histórico de pronóstico sin *look-ahead*, para cualquier programa (matriz origen × horizonte). Chequeo mensual "dentro/fuera de banda", calibración fuera de muestra (`cobertura_banda`) y *fan chart* |
| `monetario_demo/programa.py` | Eje 4 (función 4) | Programas a 1–3 meses: deriva, deriva estacional, velocidad constante y demanda MCE (con y sin dummies mensuales); los dos últimos, condicionales al IPC/EMAE/tasa observados. Compara MAE, DM-HLN y cobertura de la banda |
| `monetario_demo/no_lineal.py` | Eje 4 (exploratorio, fuera de los anexos) | MCE con transición suave logística (LSTR) en el nivel rezagado de la tasa, tendencia logística de sustitución de pagos y prueba de linealidad LM3 (Teräsvirta); evaluación expansiva a 1–3 meses contra el MCE lineal y la deriva estacional (`--reales --salida salidas/exploratorio_no_lineal.txt`). Resultado con datos reales: no mejora fuera de muestra |
| `monetario_demo/factores.py` | Eje 1 (funciones 1 y 5) | Variación diaria de las cuentas corrientes en el BCRA (15 − 16) por factores de la base (47–55, 58, 59), sin *look-ahead*: identidades contables (46 = suma de factores, 46 = Δ15, 19 = 15 − 16), descomposición de varianza por factor (por covarianza, suma 1), y tres variantes con MCO expansivo de reestimación diaria: V1 factores rezagados t−1 a t−5 + calendario; V2 calendario ampliado + fechas regulares inferidas del pasado (pagos concentrados en 55 y 51, vencimientos aproximados en 52, 53, 58); V3 previsión perfecta de 51 y 55 del mismo día y oráculos contables, rotulados **NO FACTIBLE**. Contra el ingenuo y el ensamble de A, con DM-HLN, cobertura y sesgo por día del mes; sensibilidades: rezago de publicación, ventana móvil de 500 días, sin el 10-07-2025 |
| `monetario_demo/evaluacion.py` | Ejes 1 y 4 | Diebold-Mariano (HLN), cobertura, tabla de errores |
| `monetario_demo/datos.py` | – | Cargadores de CSV `fecha,valor` (BCRA) y de los mensuales de INDEC (`mes,...`: EMAE e IPC), y generadores sintéticos rotulados |
| `descargar_bcra.py`, `series.txt` | Eje 5 | Descarga de series públicas de la API de Estadísticas Monetarias v4.0 del BCRA a `datos/` (11 IDs verificados contra el catálogo) |
| `monetario_demo/calidad.py` | Eje 5 | Controles de calidad de las series diarias: duplicados, fines de semana, huecos, saltos anómalos (> 10 MAD; las series de flujo, como la 46, se controlan en nivel), unidad según la metadata y concordancia con el último valor del catálogo; `controles_cruzados` verifica 46 = Δ15, 16 ≥ 17, 109 ≥ 197 y 109 > 17 |
| `correr_reales.py` | – | Corre las rutinas A, B y C con los datos reales de `datos/` y escribe `salidas/real_*.txt`, `salidas/fan_chart_real.pdf` y `salidas/chequeo_real.pdf` (figura 1 de los anexos), con encabezado de fuente, último dato y fecha de ejecución |
| `verificar_series.py` | Eje 5 | Tabla de IDs de `series.txt` contra `datos/catalogo_monetarias.csv` y control de las descargas (filas, primer y último dato) |
| `referencia/estadisticas-monetarias-v4.json` | – | Esquema OpenAPI público de la API (referencia) |
| `tests/` | – | Pruebas `pytest` (el descargador se prueba con respuestas simuladas) |
| `salidas/` | – | `real_factores.txt` y `demo_factores.txt` (Anexo A.2); `real_*.txt`, `fan_chart_real.pdf` y `chequeo_real.pdf` (datos reales; `chequeo_real.pdf` es la figura 1 de `anexos.tex`); `demo_*.txt` y `fan_chart_demo.pdf` (sintéticos) |

## Instalación y pruebas

Desde la carpeta `codigo/`:

```bash
pip install -r requirements.txt
python -m pytest -q          # 104 pruebas, ~100 s
```

## Uso con datos sintéticos (`--demo`)

```bash
python -m monetario_demo.liquidez --demo [--ultimos 60]
python -m monetario_demo.demanda_dinero --demo
python -m monetario_demo.bandas --demo --figura salidas/fan_chart_demo.pdf
python -m monetario_demo.programa --demo
python -m monetario_demo.factores --demo --salida salidas/demo_factores.txt
```

## Uso con datos reales

> **Estado (2026-10-23).** Las 11 series diarias, EMAE e IPC están en `datos/` y todas dan `ok`
> en `verificar_series.py`. `python correr_reales.py` (~2,5 min) corre: A con base (15), billetes
> (17), circulación (16), cuentas corrientes en el BCRA (15 − 16) y la base por componentes;
> B con M2 (109) y base (15) reales, **sólo IPC oficial de INDEC (desde 2016-12)**, EMAE s.e. y
> plazo fijo (1189) o BAIBAR (11), tasa en nivel y en log, y la submuestra 2017–2019; C con M2
> (109) y base (15) y cinco programas (`programa.py`; MCE en ventanas de 48 meses, orígenes desde
> 2021-01). La significancia económica de A se informa como ahorro de error en pp de la base.

1. Bajar las series con `descargar_bcra.py` y dejar los CSV en `datos/`; el paso a paso está en
   [`../datos/LEEME.md`](../datos/LEEME.md).
2. Correr las rutinas. `--csv` acepta una ruta o el número de serie: `104` equivale a `datos/bcra_104_daily.csv`.

```bash
# Todo junto (salidas/real_*.txt)
python correr_reales.py

# A. Liquidez: serie diaria en niveles; --desde, --inicio-eval (fecha) y --ventana (móvil, días)
python -m monetario_demo.liquidez --csv 17 --desde 2010-01-04 --inicio-eval 2022-01-03 [--ultimos 60]

# B. Demanda de dinero: M2 (109), IPC, EMAE y plazo fijo en pesos (1189, % anual)
python -m monetario_demo.demanda_dinero --dinero 109 --tasa 1189 \
    --precios datos/ipc_mensual.csv --actividad datos/emae_mensual.csv [--ventana 60] \
    [--desde AAAA-MM] [--hasta AAAA-MM] [--forma-tasa nivel|log]
# --precios empalmado (ipc_historico.csv antes de 2016-12) existe, pero se DESCARTA en los anexos:
# su tramo previo es de fuente no documentada.

# C. Banda de tolerancia: base (15) o M2 (109; 197 empieza en 2021) — diaria o mensual, se promedia por mes
python -m monetario_demo.bandas --csv 109 --trimestres 4 --figura salidas/fan_chart.pdf
python -m monetario_demo.bandas --csv 197 --ventana 24     # 197 empieza en 2021: deriva de 24 meses
# A.2. Cuentas corrientes por factores (19, 46, 47-55, 58, 59 en datos/; ~2,5 min)
python -m monetario_demo.factores --reales --salida salidas/real_factores.txt

# C con programas de demanda: deriva, deriva estacional, velocidad, MCE (condicionales)
python -m monetario_demo.programa --dinero 109 --tasa 1189 --figura salidas/fan_chart_real.pdf --figura-chequeo salidas/chequeo_real.pdf
```

### Formato de los CSV

```
fecha,valor
2024-01-02,123456.7
```

`fecha` va en ISO (`AAAA-MM-DD`). `valor` va con punto decimal y sin separador de miles. También se
acepta `;` con coma decimal, que es el formato de una planilla en español.

Los mensuales de INDEC se leen en su formato (`cargar_mensual`, `cargar_emae`, `cargar_ipc`):
columna `mes` en `d/m/aaaa` (`1/2/2004` = febrero de 2004) o mes abreviado en español
(`dic-16`, `sept-26`, `set-26`), con tolerancia a espacios finales y `\r\n`. Devuelven el índice
**a fin de mes** (2004-01-31), la misma convención que `a_mensual` y los generadores sintéticos.
`cargar_csv` (y por lo tanto `--precios`, `--actividad`, `--csv`) detecta la columna `mes`;
la columna se elige con `archivo.csv:columna` (por defecto `emae_se` e `ipc_ng`). Si dos
filas caen en el mismo mes (p. ej. por leer m/d en vez de d/m), el cargador da error.

## Supuestos y limitaciones

- **IPC.** B y C usan sólo el IPC oficial de INDEC (`ipc_mensual.csv`, desde 2016-12).
  `ipc_historico.csv` coincide con él desde 2016-12, pero su tramo previo es un empalme externo de
  fuente no documentada (cubre 2007–2016, período de emergencia del IPC oficial): se descarta.
  `cargar_ipc_historico` queda sólo para control.
- **Depósitos (104).** Incluyen moneda extranjera valuada en pesos (el catálogo los rotula
  `ME`; saltan en las devaluaciones de 2015 y 2023). No usarlos como depósitos en pesos.
- **Calendario con datos reales.** Las posiciones en el mes se calculan sobre los días con dato
  (los feriados no aparecen); sólo el mes inicial y el final incompletos se completan con lunes
  a viernes. Los meses parciales se descartan antes de promediar (`meses_completos`).
- **Resultados reales (2026-10-23).** A: el ensamble de calendario mejora al ingenuo en
  circulación (16) y billetes (17), no en la base (15) ni en las cuentas corrientes en el BCRA
  (15 − 16), que explican el 98 % de la varianza diaria de la base; la base por componentes mejora
  sólo 1 %. El total de factores (46) es idéntico a Δ15: no se puede usar como regresor sin
  *look-ahead*. B (IPC oficial, 2017–2026): sin cointegración en ninguna especificación (p EG ≥ 0,70).
  C (orígenes 2021–2026; errores en % simple, observado/programado − 1): el MCE condicional supera
  a la deriva a 2 y 3 meses (p 0,06 y 0,08) pero no a la deriva estacional; su banda cubre 74–81 %
  (nominal 90 %, 41–43 orígenes): hay que recalibrar. Ver `anexos.tex`.
- **Factores de la base (2026-10-23; `salidas/real_factores.txt`, Anexo A.2 de
  `../anexos.tex`).** Las 12 series de `series_factores.txt` dan `ok`.
  Identidades: 46 = suma de factores exacta desde 2019 (antes el residuo serían 56 y 57, no
  bajadas: hipótesis a verificar); 46 = Δ15 en el 98,9 % de los días (máx. 1,5 millones);
  19 = 15 − 16 siempre. Varianza de ΔCC 2022–2026 por covarianza: pases 50 %, LEFI 32 %, otras
  (59) 14 %, LELIQ 14 %, Tesoro (51) −11 % (las varianzas propias suman 7 veces la total: los
  factores se compensan); desde 11-07-2025: otras 55 %, Tesoro 44 %. Fuera de muestra
  (2022–2026, MAE relativo al ingenuo): ensamble 1,01, V1 1,05, V2 1,03, V3 (no factible) 1,05;
  ninguna mejora al ingenuo. Oráculo no factible del Tesoro 48–51 y 55: 1,32 (2022–2026) y 0,96
  desde 11-07-2025 (p 0,24); oráculo de 59: 0,57 desde 11-07-2025. Todos subestiman el fin de mes
  (+1,4 pp). La salida tiene un único sábado en los saldos (2005-12-31, fuera de la muestra).
- **M2 (109).** Es el M2 total: efectivo en poder del público + cuentas corrientes y cajas de
  ahorro en pesos de los sectores privado **y público** (metodología de la API). No es el M2
  privado del proyecto; el M2 transaccional privado (197) empieza en 2021.

- **Calendario.** Con `--demo` usa lunes a viernes sin feriados. En producción conviene agregar
  los vencimientos del Tesoro y del período de cómputo del efectivo mínimo.
- **Ensamble.** Es un promedio simple de tres modelos (regresión, espacio de estado, ARIMAX), y
  sus límites son el promedio de los límites de cada modelo (una simplificación).
- **Horizonte de la rutina A.** Pronostica a un día; los horizontes semanal y mensual del proyecto
  quedan para una extensión.
- **Errores estándar en la rutina B.** Los errores estándar MCO de la regresión cointegrante no
  son estándar; por eso el umbral de alerta se simula. El AR(1) de los residuos se corrige por
  sesgo, también por simulación.
  En un Monte Carlo propio (40 réplicas del generador sintético) hubo falsas alarmas en 8 de 40
  muestras estables, contando cualquiera de los dos coeficientes (≈ 10 % por coeficiente). Con un
  quiebre, la alerta saltó después del quiebre en 36 de 40 casos, con una demora mediana de 2 meses.
  Son resultados sobre datos sintéticos.
- **Muestra de la rutina B con IPC base dic-2016.** El panel empieza con la serie más corta: con
  `ipc_mensual.csv` va de 2016-12 a 2026-08 (117 meses, limitado por el último EMAE), es decir
  **46 ventanas de 72 meses** (58 con `--ventana 60`). Es viable, pero la primera ventana, que
  fija la referencia de estabilidad y el umbral simulado, abarca 2016-12 a 2022-11 e incluye la
  crisis de 2018, la pandemia y cambios de régimen: una alerta mide desvíos respecto de ese
  período, no respecto de un "equilibrio normal". Alternativas: `--ventana 60` (más ventanas,
  coeficientes más ruidosos) o un IPC empalmado hacia atrás (p. ej. IPC-GBA o índices
  provinciales públicos) para usar M2 (109) desde 2003; el empalme debe documentarse. La
  rutina corta con un mensaje si quedan menos de 24 ventanas.
- **Estacionalidad en la rutina B.** Por defecto se usa el EMAE desestacionalizado con M2 y
  tasa sin desestacionalizar (promedios mensuales); la estacionalidad del dinero (aguinaldo,
  diciembre) queda en el residuo. Lo coherente es desestacionalizar M2 (Eje 2) o usar
  `emae_orig` con dummies mensuales (no implementado).
- **Tasas cortas.** TAMAR (44) empieza en 2024-10 y M2 transaccional (197) en 2021: no alcanzan
  para ventanas de 72 meses; por eso la rutina B usa M2 (109) y plazo fijo en pesos (1189).
- **Comparación con velocidad.** Implementada en `programa.py` (velocidad constante, condicional).
- **Modelo de programación en la rutina C.** `bandas.py` usa la deriva; `programa.py` agrega la
  deriva estacional, la velocidad y la demanda MCE. Los programas condicionales usan el IPC, el
  EMAE y la tasa observados: su error es un piso del error de un programa real. El EMAE s.e. y el
  IPC son la versión actual (no en tiempo real).
- **Descargador.** Se escribió según el esquema OpenAPI público y se **probó con respuestas
  simuladas, no contra la API real**: el host estaba bloqueado en el entorno de desarrollo.
- **Confidencialidad.** Sólo series públicas. El proxy de red es opcional: se toma de
  `HTTPS_PROXY`/`HTTP_PROXY` o de `--proxy` y no se escribe en ningún archivo del repositorio.
