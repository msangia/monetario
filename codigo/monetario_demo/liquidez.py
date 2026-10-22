"""Anexo A (Eje 1): pronóstico diario de liquidez/base con efectos de calendario.

Variable pronosticada: variación diaria (%) del nivel, 100 * diff(log(nivel)),
a un día hábil. Modelos:

* ``ingenuo``   (benchmark): variación nula, el nivel de mañana es el de hoy;
* ``regresion``: MCO sobre variables de calendario;
* ``arimax``:    AR(1) con las mismas variables exógenas (espacio de estado, SARIMAX);
* ``ensamble``:  promedio simple de ``regresion`` y ``arimax``.

Evaluación fuera de muestra con ventana expansiva: los parámetros se
reestiman cada ``cada`` días con información disponible hasta ese momento
(sin *look-ahead*); el calendario es conocido de antemano.

Uso::

    python -m monetario_demo.liquidez --demo
    python -m monetario_demo.liquidez --csv datos/base_monetaria_diaria.csv
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
    sobre días hábiles de lunes a viernes (sin feriados) completando el último
    mes, para que una muestra que termina a mitad de mes no marque fin de mes.
    """
    completo = pd.bdate_range(idx.min().replace(day=1), idx.max() + pd.offsets.MonthEnd(0))
    completo = completo.union(idx)
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


def pronostico_fuera_de_muestra(nivel: pd.Series, inicio_eval: float = 0.5,
                                cada: int = 60) -> dict[str, pd.DataFrame]:
    """Pronósticos a un día, fuera de muestra, de los cuatro modelos.

    Args:
        nivel: serie diaria en niveles (p. ej., base monetaria), días hábiles.
        inicio_eval: fracción de la muestra usada en la primera estimación.
        cada: cada cuántos días se reestiman los parámetros.

    Returns:
        dict modelo -> DataFrame con columnas ``obs``, ``pron``, ``inf``, ``sup``.
    """
    y = (100 * np.log(nivel).diff()).dropna().rename("var_pct")
    X = sm.add_constant(variables_calendario(y.index))
    n0 = int(len(y) * inicio_eval)
    salida: dict[str, list[pd.DataFrame]] = {m: [] for m in ("ingenuo", "regresion", "arimax")}
    for t0 in range(n0, len(y), cada):
        t1 = min(t0 + cada, len(y))
        y_tr, X_tr, X_te = y.iloc[:t0], X.iloc[:t0], X.iloc[t0:t1]
        obs = y.iloc[t0:t1]
        # Benchmark ingenuo: variación nula; intervalo con el cuantil 90 % de |var| pasada.
        q = float(np.quantile(np.abs(y_tr), 1 - ALFA))
        salida["ingenuo"].append(pd.DataFrame({"obs": obs, "pron": 0.0, "inf": -q, "sup": q}))
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
        pa = res_ext.get_prediction(start=t0, end=t1 - 1)
        ci = np.asarray(pa.conf_int(alpha=ALFA))
        salida["arimax"].append(pd.DataFrame({
            "obs": obs, "pron": np.asarray(pa.predicted_mean),
            "inf": ci[:, 0], "sup": ci[:, 1]}, index=obs.index))
    out = {m: pd.concat(v) for m, v in salida.items()}
    # Ensamble: promedio simple de puntos y de límites (simplificación documentada).
    out["ensamble"] = (out["regresion"] + out["arimax"]) / 2
    out["ensamble"]["obs"] = out["regresion"]["obs"]
    return out


def evaluar(pronos: dict[str, pd.DataFrame], ultimos: int | None = None) -> dict[str, object]:
    """Tabla de errores, sesgo por día del mes y test DM (ensamble vs. ingenuo).

    ``ultimos`` restringe la evaluación a los últimos N días (p. ej., 60, como
    la corrida en paralelo del indicador (i) del proyecto).
    """
    if ultimos:
        pronos = {m: d.iloc[-ultimos:] for m, d in pronos.items()}
    obs = pronos["ingenuo"]["obs"]
    tabla = tabla_errores(obs, {m: d["pron"] for m, d in pronos.items()},
                          {m: (d["inf"], d["sup"]) for m, d in pronos.items()})
    e_ens = obs - pronos["ensamble"]["pron"]
    e_ing = obs - pronos["ingenuo"]["pron"]
    dm = diebold_mariano(e_ens, e_ing, h=1, perdida="abs", alternativa="menor")
    cal = variables_calendario(obs.index)
    grupo = np.where(cal["fin_mes"] == 1, "fin de mes",
                     np.where(cal["ini_mes"] == 1, "inicio de mes", "resto"))
    sesgo_pos = pd.DataFrame({"ensamble": e_ens.groupby(grupo).mean(),
                              "ingenuo": e_ing.groupby(grupo).mean()})
    return {"tabla": tabla, "dm": dm, "sesgo_posicion": sesgo_pos,
            "sesgo_dia": sesgo_por_dia(e_ens), "n": len(obs)}


def informe(ev: dict[str, object], rotulo: str) -> str:
    """Texto breve con los resultados (para consola y para el anexo)."""
    dm = ev["dm"]
    lineas = [f"[{rotulo}]", f"Evaluación fuera de muestra, 1 día, n = {ev['n']}",
              ev["tabla"].round(3).to_string(),
              f"DM-HLN ensamble vs. ingenuo (pérdida abs., H1: ensamble mejor): "
              f"est. = {dm.estadistico:.2f}, p = {dm.p_valor:.3f} -> "
              + ("rechaza igualdad al 10 %" if dm.rechaza(0.10) else "no rechaza al 10 %")
              + (" (n >= 60: cumple)" if dm.n >= 60 else " (n < 60: no cumple el mínimo)"),
              "Sesgo medio por posición en el mes (pp):",
              ev["sesgo_posicion"].round(3).to_string()]
    return "\n".join(lineas)


def main(argv: list[str] | None = None) -> str:
    """Punto de entrada de línea de comandos."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--demo", action="store_true", help="usa datos sintéticos de demostración")
    g.add_argument("--csv", help="CSV diario fecha,valor (nivel de la base o de la liquidez)")
    ap.add_argument("--cada", type=int, default=60, help="reestimación cada N días")
    ap.add_argument("--ultimos", type=int, default=None, help="evaluar sólo los últimos N días")
    a = ap.parse_args(argv)
    if a.demo:
        nivel, rotulo = demo_liquidez_diaria(), ROTULO_SINTETICO
    else:
        nivel, rotulo = cargar_csv(a.csv), f"Datos: {a.csv}"
    texto = informe(evaluar(pronostico_fuera_de_muestra(nivel, cada=a.cada), a.ultimos), rotulo)
    print(texto)
    return texto


if __name__ == "__main__":
    main()
