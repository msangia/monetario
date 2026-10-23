"""Anexo A (Eje 1, funciones 1 y 5): cuentas corrientes en el BCRA por factores de la base.

Variable pronosticada: variación diaria de las cuentas corrientes de las entidades
en el BCRA, CC = base (15) - circulación (16), en puntos porcentuales de la base del
día hábil previo: ``y_t = 100 * (CC_t - CC_{t-1}) / B_{t-1}``. En esa unidad la
identidad es aditiva: ``y_t = suma de factores_t (46) - 100 * dC_t / B_{t-1}``.

Por esa identidad los factores del **mismo día** son la respuesta y no pueden ser
regresores. Se informan tres variantes por separado (MCO, ventana expansiva desde
2010, reestimación diaria, pronóstico a un día):

* **V1** factores rezagados (t-1 a t-5) por bloque, más el calendario del Anexo A;
* **V2** calendario ampliado (posición en el mes, día de la semana, quincena,
  aguinaldo) e indicadoras de fechas regulares inferidas sólo con el pasado:
  días de concentración de pagos en 55 (intereses) y 51 (Tesoro) y vencimientos
  aproximados (7, 14 y 28 días corridos después de un salto en 52, 53 o 58);
  no usa montos del mismo día;
* **V3** cota superior de *previsión perfecta*: V2 + los factores 51 y 55 del mismo
  día (V3b: el bloque del Tesoro 48-51 y 55). **NO FACTIBLE** con información
  pública: sólo mide cuánto valdría conocer los montos programados.

Benchmarks: ingenuo (variación nula) y el ensamble de calendario del Anexo A
(``liquidez.pronostico_fuera_de_muestra`` sobre el nivel de CC, convertido a pp de
la base). Diebold-Mariano con corrección HLN, pérdida absoluta, unilateral.

Uso (desde ``codigo/``)::

    python -m monetario_demo.factores --demo
    python -m monetario_demo.factores --reales --salida salidas/real_factores.txt
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import datos
from .datos import ROTULO_SINTETICO, posicion_en_mes
from .evaluacion import diebold_mariano, sesgo_por_dia
from .liquidez import pronostico_fuera_de_muestra, variables_calendario

ALFA = 0.10
FACTORES = (47, 48, 49, 50, 51, 52, 53, 54, 55, 58, 59)
NOMBRES = {47: "divisas sector privado", 48: "divisas Tesoro", 49: "adelantos transitorios",
           50: "utilidades", 51: "resto op. Tesoro", 52: "pases", 53: "LELIQ y NOTALIQ",
           54: "redescuentos", 55: "intereses y remuneración", 58: "LEFI", 59: "otras",
           "circulacion": "- variación de la circulación (16)",
           "resto": "resto (56, 57 y redondeo)"}
BLOQUES = {"divisas": (47, 48), "tesoro": (49, 50, 51), "instrumentos": (52, 53, 54, 58),
           "intereses": (55,), "otros": (59,)}
FECHA_LEFI = "2025-07-10"           # salto de la base por el fin de las LEFI
ROTULO_REAL = ("Datos: BCRA, API de Estadísticas Monetarias v4.0 (descarga {descarga}); "
               "cálculo propio, NO OFICIAL.")


# --------------------------------------------------------------------------- datos

def cargar_factores(carpeta: Path | None = None) -> pd.DataFrame:
    """Base (15), circulación (16), cuentas corrientes (19), total (46) y factores.

    Returns:
        DataFrame en millones de ARS, columnas = IDs (enteros), índice = fechas.
    """
    carpeta = Path(carpeta or datos.CARPETA_DATOS)
    ids = (15, 16, 19, 46, *FACTORES)
    s = {i: datos.cargar_csv(carpeta / f"bcra_{i}_daily.csv") for i in ids}
    return pd.concat(s, axis=1, sort=True)


def fechas_descarga(carpeta: Path | None = None) -> str:
    """Rango de fechas de descarga según los ``metadata_<id>.json``."""
    carpeta = Path(carpeta or datos.CARPETA_DATOS)
    f = []
    for i in (15, 16, 19, 46, *FACTORES):
        ruta = carpeta / f"metadata_{i}.json"
        if ruta.exists():
            d = json.loads(ruta.read_text(encoding="utf-8")).get("descarga", {})
            if d.get("fecha_descarga"):
                f.append(d["fecha_descarga"][:10])
    if not f:
        return "sin metadata"
    return min(f) if min(f) == max(f) else f"{min(f)} a {max(f)}"


def verificar_identidades(df: pd.DataFrame, tol: float = 1.0) -> dict[str, float]:
    """Grado de cumplimiento de las identidades contables (millones de ARS).

    (a) 46 = suma de 47-55, 58, 59 (cada factor ya viene con el signo de su efecto
    monetario: + expansión, - contracción); (b) 46 = variación diaria de 15;
    (c) 19 = 15 - 16. ``tol``: diferencia admitida por redondeo (1 millón).
    """
    x = df[[46, *FACTORES]].dropna()
    ra = x[46] - x[list(FACTORES)].sum(axis=1)
    p = pd.concat([df[15].dropna().diff().rename("d15"), df[46]], axis=1, sort=True).dropna()
    rb = p["d15"] - p[46]
    c = pd.concat([(df[15] - df[16]).rename("cc"), df[19]], axis=1, sort=True).dropna()
    rc = c["cc"] - c[19]
    ra19 = ra.loc["2019":]
    malos = ra[ra.abs() > tol]
    return {
        "a_n": len(ra), "a_ok": float((ra.abs() <= tol).mean()),
        "a_ok_desde_2019": float((ra19.abs() <= tol).mean()),
        "a_max_desde_2019": float(ra19.abs().max()), "a_max": float(ra.abs().max()),
        "a_ultimo_desvio": malos.index.max() if len(malos) else None,
        "b_n": len(rb), "b_ok": float((rb.abs() <= tol).mean()), "b_max": float(rb.abs().max()),
        "c_n": len(rc), "c_ok": float((rc.abs() <= tol).mean()), "c_max": float(rc.abs().max()),
    }


def texto_identidades(v: dict[str, float]) -> str:
    """Resumen legible de :func:`verificar_identidades`."""
    ult = v["a_ultimo_desvio"]
    ult = "ninguno" if ult is None else f"{ult:%Y-%m-%d}"
    return "\n".join([
        f"(a) 46 = suma de 47-55, 58, 59: {v['a_n']} días; |residuo| <= 1 millón en "
        f"{v['a_ok']:.1%} (desde 2019: {v['a_ok_desde_2019']:.1%}, máx. "
        f"{v['a_max_desde_2019']:.1f} millones); máx. histórico {v['a_max']:,.0f} millones; "
        f"último día con residuo > 1 millón: {ult}",
        "    (hipótesis, a verificar bajando 56 y 57: el residuo previo a 2019 serían los "
        "factores no descargados 56 LEBAC y NOBAC y 57 rescate de cuasimonedas)",
        f"(b) 46 = variación diaria de 15: {v['b_n']} días; |dif| <= 1 millón en "
        f"{v['b_ok']:.1%}; máx. |dif| = {v['b_max']:.2f} millones",
        f"(c) 19 = 15 - 16: {v['c_n']} días; |dif| <= 1 millón en {v['c_ok']:.1%}; "
        f"máx. |dif| = {v['c_max']:.2f} millones"])


def a_pp_base(df: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    """Variación de CC y factores en pp de la base del día hábil previo.

    ``F`` agrega ``circulacion`` (= -100 dC / B_{t-1}) y ``resto`` (lo que falta para
    la identidad: 56 y 57 antes de 2019, y redondeo), de modo que ``y = F.sum(1)``.
    """
    b1 = df[15].shift()
    y = ((df[15] - df[16]).diff() / b1 * 100).rename("y")
    F = df[list(FACTORES)].div(b1, axis=0) * 100
    F["circulacion"] = -df[16].diff() / b1 * 100
    F["resto"] = y - F.sum(axis=1, min_count=len(FACTORES) + 1)
    return y, F


def descomponer_por_factor(y: pd.Series, F: pd.DataFrame, desde: str | None = None,
                           hasta: str | None = None, excluir: tuple[str, ...] = ()) -> pd.DataFrame:
    """Participación de cada factor en la varianza diaria de CC.

    Como ``y = sum_k F_k``, ``var(y) = sum_k cov(F_k, y)``: la participación
    ``cov(F_k, y) / var(y)`` suma 1 y reparte las covarianzas entre factores (un
    factor que se compensa con otro aporta poco aunque su varianza propia sea grande).
    Se informa también ``var(F_k) / var(y)``, que no suma 1.
    """
    Z = F.loc[desde:hasta].dropna()
    if excluir:
        Z = Z.drop(index=pd.to_datetime(list(excluir)), errors="ignore")
    yy = y.reindex(Z.index)
    v = yy.var()
    t = pd.DataFrame({"participacion": Z.apply(lambda c: c.cov(yy)) / v,
                      "varianza_propia": Z.var() / v})
    t.attrs.update(n=len(Z), desde=Z.index[0], hasta=Z.index[-1])
    return t


# --------------------------------------------------------------------------- rasgos

def _posiciones(idx: pd.DatetimeIndex) -> pd.DataFrame:
    """Posición del día hábil en el mes (desde el inicio y desde el fin), como el Anexo A."""
    un_dia = pd.Timedelta(days=1)
    antes = pd.bdate_range(idx.min().replace(day=1), idx.min() - un_dia)
    despues = pd.bdate_range(idx.max() + un_dia, idx.max() + pd.offsets.MonthEnd(0))
    completo = antes.union(idx).union(despues)
    pos, pos_fin = posicion_en_mes(completo)
    return pd.DataFrame({"pos": pos, "pos_fin": pos_fin}, index=completo).loc[idx]


def calendario_ampliado(idx: pd.DatetimeIndex) -> pd.DataFrame:
    """Calendario público: 3 primeros y 3 últimos días hábiles, día de la semana, etc."""
    p = _posiciones(idx)
    c = variables_calendario(idx)[["quincena", "aguinaldo", "diciembre"]]
    for k in (1, 2, 3):
        c[f"ini{k}"] = (p["pos"] == k).astype(float)
        c[f"fin{k}"] = (p["pos_fin"] == k).astype(float)
    for d, nombre in ((1, "mar"), (2, "mie"), (3, "jue"), (4, "vie")):
        c[nombre] = (idx.dayofweek == d).astype(float)
    return c


def posiciones_concentradas(serie: pd.Series, umbral: float = 1.5,
                            minimo: int = 12) -> tuple[set[int], set[int]]:
    """Posiciones en el mes con |flujo| medio mayor que ``umbral`` veces el promedio.

    Devuelve (posiciones desde el inicio, posiciones desde el fin, ésta sólo 1 a 5).
    Se exige al menos ``minimo`` observaciones por posición.
    """
    s = serie.dropna().abs()
    if s.empty or s.mean() == 0:
        return set(), set()
    p = _posiciones(s.index)
    media = s.mean()
    g_ini = s.groupby(p["pos"].to_numpy()).agg(["mean", "count"])
    g_fin = s.groupby(p["pos_fin"].to_numpy()).agg(["mean", "count"])
    ini = {int(k) for k, r in g_ini.iterrows() if r["count"] >= minimo and r["mean"] > umbral * media}
    fin = {int(k) for k, r in g_fin.iterrows()
           if k <= 5 and r["count"] >= minimo and r["mean"] > umbral * media}
    return ini, fin


def dias_concentrados(serie: pd.Series, idx: pd.DatetimeIndex, umbral: float = 1.5,
                      ventana_dias: int = 500) -> pd.Series:
    """Indicadora de días de pago concentrado, inferida sin *look-ahead*.

    Para cada mes se usan sólo los ``ventana_dias`` días hábiles anteriores al primer
    día del mes (:func:`posiciones_concentradas`); las posiciones marcadas se aplican
    a los días de ese mes. No usa el monto del día.
    """
    p = _posiciones(idx)
    out = pd.Series(0.0, index=idx)
    s = serie.dropna()
    for mes, dias in pd.Series(idx, index=idx).groupby(idx.to_period("M")):
        pasado = s.loc[: mes.start_time - pd.Timedelta(days=1)].iloc[-ventana_dias:]
        if len(pasado) < 120:
            continue
        ini, fin = posiciones_concentradas(pasado, umbral)
        pm = p.loc[dias.index]
        out.loc[dias.index] = (pm["pos"].isin(ini) | pm["pos_fin"].isin(fin)).astype(float).to_numpy()
    return out


def indicadoras_vencimientos(serie: pd.Series, idx: pd.DatetimeIndex,
                             plazos: tuple[int, ...] = (7, 14, 28), q: float = 0.9,
                             minimo: float = 0.5, ventana: int = 500) -> pd.DataFrame:
    """Vencimientos aproximados: días ``h`` corridos después de un salto del factor.

    Salto en ``s``: |F_s| mayor que el cuantil ``q`` de |F| en los ``ventana`` días
    previos (sin incluir ``s``) y mayor que ``minimo`` pp de la base. La indicadora se
    pone en el primer día hábil de ``idx`` igual o posterior a ``s + h``. Como ``h``
    >= 7 días, sólo usa información publicada antes del día pronosticado; no usa el
    monto ni el signo del vencimiento.
    """
    a = serie.abs()
    umbral = a.rolling(ventana, min_periods=60).quantile(q).shift()
    saltos = a.index[((a > umbral) & (a > minimo)).to_numpy()]
    out = pd.DataFrame(0.0, index=idx, columns=[f"vto_{serie.name}_{h}" for h in plazos])
    for h, col in zip(plazos, out.columns):
        pos = idx.searchsorted(saltos + pd.Timedelta(days=h))
        pos = pos[pos < len(idx)]
        out.iloc[np.unique(pos), out.columns.get_loc(col)] = 1.0
    return out


def rasgos_v1(F: pd.DataFrame, rezagos: range = range(1, 6)) -> pd.DataFrame:
    """Factores rezagados por bloque (más circulación y resto) y calendario del Anexo A."""
    bloques = {b: F[list(ids)].sum(axis=1, min_count=len(ids)) for b, ids in BLOQUES.items()}
    bloques["circulacion"] = F["circulacion"]
    bloques["resto"] = F["resto"]
    cols = {f"{b}_l{k}": s.shift(k) for b, s in bloques.items() for k in rezagos}
    X = pd.DataFrame(cols, index=F.index)
    return X.join(variables_calendario(F.index))


def rasgos_v2(F: pd.DataFrame) -> pd.DataFrame:
    """Calendario ampliado e indicadoras de fechas regulares (sin montos del mismo día)."""
    idx = F.index
    X = calendario_ampliado(idx)
    X["pago_55"] = dias_concentrados(F[55], idx)
    X["pago_51"] = dias_concentrados(F[51], idx)
    for k in (52, 53, 58):
        X = X.join(indicadoras_vencimientos(F[k].rename(k), idx))
    return X


def rasgos_v3(F: pd.DataFrame, tesoro_completo: bool = False) -> pd.DataFrame:
    """V2 + factores del Tesoro e intereses del MISMO día. NO FACTIBLE (previsión perfecta)."""
    X = rasgos_v2(F)
    if tesoro_completo:
        X["tesoro_48_51_t"] = F[[48, 49, 50, 51]].sum(axis=1, min_count=4)
    else:
        X["f51_t"] = F[51]
    X["f55_t"] = F[55]
    return X


# --------------------------------------------------------------------------- pronósticos

def pronostico_ols(y: pd.Series, X: pd.DataFrame, inicio_eval: str, desde: str = "2010-01-04",
                   excluir: tuple[str, ...] = (), ventana_resid: int = 250,
                   ventana: int | None = None) -> pd.DataFrame:
    """MCO con ventana expansiva (o móvil) y reestimación diaria; pronóstico a un día.

    Para el día ``t`` se estima con las filas anteriores a ``t`` (menos ``excluir``;
    con ``ventana``, sólo las últimas ``ventana``)
    y se pronostica con ``X_t`` (que, en V1 y V2, sólo contiene información conocida
    antes de ``t``). Intervalo del 90 %: ``pron`` + cuantiles 5 % y 95 % de los
    últimos ``ventana_resid`` residuos de la estimación.
    """
    d = pd.concat([y.rename("y"), X], axis=1, sort=True).loc[desde:].dropna()
    fuera = d.index.isin(pd.to_datetime(list(excluir)))
    Y = d["y"].to_numpy()
    M = np.column_stack([np.ones(len(d)), d.drop(columns="y").to_numpy()])
    n0 = int(d.index.searchsorted(pd.Timestamp(inicio_eval)))
    if n0 < 60:
        raise ValueError("Muy pocos días antes del inicio de la evaluación.")
    filas = []
    for t in range(n0, len(d)):
        tr = np.flatnonzero(~fuera[:t])
        if ventana:
            tr = tr[-ventana:]
        A, b = M[tr], Y[tr]
        activas = np.flatnonzero(A.std(axis=0) > 1e-3)        # descarta columnas ~constantes
        activas = np.union1d([0], activas)
        beta, *_ = np.linalg.lstsq(A[:, activas], b, rcond=None)
        res = (b - A[:, activas] @ beta)[-ventana_resid:]
        pr = float(M[t, activas] @ beta)
        lo, hi = np.quantile(res, [ALFA / 2, 1 - ALFA / 2])
        filas.append((d.index[t], Y[t], pr, pr + lo, pr + hi))
    return pd.DataFrame(filas, columns=["fecha", "obs", "pron", "inf", "sup"]).set_index("fecha")


def pronostico_oraculo(y: pd.Series, F: pd.DataFrame, columnas: list, inicio_eval: str,
                       ventana_resid: int = 250) -> pd.DataFrame:
    """Oráculo contable NO FACTIBLE: el pronóstico es la suma de ``columnas`` del MISMO día.

    Coeficiente 1, sin estimar: por la identidad ``y = sum_k F_k``, es lo que se
    pronosticaría si se conocieran de antemano esos factores y el resto fuera nulo.
    Intervalo: cuantiles de los últimos ``ventana_resid`` errores ya observados.
    """
    pron = F[list(columnas)].sum(axis=1, min_count=len(columnas))
    err = (y - pron).shift()
    out = pd.DataFrame({"obs": y, "pron": pron,
                        "inf": pron + err.rolling(ventana_resid, min_periods=60).quantile(ALFA / 2),
                        "sup": pron + err.rolling(ventana_resid, min_periods=60).quantile(1 - ALFA / 2)})
    return out.dropna(subset=["obs", "pron"]).loc[inicio_eval:]


def pronostico_ingenuo(y: pd.Series, inicio_eval: str, desde: str = "2010-01-04",
                       ventana_resid: int = 250) -> pd.DataFrame:
    """Variación nula; intervalo con los cuantiles 5 % y 95 % de las últimas variaciones."""
    s = y.loc[desde:].dropna()
    q_inf = s.shift().rolling(ventana_resid, min_periods=60).quantile(ALFA / 2)
    q_sup = s.shift().rolling(ventana_resid, min_periods=60).quantile(1 - ALFA / 2)
    out = pd.DataFrame({"obs": s, "pron": 0.0, "inf": q_inf, "sup": q_sup})
    return out.loc[inicio_eval:]


def ensamble_actual(df: pd.DataFrame, inicio_eval: str, desde: str = "2010-01-04",
                    cada: int = 60) -> pd.DataFrame:
    """Ensamble de calendario del Anexo A sobre el nivel de CC, convertido a pp de la base."""
    cc = (df[15] - df[16]).dropna().loc[desde:]
    p = pronostico_fuera_de_muestra(cc, inicio_eval, cada=cada)["ensamble"]
    cc1 = cc.shift().reindex(p.index)
    b1 = df[15].shift().reindex(p.index)
    a_pp = lambda v: 100 * cc1 * (np.exp(v / 100) - 1) / b1          # noqa: E731
    y, _ = a_pp_base(df)
    return pd.DataFrame({"obs": y.reindex(p.index), "pron": a_pp(p["pron"]),
                         "inf": a_pp(p["inf"]), "sup": a_pp(p["sup"])})


# --------------------------------------------------------------------------- evaluación

def evaluar(pronos: dict[str, pd.DataFrame], desde: str | None = None, hasta: str | None = None,
            excluir: tuple[str, ...] = ()) -> pd.DataFrame:
    """MAE, MAE relativo al ingenuo, DM-HLN (vs. ingenuo y vs. ensamble), cobertura y sesgo.

    Todos los modelos se comparan en los mismos días (intersección).
    """
    idx = None
    for d in pronos.values():
        i = d.dropna(subset=["obs", "pron"]).loc[desde:hasta].index
        idx = i if idx is None else idx.intersection(i)
    if excluir:
        idx = idx.difference(pd.to_datetime(list(excluir)))
    e = {m: (d["obs"] - d["pron"]).reindex(idx) for m, d in pronos.items()}
    mae_ing = float(e["ingenuo"].abs().mean())
    filas = {}
    for m, d in pronos.items():
        dd = d.reindex(idx)
        fila = {"n": len(idx), "MAE": float(e[m].abs().mean()),
                "MAE_rel": float(e[m].abs().mean()) / mae_ing,
                "p_DM_ing": np.nan, "p_DM_ens": np.nan, "sesgo": float(e[m].mean())}
        if m != "ingenuo":
            fila["p_DM_ing"] = diebold_mariano(e[m], e["ingenuo"]).p_valor
        if m not in ("ingenuo", "ensamble") and "ensamble" in e:
            fila["p_DM_ens"] = diebold_mariano(e[m], e["ensamble"]).p_valor
        ci = dd.dropna(subset=["inf", "sup"])
        fila["cobertura"] = float(((ci["obs"] >= ci["inf"]) & (ci["obs"] <= ci["sup"])).mean())
        filas[m] = fila
    return pd.DataFrame(filas).T


def sesgos(pronos: dict[str, pd.DataFrame], desde: str | None = None) -> str:
    """Sesgo medio por posición en el mes y los tres días del mes con mayor |sesgo|."""
    lineas = []
    for m, d in pronos.items():
        e = (d["obs"] - d["pron"]).loc[desde:].dropna()
        p = _posiciones(e.index)
        g = np.where(p["pos_fin"] <= 2, "fin", np.where(p["pos"] <= 2, "inicio", "resto"))
        sp = e.groupby(g).mean()
        sd = sesgo_por_dia(e)
        top = sd.abs().sort_values(ascending=False).head(3).index
        lineas.append(f"  {m:<10} inicio {sp.get('inicio', np.nan):+.2f}, fin {sp.get('fin', np.nan):+.2f}, "
                      f"resto {sp.get('resto', np.nan):+.2f}; días con mayor |sesgo|: "
                      + ", ".join(f"{k}: {sd[k]:+.2f}" for k in top))
    return "\n".join(lineas)


def correr_variantes(df: pd.DataFrame, inicio_eval: str = "2022-01-03",
                     desde: str = "2010-01-04", excluir: tuple[str, ...] = (),
                     con_ensamble: bool = True, cada_ensamble: int = 60,
                     movil: int | None = 500) -> dict[str, pd.DataFrame]:
    """Pronósticos fuera de muestra: ingenuo, ensamble, V1, V2, V3 y oráculos contables.

    Sensibilidades: V1 con rezago de publicación (t-2 a t-6) y, si ``movil``, V1-V3
    con ventana móvil de ``movil`` días hábiles. Los rótulos ``_NF`` son NO FACTIBLES.
    """
    y, F = a_pp_base(df)
    y = y.loc[F.dropna().index]                 # días con factores publicados
    pr = {"ingenuo": pronostico_ingenuo(y, inicio_eval, desde)}
    if con_ensamble:
        pr["ensamble"] = ensamble_actual(df, inicio_eval, desde, cada_ensamble)
    pr["V1"] = pronostico_ols(y, rasgos_v1(F), inicio_eval, desde, excluir)
    pr["V1_rez2"] = pronostico_ols(y, rasgos_v1(F, range(2, 7)), inicio_eval, desde, excluir)
    pr["V2"] = pronostico_ols(y, rasgos_v2(F), inicio_eval, desde, excluir)
    pr["V3_NF"] = pronostico_ols(y, rasgos_v3(F), inicio_eval, desde, excluir)
    pr["V3b_NF"] = pronostico_ols(y, rasgos_v3(F, True), inicio_eval, desde, excluir)
    if movil:
        pr["V1_movil"] = pronostico_ols(y, rasgos_v1(F), inicio_eval, desde, excluir, ventana=movil)
        pr["V2_movil"] = pronostico_ols(y, rasgos_v2(F), inicio_eval, desde, excluir, ventana=movil)
        pr["V3_movil_NF"] = pronostico_ols(y, rasgos_v3(F), inicio_eval, desde, excluir,
                                           ventana=movil)
    pr["O51_55_NF"] = pronostico_oraculo(y, F, [51, 55], inicio_eval)
    pr["OTes_NF"] = pronostico_oraculo(y, F, [48, 49, 50, 51, 55], inicio_eval)
    pr["O59_NF"] = pronostico_oraculo(y, F, [59], inicio_eval)
    return pr


# --------------------------------------------------------------------------- datos sintéticos

def demo_factores(n_dias: int = 900, semilla: int = 426) -> pd.DataFrame:
    """Base, circulación y factores diarios. DATOS SINTÉTICOS DE DEMOSTRACIÓN, NO OFICIALES.

    Estructura conocida para probar la lógica: el Tesoro (51) es grande, de colas
    pesadas, con una licitación en los días hábiles 12-13; los intereses (55) se
    pagan sobre todo el primer día hábil; "otras" (59) revierte la mitad al día
    siguiente; las compras de divisas (47) son persistentes; los pases (52) tienen
    colocaciones que vencen a los 7 días corridos.
    """
    rng = np.random.default_rng(semilla)
    idx = pd.bdate_range("2019-01-02", periods=n_dias)
    p = _posiciones(idx)
    f = {k: np.zeros(n_dias) for k in FACTORES}
    B, C = np.empty(n_dias), np.empty(n_dias)
    B[0], C[0] = 1.0e6, 6.0e5
    vence: dict[pd.Timestamp, float] = {}
    o_prev = d_prev = 0.0
    for t in range(1, n_dias):
        b1 = B[t - 1] / 100                                  # 1 pp de la base, en millones
        lic = -2.0 if p["pos"].iloc[t] in (12, 13) else 0.0
        f[51][t] = b1 * (lic + 0.8 * rng.standard_t(3))
        f[55][t] = b1 * (1.5 if p["pos"].iloc[t] == 1 else 0.2)
        o = -0.5 * o_prev + rng.normal(0, 1.0)
        f[59][t], o_prev = b1 * o, o
        dv = 0.6 * d_prev + rng.normal(0, 0.3)
        f[47][t], d_prev = b1 * dv, dv
        pase = 0.0
        if rng.random() < 0.15:
            monto = rng.normal(0, 2.0)
            pase += monto
            vence[idx[min(idx.searchsorted(idx[t] + pd.Timedelta(days=7)), n_dias - 1)]] = -monto
        pase += vence.pop(idx[t], 0.0)
        f[52][t] = b1 * pase
        dC = b1 * (0.4 * (p["pos_fin"].iloc[t] <= 2) - 0.2 * (p["pos"].iloc[t] <= 2)
                   + rng.normal(0, 0.15))
        B[t] = B[t - 1] + sum(v[t] for v in f.values())
        C[t] = C[t - 1] + dC
    df = pd.DataFrame({k: v for k, v in f.items()}, index=idx)
    df[15], df[16] = B, C
    df[19] = B - C
    df[46] = df[list(FACTORES)].sum(axis=1)
    df.iloc[0, [df.columns.get_loc(k) for k in (*FACTORES, 46)]] = np.nan
    df.index.name = "fecha"
    return df[[15, 16, 19, 46, *FACTORES]]


# --------------------------------------------------------------------------- informe

def _tabla(ev: pd.DataFrame) -> str:
    t = ev.copy()
    t["n"] = t["n"].astype(int)
    return t.to_string(float_format=lambda v: f"{v:.3f}")


def informe(df: pd.DataFrame, rotulo: str, inicio_eval: str = "2022-01-03",
            desde: str = "2010-01-04", con_ensamble: bool = True,
            tramos: bool = True) -> str:
    """Informe completo: identidades, descomposición, resultados y sesgos."""
    y, F = a_pp_base(df)
    ult = F.dropna().index.max()
    L = [f"[{rotulo}]", f"Ejecución: {datetime.now():%Y-%m-%d %H:%M}. Último dato de factores: "
         f"{ult:%Y-%m-%d}; de la base: {df[15].dropna().index.max():%Y-%m-%d}.", "",
         "1. Identidades contables (millones de ARS)", texto_identidades(verificar_identidades(df)), "",
         "2. Descomposición de la varianza diaria de CC = 15 - 16 (pp de la base del día previo)",
         "   participación = cov(F_k, dCC) / var(dCC) (suma 1); varianza propia = var(F_k)/var(dCC)"]
    periodos = [(inicio_eval, None, ()), (inicio_eval, None, (FECHA_LEFI,)),
                ("2025-07-11", None, ())] if tramos else [(inicio_eval, None, ())]
    for a, b, ex in periodos:
        t = descomponer_por_factor(y, F, a, b, ex)
        t = t[(t["varianza_propia"] > 1e-6)].sort_values("participacion", ascending=False)
        t.index = [f"{k} {NOMBRES[k]}" for k in t.index]
        L += [f"   {t.attrs['desde']:%Y-%m-%d} a {t.attrs['hasta']:%Y-%m-%d}, n = {t.attrs['n']}"
              + (f", sin {', '.join(ex)}" if ex else "")
              + f"; suma de varianzas propias = {t['varianza_propia'].sum():.1f}",
              t.round(3).to_string()]
    L += ["   Correlación de dCC con cada factor del mismo día (y entre 50 y 51):"]
    for a in (inicio_eval, "2025-07-11") if tramos else (inicio_eval,):
        Z = F.loc[a:].dropna()
        yy = y.reindex(Z.index)
        cs = {k: yy.corr(Z[k]) for k in (51, 55, 59) if Z[k].std() > 0}
        cs["48-51"] = yy.corr(Z[[48, 49, 50, 51]].sum(axis=1))
        L.append(f"   desde {a}: " + ", ".join(f"{k}: {v:+.2f}" for k, v in cs.items())
                 + (f"; corr(50, 51) = {Z[50].corr(Z[51]):+.2f}" if Z[50].std() > 0 else ""))
    ini, fin = posiciones_concentradas(F[55].loc[:inicio_eval].iloc[-500:])
    ini51, fin51 = posiciones_concentradas(F[51].loc[:inicio_eval].iloc[-500:])
    L += ["", "3. Pronóstico a un día de dCC, fuera de muestra (MCO expansivo desde "
          f"{desde}, reestimación diaria)",
          f"   Días concentrados inferidos al {inicio_eval} (500 días previos): 55 inicio {sorted(ini)}, "
          f"fin {sorted(fin)}; 51 inicio {sorted(ini51)}, fin {sorted(fin51)}",
          "   V1: factores por bloque en t-1..t-5 + calendario; V1_rez2: t-2..t-6 (rezago de "
          "publicación); V2: calendario ampliado + días concentrados (55, 51) + vencimientos "
          "aproximados (52, 53, 58); V3_NF / V3b_NF: V2 + 51 y 55 del mismo día / bloque "
          "Tesoro 48-51 y 55 del mismo día: NO FACTIBLE (previsión perfecta, cota superior, "
          "coeficientes estimados); *_movil: ventana móvil de 500 días hábiles; O51_55_NF, "
          "OTes_NF (48-51 y 55), O59_NF: oráculo contable NO FACTIBLE (pronóstico = suma de "
          "esos factores del mismo día, coeficiente 1, sin estimar).",
          "   p_DM_*: DM-HLN unilateral (H1: el modelo tiene menor error absoluto) contra el "
          "ingenuo / el ensamble del Anexo A; cobertura del intervalo del 90 %."]
    pr = correr_variantes(df, inicio_eval, desde, con_ensamble=con_ensamble)
    tramos_ev = [("desde " + inicio_eval, inicio_eval, ())]
    if tramos:
        tramos_ev += [("desde 2025-07-11", "2025-07-11", ())]
    for nombre, a, ex in tramos_ev:
        L += [f"   [{nombre}]", _tabla(evaluar(pr, a, excluir=ex))]
    if tramos:
        pr_sin = correr_variantes(df, inicio_eval, desde, excluir=(FECHA_LEFI,),
                                  con_ensamble=False)
        pr_sin["ensamble"] = pr["ensamble"] if con_ensamble else None
        pr_sin = {k: v for k, v in pr_sin.items() if v is not None}
        L += [f"   [sensibilidad: sin el {FECHA_LEFI} en la estimación y en la evaluación; "
              "el ensamble sólo se excluye de la evaluación]",
              _tabla(evaluar(pr_sin, inicio_eval, excluir=(FECHA_LEFI,)))]
    L += ["   Sesgo medio (obs - pron, pp de la base) por posición y por día del mes:",
          sesgos(pr, inicio_eval)]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> str:
    """Punto de entrada de línea de comandos."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--demo", action="store_true", help="datos sintéticos de demostración")
    g.add_argument("--reales", action="store_true", help="CSV de datos/ (API BCRA v4.0)")
    ap.add_argument("--salida", type=Path, default=None, help="archivo de texto de salida")
    ap.add_argument("--inicio-eval", default=None)
    a = ap.parse_args(argv)
    if a.demo:
        df = demo_factores()
        texto = informe(df, ROTULO_SINTETICO, a.inicio_eval or "2021-10-01", desde="2019-01-02",
                        con_ensamble=False, tramos=False)
    else:
        df = cargar_factores()
        texto = informe(df, ROTULO_REAL.format(descarga=fechas_descarga()),
                        a.inicio_eval or "2022-01-03")
    print(texto)
    if a.salida:
        a.salida.write_text(texto + "\n", encoding="utf-8")
    return texto


if __name__ == "__main__":
    main()
