# Rutinas ilustrativas – Gerencia de Análisis Monetario (426 05)

Código que acompaña a `anexos.tex`. Ilustra cómo se aplicarían tres propuestas del
proyecto (`proyecto.tex`). **No forma parte del límite de 4 páginas del proyecto.**

> Con `--demo` todo corre con **datos sintéticos de demostración, no oficiales**:
> las cifras no son del BCRA y sólo sirven para verificar que el código funciona.

## Contenido

| Archivo | Eje del proyecto | Qué hace |
|---|---|---|
| `monetario_demo/liquidez.py` | Eje 1 (funciones 1 y 5) | Pronóstico diario a un día de la variación de la base o la liquidez con efectos de calendario (inicio y fin de mes, quincena, aguinaldo, diciembre, lunes). Usa regresión, ARIMAX (espacio de estado) y un ensamble, contra un benchmark ingenuo. Evalúa fuera de muestra con ventana expansiva y reporta MAE relativo, sesgo por posición y por día del mes, cobertura de intervalos del 90 % y Diebold-Mariano con corrección HLN al 10 % (`--ultimos 60` reproduce el mínimo de 60 días en paralelo) |
| `monetario_demo/demanda_dinero.py` | Eje 4 (función 4) | Demanda de dinero real (base o M2 privado) por Engle-Granger en dos pasos con corrección de errores, en ventanas móviles. Da una alerta de inestabilidad de los coeficientes de largo plazo con un umbral simulado bajo estabilidad, y agrega CUSUM |
| `monetario_demo/bandas.py` | Eje 4 (función 4) | Banda de tolerancia para base o M2 a 1–3 meses, a partir de cuantiles empíricos del error histórico de pronóstico sin *look-ahead*. Hace el chequeo mensual "dentro/fuera de banda" de cada trimestre y un *fan chart* |
| `monetario_demo/evaluacion.py` | Ejes 1 y 4 | Diebold-Mariano (HLN), cobertura, tabla de errores |
| `monetario_demo/datos.py` | – | Cargadores de CSV `fecha,valor` (BCRA) y de los mensuales de INDEC (`mes,...`: EMAE e IPC), y generadores sintéticos rotulados |
| `descargar_bcra.py`, `series.txt` | Eje 5 | Descarga de series públicas de la API de Estadísticas Monetarias v4.0 del BCRA a `datos/` (11 IDs verificados contra el catálogo) |
| `verificar_series.py` | Eje 5 | Tabla de IDs de `series.txt` contra `datos/catalogo_monetarias.csv` y control de las descargas (filas, primer y último dato) |
| `referencia/estadisticas-monetarias-v4.json` | – | Esquema OpenAPI público de la API (referencia) |
| `tests/` | – | Pruebas `pytest` (el descargador se prueba con respuestas simuladas) |
| `salidas/` | – | Salidas demostrativas usadas en `anexos.tex` |

## Instalación y pruebas

Desde la carpeta `codigo/`:

```bash
pip install -r requirements.txt
python -m pytest -q          # 58 pruebas, ~35 s
```

## Uso con datos sintéticos (`--demo`)

```bash
python -m monetario_demo.liquidez --demo [--ultimos 60]
python -m monetario_demo.demanda_dinero --demo
python -m monetario_demo.bandas --demo --figura salidas/fan_chart_demo.pdf
```

## Uso con datos reales

> **Estado (2026-10).** En `datos/` ya están el catálogo, el EMAE y el IPC (INDEC). **Faltan las
> series diarias del BCRA** (`bcra_<id>_daily.csv`: base, M2, tasas), que se bajan dentro del
> BCRA con `descargar_bcra.py`. Hasta entonces, las rutinas A, B y C no corren con datos reales:
> la B lee EMAE e IPC y se detiene con un mensaje claro al no encontrar `bcra_109_daily.csv`.
> El *smoke test* de la B (`tests/test_demanda_dinero.py`) combina EMAE e IPC reales con M2 y
> tasa diarias **sintéticas, sólo dentro del test**; no produce resultados para el anexo.

1. Bajar las series con `descargar_bcra.py` y dejar los CSV en `datos/`; el paso a paso está en
   [`../datos/LEEME.md`](../datos/LEEME.md).
2. Correr las rutinas. `--csv` acepta una ruta o el número de serie: `104` equivale a `datos/bcra_104_daily.csv`.

```bash
# A. Liquidez: serie diaria en niveles (base monetaria o la de liquidez que se pronostique)
python -m monetario_demo.liquidez --csv <id_base_monetaria> --ultimos 60

# B. Demanda de dinero: M2 (109), IPC, EMAE y plazo fijo en pesos (1189, % anual)
python -m monetario_demo.demanda_dinero --dinero 109 --tasa 1189 \
    --precios datos/ipc_mensual.csv --actividad datos/emae_mensual.csv [--ventana 60]

# C. Banda de tolerancia: base (15) o M2 (109; 197 empieza en 2021) — diaria o mensual, se promedia por mes
python -m monetario_demo.bandas --csv 109 --trimestres 4 --figura salidas/fan_chart.pdf
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

- **Calendario.** Usa días hábiles de lunes a viernes, sin feriados argentinos. En producción
  conviene agregar el calendario de feriados y los vencimientos del Tesoro y del período de
  cómputo del efectivo mínimo.
- **Ensamble.** Es un promedio simple de dos modelos, y sus límites son el promedio de los
  límites de cada modelo (una simplificación).
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
- **Comparación con velocidad.** La comparación con un modelo simple de velocidad, que propone el
  proyecto, queda pendiente.
- **Modelo de programación en la rutina C.** Usa un modelo ilustrativo: deriva de 36 meses. La
  banda sólo necesita el historial de errores del modelo que se use en la programación.
- **Descargador.** Se escribió según el esquema OpenAPI público y se **probó con respuestas
  simuladas, no contra la API real**: el host estaba bloqueado en el entorno de desarrollo.
- **Confidencialidad.** Sólo series públicas. El proxy de red es opcional: se toma de
  `HTTPS_PROXY`/`HTTP_PROXY` o de `--proxy` y no se escribe en ningún archivo del repositorio.
