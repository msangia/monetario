"""Anexo A (Eje 1): pronóstico diario de liquidez/base con efectos de calendario.

Variable pronosticada: variación diaria (%) del nivel, 100 * diff(log(nivel)),
a un día hábil. Modelos:

* ``ingenuo``   (benchmark): variación nula, el nivel de mañana es el de hoy;
* ``deriva``    (benchmark auxiliar): variación media del período de estimación
  (paseo al azar con deriva); separa la ganancia por calendario de la que sólo
  refleja el crecimiento nominal medio;
* ``regresion``: MCO sobre variables de calendario;
* ``arimax``:    AR(1) con las mismas variables exógenas (espacio de estado, SARIMAX);
* ``ensamble``:  promedio simple de ``regresion`` y ``arimax``.

Evaluación fuera de muestra con ventana expansiva (o móvil): los parámetros se
reestiman cada ``cada`` días con información disponible hasta ese momento
(sin *look-ahead*); el calendario es conocido de antemano.

Uso::

    python -m monetario_demo.liquidez --demo
    python -m monetario_demo.liquidez --csv 15 --desde 2010-01-04 --inicio-eval 2022-01-03
"""

from __future__ import annotations

import argparse
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.statespace.sarimax import SARIMAX

from .datos import ROTULO_SINTETICO, cargar_csv, demo_liquidez_diaria, posicion_en_mes
from .evaluacion import diebold_mariano, sesgo_por_dia, tabla_errores

ALFA = 0.10  # intervalos al 90 %


def variables_calendario(idx: pd.DatetimeIndex) -> pd.DataFrame:
    """Variables de calendario conocidas de antemano para cada día hábil.

    ``ini_mes``/``fin_mes``: dos primeros/últimos días hábiles del mes;
    ``quincena``: días 14 a 16; ``aguinaldo``: segunda quincena de junio y
    diciembre; ``diciembre``; ``lunes``. Las posiciones en el mes se calculan
    sobre los días observados de la serie (con datos reales, los días hábiles
    efectivos: los feriados no aparecen, y el calendario de feriados se conoce de
    antemano, por lo que no hay *look-ahead*). Fuera del rango observado (el mes
    inicial y el final incompletos) se completa con días de lunes a viernes, para
    que una muestra que termina a mitad de mes no marque fin de mes.
    """
    un_dia = pd.Timedelta(days=1)
    antes = pd.bdate_range(idx.min().replace(day=1), idx.min() - un_dia)
    despues = pd.bdate_range(idx.max() + un_dia, idx.max() + pd.offsets.MonthEnd(0))
    completo = antes.union(idx).union(despues)
    pos, pos_fin = posicion_en_mes(completo)
    p = pd.DataFrame({"pos": pos, "pos_fin": pos_fin}, index=completo).loc[idx]
    return pd.DataFrame({
        "ini_mes": (p["pos"] <= 2).astype(float),
        "fin_mes": (p["pos_fin"] <= 2).astype(float),
        "quincena": ((idx.day >= 14) & (idx.day <= 16)).astype(float),
        "aguinaldo": (np.isin(idx.month, [6, 12]) & (idx.day >= 15)).astype(float),
        "diciembre": (idx.month == 12).astype(float),
        "lunes": (idx.dayofweek == 0).astype(float),
    }, index=idx)


def pronostico_fuera_de_muestra(nivel: pd.Series, inicio_eval: float | str = 0.5,
                                cada: int = 60,
                                ventana: int | None = None) -> dict[str, pd.DataFrame]:
    """Pronósticos a un día, fuera de muestra, de los cuatro modelos.

    Args:
        nivel: serie diaria en niveles (p. ej., base monetaria), días hábiles.
        inicio_eval: fracción de la muestra usada en la primera estimación, o fecha
            (``"AAAA-MM-DD"``) del primer día evaluado.
        cada: cada cuántos días se reestiman los parámetros.
        ventana: ``None`` = ventana expansiva (todo el pasado); un entero = ventana
            móvil con los últimos ``ventana`` días (se adapta antes a cambios de régimen).

    Returns:
        dict modelo -> DataFrame con columnas ``obs``, ``pron``, ``inf``, ``sup``.
    """
    y = (100 * np.log(nivel).diff()).dropna().rename("var_pct")
    X = sm.add_constant(variables_calendario(y.index))
    if isinstance(inicio_eval, (str, pd.Timestamp)):
        n0 = int(y.index.searchsorted(pd.Timestamp(inicio_eval)))
    else:
        n0 = int(len(y) * inicio_eval)
    if not 30 <= n0 < len(y):
        raise ValueError(f"Inicio de la evaluación fuera de rango ({n0} de {len(y)} días).")
    salida: dict[str, list[pd.DataFrame]] = {
        m: [] for m in ("ingenuo", "deriva", "regresion", "arimax")}
    for t0 in range(n0, len(y), cada):
        t1 = min(t0 + cada, len(y))
        a0 = 0 if ventana is None else max(0, t0 - ventana)
        y_tr, X_tr, X_te = y.iloc[a0:t0], X.iloc[a0:t0], X.iloc[t0:t1]
        obs = y.iloc[t0:t1]
        # Benchmark ingenuo: variación nula; intervalo con el cuantil 90 % de |var| pasada.
        q = float(np.quantile(np.abs(y_tr), 1 - ALFA))
        salida["ingenuo"].append(pd.DataFrame({"obs": obs, "pron": 0.0, "inf": -q, "sup": q}))
        # Deriva: media del período de estimación; intervalo con cuantiles de sus errores.
        mu = float(y_tr.mean())
        qd = float(np.quantile(np.abs(y_tr - mu), 1 - ALFA))
        salida["deriva"].append(pd.DataFrame({"obs": obs, "pron": mu,
                                              "inf": mu - qd, "sup": mu + qd}))
        # Regresión con efectos de calendario.
        mco = sm.OLS(y_tr, X_tr).fit()
        pr = mco.get_prediction(X_te).summary_frame(alpha=ALFA)
        salida["regresion"].append(pd.DataFrame({
            "obs": obs, "pron": pr["mean"].to_numpy(),
            "inf": pr["obs_ci_lower"].to_numpy(), "sup": pr["obs_ci_upper"].to_numpy()},
            index=obs.index))
        # ARIMAX: parámetros estimados hasta t0, filtrado un paso adelante en [t0, t1).
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # Se usan arreglos (no fechas) porque los días hábiles reales tienen feriados.
            ex_tr = X_tr.drop(columns="const").to_numpy()
            ex_te = X_te.drop(columns="const").to_numpy()
            res = SARIMAX(y_tr.to_numpy(), exog=ex_tr, order=(1, 0, 0), trend="c").fit(disp=False)
            res_ext = res.append(obs.to_numpy(), exog=ex_te)
        n_tr = len(y_tr)
        pa = res_ext.get_prediction(start=n_tr, end=n_tr + (t1 - t0) - 1)
        ci = np.asarray(pa.conf_int(alpha=ALFA))
        salida["arimax"].append(pd.DataFrame({
            "obs": obs, "pron": np.asarray(pa.predicted_mean),
            "inf": ci[:, 0], "sup": ci[:, 1]}, index=obs.index))
    out = {m: pd.concat(v) for m, v in salida.items()}
    # Ensamble: promedio simple de puntos y de límites (simplificación documentada).
    out["ensamble"] = (out["regresion"] + out["arimax"]) / 2
    out["ensamble"]["obs"] = out["regresion"]["obs"]
    return out


def evaluar(pronos: dict[str, pd.DataFrame], ultimos: int | None = None,
            desde: str | None = None) -> dict[str, object]:
    """Tabla de errores, sesgo por día del mes y test DM (ensamble vs. ingenuo).

    ``ultimos`` restringe la evaluación a los últimos N días (p. ej., 60, como
    la corrida en paralelo del indicador (i) del proyecto); ``desde`` la restringe a
    un subperíodo (p. ej., un régimen operativo); los pronósticos no cambian.
    """
    if desde:
        pronos = {m: d.loc[desde:] for m, d in pronos.items()}
    if ultimos:
        pronos = {m: d.iloc[-ultimos:] for m, d in pronos.items()}
    obs = pronos["ingenuo"]["obs"]
    tabla = tabla_errores(obs, {m: d["pron"] for m, d in pronos.items()},
                          {m: (d["inf"], d["sup"]) for m, d in pronos.items()})
    e_ens = obs - pronos["ensamble"]["pron"]
    e_ing = obs - pronos["ingenuo"]["pron"]
    dm = diebold_mariano(e_ens, e_ing, h=1, perdida="abs", alternativa="menor")
    dm_der = (diebold_mariano(e_ens, obs - pronos["deriva"]["pron"], h=1, perdida="abs",
                              alternativa="menor") if "deriva" in pronos else None)
    cal = variables_calendario(obs.index)
    grupo = np.where(cal["fin_mes"] == 1, "fin de mes",
                     np.where(cal["ini_mes"] == 1, "inicio de mes", "resto"))
    sesgo_pos = pd.DataFrame({"ensamble": e_ens.groupby(grupo).mean(),
                              "ingenuo": e_ing.groupby(grupo).mean()})
    return {"tabla": tabla, "dm": dm, "dm_deriva": dm_der, "sesgo_posicion": sesgo_pos,
            "sesgo_dia": sesgo_por_dia(e_ens), "n": len(obs),
            "periodo": (obs.index[0], obs.index[-1])}


def informe(ev: dict[str, object], rotulo: str) -> str:
    """Texto breve con los resultados (para consola y para el anexo)."""
    dm = ev["dm"]
    sd = ev["sesgo_dia"].abs().sort_values(ascending=False).head(3)
    obs_ini, obs_fin = ev.get("periodo", (None, None))
    periodo = f" ({obs_ini:%Y-%m-%d} a {obs_fin:%Y-%m-%d})" if obs_ini is not None else ""
    lineas = [f"[{rotulo}]", f"Evaluación fuera de muestra, 1 día, n = {ev['n']}{periodo}",
              ev["tabla"].round(3).to_string(),
              f"DM-HLN ensamble vs. ingenuo (pérdida abs., H1: ensamble mejor): "
              f"est. = {dm.estadistico:.2f}, p = {dm.p_valor:.3f} -> "
              + ("rechaza igualdad al 10 %" if dm.rechaza(0.10) else "no rechaza al 10 %")
              + (" (n >= 60: cumple)" if dm.n >= 60 else " (n < 60: no cumple el mínimo)"),
              *([f"DM-HLN ensamble vs. deriva: est. = {ev['dm_deriva'].estadistico:.2f}, "
                 f"p = {ev['dm_deriva'].p_valor:.3f}"] if ev.get("dm_deriva") else []),
              "Sesgo medio por posición en el mes (pp):",
              ev["sesgo_posicion"].round(3).to_string(),
              "Días del mes con mayor |sesgo| del ensamble (pp): "
              + ", ".join(f"día {d}: {ev['sesgo_dia'][d]:+.2f}" for d in sd.index)]
    return "\n".join(lineas)


def descomponer_varianza(base: pd.Series, circulacion: pd.Series) -> dict[str, float]:
    """Participación de cada componente en la varianza de la variación diaria de la base.

    Base = circulación monetaria (16) + cuentas corrientes de las entidades en el BCRA
    (15 - 16). Las variaciones se miden en % de la base del día anterior, así que
    var(dB) = var(dC) + var(dCC) + 2 cov(dC, dCC) y las tres partes suman 1.
    """
    cc = base - circulacion
    previo = base.shift()
    d = pd.DataFrame({"dB": base.diff(), "dC": circulacion.diff(), "dCC": cc.diff()})
    d = d.div(previo, axis=0).mul(100).dropna()
    v = d["dB"].var()
    return {"circulacion": float(d["dC"].var() / v), "cuentas_corrientes": float(d["dCC"].var() / v),
            "covarianza": float(2 * d["dC"].cov(d["dCC"]) / v), "n": len(d)}


def pronostico_por_componentes(base: pd.Series, circulacion: pd.Series,
                               inicio_eval: str, cada: int = 60, ventana: int | None = None,
                               cc_modelo: str = "ingenuo", ventana_error: int = 250,
                               minimo_error: int = 60) -> pd.DataFrame:
    """Pronóstico de la variación de la base sumando el de sus componentes (sin *look-ahead*).

    La circulación (16) se pronostica con el ensamble de calendario; las cuentas
    corrientes en el BCRA (15 - 16) con el ingenuo (``cc_modelo="ingenuo"``) o con
    el ensamble (``"ensamble"``). Se suman en millones y se pasan a % de la base del
    día anterior. El intervalo del 90 % sale de los cuantiles de los últimos
    ``ventana_error`` errores fuera de muestra ya observados (NaN mientras haya menos
    de ``minimo_error``).

    Returns:
        DataFrame con ``obs``, ``pron``, ``inf``, ``sup`` (variación % de la base).
    """
    base, circulacion = base.align(circulacion, join="inner")
    cc = base - circulacion
    p_c = pronostico_fuera_de_muestra(circulacion, inicio_eval, cada, ventana)["ensamble"]
    idx = p_c.index
    b_1, c_1, cc_1 = (s.shift().reindex(idx) for s in (base, circulacion, cc))
    delta = c_1 * (np.exp(p_c["pron"] / 100) - 1)
    if cc_modelo == "ensamble":
        p_cc = pronostico_fuera_de_muestra(cc, inicio_eval, cada, ventana)["ensamble"]
        delta = delta + cc_1 * (np.exp(p_cc["pron"].reindex(idx) / 100) - 1)
    elif cc_modelo != "ingenuo":
        raise ValueError("cc_modelo debe ser 'ingenuo' o 'ensamble'")
    pron = 100 * np.log1p(delta / b_1)
    obs = (100 * np.log(base).diff()).reindex(idx)
    err = obs - pron
    previos = err.shift()                                   # sólo errores ya observados
    q_inf = previos.rolling(ventana_error, min_periods=minimo_error).quantile(ALFA / 2)
    q_sup = previos.rolling(ventana_error, min_periods=minimo_error).quantile(1 - ALFA / 2)
    return pd.DataFrame({"obs": obs, "pron": pron, "inf": pron + q_inf, "sup": pron + q_sup})


def evaluar_contra_ingenuo(modelo: pd.DataFrame, ingenuo: pd.DataFrame,
                           desde: str | None = None, ultimos: int | None = None) -> dict:
    """MAE relativo al ingenuo, DM-HLN unilateral y cobertura (días con intervalo)."""
    m, g = modelo.loc[desde:], ingenuo.loc[desde:]
    if ultimos:
        m, g = m.iloc[-ultimos:], g.iloc[-ultimos:]
    e_m, e_g = m["obs"] - m["pron"], g["obs"] - g["pron"]
    con_int = m.dropna(subset=["inf", "sup"])
    dm = diebold_mariano(e_m, e_g, h=1, perdida="abs", alternativa="menor")
    return {"n": len(m), "MAE_rel": float(e_m.abs().mean() / e_g.abs().mean()),
            "p_DM": dm.p_valor,
            "cobertura": float(((con_int["obs"] >= con_int["inf"])
                                & (con_int["obs"] <= con_int["sup"])).mean())}


def main(argv: list[str] | None = None) -> str:
    """Punto de entrada de línea de comandos."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--demo", action="store_true", help="usa datos sintéticos de demostración")
    g.add_argument("--csv", help="CSV diario fecha,valor (nivel de la base o de la liquidez)")
    ap.add_argument("--cada", type=int, default=60, help="reestimación cada N días")
    ap.add_argument("--ultimos", type=int, default=None, help="evaluar sólo los últimos N días")
    ap.add_argument("--ventana", type=int, default=None,
                    help="ventana móvil de N días (por defecto, expansiva)")
    ap.add_argument("--desde", default=None, help="primer día de la muestra (AAAA-MM-DD)")
    ap.add_argument("--inicio-eval", default=None,
                    help="primer día evaluado (AAAA-MM-DD); por defecto, mitad de la muestra")
    a = ap.parse_args(argv)
    if a.demo:
        nivel, rotulo = demo_liquidez_diaria(), ROTULO_SINTETICO
    else:
        nivel, rotulo = cargar_csv(a.csv), f"Datos: {a.csv}"
    if a.desde:
        nivel = nivel.loc[a.desde:]
    pronos = pronostico_fuera_de_muestra(nivel, a.inicio_eval or 0.5, cada=a.cada,
                                         ventana=a.ventana)
    texto = informe(evaluar(pronos, a.ultimos), rotulo)
    print(texto)
    return texto


if __name__ == "__main__":
    main()
