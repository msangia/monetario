"""Anexo C (Eje 4): banda de tolerancia para base/M2 y chequeo de desvíos.

1. Errores históricos de pronóstico a h = 1..3 meses (origen móvil): el
   programa proyecta log(M_{t+h}) = log(M_t) + h * deriva_t, con deriva igual
   al crecimiento mensual medio de los últimos ``ventana`` meses. Error en %:
   100 * (log observado - log programado). El modelo de programación es
   intercambiable: la banda sólo necesita su historial de errores.
2. Banda de tolerancia por horizonte: cuantiles empíricos de esos errores,
   usando sólo errores ya observados al momento del programa (sin look-ahead).
3. Chequeo mensual de cada trimestre: desvío del observado frente al programa,
   "dentro de banda" o "fuera de banda" (banda central del 90 %).
4. Fan chart simple con bandas del 50, 70 y 90 %.

Uso::

    python -m monetario_demo.bandas --demo
    python -m monetario_demo.bandas --csv datos/m2_privado_mensual.csv --trimestres 4
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .datos import (CARPETA_DATOS, ROTULO_SINTETICO, a_mensual, cargar_csv, demo_agregado_mensual,
                    meses_completos)

NIVELES = (0.5, 0.7, 0.9)
H = 3


def pronostico_deriva(serie: pd.Series, ventana: int = 36, h_max: int = H) -> pd.DataFrame:
    """Log del nivel programado por el programa de deriva (filas = origen, columnas = h)."""
    lg = np.log(serie)
    deriva = lg.diff().rolling(ventana).mean()
    filas = {lg.index[t]: {h: lg.iloc[t] + h * deriva.iloc[t] for h in range(1, h_max + 1)}
             for t in range(ventana, len(lg) - 1)}
    return pd.DataFrame(filas).T


def errores_de_pronostico(log_obs: pd.Series, pron_log: pd.DataFrame) -> pd.DataFrame:
    """Errores (%) = 100 * (log observado en t + h - log programado en t para t + h).

    ``pron_log`` tiene índice = origen t (fechas de ``log_obs``) y columnas h = 1, 2, ...
    Si t + h cae fuera de la muestra, el error es NaN (todavía no se observó).
    """
    pos = log_obs.index.get_indexer(pron_log.index)
    out = {}
    for h in pron_log.columns:
        destino = pos + int(h)
        valido = (pos >= 0) & (destino < len(log_obs))
        obs = np.full(len(pos), np.nan)
        obs[valido] = log_obs.to_numpy()[destino[valido]]
        out[h] = 100 * (obs - pron_log[h].to_numpy())
    return pd.DataFrame(out, index=pron_log.index)


def errores_historicos(serie: pd.Series, ventana: int = 36, h_max: int = H) -> pd.DataFrame:
    """Errores (%) del programa de deriva por origen (filas) y horizonte (columnas 1..h_max)."""
    return errores_de_pronostico(np.log(serie), pronostico_deriva(serie, ventana, h_max))


def banda_tolerancia(errores: pd.DataFrame, corte: pd.Timestamp,
                     niveles: tuple[float, ...] = NIVELES, minimo: int = 24) -> pd.DataFrame:
    """Cuantiles empíricos de los errores por horizonte, observados hasta ``corte``.

    Un error de origen t y horizonte h se conoce en t + h meses; sólo se usan
    los que cumplen t + h <= corte.

    Returns:
        DataFrame (índice = h) con columnas ``inf_50``, ``sup_50``, ... ``sup_90``.
    """
    pos_corte = errores.index.get_indexer([corte], method="pad")[0]
    out = {}
    for h in errores.columns:
        e = errores[h].iloc[: max(pos_corte - h + 1, 0)].dropna()
        if len(e) < minimo:
            raise ValueError(f"h={h}: sólo {len(e)} errores históricos (mínimo {minimo}).")
        out[h] = {f"{lado}_{int(n * 100)}": float(np.quantile(e, q))
                  for n in niveles for lado, q in (("inf", (1 - n) / 2), ("sup", (1 + n) / 2))}
    return pd.DataFrame(out).T


def chequear_programa(serie: pd.Series, pron_log: pd.DataFrame, trimestres: int = 4,
                      nivel: float = 0.9) -> pd.DataFrame:
    """Chequeo mensual de los últimos ``trimestres`` trimestres completos, cualquier programa.

    Para cada trimestre, el programa se arma al cierre del trimestre previo (origen
    con pronóstico para h = 1..3 y observación en t + 3) y la banda usa sólo errores
    conocidos a esa fecha (:func:`banda_tolerancia`).
    """
    lg = np.log(serie)
    errores = errores_de_pronostico(lg, pron_log)
    validos = errores.dropna().index
    origenes = [f for f in validos if f.month in (3, 6, 9, 12)][-trimestres:]
    filas = []
    for o in origenes:
        banda = banda_tolerancia(errores, o)
        t = serie.index.get_loc(o)
        for h in range(1, H + 1):
            prog = float(pron_log.loc[o, h])
            desvio = float(errores.loc[o, h])
            inf, sup = banda.loc[h, f"inf_{int(nivel*100)}"], banda.loc[h, f"sup_{int(nivel*100)}"]
            filas.append({"mes": serie.index[t + h].strftime("%Y-%m"), "h": h,
                          "programado": float(np.exp(prog)), "observado": float(serie.iloc[t + h]),
                          "desvio_%": desvio, "inf_%": inf, "sup_%": sup,
                          "estado": "dentro de banda" if inf <= desvio <= sup else "fuera de banda"})
    return pd.DataFrame(filas)


def chequear_desvios(serie: pd.Series, trimestres: int = 4, ventana: int = 36,
                     nivel: float = 0.9) -> pd.DataFrame:
    """Chequeo mensual de los últimos ``trimestres`` trimestres con el programa de deriva."""
    return chequear_programa(serie, pronostico_deriva(serie, ventana), trimestres, nivel)


def cobertura_banda(errores: pd.DataFrame, nivel: float = 0.9,
                    minimo: int = 24) -> pd.DataFrame:
    """Calibración fuera de muestra de la banda: para cada origen con historia suficiente,
    ¿el error cayó dentro de la banda armada sólo con errores anteriores?

    Returns:
        DataFrame (índice = h) con ``n`` (orígenes evaluados), ``cobertura`` (proporción
        dentro; la nominal es ``nivel``) y ``ancho`` (ancho medio de la banda, pp).
    """
    q = ((1 - nivel) / 2, (1 + nivel) / 2)
    filas = {}
    for h in errores.columns:
        e = errores[h]
        dentro, anchos = [], []
        for p in range(len(e)):
            if np.isnan(e.iloc[p]):
                continue
            previos = e.iloc[: max(p - int(h) + 1, 0)].dropna()   # conocidos en t
            if len(previos) < minimo:
                continue
            inf, sup = np.quantile(previos, q)
            dentro.append(inf <= e.iloc[p] <= sup)
            anchos.append(sup - inf)
        filas[h] = {"n": len(dentro), "cobertura": float(np.mean(dentro)) if dentro else np.nan,
                    "ancho": float(np.mean(anchos)) if anchos else np.nan}
    return pd.DataFrame(filas).T


def fan_chart(serie: pd.Series, ruta: str | Path, ventana: int = 36, historia: int = 12,
              rotulo: str = "", unidad: str = "nivel",
              pron_log: pd.DataFrame | None = None, etiqueta: str = "programa") -> Path:
    """Fan chart del último trimestre chequeado: historia, programa, bandas y observados.

    ``pron_log`` (origen x h, log del nivel) elige el programa; por defecto, deriva.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker

    lg = np.log(serie)
    if pron_log is None:
        pron_log = pronostico_deriva(serie, ventana)
    errores = errores_de_pronostico(lg, pron_log)
    o = [f for f in errores.dropna().index if f.month in (3, 6, 9, 12)][-1]
    t = serie.index.get_loc(o)
    banda = banda_tolerancia(errores, o)
    # En el gráfico cada mes se ubica en su primer día (el tick "2026-05" = mayo de 2026).
    mes_x = lambda idx: pd.DatetimeIndex(idx).to_period("M").to_timestamp()
    fechas = mes_x(serie.index[t:t + H + 1])
    prog = np.exp(np.r_[lg.iloc[t], pron_log.loc[o, list(range(1, H + 1))].to_numpy(float)])
    tonos = {90: "#b7d3f6", 70: "#86b6ef", 50: "#5598e7"}  # azul secuencial claro -> oscuro
    fig, ax = plt.subplots(figsize=(5.2, 2.5), dpi=150)
    for n in (90, 70, 50):
        inf = prog * np.exp(np.r_[0, banda[f"inf_{n}"]] / 100)
        sup = prog * np.exp(np.r_[0, banda[f"sup_{n}"]] / 100)
        ax.fill_between(fechas, inf, sup, color=tonos[n], lw=0, label=f"banda {n} %")
    hist = serie.iloc[max(t - historia, 0):t + 1]
    ax.plot(mes_x(hist.index), hist, color="#52514e", lw=1.5, label="observado")
    ax.plot(fechas, prog, color="#0d366b", lw=1.5, ls="--", label=etiqueta)
    obs = serie.iloc[t:t + H + 1]
    ax.plot(mes_x(obs.index), obs, color="#52514e", lw=1.5, marker="o", ms=4)
    chk = chequear_programa(serie, pron_log, 1)
    fuera = chk[chk["estado"] == "fuera de banda"]
    for _, r in fuera.iterrows():
        f = pd.Timestamp(r["mes"])
        ax.plot(f, r["observado"], marker="o", ms=7, color="#d03b3b", zorder=5)
    if len(fuera):
        r = fuera.iloc[0]
        ax.annotate(f"fuera de banda ({len(fuera)} meses)",
                    (pd.Timestamp(r["mes"]), r["observado"]),
                    xytext=(-95, 6), textcoords="offset points", fontsize=8, color="#0b0b0b")
    if "millones" in unidad.lower() and float(serie.max()) > 1e6:
        # millones de ARS -> billones de ARS (10^12) para evitar la notación científica
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
            lambda v, _: f"{v / 1e6:.0f}"))
        unidad = unidad.replace("millones", "billones").replace("Millones", "Billones")
    ax.set_ylabel("nivel (unidades sintéticas)" if "SINT" in rotulo else unidad,
                  fontsize=8, color="#52514e")
    ax.set_title(rotulo, fontsize=8, color="#52514e", loc="left")
    ax.tick_params(labelsize=8, colors="#52514e")
    import matplotlib.dates
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y-%m"))
    ax.set_xlabel("mes (promedio de días hábiles)", fontsize=8, color="#52514e")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#e6e5e1", lw=0.6)
    ax.legend(fontsize=7.5, frameon=False, loc="upper left", ncol=2)
    fig.tight_layout()
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta)
    plt.close(fig)
    return ruta


def main(argv: list[str] | None = None) -> str:
    """Punto de entrada de línea de comandos."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--demo", action="store_true", help="datos sintéticos de demostración")
    g.add_argument("--csv", help="CSV fecha,valor de base o M2 (diario o mensual)")
    ap.add_argument("--trimestres", type=int, default=4)
    ap.add_argument("--ventana", type=int, default=36, help="meses para la deriva del programa")
    ap.add_argument("--desde", default=None, help="primer mes de la muestra (AAAA-MM)")
    ap.add_argument("--figura", default=None, help="ruta del fan chart (PDF o PNG)")
    a = ap.parse_args(argv)
    if a.demo:
        serie = demo_agregado_mensual()
        rotulo = ROTULO_SINTETICO + " (shock agregado en los dos últimos meses)"
    else:
        # Promedio mensual sólo de meses completos (se descarta un último mes parcial).
        serie, rotulo = a_mensual(meses_completos(cargar_csv(a.csv))), f"Datos: {a.csv}"
        if a.desde:
            serie = serie.loc[a.desde:]
    tabla = chequear_desvios(serie, a.trimestres, a.ventana)
    cols = ["mes", "h", "desvio_%", "inf_%", "sup_%", "estado"]
    texto = f"[{rotulo}]\nBanda central del 90 % por horizonte (cuantiles empíricos)\n" \
            + tabla[cols].round(1).to_string(index=False)
    print(texto)
    if a.figura:
        unidad = "nivel"
        meta = CARPETA_DATOS / f"metadata_{a.csv}.json"
        if a.csv and a.csv.isdigit() and meta.exists():
            cat = json.loads(meta.read_text(encoding="utf-8")).get("catalogo", {})
            unidad = cat.get("unidadExpresion", unidad).replace("En ", "").strip()
            desc = cat.get("descripcion", "").strip()
            rotulo = f"Datos reales: BCRA, API v4.0, id {a.csv} ({desc}), promedio mensual"
        fan_chart(serie, a.figura, ventana=a.ventana, rotulo=rotulo, unidad=unidad)
    return texto


if __name__ == "__main__":
    main()
