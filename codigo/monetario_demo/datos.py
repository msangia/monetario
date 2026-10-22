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

Series mensuales de INDEC (formatos tal como los dejó el usuario en ``datos/``)::

    mes,emae_orig,emae_se          mes,ipc_ng
    1/1/2004,92.6,98.5             dic-16,100.0
    1/2/2004,90.2,98.0             sept-26,12514.2

* ``mes`` en ``d/m/aaaa`` (se toma mes y año) o mes en español abreviado con año
  de 2 o 4 cifras (``ene-17``, ``sept-26``, ``set-26``, ``Dic.2016``); también ISO.
* Se toleran espacios (``"98.5 "``), finales de línea ``\r\n`` y coma decimal.
* :func:`cargar_mensual` (y sus atajos :func:`cargar_emae`, :func:`cargar_ipc`)
  devuelve una serie con ``DatetimeIndex`` **a fin de mes** (p. ej. 2004-01-31),
  la misma convención que :func:`a_mensual` (``resample("ME")``) y que los
  generadores sintéticos, de modo que ``a_mensual`` la deja igual.
* :func:`cargar_csv` detecta este formato (columna ``mes``) y lo deriva a
  :func:`cargar_mensual`; la columna se elige con ``archivo.csv:columna``
  (p. ej. ``datos/emae_mensual.csv:emae_orig``). Sin columna, se usa la única
  disponible o la preferida de :data:`COLUMNAS_PREFERIDAS` (``emae_se``, ``ipc_ng``).
* :func:`cargar_ipc_historico` empalma ``ipc_historico.csv`` (``fecha,ipc``, desde
  1992-12) con el IPC oficial desde 2016-12, previo control de razón constante.

Los generadores ``demo_*`` producen DATOS SINTÉTICOS DE DEMOSTRACIÓN, NO
OFICIALES: sirven sólo para ejecutar y probar las rutinas.
"""

from __future__ import annotations

from pathlib import Path

import re

import numpy as np
import pandas as pd

ROTULO_SINTETICO = "DATOS SINTÉTICOS DE DEMOSTRACIÓN, NO OFICIALES"

# Carpeta datos/ del repositorio (relativa a este archivo, sin rutas absolutas).
CARPETA_DATOS = Path(__file__).resolve().parents[2] / "datos"


# Meses en español abreviados (INDEC usa "sept"; algunas planillas, "set").
MESES_ES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7,
            "ago": 8, "sep": 9, "sept": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12}

# Columna que se usa por defecto cuando un CSV mensual trae varias.
COLUMNAS_PREFERIDAS = ("emae_se", "ipc_ng", "valor")

_RE_MES_ES = re.compile(r"^([a-záé]+)\.?[-/ .]?(\d{2}|\d{4})$")
_RE_DMA = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_RE_ISO = re.compile(r"^(\d{4})-(\d{1,2})(?:-(\d{1,2}))?$")


# ---------------------------------------------------------------------------
# Fechas y números
# ---------------------------------------------------------------------------
def parsear_mes(texto: str) -> pd.Timestamp:
    """Convierte un rótulo de mes a ``Timestamp`` de **fin de mes**.

    Acepta ``d/m/aaaa`` (``"1/2/2004"`` = febrero de 2004; el día se ignora),
    mes en español abreviado con año de 2 o 4 cifras (``"dic-16"``, ``"sept-26"``,
    ``"set-26"``, ``"Ene.2017"``) e ISO (``"2004-02"``, ``"2004-02-01"``).

    Raises:
        ValueError: si el rótulo no tiene un formato reconocido o el mes no existe.
    """
    t = str(texto).strip().lower()
    if m := _RE_DMA.match(t):
        anio, mes = int(m.group(3)), int(m.group(2))
    elif m := _RE_ISO.match(t):
        anio, mes = int(m.group(1)), int(m.group(2))
    elif (m := _RE_MES_ES.match(t)) and m.group(1) in MESES_ES:
        mes, anio = MESES_ES[m.group(1)], int(m.group(2))
        anio += 2000 if anio < 100 else 0
    else:
        raise ValueError(f"Fecha mensual no reconocida: {texto!r}")
    if not 1 <= mes <= 12:
        raise ValueError(f"Mes inválido en {texto!r}")
    return pd.Timestamp(anio, mes, 1) + pd.offsets.MonthEnd(0)


def _a_numero(col: pd.Series) -> pd.Series:
    """Texto a ``float`` tolerando espacios y coma decimal; vacíos -> NaN.

    Raises:
        ValueError: si hay un valor no vacío que no es numérico.
    """
    t = col.astype("string").str.strip().str.replace(r"\s+", "", regex=True)
    coma = t.str.contains(",", na=False) & ~t.str.contains(r"\.", na=False)
    t = t.where(~coma, t.str.replace(",", ".", regex=False))
    t = t.replace("", pd.NA)
    v = pd.to_numeric(t, errors="coerce")
    malos = t.notna() & v.isna()
    if malos.any():
        raise ValueError(f"Valores no numéricos: {list(t[malos].head(3))}")
    return v.astype(float)


def _separar_columna(ruta: str | Path) -> tuple[str | Path, str | None]:
    """Separa ``"archivo.csv:columna"``; no confunde ``C:\\...`` de Windows."""
    texto = str(ruta)
    if ":" in texto:
        base, col = texto.rsplit(":", 1)
        if base.lower().endswith(".csv") and col and not re.search(r"[\\/]", col):
            return base, col
    return ruta, None


def _resolver_ruta(ruta: str | Path) -> Path:
    """Ruta tal cual, o dentro de ``datos/``; un número solo es ``bcra_<id>_daily.csv``."""
    if str(ruta).isdigit():
        ruta = CARPETA_DATOS / f"bcra_{ruta}_daily.csv"
    ruta = Path(ruta)
    if not ruta.exists() and (CARPETA_DATOS / ruta.name).exists():
        ruta = CARPETA_DATOS / ruta.name
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró {ruta}. Ver datos/LEEME.md.")
    return ruta


# ---------------------------------------------------------------------------
# CSV mensuales (INDEC)
# ---------------------------------------------------------------------------
def cargar_mensual(ruta: str | Path, columna: str | None = None,
                   nombre: str | None = None) -> pd.Series:
    """Lee un CSV mensual (columna ``mes`` o ``fecha`` + una o más columnas de valores).

    Args:
        ruta: archivo (se busca también en ``datos/``).
        columna: columna de valores; si es ``None``, la única que haya o la primera
            de :data:`COLUMNAS_PREFERIDAS` presente.
        nombre: nombre de la serie (por defecto, ``<archivo>:<columna>``).

    Returns:
        ``pd.Series`` de ``float`` con ``DatetimeIndex`` a **fin de mes**, ordenada,
        sin NaN (se descartan filas vacías, p. ej. al final de una planilla).

    Raises:
        ValueError: si falta la columna de fechas o de valores, si una fecha o un
            valor no se reconoce, o si hay meses repetidos (señal de que el formato
            de fecha se interpretó mal, p. ej. m/d en vez de d/m).
    """
    ruta = _resolver_ruta(ruta)
    df = pd.read_csv(ruta, dtype=str, skipinitialspace=True, encoding="utf-8-sig")
    df.columns = [str(c).strip().lower() for c in df.columns]
    col_fecha = next((c for c in ("mes", "fecha", "periodo") if c in df.columns), None)
    if col_fecha is None:
        raise ValueError(f"{ruta.name}: falta la columna 'mes' (o 'fecha').")
    otras = [c for c in df.columns if c != col_fecha and not c.startswith("unnamed")]
    if columna is None:
        pref = [c for c in COLUMNAS_PREFERIDAS if c in otras]
        if len(otras) == 1 or pref:
            columna = otras[0] if len(otras) == 1 else pref[0]
        else:
            raise ValueError(f"{ruta.name}: indicar la columna ({', '.join(otras)}), "
                             f"p. ej. '{ruta.name}:{otras[0]}'.")
    columna = columna.strip().lower()
    if columna not in otras:
        raise ValueError(f"{ruta.name}: no existe la columna {columna!r} ({', '.join(otras)}).")
    df = df[df[col_fecha].notna() & (df[col_fecha].str.strip() != "")]
    try:
        valores = _a_numero(df[columna])
    except ValueError as e:
        raise ValueError(f"{ruta.name}:{columna}: {e}") from None
    idx = pd.DatetimeIndex([parsear_mes(t) for t in df[col_fecha]])
    s = pd.Series(valores.to_numpy(), index=idx, name=nombre or f"{ruta.stem}:{columna}")
    s = s.dropna().sort_index()
    if s.index.has_duplicates:
        rep = s.index[s.index.duplicated()][:3].strftime("%Y-%m").tolist()
        raise ValueError(f"{ruta.name}: meses repetidos {rep}; revisar el formato de 'mes'.")
    if s.empty:
        raise ValueError(f"{ruta.name}: no hay valores numéricos.")
    return s


def cargar_emae(ruta: str | Path = "emae_mensual.csv", columna: str = "emae_se") -> pd.Series:
    """EMAE mensual (INDEC): ``emae_se`` (desestacionalizado, por defecto) o ``emae_orig``."""
    return cargar_mensual(ruta, columna)


def cargar_ipc(ruta: str | Path = "ipc_mensual.csv", columna: str = "ipc_ng") -> pd.Series:
    """IPC nivel general mensual (INDEC, base dic-2016 = 100)."""
    return cargar_mensual(ruta, columna)


INICIO_IPC_OFICIAL = pd.Timestamp("2016-12-31")


def cargar_ipc_historico(ruta_historico: str | Path = "ipc_historico.csv",
                         ruta_oficial: str | Path = "ipc_mensual.csv",
                         tolerancia: float = 1e-3) -> pd.Series:
    """IPC empalmado: el oficial (INDEC, base dic-2016) desde 2016-12 y el histórico antes.

    ``ipc_historico.csv`` (columnas ``fecha,ipc``, fechas ``d/m/aaaa``) es un IPC ya
    empalmado de origen externo. El empalme se hace **hacia atrás** en dic-2016: el
    tramo previo del histórico se reescala por la razón oficial/histórico de ese mes,
    de modo que desde 2016-12 la serie es exactamente la oficial. Antes se controla
    que la razón sea constante en todo el tramo común (desvío relativo máximo menor
    que ``tolerancia``); si no lo es, las dos series no tienen la misma base o
    metodología y el empalme no es válido.

    Returns:
        ``pd.Series`` mensual (índice a fin de mes) con atributo ``attrs["empalme"]``
        que describe el empalme (fecha, razón y desvío máximo en el tramo común).

    Raises:
        ValueError: si no hay tramo común, si el histórico tiene meses faltantes o si
            la razón no es constante.
    """
    hist = cargar_mensual(ruta_historico, "ipc", nombre="ipc_historico")
    ofic = cargar_ipc(ruta_oficial)
    esperado = pd.date_range(hist.index[0], hist.index[-1], freq="ME")
    if not hist.index.equals(esperado):
        faltan = esperado.difference(hist.index)[:3].strftime("%Y-%m").tolist()
        raise ValueError(f"ipc_historico: meses faltantes {faltan}.")
    comun = ofic.index.intersection(hist.index)
    if INICIO_IPC_OFICIAL not in comun:
        raise ValueError("No hay tramo común en dic-2016 para empalmar.")
    razon = ofic.loc[comun] / hist.loc[comun]
    r0 = float(razon.loc[INICIO_IPC_OFICIAL])
    desvio = float((razon / r0 - 1).abs().max())
    if desvio > tolerancia:
        raise ValueError(f"La razón oficial/histórico no es constante (desvío {desvio:.2%}).")
    antes = hist.loc[hist.index < INICIO_IPC_OFICIAL] * r0
    s = pd.concat([antes, ofic.loc[ofic.index >= INICIO_IPC_OFICIAL]]).rename("ipc_empalmado")
    s.attrs["empalme"] = (f"IPC empalmado: {Path(ruta_historico).name} hasta 2016-11 "
                          f"(x {r0:.6f}), {Path(ruta_oficial).name} (INDEC) desde 2016-12; "
                          f"razón en el tramo común "
                          f"{comun[0]:%Y-%m} a {comun[-1]:%Y-%m}: desvío máx. {desvio:.1e}")
    return s


def meses_completos(diaria: pd.Series, holgura: int = 4) -> pd.Series:
    """Quita el último mes de una serie diaria si está incompleto.

    El último mes se considera completo si su último dato cae a menos de ``holgura``
    días hábiles del último día hábil (lunes a viernes) del mes. Evita promediar un
    mes parcial (p. ej., datos hasta el 20 de octubre) como si fuera completo.
    """
    if diaria.empty:
        return diaria
    ultimo = diaria.index[-1]
    fin_habil = pd.bdate_range(ultimo.replace(day=1), ultimo + pd.offsets.MonthEnd(0))[-1]
    if len(pd.bdate_range(ultimo, fin_habil)) - 1 > holgura:
        return diaria[diaria.index < ultimo.replace(day=1)]
    return diaria


# ---------------------------------------------------------------------------
# CSV fecha,valor
# ---------------------------------------------------------------------------
def cargar_csv(ruta: str | Path, nombre: str | None = None) -> pd.Series:
    """Lee un CSV ``fecha,valor`` y devuelve una serie ordenada por fecha.

    Si el archivo tiene columna ``mes`` (o se indica ``archivo.csv:columna``), se
    lee con :func:`cargar_mensual` (índice a fin de mes).

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
    ruta, columna = _separar_columna(ruta)
    ruta = _resolver_ruta(ruta)
    df = pd.read_csv(ruta)
    cols = {str(c).strip().lower() for c in df.columns}
    if columna is not None or ("mes" in cols and "fecha" not in cols):
        return cargar_mensual(ruta, columna, nombre)
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
