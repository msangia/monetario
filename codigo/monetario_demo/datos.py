"""Carga de datos: CSV locales, API pública del BCRA y datos sintéticos de demostración.

Formato CSV estándar del repositorio (carpeta ``datos/``)::

    fecha,valor
    2024-01-02,123456.7
    2024-01-03,124001.2

* ``fecha`` en formato ISO ``AAAA-MM-DD``; ``valor`` con punto decimal y sin
  separador de miles. Se tolera también ``;`` como separador con coma decimal
  (formato típico de una planilla en español).

Los CSV que genera ``codigo/descargar_bcra.py`` (``datos/bcra_<id>_daily.csv``)
tienen este mismo formato; ``cargar_csv("104")`` lee ``datos/bcra_104_daily.csv``.

Los generadores ``demo_*`` producen DATOS SINTÉTICOS DE DEMOSTRACIÓN, NO
OFICIALES: sirven sólo para ejecutar y probar las rutinas.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROTULO_SINTETICO = "DATOS SINTÉTICOS DE DEMOSTRACIÓN, NO OFICIALES"

# Carpeta datos/ del repositorio (relativa a este archivo, sin rutas absolutas).
CARPETA_DATOS = Path(__file__).resolve().parents[2] / "datos"


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------
def cargar_csv(ruta: str | Path, nombre: str | None = None) -> pd.Series:
    """Lee un CSV ``fecha,valor`` y devuelve una serie ordenada por fecha.

    Args:
        ruta: archivo CSV (si no existe tal cual, se busca dentro de ``datos/``);
            un número solo (p. ej. ``"104"``) se lee como ``datos/bcra_104_daily.csv``.
        nombre: nombre de la serie devuelta (por defecto, el del archivo).

    Returns:
        ``pd.Series`` de ``float`` con ``DatetimeIndex``, sin fechas duplicadas.

    Raises:
        FileNotFoundError: si no se encuentra el archivo.
        ValueError: si faltan las columnas ``fecha`` y ``valor`` o no hay datos.
    """
    if str(ruta).isdigit():
        ruta = CARPETA_DATOS / f"bcra_{ruta}_daily.csv"
    ruta = Path(ruta)
    if not ruta.exists() and (CARPETA_DATOS / ruta.name).exists():
        ruta = CARPETA_DATOS / ruta.name
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró {ruta}. Ver datos/LEEME.md.")
    df = pd.read_csv(ruta)
    if not {"fecha", "valor"} <= set(c.strip().lower() for c in df.columns):
        df = pd.read_csv(ruta, sep=";", decimal=",", thousands=".")
    df.columns = [c.strip().lower() for c in df.columns]
    if not {"fecha", "valor"} <= set(df.columns):
        raise ValueError(f"{ruta.name}: se esperaban las columnas 'fecha,valor'.")
    fechas = pd.to_datetime(df["fecha"], format="ISO8601")
    valores = pd.to_numeric(df["valor"], errors="coerce")
    s = pd.Series(valores.to_numpy(float), index=pd.DatetimeIndex(fechas),
                  name=nombre or ruta.stem).dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    if s.empty:
        raise ValueError(f"{ruta.name}: no hay valores numéricos.")
    return s


def a_mensual(s: pd.Series, como: str = "promedio") -> pd.Series:
    """Pasa una serie diaria a mensual (``promedio`` o ``fin`` de mes), índice fin de mes."""
    r = s.resample("ME")
    out = r.mean() if como == "promedio" else r.last()
    return out.dropna()


# ---------------------------------------------------------------------------
# Datos sintéticos de demostración
# ---------------------------------------------------------------------------
def posicion_en_mes(idx: pd.DatetimeIndex) -> tuple[np.ndarray, np.ndarray]:
    """Posición de cada fecha entre los días observados de su mes.

    Returns:
        (desde el inicio: 1 = primer día hábil; desde el fin: 1 = último día hábil).
    """
    clave = idx.year * 100 + idx.month
    pos = pd.Series(1, index=idx).groupby(clave).cumsum().to_numpy()
    total = pd.Series(1, index=idx).groupby(clave).transform("sum").to_numpy()
    return pos, total - pos + 1


def demo_liquidez_diaria(inicio: str = "2019-01-02", fin: str = "2024-12-31",
                         semilla: int = 426) -> pd.Series:
    """Serie diaria (días hábiles) tipo base monetaria. DATOS SINTÉTICOS, NO OFICIALES.

    La variación diaria (%) combina efectos de calendario (fin e inicio de mes,
    quincena, aguinaldo en junio y diciembre, día de la semana) con ruido AR(1).
    No incorpora feriados argentinos.
    """
    rng = np.random.default_rng(semilla)
    idx = pd.bdate_range(inicio, fin)
    pos, pos_fin = posicion_en_mes(idx)
    efecto = (1.4 * (pos_fin <= 2) - 0.9 * (pos <= 2)
              + 0.3 * ((idx.day >= 14) & (idx.day <= 16))
              + 0.7 * (np.isin(idx.month, [6, 12]) & (idx.day >= 15))
              + 0.15 * (idx.dayofweek == 0) + 0.25 * (idx.month == 12))
    ruido = np.zeros(len(idx))
    e = rng.normal(0, 0.8, len(idx))
    for t in range(1, len(idx)):
        ruido[t] = 0.3 * ruido[t - 1] + e[t]
    var_pct = 0.05 + efecto + ruido
    nivel = 1000 * np.exp(np.cumsum(var_pct) / 100)
    return pd.Series(nivel, index=idx, name="base_sintetica")


def demo_demanda_dinero(inicio: str = "2004-01", n_meses: int = 252,
                        mes_quiebre: int | None = 144, semilla: int = 426) -> pd.DataFrame:
    """Panel mensual para demanda de dinero. DATOS SINTÉTICOS, NO OFICIALES.

    Relación de largo plazo: m - p = 1.0 * y - b_i * i + u, con u AR(1)
    estacionario; ``b_i`` pasa de 2 a 4 en ``mes_quiebre`` (``None`` = sin quiebre).

    Returns:
        DataFrame con ``m_real`` (log del dinero real), ``y`` (log de actividad) e
        ``i`` (costo de oportunidad, tasa anual en tanto por uno).
    """
    rng = np.random.default_rng(semilla)
    idx = pd.period_range(inicio, periods=n_meses, freq="M").to_timestamp("M")
    y = 4.6 + np.cumsum(rng.normal(0.002, 0.012, n_meses))
    i = 0.3 + np.cumsum(rng.normal(0, 0.02, n_meses))
    b_i = np.full(n_meses, 2.0)
    if mes_quiebre is not None:
        b_i[mes_quiebre:] = 4.0
    u = np.zeros(n_meses)
    e = rng.normal(0, 0.02, n_meses)
    for t in range(1, n_meses):
        u[t] = 0.7 * u[t - 1] + e[t]
    m_real = 1.0 + 1.0 * y - b_i * i + u
    return pd.DataFrame({"m_real": m_real, "y": y, "i": i}, index=idx)


def demo_agregado_mensual(inicio: str = "2012-01", n_meses: int = 156,
                          shock_final: float = 0.06, semilla: int = 426) -> pd.Series:
    """Agregado nominal mensual (tipo M2 privado). DATOS SINTÉTICOS, NO OFICIALES.

    ``shock_final`` suma un desvío (en log) a los dos últimos meses para ilustrar
    un caso "fuera de banda".
    """
    rng = np.random.default_rng(semilla)
    idx = pd.period_range(inicio, periods=n_meses, freq="M").to_timestamp("M")
    crec = 0.025 + 0.004 * np.sin(np.arange(n_meses) / 9) + rng.normal(0, 0.012, n_meses)
    log_m = np.log(1000) + np.cumsum(crec)
    log_m[-2:] += shock_final
    return pd.Series(np.exp(log_m), index=idx, name="m2_sintetico")
