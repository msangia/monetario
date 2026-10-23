"""Exploratorio (Eje 4, modelos A-B-C): MCE con transición suave logística (LSTR) en la tasa
y tendencia logística de sustitución de medios de pago.

Prototipo **exploratorio**, no forma parte de los anexos. Implementación propia a partir de
literatura pública estándar sobre modelos de transición suave (Granger y Teräsvirta, 1993;
Teräsvirta, 1994; van Dijk, Teräsvirta y Franses, 2002) y de la prueba de linealidad por
aproximación de Taylor (Luukkonen, Saikkonen y Teräsvirta, 1988).

Modelo mensual para x = log del dinero real (billetes, circulación o M2 deflactados por el IPC):

1. Largo plazo (MCO): x_t = c + b_y y_t + b_i i_t [+ d * T_t], con
   T_t = 1 / (1 + exp(-g_T (t - tau))) una **tendencia logística en el tiempo** (curva de
   difusión de los pagos electrónicos; ``tecnologia=True``). (g_T, tau) se eligen por grilla
   minimizando la suma de cuadrados del largo plazo. Es determinística: proyectarla no usa
   información futura, pero se identifica sólo por la forma temporal de la serie (ver
   limitaciones).
2. Corto plazo: dx_t = a + meses + d_y dy_t + r dx_{t-1} + S_t' th_L + F_t S_t' (th_H - th_L) + e,
   con S_t = (u_{t-1}, di_t, di_{t-1}) y F_t = G(s_{t-1}; gamma, c) logística en el **nivel
   rezagado** de la variable de transición s (por defecto la tasa). F = 0 es el régimen de
   tasa baja; F = 1, el de tasa alta. (gamma, c) por grilla (NLS concentrado): gamma se
   escala por el desvío de s y c recorre los percentiles 15-85 de s en la muestra de
   estimación (recorte habitual para que haya observaciones en ambos regímenes).

Prueba de linealidad (LM3, versión F): residuos del MCE lineal sobre los regresores y S_t
multiplicado por s, s^2 y s^3; la secuencia H04-H03-H02 (Teräsvirta, 1994) orienta entre
transición logística (LSTR) y exponencial (ESTR). u_{t-1} es un regresor generado: los
p-valores son aproximados.

Los pronósticos a 1-3 meses son **condicionales** (usan y, i y P observados entre t y t + h,
como ``programa.py``) y se estiman con ventana expansiva sin *look-ahead*. Los errores se
informan en % simple: 100 * (observado / programado - 1).

Uso::

    python -m monetario_demo.no_lineal --demo
    python -m monetario_demo.no_lineal --reales --salida salidas/exploratorio_no_lineal.txt
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from . import bandas
from .datos import (ROTULO_SINTETICO, a_mensual, cargar_csv, cargar_emae, cargar_ipc,
                    meses_completos)
from .evaluacion import diebold_mariano
from .programa import armar_panel_programa, pronostico_deriva_estacional

H = 3
MODELOS = ("lineal", "lstr", "tec", "lstr_tec")
GAMMAS = (1.0, 2.5, 5.0, 10.0, 25.0)            # pendiente, en unidades de 1/desvío(s)
PCT_UMBRAL = np.linspace(15, 85, 15)             # percentiles candidatos del umbral c
GAMMAS_T = (0.03, 0.06, 0.12, 0.25)              # pendiente de la difusión (1/mes)
ROTULO_EXPLORATORIO = ("EXPLORATORIO. Datos reales; cálculo propio, no oficial. "
                       "No es un modelo ni un pronóstico del BCRA.")


# ---------------------------------------------------------------------------
# Piezas básicas
# ---------------------------------------------------------------------------
def logistica(s: np.ndarray | float, gamma: float, c: float, escala: float = 1.0) -> np.ndarray:
    """G(s) = 1 / (1 + exp(-gamma (s - c) / escala)), entre 0 y 1; G(c) = 0,5."""
    z = np.clip(gamma * (np.asarray(s, float) - c) / escala, -60, 60)
    return 1.0 / (1.0 + np.exp(-z))


def _dummies_mes(meses: np.ndarray) -> np.ndarray:
    """Dummies de febrero a diciembre (enero es la base)."""
    return (meses[:, None] == np.arange(2, 13)[None, :]).astype(float)


def _ols(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
    """Coeficientes MCO y suma de cuadrados de los residuos."""
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ b
    return b, float(e @ e)


@dataclass
class Datos:
    """Arreglos del panel mensual (x = dinero real en log; s = variable de transición)."""

    x: np.ndarray
    y: np.ndarray
    i: np.ndarray
    lp: np.ndarray
    s: np.ndarray
    dum: np.ndarray
    indice: pd.DatetimeIndex

    @classmethod
    def desde_panel(cls, panel: pd.DataFrame, transicion: str = "i") -> "Datos":
        """``panel`` con ``m_real``, ``y``, ``i``, ``log_p`` y la columna ``transicion``."""
        return cls(*(panel[c].to_numpy(float) for c in ("m_real", "y", "i", "log_p")),
                   s=panel[transicion].to_numpy(float),
                   dum=_dummies_mes(panel.index.month.to_numpy()), indice=panel.index)


@dataclass
class Ajuste:
    """Parámetros estimados del MCE (lineal o LSTR, con o sin tendencia de pagos)."""

    modelo: str
    beta: np.ndarray                      # largo plazo: c, b_y, b_i[, d]
    theta: np.ndarray                     # corto plazo
    tec: tuple[float, float] | None       # (g_T, tau) de la tendencia logística
    trans: tuple[float, float] | None     # (gamma, c) de la transición en s
    escala: float                         # desvío de s en la muestra
    ssr: float
    n: int
    extra: dict = field(default_factory=dict)

    def tendencia(self, t: np.ndarray) -> np.ndarray:
        """T_t evaluada en las posiciones ``t`` (0 si no hay tendencia)."""
        if self.tec is None:
            return np.zeros(len(np.atleast_1d(t)))
        return logistica(np.asarray(t, float), self.tec[0], self.tec[1])

    def largo_plazo(self, d: Datos, t: np.ndarray) -> np.ndarray:
        """x* en las posiciones ``t``."""
        X = np.column_stack([np.ones(len(t)), d.y[t], d.i[t]])
        if self.tec is not None:
            X = np.column_stack([X, self.tendencia(t)])
        return X @ self.beta

    def F(self, d: Datos, t: np.ndarray) -> np.ndarray:
        """Peso del régimen de tasa alta en t (usa s_{t-1})."""
        if self.trans is None:
            return np.zeros(len(t))
        return logistica(d.s[np.asarray(t) - 1], self.trans[0], self.trans[1], self.escala)


def _largo_plazo(d: Datos, a: int, fin: int, tecnologia: bool
                 ) -> tuple[np.ndarray, tuple[float, float] | None]:
    """Largo plazo por MCO en filas a..fin; con tendencia logística elegida por grilla."""
    t = np.arange(a, fin + 1)
    X0 = np.column_stack([np.ones(len(t)), d.y[t], d.i[t]])
    if not tecnologia:
        return _ols(X0, d.x[t])[0], None
    mejor = (np.inf, None, None)
    for g in GAMMAS_T:
        for tau in np.linspace(a + 0.2 * (fin - a), fin, 17):
            b, ssr = _ols(np.column_stack([X0, logistica(t, g, tau)]), d.x[t])
            if ssr < mejor[0]:
                mejor = (ssr, b, (g, float(tau)))
    return mejor[1], mejor[2]


def _corto_plazo(d: Datos, r: np.ndarray, u: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Regresores comunes (constante, meses, dy, dx_{t-1}) y conmutables S_t en las filas r."""
    comunes = np.column_stack([np.ones(len(r)), d.dum[r], d.y[r] - d.y[r - 1],
                               d.x[r - 1] - d.x[r - 2]])
    S = np.column_stack([u[r - 1], d.i[r] - d.i[r - 1], d.i[r - 1] - d.i[r - 2]])
    return comunes, S


def estimar(d: Datos, fin: int, modelo: str = "lstr", inicio: int = 0) -> Ajuste:
    """Estima el modelo con las filas ``inicio``..``fin`` (sólo información hasta ``fin``).

    Args:
        d: datos del panel.
        fin: última fila usada (el origen del pronóstico).
        modelo: ``lineal``, ``lstr`` (transición en s), ``tec`` (tendencia de pagos,
            dinámica lineal) o ``lstr_tec`` (ambas).
        inicio: primera fila (0 = ventana expansiva).
    """
    if modelo not in MODELOS:
        raise ValueError(f"modelo debe ser uno de {MODELOS}")
    tecnologia = modelo in ("tec", "lstr_tec")
    beta, tec = _largo_plazo(d, inicio, fin, tecnologia)
    aj = Ajuste(modelo, beta, np.empty(0), tec, None, 1.0, np.inf, 0)
    t_all = np.arange(len(d.x))
    u = d.x - aj.largo_plazo(d, t_all)              # sólo usa beta (estimado hasta fin)
    r = np.arange(inicio + 2, fin + 1)
    comunes, S = _corto_plazo(d, r, u)
    dx = d.x[r] - d.x[r - 1]
    if modelo in ("lineal", "tec"):
        aj.theta, aj.ssr = _ols(np.column_stack([comunes, S]), dx)
        aj.n = len(r)
        return aj
    sv = d.s[inicio:fin]                            # s_{t-1} para t = inicio+1..fin
    aj.escala = float(np.std(sv, ddof=1)) or 1.0
    mejor = (np.inf, None, None)
    for c in np.percentile(sv, PCT_UMBRAL):
        for g in GAMMAS:
            Fr = logistica(d.s[r - 1], g, c, aj.escala)
            th, ssr = _ols(np.column_stack([comunes, S, S * Fr[:, None]]), dx)
            if ssr < mejor[0]:
                mejor = (ssr, th, (g, float(c)))
    aj.ssr, aj.theta, aj.trans, aj.n = mejor[0], mejor[1], mejor[2], len(r)
    return aj


def coeficientes_regimen(aj: Ajuste) -> pd.DataFrame:
    """Coeficientes de S_t = (u_{t-1}, di_t, di_{t-1}) en los regímenes bajo (F=0) y alto (F=1)."""
    k = aj.theta.size - (6 if aj.trans is not None else 3)
    bajo = aj.theta[k:k + 3]
    alto = bajo + (aj.theta[k + 3:k + 6] if aj.trans is not None else 0)
    return pd.DataFrame({"bajo": bajo, "alto": alto}, index=["u_1", "di", "di_1"])


def pronosticar(d: Datos, aj: Ajuste, t: int, h_max: int = H) -> dict[int, float]:
    """Log del agregado nominal en t + 1..t + h_max, recursivo y condicional a y, i, P, s."""
    actual, previo, fila = d.x[t], d.x[t - 1], {}
    for h in range(1, h_max + 1):
        s = t + h
        if s >= len(d.x):
            fila[h] = np.nan
            continue
        u_1 = actual - aj.largo_plazo(d, np.array([s - 1]))[0]
        comunes = np.r_[1.0, d.dum[s], d.y[s] - d.y[s - 1], actual - previo]
        S = np.array([u_1, d.i[s] - d.i[s - 1], d.i[s - 1] - d.i[s - 2]])
        z = np.r_[comunes, S]
        if aj.trans is not None:
            z = np.r_[z, S * aj.F(d, np.array([s]))[0]]
        previo, actual = actual, actual + float(z @ aj.theta)
        fila[h] = actual + d.lp[s]
    return fila


def pronostico_expansivo(d: Datos, modelo: str, min_obs: int = 48, h_max: int = H,
                         guardar: list | None = None) -> pd.DataFrame:
    """Pronósticos fuera de muestra con ventana expansiva (filas = origen, columnas = h).

    El primer origen tiene ``min_obs`` filas de estimación. ``guardar`` (lista) recibe el
    ``Ajuste`` de cada origen, para seguir la estabilidad de (gamma, c) y de la tendencia.
    """
    filas = {}
    for t in range(min_obs - 1, len(d.x) - 1):
        aj = estimar(d, t, modelo)
        if guardar is not None:
            guardar.append((d.indice[t], aj))
        filas[d.indice[t]] = pronosticar(d, aj, t, h_max)
    return pd.DataFrame(filas).T


# ---------------------------------------------------------------------------
# Prueba de linealidad (Luukkonen-Saikkonen-Teräsvirta / Teräsvirta 1994)
# ---------------------------------------------------------------------------
def test_linealidad(d: Datos, fin: int | None = None, inicio: int = 0) -> dict[str, float]:
    """LM3 (versión F) contra transición suave en s_{t-1} y secuencia H04, H03, H02.

    Returns:
        dict con ``F``, ``p_LM3``, ``p_H04``, ``p_H03``, ``p_H02``, ``n`` y ``sugerido``
        (``"LSTR"`` o ``"ESTR"`` según la regla de Teräsvirta: ESTR si H03 tiene el menor
        p-valor de la secuencia).
    """
    fin = len(d.x) - 1 if fin is None else fin
    lin = estimar(d, fin, "lineal", inicio)
    u = d.x - lin.largo_plazo(d, np.arange(len(d.x)))
    r = np.arange(inicio + 2, fin + 1)
    comunes, S = _corto_plazo(d, r, u)
    X0 = np.column_stack([comunes, S])
    dx = d.x[r] - d.x[r - 1]
    e0 = dx - X0 @ np.linalg.lstsq(X0, dx, rcond=None)[0]
    sv = d.s[r - 1]
    sv = (sv - sv.mean()) / sv.std(ddof=1)
    A = [S * sv[:, None] ** j for j in (1, 2, 3)]

    def _ssr(X: np.ndarray) -> float:
        return _ols(X, e0)[1]

    def _f(ssr_r: float, ssr_u: float, q: int, k: int) -> tuple[float, float]:
        gl = len(r) - k
        f = ((ssr_r - ssr_u) / q) / (ssr_u / gl)
        return float(f), float(stats.f.sf(f, q, gl))

    X1, X2, X3 = (np.column_stack([X0, *A[:j]]) for j in (1, 2, 3))
    s0, s1, s2, s3 = _ssr(X0), _ssr(X1), _ssr(X2), _ssr(X3)
    q = S.shape[1]
    F3, p3 = _f(s0, s3, 3 * q, X3.shape[1])
    _, p04 = _f(s2, s3, q, X3.shape[1])
    _, p03 = _f(s1, s2, q, X2.shape[1])
    _, p02 = _f(s0, s1, q, X1.shape[1])
    sugerido = "ESTR" if p03 < min(p04, p02) else "LSTR"
    return {"F": F3, "p_LM3": p3, "p_H04": p04, "p_H03": p03, "p_H02": p02,
            "n": len(r), "sugerido": sugerido}


# ---------------------------------------------------------------------------
# Evaluación fuera de muestra
# ---------------------------------------------------------------------------
def comparar(log_obs: pd.Series, pron: dict[str, pd.DataFrame], desde: str,
             base: str = "lineal", otra: str = "deriva_estacional",
             nivel: float = 0.9) -> pd.DataFrame:
    """MAE (% simple), DM-HLN unilateral contra ``base`` y ``otra``, y cobertura de la banda.

    Todos los modelos se evalúan en los mismos orígenes (comunes, desde ``desde``). La
    banda del 90 % es la de cuantiles empíricos de errores previos (``bandas.cobertura_banda``),
    la misma regla del núcleo.
    """
    err = {k: bandas.errores_de_pronostico(log_obs, v) for k, v in pron.items()}
    comunes = err[base].dropna().index
    for e in err.values():
        comunes = comunes.intersection(e.dropna().index)
    comunes = comunes[comunes >= pd.Timestamp(desde)]
    filas = []
    for k, e in err.items():
        cob = bandas.cobertura_banda(e.loc[comunes[0]:comunes[-1]], nivel)
        for h in e.columns:
            ec = e.loc[comunes, h]
            fila = {"modelo": k, "h": int(h), "n": len(ec), "MAE_%": float(ec.abs().mean()),
                    "MAE_rel_lineal": float(ec.abs().mean() / err[base].loc[comunes, h].abs().mean())}
            for etiqueta, ref in (("p_DM_vs_lineal", base), ("p_DM_vs_estac", otra)):
                fila[etiqueta] = (np.nan if k == ref or ref not in err else
                                  diebold_mariano(ec, err[ref].loc[comunes, h], h=int(h)).p_valor)
            fila.update({"n_cob": int(cob.loc[h, "n"]), "cobertura_90": float(cob.loc[h, "cobertura"]),
                         "ancho_90_pp": float(cob.loc[h, "ancho"])})
            filas.append(fila)
    return pd.DataFrame(filas)


def correr(panel: pd.DataFrame, log_m_largo: pd.Series, desde: str = "2021-01",
           min_obs: int = 48, transicion: str = "i") -> dict:
    """Corre los cuatro modelos y la deriva estacional; devuelve tabla, ajustes y pruebas."""
    d = Datos.desde_panel(panel, transicion)
    pron, ajustes = {}, {}
    for m in MODELOS:
        ajustes[m] = []
        pron[m] = pronostico_expansivo(d, m, min_obs, guardar=ajustes[m])
    pron["deriva_estacional"] = pronostico_deriva_estacional(log_m_largo)
    tabla = comparar(log_m_largo, pron, desde)
    return {"tabla": tabla, "ajustes": ajustes, "datos": d, "pron": pron}


# ---------------------------------------------------------------------------
# Datos sintéticos de demostración
# ---------------------------------------------------------------------------
def demo_panel(n: int = 200, semilla: int = 426, lineal: bool = False) -> pd.DataFrame:
    """Panel con un MCE LSTR conocido (umbral 0,5) y una caída logística del largo plazo.

    DATOS SINTÉTICOS DE DEMOSTRACIÓN, NO OFICIALES. Con ``lineal=True`` el corto plazo es
    lineal y no hay tendencia (para medir el tamaño de la prueba de linealidad).
    """
    rng = np.random.default_rng(semilla)
    idx = pd.period_range("2005-01", periods=n, freq="M").to_timestamp("M")
    y = 4.6 + np.cumsum(rng.normal(0.002, 0.01, n))
    i = np.empty(n)
    i[0] = 0.4
    for t in range(1, n):                                   # tasa acotada entre 0,1 y 1,1
        i[t] = np.clip(i[t - 1] + rng.normal(0, 0.05), 0.1, 1.1)
    T = np.zeros(n) if lineal else logistica(np.arange(n), 0.08, 0.7 * n)
    xs = 1.0 + 1.0 * y - 1.0 * i - 0.4 * T
    F = np.zeros(n) if lineal else logistica(np.r_[i[0], i[:-1]], 10.0, 0.5, 1.0)
    g, di0 = -0.15 - 0.25 * F, -0.6 + 0.5 * F
    x = xs.copy()
    e = rng.normal(0, 0.01, n)
    for t in range(2, n):
        x[t] = (x[t - 1] + g[t] * (x[t - 1] - xs[t - 1]) + di0[t] * (i[t] - i[t - 1])
                + 0.2 * (x[t - 1] - x[t - 2]) + 0.5 * (y[t] - y[t - 1]) + e[t])
    lp = np.cumsum(np.full(n, 0.02))
    return pd.DataFrame({"m_real": x, "y": y, "i": i, "log_p": lp, "log_m": x + lp},
                        index=idx)


# ---------------------------------------------------------------------------
# Datos reales
# ---------------------------------------------------------------------------
def panel_real(dinero_id: str, tasa_id: str = "1189") -> tuple[pd.DataFrame, pd.Series]:
    """Panel mensual real (IPC oficial desde 2016-12) y log del agregado con toda su historia.

    Agrega columnas de transición alternativas: ``i_11`` (BAIBAR), ``i_150`` (pases entre
    terceros) e ``infl`` (inflación mensual promedio de 3 meses, en tanto por uno).
    """
    dinero = cargar_csv(dinero_id)
    panel = armar_panel_programa(dinero, cargar_ipc(), cargar_emae(), cargar_csv(tasa_id))
    for k in ("11", "150"):
        panel[f"i_{k}"] = a_mensual(cargar_csv(k)).reindex(panel.index) / 100
    panel["infl"] = panel["log_p"].diff().rolling(3).mean()
    panel = panel.dropna()
    lm = np.log(a_mensual(meses_completos(dinero))).loc[:panel.index[-1]]
    return panel, lm


def _resumen_ajuste(aj: Ajuste, d: Datos) -> str:
    """Texto breve con el ajuste de muestra completa."""
    partes = [f"largo plazo: b_y = {aj.beta[1]:.2f}, b_i = {aj.beta[2]:.2f}"]
    if aj.tec is not None:
        pos = int(round(min(aj.tec[1], len(d.indice) - 1)))
        partes.append(f"tendencia: d = {aj.beta[3]:.2f}, g_T = {aj.tec[0]:.2f}/mes, "
                      f"punto medio ~ {d.indice[pos]:%Y-%m}")
    if aj.trans is not None:
        partes.append(f"transición: c = {100 * aj.trans[1]:.0f} % anual, "
                      f"gamma = {aj.trans[0]:.1f}/desvío")
    cr = coeficientes_regimen(aj).round(3)
    partes.append("S_t (bajo/alto): " + "; ".join(f"{k} {v.bajo}/{v.alto}"
                                                   for k, v in cr.iterrows()))
    return " | ".join(partes)


def informe_real(series: tuple[str, ...] = ("17", "16", "109"), tasa: str = "1189",
                 desde: str = "2021-01", corte_episodio: str = "2023-06-30",
                 desde_post: str = "2024-07") -> str:
    """Corre todo con datos reales y arma el informe de texto.

    ``corte_episodio``: fin de muestra para repetir la prueba de linealidad sin el episodio
    de tasas superiores al 100 % anual (fines de 2023); ``desde_post``: primer origen de la
    submuestra descriptiva posterior a ese episodio (elegida ex post).
    """
    nombres = {"17": "billetes y monedas en poder del público (17)",
               "16": "circulación monetaria (16)", "109": "M2 total (109)"}
    out = [f"# {ROTULO_EXPLORATORIO}",
           "# Fuente: BCRA, API de Estadísticas Monetarias v4.0 (datos/bcra_<id>_daily.csv); "
           "INDEC (EMAE s.e.; IPC oficial desde 2016-12, sin empalme previo).",
           f"# Ejecución: {datetime.now():%Y-%m-%d %H:%M}", "",
           "Dinero real = promedio mensual (meses completos) / IPC; tasa = plazo fijo en pesos "
           f"(id {tasa}, TNA en tanto por uno). MCE con dummies mensuales (dinero sin "
           "desestacionalizar). Pronósticos condicionales a IPC, EMAE y tasa observados "
           f"(piso del error de un programa real); ventana expansiva desde 2017 (mínimo 48 meses); "
           f"orígenes evaluados desde {desde}. Errores en % simple: 100 * (obs / prog - 1). "
           "DM-HLN unilateral (H1: el modelo de la fila es más preciso), pérdida absoluta. "
           "Banda del 90 % por cuantiles empíricos de errores previos (mín. 24).", ""]
    for sid in series:
        panel, lm = panel_real(sid, tasa)
        d0 = Datos.desde_panel(panel)
        out.append(f"## {nombres.get(sid, sid)}")
        out.append(f"Panel {panel.index[0]:%Y-%m} a {panel.index[-1]:%Y-%m} ({len(panel)} meses)")
        out.append("Prueba de linealidad LM3 (F) contra transición en s_{t-1}; muestra completa "
                   "y primera ventana (48 meses, lo que se sabía en el primer origen):")
        filas = []
        fin_pre = int(panel.index.get_indexer([pd.Timestamp(corte_episodio)], method="pad")[0])
        for col, etq in (("i", f"tasa plazo fijo ({tasa})"), ("i_11", "BAIBAR (11)"),
                         ("i_150", "pases entre terceros (150)"), ("infl", "inflación 3m")):
            d = Datos.desde_panel(panel, col)
            tc, tv = test_linealidad(d), test_linealidad(d, fin=47)
            tp = test_linealidad(d, fin=fin_pre)
            filas.append({"transición": etq, "p_LM3_completa": tc["p_LM3"],
                          "p_H04": tc["p_H04"], "p_H03": tc["p_H03"], "p_H02": tc["p_H02"],
                          "sugerido": tc["sugerido"], "p_LM3_1ra_ventana": tv["p_LM3"],
                          f"p_LM3_hasta_{corte_episodio}": tp["p_LM3"]})
        out.append(pd.DataFrame(filas).round(3).to_string(index=False))
        out.append("Ajuste de muestra completa (in-sample, sólo descriptivo):")
        for m in MODELOS:
            aj = estimar(d0, len(d0.x) - 1, m)
            out.append(f"  {m}: SSR = {aj.ssr:.4f}, n = {aj.n}, parámetros = "
                       f"{aj.theta.size + aj.beta.size + 2 * (aj.trans is not None) + 2 * (aj.tec is not None)}; "
                       + _resumen_ajuste(aj, d0))
        res = correr(panel, lm, desde)
        out.append("Fuera de muestra (orígenes comunes):")
        out.append(res["tabla"].round(3).to_string(index=False))
        c = np.array([a.trans[1] for _, a in res["ajustes"]["lstr"]]) * 100
        tau = [a.tec[1] for _, a in res["ajustes"]["tec"]]
        en_borde = np.mean([abs(t_ - (k + 47)) < 1e-6 for k, t_ in enumerate(tau)])
        g = np.array([a.trans[0] for _, a in res["ajustes"]["lstr"]])
        out.append(f"Estabilidad entre orígenes: umbral c del LSTR entre {c.min():.0f} y "
                   f"{c.max():.0f} % anual (mediana {np.median(c):.0f}); gamma en el mínimo de "
                   f"la grilla ({min(GAMMAS)}/desvío, transición casi lineal) en "
                   f"{100 * np.mean(g == min(GAMMAS)):.0f} % de los orígenes; tendencia de pagos "
                   f"con punto medio en el último dato de la ventana en {100 * en_borde:.0f} % de "
                   "los orígenes (no identificada: se extrapola).")
        err = {k: bandas.errores_de_pronostico(lm, v) for k, v in res["pron"].items()}
        comunes = err["lineal"].dropna().index
        for e in err.values():
            comunes = comunes.intersection(e.dropna().index)
        post = comunes[comunes >= pd.Timestamp(desde_post)]
        mae = pd.DataFrame({k: [e.loc[post, h].abs().mean() for h in (1, 2, 3)]
                            for k, e in err.items()}, index=["h=1", "h=2", "h=3"]).T
        out.append(f"Submuestra ELEGIDA EX POST (orígenes desde {desde_post}, {len(post)} "
                   "orígenes, ya con el episodio de tasa > 100 % en la estimación; sólo "
                   "descriptiva, sin DM por su tamaño). MAE en %:")
        out.append(mae.round(2).to_string())
        out.append("")
    out.append("Lectura: ver trabajo/analisis_no_lineal.md. Resultados exploratorios; la "
               "selección de modelo, grilla y variable de transición con ~115 meses implica "
               "riesgo de sobreajuste y de búsqueda de especificación.")
    return "\n".join(out)


def informe_demo() -> str:
    """Corre el prototipo con datos sintéticos (umbral verdadero 0,5)."""
    panel = demo_panel()
    d = Datos.desde_panel(panel)
    t = test_linealidad(d)
    aj = estimar(d, len(d.x) - 1, "lstr_tec")
    res = correr(panel, panel["log_m"], desde=str(panel.index[120].date())[:7], min_obs=96)
    return "\n".join([f"[{ROTULO_SINTETICO}]",
                      f"LM3: p = {t['p_LM3']:.4f} (sugerido {t['sugerido']})",
                      "lstr_tec: " + _resumen_ajuste(aj, d),
                      res["tabla"].round(3).to_string(index=False)])


def main(argv: list[str] | None = None) -> str:
    """Punto de entrada de línea de comandos."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--demo", action="store_true", help="datos sintéticos de demostración")
    g.add_argument("--reales", action="store_true", help="datos reales de datos/")
    ap.add_argument("--series", default="17,16,109", help="IDs del agregado, separados por coma")
    ap.add_argument("--tasa", default="1189")
    ap.add_argument("--salida", default=None, help="archivo de texto de salida")
    a = ap.parse_args(argv)
    texto = (informe_demo() if a.demo else
             informe_real(tuple(a.series.split(",")), a.tasa))
    print(texto)
    if a.salida:
        Path(a.salida).write_text(texto + "\n", encoding="utf-8")
    return texto


if __name__ == "__main__":
    main()
