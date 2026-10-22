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
| `monetario_demo/datos.py` | – | Cargador de CSV `fecha,valor` y generadores sintéticos rotulados |
| `descargar_bcra.py`, `series.txt` | Eje 5 | Descarga de series públicas de la API de Estadísticas Monetarias v4.0 del BCRA a `datos/` |
| `referencia/estadisticas-monetarias-v4.json` | – | Esquema OpenAPI público de la API (referencia) |
| `tests/` | – | Pruebas `pytest` (el descargador se prueba con respuestas simuladas) |
| `salidas/` | – | Salidas demostrativas usadas en `anexos.tex` |

## Instalación y pruebas

Desde la carpeta `codigo/`:

```bash
pip install -r requirements.txt
python -m pytest -q          # 34 pruebas, ~35 s
```

## Uso con datos sintéticos (`--demo`)

```bash
python -m monetario_demo.liquidez --demo [--ultimos 60]
python -m monetario_demo.demanda_dinero --demo
python -m monetario_demo.bandas --demo --figura salidas/fan_chart_demo.pdf
```

## Uso con datos reales

1. Bajar las series con `descargar_bcra.py` y dejar los CSV en `datos/`; el paso a paso está en
   [`../datos/LEEME.md`](../datos/LEEME.md).
2. Correr las rutinas. `--csv` acepta una ruta o el número de serie: `104` equivale a `datos/bcra_104_daily.csv`.

```bash
# A. Liquidez: serie diaria en niveles (base monetaria o la de liquidez que se pronostique)
python -m monetario_demo.liquidez --csv <id_base_monetaria> --ultimos 60

# B. Demanda de dinero: dinero nominal, IPC, EMAE y costo de oportunidad (% anual)
python -m monetario_demo.demanda_dinero --dinero <id_M2_privado> --precios datos/ipc_mensual.csv \
    --actividad datos/emae_mensual.csv --tasa <id_tasa>

# C. Banda de tolerancia: base o M2 (diaria o mensual; se promedia por mes)
python -m monetario_demo.bandas --csv <id_M2_privado> --trimestres 4 --figura salidas/fan_chart.pdf
```

### Formato de los CSV

```
fecha,valor
2024-01-02,123456.7
```

`fecha` va en ISO (`AAAA-MM-DD`). `valor` va con punto decimal y sin separador de miles. También se
acepta `;` con coma decimal, que es el formato de una planilla en español.

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
- **Comparación con velocidad.** La comparación con un modelo simple de velocidad, que propone el
  proyecto, queda pendiente.
- **Modelo de programación en la rutina C.** Usa un modelo ilustrativo: deriva de 36 meses. La
  banda sólo necesita el historial de errores del modelo que se use en la programación.
- **Descargador.** Se escribió según el esquema OpenAPI público y se **probó con respuestas
  simuladas, no contra la API real**: el host estaba bloqueado en el entorno de desarrollo.
- **Confidencialidad.** Sólo series públicas. El proxy de red es opcional: se toma de
  `HTTPS_PROXY`/`HTTP_PROXY` o de `--proxy` y no se escribe en ningún archivo del repositorio.
