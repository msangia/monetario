"""Anexo B (Eje 4): demanda de dinero con corrección de errores en ventanas móviles.

Engle-Granger en dos pasos, mensual:

1. Largo plazo (MCO en niveles): m_t = c + b_y y_t + b_i i_t + u_t, con
   m = log del dinero real (base o M2 privado deflactado por IPC),
   y = log de la actividad (EMAE) e i = costo de oportunidad (tanto por uno).
   Cointegración: test de Engle-Granger (``statsmodels.tsa.stattools.coint``).
2. Corto plazo (MCE): dm_t = a + g u_{t-1} + d_y dy_t + d_i di_t + r dm_{t-1} + e_t;
   g < 0 es la velocidad de ajuste al equilibrio.

Inestabilidad: se reestima en ventanas móviles y se marca un coeficiente de
largo plazo como inestable cuando se aleja del de la primera ventana más que
un umbral *simulado bajo estabilidad*: con los regresores observados, los
coeficientes de la primera ventana y un error AR(1) ajustado en ella, se
generan ``B`` muestras artificiales sin quiebre y el umbral es el cuantil
``nivel`` de la máxima desviación entre ventanas. Así, la probabilidad de
falsa alarma en toda la muestra es de alrededor de 1 - ``nivel`` por
coeficiente (bootstrap paramétrico; no se usan los errores estándar de MCO,
que en regresiones cointegrantes no tienen distribución estándar). Como
contraste complementario se informa el CUSUM de residuos MCO del MCE de
muestra completa, que capta inestabilidad de corto plazo.

Uso::

    python -m monetario_demo.demanda_dinero --demo
    python -m monetario_demo.demanda_dinero --dinero datos/m2_privado_mensual.csv \
        --precios datos/ipc_mensual.csv --actividad datos/emae_mensual.csv \
        --tasa datos/tasa_plazo_fijo_mensual.csv
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import breaks_cusumolsresid
from statsmodels.tsa.stattools import coint

from .datos import ROTULO_SINTETICO, a_mensual, cargar_csv, demo_demanda_dinero


def engle_granger(df: pd.DataFrame) -> dict[str, float]:
    """Estima los dos pasos de Engle-Granger sobre ``df`` (``m_real``, ``y``, ``i``).

    Returns:
        dict con ``b_y``, ``b_i``, sus errores estándar HAC (``se_y``, ``se_i``),
        ``p_coint`` (Engle-Granger), ``g`` (ajuste) y ``t_g``.
    """
    X = sm.add_constant(df[["y", "i"]])
    lp = sm.OLS(df["m_real"], X).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    u = lp.resid
    p_coint = float(coint(df["m_real"], df[["y", "i"]], trend="c")[1])
    d = df.diff()
    Z = pd.DataFrame({"u_1": u.shift(1), "dy": d["y"], "di": d["i"],
                      "dm_1": d["m_real"].shift(1)})
    datos = pd.concat([d["m_real"].rename("dm"), Z], axis=1).dropna()
    mce = sm.OLS(datos["dm"], sm.add_constant(datos.drop(columns="dm"))).fit()
    return {"b_y": float(lp.params["y"]), "b_i": float(lp.params["i"]),
            "se_y": float(lp.bse["y"]), "se_i": float(lp.bse["i"]),
            "p_coint": p_coint, "g": float(mce.params["u_1"]),
            "t_g": float(mce.tvalues["u_1"]), "_mce": mce}


def ventanas_moviles(df: pd.DataFrame, ventana: int = 72) -> pd.DataFrame:
    """Estimaciones de Engle-Granger en ventanas móviles; índice = fin de ventana."""
    filas = {}
    for fin in range(ventana, len(df) + 1):
        r = engle_granger(df.iloc[fin - ventana:fin])
        r.pop("_mce")
        filas[df.index[fin - 1]] = r
    return pd.DataFrame(filas).T


def _betas_moviles(m: np.ndarray, X: np.ndarray, ventana: int) -> np.ndarray:
    """Coeficientes MCO de largo plazo en cada ventana (filas) - versión rápida."""
    return np.array([np.linalg.lstsq(X[f - ventana:f], m[f - ventana:f], rcond=None)[0]
                     for f in range(ventana, len(m) + 1)])


def umbral_simulado(df: pd.DataFrame, ventana: int = 72, B: int = 200,
                    nivel: float = 0.90, semilla: int = 426) -> dict[str, float]:
    """Umbral de desviación máxima de b_y y b_i bajo estabilidad (bootstrap paramétrico).

    Returns:
        dict ``{"b_y": umbral, "b_i": umbral}`` en unidades del coeficiente.
    """
    rng = np.random.default_rng(semilla)
    X = np.column_stack([np.ones(len(df)), df["y"], df["i"]])
    m = df["m_real"].to_numpy()
    beta = np.linalg.lstsq(X[:ventana], m[:ventana], rcond=None)[0]
    u = m[:ventana] - X[:ventana] @ beta
    Xr = X[:ventana]

    def _ar1(v: np.ndarray) -> float:
        return float(np.dot(v[1:], v[:-1]) / np.dot(v[:-1], v[:-1]))

    def _simular_u(phi: float, sigma: float, n: int) -> np.ndarray:
        e = rng.normal(0, sigma, n)
        us = np.empty(n)
        us[0] = e[0] / np.sqrt(1 - phi ** 2)
        for t in range(1, n):
            us[t] = phi * us[t - 1] + e[t]
        return us

    phi_hat = _ar1(u)
    sigma = float(np.std(u[1:] - phi_hat * u[:-1], ddof=1))
    # Corrección del sesgo de phi por simulación (incluye el efecto de estimar beta).
    sesgo = np.mean([_ar1(us - Xr @ np.linalg.lstsq(Xr, us, rcond=None)[0])
                     for us in (_simular_u(phi_hat, sigma, ventana) for _ in range(B))]) - phi_hat
    phi = float(np.clip(phi_hat - sesgo, -0.98, 0.98))
    maximos = np.empty((B, 2))
    for b in range(B):
        us = _simular_u(phi, sigma, len(df))
        bm = _betas_moviles(X @ beta + us, X, ventana)[:, 1:]
        maximos[b] = np.abs(bm - bm[0]).max(axis=0)
    q = np.quantile(maximos, nivel, axis=0)
    return {"b_y": float(q[0]), "b_i": float(q[1])}


def detectar_inestabilidad(rol: pd.DataFrame,
                           umbral: dict[str, float]) -> dict[str, pd.Timestamp | None]:
    """Primer fin de ventana en que b_y o b_i se aleja de la primera ventana más que ``umbral``."""
    out: dict[str, pd.Timestamp | None] = {}
    for coef in ("b_y", "b_i"):
        fuera = (rol[coef] - rol[coef].iloc[0]).abs() > umbral[coef]
        out[coef] = fuera.idxmax() if fuera.any() else None
    return out


def analizar(df: pd.DataFrame, ventana: int = 72, B: int = 200) -> dict[str, object]:
    """Muestra completa, ventanas móviles, alertas de inestabilidad y CUSUM."""
    completa = engle_granger(df)
    mce = completa.pop("_mce")
    _, p_cusum, _ = breaks_cusumolsresid(np.asarray(mce.resid), ddof=int(mce.df_model) + 1)
    rol = ventanas_moviles(df, ventana)
    umbral = umbral_simulado(df, ventana, B)
    return {"completa": completa, "rolling": rol, "umbral": umbral,
            "alertas": detectar_inestabilidad(rol, umbral), "p_cusum": float(p_cusum),
            "ventana": ventana}


def informe(res: dict[str, object], rotulo: str) -> str:
    """Resumen breve para consola y anexo."""
    c, rol, al = res["completa"], res["rolling"], res["alertas"]
    fmt = lambda f: f.strftime("%Y-%m") if f is not None else "sin alerta"
    ini = rol.iloc[0]
    fin = rol.iloc[-1]
    return "\n".join([
        f"[{rotulo}]",
        f"Muestra completa: b_y = {c['b_y']:.2f}, b_i = {c['b_i']:.2f}, "
        f"p Engle-Granger = {c['p_coint']:.3f}, ajuste g = {c['g']:.3f} (t = {c['t_g']:.1f})",
        f"CUSUM del MCE: p = {res['p_cusum']:.3f}",
        f"Ventanas de {res['ventana']} meses (fin de ventana):",
        f"  primera {rol.index[0]:%Y-%m}: b_y = {ini['b_y']:.2f}, b_i = {ini['b_i']:.2f}, "
        f"p EG = {ini['p_coint']:.3f}, g = {ini['g']:.3f}",
        f"  última  {rol.index[-1]:%Y-%m}: b_y = {fin['b_y']:.2f}, b_i = {fin['b_i']:.2f}, "
        f"p EG = {fin['p_coint']:.3f}, g = {fin['g']:.3f}",
        f"  ventanas sin cointegración al 10 %: {(rol['p_coint'] > 0.10).mean():.0%}",
        f"Umbral simulado bajo estabilidad (90 %): b_y +/- {res['umbral']['b_y']:.2f}, "
        f"b_i +/- {res['umbral']['b_i']:.2f}",
        f"Alerta de inestabilidad (primer fin de ventana fuera del umbral): "
        f"b_y: {fmt(al['b_y'])}; b_i: {fmt(al['b_i'])}",
    ])


def armar_panel(dinero: pd.Series, precios: pd.Series, actividad: pd.Series,
                tasa_pct: pd.Series) -> pd.DataFrame:
    """Arma el panel mensual (promedios mensuales) a partir de series en niveles.

    ``tasa_pct`` en porcentaje anual (p. ej., 35.0); se pasa a tanto por uno.
    """
    m = [a_mensual(s) for s in (dinero, precios, actividad, tasa_pct)]
    df = pd.concat(m, axis=1, keys=["dinero", "precios", "actividad", "tasa"]).dropna()
    return pd.DataFrame({"m_real": np.log(df["dinero"] / df["precios"]),
                         "y": np.log(df["actividad"]), "i": df["tasa"] / 100})


def main(argv: list[str] | None = None) -> str:
    """Punto de entrada de línea de comandos."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--demo", action="store_true", help="datos sintéticos de demostración")
    ap.add_argument("--dinero"), ap.add_argument("--precios")
    ap.add_argument("--actividad"), ap.add_argument("--tasa")
    ap.add_argument("--ventana", type=int, default=72, help="meses por ventana")
    a = ap.parse_args(argv)
    if a.demo:
        df, rotulo = demo_demanda_dinero(), ROTULO_SINTETICO + " (quiebre en b_i en 2016-01)"
    elif all([a.dinero, a.precios, a.actividad, a.tasa]):
        df = armar_panel(*(cargar_csv(p) for p in (a.dinero, a.precios, a.actividad, a.tasa)))
        rotulo = "Datos: " + ", ".join([a.dinero, a.precios, a.actividad, a.tasa])
    else:
        ap.error("usar --demo o indicar --dinero, --precios, --actividad y --tasa")
    texto = informe(analizar(df, ventana=a.ventana), rotulo)
    print(texto)
    return texto


if __name__ == "__main__":
    main()
