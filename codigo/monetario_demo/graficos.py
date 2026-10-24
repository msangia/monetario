"""Figuras de los anexos (Ejes 1 y 4): funciones de dibujo sobre resultados ya calculados.

Convenciones comunes a todas las figuras:

* **sin título dentro de la imagen**: el título, la fuente y la fecha van en el
  ``\\caption`` de LaTeX;
* ancho de 6,3 pulgadas (16 cm, el ancho de texto A4 con márgenes de 2,5 cm): incluidas
  a ``\\linewidth`` los rótulos quedan a su tamaño nominal (9,5 pt; nunca menos de 9 pt);
* paleta de Okabe e Ito (apta para daltonismo) con el mismo significado en todas las
  figuras cuando se repite una categoría (azul: período completo 2022-2026; naranja:
  desde el 11-07-2025; bermellón: alertas, fuera de banda o metas);
* ejes rotulados con unidades y coma decimal.

Las funciones reciben tablas (``pandas``) y una ruta, y devuelven la ruta escrita. Los
datos los calculan ``correr_reales.py`` y ``monetario_demo.factores``; aquí sólo se
dibuja, salvo :func:`perfil_por_posicion`, que resume errores por posición en el mes.

Uso (datos sintéticos de demostración, rotulados en el nombre del archivo)::

    python -m monetario_demo.graficos --demo
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

# Paleta de Okabe e Ito (2008), apta para daltonismo.
AZUL, NARANJA, BERMELLON = "#0072B2", "#E69F00", "#D55E00"
CELESTE, VERDE, PURPURA, GRIS = "#56B4E9", "#009E73", "#CC79A7", "#595959"
GRIS_CLARO, GRILLA = "#BDBDBD", "#E6E6E6"
ANCHO = 6.3            # pulgadas: ancho de texto A4 con márgenes de 2,5 cm
FUENTE = 9.5           # pt a tamaño de inclusión (\linewidth)


def _plt():
    """Importa matplotlib sin pantalla y fija el estilo común."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": FUENTE, "axes.labelsize": FUENTE, "xtick.labelsize": FUENTE,
        "ytick.labelsize": FUENTE, "legend.fontsize": FUENTE, "axes.titlesize": FUENTE,
        "axes.edgecolor": GRIS, "axes.labelcolor": "#222222", "xtick.color": "#222222",
        "ytick.color": "#222222", "axes.spines.top": False, "axes.spines.right": False,
        "legend.frameon": False, "pdf.fonttype": 42, "axes.titlelocation": "left"})
    return plt


def coma(v: float, decimales: int = 1) -> str:
    """Número con coma decimal (``0.95`` -> ``"0,95"``)."""
    return f"{v:.{decimales}f}".replace(".", ",").replace("-", "−")


def _formato_coma(ax, eje: str = "y", decimales: int = 1) -> None:
    import matplotlib.ticker as mt
    f = mt.FuncFormatter(lambda v, _: coma(v, decimales))
    (ax.yaxis if eje == "y" else ax.xaxis).set_major_formatter(f)


def _guardar(fig, ruta: str | Path) -> Path:
    import matplotlib.pyplot as plt
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    return ruta


# --------------------------------------------------------------------------- (a) varianza

def fig_varianza(base: pd.DataFrame, factores: pd.DataFrame, ruta: str | Path) -> Path:
    """Quién mueve la base: participación en la varianza diaria (dos paneles).

    Args:
        base: filas = períodos (rótulo), columna ``cuentas_corrientes`` (participación
            de las cuentas corrientes en la varianza de la base, tanto por uno, como en
            :func:`monetario_demo.liquidez.descomponer_varianza`).
        factores: filas = factores (rótulo), columnas = períodos (dos), participación
            en la varianza de la variación de las cuentas corrientes, tanto por uno.
        ruta: archivo de salida (PDF o PNG).
    """
    plt = _plt()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(ANCHO, 2.2), layout="constrained",
                                 gridspec_kw={"width_ratios": [1, 1.75]})
    # Izquierda: participación de las cuentas corrientes en la varianza de la base
    # (circulación y covarianza, de 1 % cada una, van en la nota de la figura).
    yb = np.arange(len(base))[::-1]
    v = 100 * base["cuentas_corrientes"].to_numpy(float)
    a1.barh(yb, v, 0.55, color=VERDE)
    for yi, vi in zip(yb, v):
        a1.text(vi - 2, yi, coma(vi), va="center", ha="right", color="white",
                fontsize=FUENTE, fontweight="bold")
    a1.set_yticks(yb, base.index)
    a1.set_xlim(0, 100)
    a1.set_xlabel("% de la varianza diaria\nde la base")
    a1.grid(axis="x", color=GRILLA, lw=0.6)
    a1.set_axisbelow(True)
    # Derecha: factores (de arriba hacia abajo en el orden recibido).
    y = np.arange(len(factores))[::-1]
    colores = (AZUL, NARANJA)
    h = 0.4
    for j, per in enumerate(factores.columns):
        vals = 100 * factores[per].to_numpy(float)
        yy = y + (0.5 - j) * h
        a2.barh(yy, np.nan_to_num(vals), h, color=colores[j], label=per)
        for yi, vi in zip(yy, vals):
            if not np.isnan(vi):
                a2.text(vi + (1 if vi >= 0 else -1), yi, coma(vi), va="center",
                        ha="left" if vi >= 0 else "right", fontsize=FUENTE - 0.5)
    a2.set_yticks(y, factores.index)
    a2.axvline(0, color=GRIS, lw=0.8)
    todos = 100 * factores.to_numpy(float)
    a2.set_xlim(min(-20.0, float(np.nanmin(todos)) - 17), max(70.0, float(np.nanmax(todos)) + 12))
    a2.set_xlabel("% de la varianza diaria\nde las cuentas corrientes")
    a2.grid(axis="x", color=GRILLA, lw=0.6)
    a2.set_axisbelow(True)
    a2.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, handlelength=1.0,
               borderaxespad=0.2)
    return _guardar(fig, ruta)


# --------------------------------------------------------------------------- (b) MAE relativo

def fig_mae_relativo(mae: pd.DataFrame, p: pd.DataFrame, ruta: str | Path,
                     meta: float | None = None, alfa: float = 0.10,
                     xlim: tuple[float, float] | None = None,
                     rotulo_meta: str = "meta", leyenda: str | None = None) -> Path:
    """Error relativo al ingenuo por serie (filas) y período (columnas), con significancia.

    Puntos llenos: el modelo erra menos que el ingenuo con p (Diebold-Mariano con
    corrección HLN, unilateral) menor que ``alfa``; huecos: no significativo. Línea
    vertical en 1 (igual error que el ingenuo) y, si se da, en ``meta``.

    Args:
        mae: MAE relativo al ingenuo; índice = series o modelos; columnas = períodos.
        p: p-valores con la misma forma que ``mae``.
        ruta: archivo de salida.
        meta: umbral a marcar (p. ej., 0,95 del indicador (i)).
        leyenda: ubicación de la leyenda dentro del gráfico (p. ej., ``"lower left"``)
            si hay una zona vacía; por defecto, debajo del eje.
    """
    plt = _plt()
    colores = (AZUL, NARANJA, VERDE)
    marcas = ("o", "s", "D")
    n, k = mae.shape
    fig, ax = plt.subplots(figsize=(ANCHO, 0.32 * n + (0.75 if leyenda else 1.2)),
                           layout="constrained")
    y = np.arange(n)[::-1]
    sep = 0.26 if k > 1 else 0
    for j, per in enumerate(mae.columns):
        yy = y + ((k - 1) / 2 - j) * sep
        v = mae[per].to_numpy(float)
        sig = p[per].to_numpy(float) < alfa
        ax.scatter(v[sig], yy[sig], s=46, marker=marcas[j], color=colores[j], zorder=3,
                   label=f"{per}")
        ax.scatter(v[~sig], yy[~sig], s=46, marker=marcas[j], facecolor="white",
                   edgecolor=colores[j], lw=1.5, zorder=3)
        for xi, yi in zip(v, yy):
            ax.annotate(coma(xi, 2), (xi, yi), xytext=(6, 0), textcoords="offset points",
                        va="center", ha="left", fontsize=FUENTE - 0.5, color="#222222")
    ax.axvline(1, color=GRIS, lw=1.1)
    ax.text(1.0, n - 0.35, " igual al ingenuo", ha="left", va="bottom", color=GRIS,
            fontsize=FUENTE - 0.5)
    if meta is not None:
        ax.axvline(meta, color=BERMELLON, lw=1.1, ls="--")
        # Rótulo abajo, para no competir con la leyenda ni con "igual al ingenuo".
        ax.text(meta, -0.55, f"{rotulo_meta} ({coma(meta, 2)}) ", ha="right", va="bottom",
                color=BERMELLON, fontsize=FUENTE - 0.5)
    ax.set_yticks(y, mae.index)
    ax.set_ylim(-0.6, n - 0.1)
    if xlim:
        ax.set_xlim(*xlim)
    _formato_coma(ax, "x", 1)
    ax.set_xlabel("error absoluto medio relativo al ingenuo (menos de 1: el modelo erra menos)")
    ax.grid(axis="x", color=GRILLA, lw=0.6)
    ax.set_axisbelow(True)
    # Leyenda: períodos (color) y significancia (relleno).
    from matplotlib.lines import Line2D
    extra = [Line2D([], [], marker="o", ls="none", color=GRIS, ms=7,
                    label=f"lleno: significativa (p < {coma(alfa, 2)})"),
             Line2D([], [], marker="o", ls="none", mfc="white", mec=GRIS, mew=1.5, ms=7,
                    label="hueco: no significativa")]
    h, _ = ax.get_legend_handles_labels()
    if leyenda:
        todos = h + extra
        ax.legend(todos, [o.get_label() for o in todos], loc=leyenda, ncol=1,
                  fontsize=FUENTE - 0.5, handletextpad=0.3, borderaxespad=0.3,
                  labelspacing=0.25, frameon=True, framealpha=0.95, edgecolor="none")
        return _guardar(fig, ruta)
    # Primera fila: períodos; segunda: significancia (matplotlib llena por columnas).
    vacio = Line2D([], [], ls="none", label=" ")
    segunda = extra + [vacio] * max(0, k - len(extra))
    orden = [x for par in zip(h, segunda) for x in par] + segunda[len(h):]
    fig.legend(orden, [o.get_label() for o in orden], loc="outside lower center",
               ncol=max(k, 2), columnspacing=1.2, handletextpad=0.3)
    return _guardar(fig, ruta)


# --------------------------------------------------------------------------- (c) perfil del mes

def perfil_por_posicion(errores: pd.Series, posiciones: pd.DataFrame, k: int = 5,
                        z: float = 1.645) -> pd.DataFrame:
    """Error medio por posición del día hábil en el mes: primeros y últimos ``k`` días.

    Args:
        errores: observado menos pronóstico (índice = días).
        posiciones: columnas ``pos`` (1 = primer día hábil) y ``pos_fin`` (1 = último),
            con el mismo índice (p. ej., ``factores._posiciones``).
        k: cantidad de días al inicio y al fin.
        z: cuantil normal del intervalo de la media (1,645: 90 %).

    Returns:
        DataFrame con índice ``"1".."k"`` (inicio) y ``"-k".."-1"`` (fin; -1 = último
        día hábil) y columnas ``media``, ``inf``, ``sup``, ``n``. Los días que son a la
        vez de inicio y de fin (meses muy cortos) cuentan en ambos grupos.
    """
    e = errores.dropna()
    p = posiciones.reindex(e.index)
    filas = {}
    for j in range(1, k + 1):
        filas[str(j)] = e[p["pos"].to_numpy() == j]
    for j in range(k, 0, -1):
        filas[str(-j)] = e[p["pos_fin"].to_numpy() == j]
    out = pd.DataFrame({c: {"media": s.mean(), "ee": s.std(ddof=1) / np.sqrt(len(s)),
                            "n": len(s)} for c, s in filas.items()}).T
    out["inf"] = out["media"] - z * out["ee"]
    out["sup"] = out["media"] + z * out["ee"]
    out["n"] = out["n"].astype(int)
    return out[["media", "inf", "sup", "n"]]


def fig_perfil_mes(perfiles: dict[str, pd.DataFrame], ruta: str | Path,
                   banda: str | None = None, ylabel: str = "error medio (pp de la base)") -> Path:
    """Perfil del error medio por posición en el mes (huella de inicio y fin de mes).

    Args:
        perfiles: rótulo -> salida de :func:`perfil_por_posicion` (mismo índice).
        banda: rótulo cuyo intervalo del 90 % de la media se sombrea (p. ej., el ingenuo).
        ruta: archivo de salida.
    """
    plt = _plt()
    estilos = ((AZUL, "o", "-"), (NARANJA, "s", "--"), (VERDE, "D", ":"), (PURPURA, "^", "-."))
    idx = list(next(iter(perfiles.values())).index)
    k = sum(1 for c in idx if not c.startswith("-"))
    x = np.r_[np.arange(k), np.arange(k) + k + 1]           # hueco en el medio del mes
    fig, ax = plt.subplots(figsize=(ANCHO, 2.1), layout="constrained")
    ax.axvspan(x[-2] - 0.45, x[-1] + 0.45, color="#F3E3D3", lw=0, zorder=0)
    ax.text(x[-1] + 0.4, 0.03, "fin de mes (dos últimos\ndías hábiles)", ha="right",
            va="bottom", transform=ax.get_xaxis_transform(), fontsize=FUENTE - 0.5,
            color=BERMELLON)
    ax.axhline(0, color=GRIS, lw=0.9)
    for (rot, t), (color, marca, ls) in zip(perfiles.items(), estilos):
        if rot == banda:
            ax.fill_between(x[:k], t["inf"].iloc[:k], t["sup"].iloc[:k], color=color,
                            alpha=0.15, lw=0)
            ax.fill_between(x[k:], t["inf"].iloc[k:], t["sup"].iloc[k:], color=color,
                            alpha=0.15, lw=0, label=f"{rot}: IC 90 % de la media")
        for tramo in (slice(0, k), slice(k, 2 * k)):
            ax.plot(x[tramo], t["media"].iloc[tramo], color=color, marker=marca, ls=ls,
                    lw=1.4, ms=5, label=rot if tramo.start == 0 else None)
    etiquetas = [f"{j}" for j in range(1, k + 1)] + [
        "últ." if c == "-1" else c.replace("-", "−") for c in idx[k:]]
    ax.set_xticks(x, etiquetas)
    ax.set_xlabel("día hábil desde el inicio del mes"  + " " * 30
                  + "día hábil contado desde el fin del mes")
    ax.set_ylabel(ylabel)
    _formato_coma(ax, "y", 1)
    ax.grid(axis="y", color=GRILLA, lw=0.6)
    ax.set_axisbelow(True)
    # Leyenda en la zona libre de la mitad del mes (arriba, al centro).
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=2, columnspacing=1.0,
              fontsize=FUENTE - 0.5, handlelength=2.2, borderaxespad=0.2, labelspacing=0.25)
    ymin, ymax = ax.get_ylim()
    ax.set_ylim(ymin, ymax + 0.35 * (ymax - ymin))
    return _guardar(fig, ruta)


# --------------------------------------------------------------------------- (e) cobertura

def fig_cobertura(tablas: dict[str, pd.DataFrame], ruta: str | Path,
                  programas: dict[str, str], nominal: float = 0.9) -> Path:
    """Cobertura empírica de la banda del 90 % y su ancho, por programa y horizonte.

    Args:
        tablas: agregado (rótulo) -> salida de :func:`monetario_demo.programa.comparar`
            (columnas ``programa``, ``h``, ``cobertura_90``, ``ancho_90_pp``).
        programas: clave de programa -> rótulo corto, en el orden a mostrar.
        nominal: cobertura nominal (línea de referencia).
    """
    plt = _plt()
    colores = {1: CELESTE, 2: AZUL, 3: "#003F6B"}
    fig, ejes = plt.subplots(2, len(tablas), figsize=(ANCHO, 2.6), sharex=True,
                             sharey="row", layout="constrained",
                             gridspec_kw={"height_ratios": [1.7, 1]})
    ejes = np.atleast_2d(ejes).reshape(2, len(tablas))
    claves = list(programas)
    x = np.arange(len(claves))
    w = 0.26
    for c, (nombre, t) in enumerate(tablas.items()):
        a_cob, a_anc = ejes[0, c], ejes[1, c]
        for h in (1, 2, 3):
            s = t[t["h"] == h].set_index("programa").reindex(claves)
            v = 100 * s["cobertura_90"].to_numpy(float)
            a_cob.bar(x + (h - 2) * w, v, w, color=colores[h],
                      label=f"h = {h} {'mes' if h == 1 else 'meses'}")
            # Cifra dentro de cada barra (vertical), para leer la cobertura exacta.
            for xi, vi in zip(x + (h - 2) * w, v):
                a_cob.text(xi, vi - 1.2, coma(vi), rotation=90, ha="center", va="top",
                           fontsize=FUENTE - 0.5, color="#222222" if h == 1 else "white")
            a_anc.bar(x + (h - 2) * w, s["ancho_90_pp"], w, color=colores[h])
        a_cob.axhline(100 * nominal, color=BERMELLON, lw=1.2, ls="--", zorder=0.5)
        a_cob.set_ylim(40, 100)
        a_cob.text(0.01, 1.0, nombre, transform=a_cob.transAxes, ha="left", va="bottom",
                   fontsize=FUENTE, fontweight="bold", color="#222222")
        for a in (a_cob, a_anc):
            a.grid(axis="y", color=GRILLA, lw=0.6)
            a.set_axisbelow(True)
        a_anc.set_xticks(x, [programas[k] for k in claves])
    ejes[0, 0].set_ylabel("cobertura (%)")
    ejes[1, 0].set_ylabel("ancho (pp)")
    ejes[0, -1].text(len(claves) - 0.5, 100 * nominal + 0.8, f"nominal {int(100 * nominal)} %",
                     ha="right", va="bottom", color=BERMELLON, fontsize=FUENTE - 0.5)
    ejes[0, -1].set_ylim(40, 100)
    h, l = ejes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="outside lower center", ncol=3)
    return _guardar(fig, ruta)


# --------------------------------------------------------------------------- (f) estabilidad

def fig_estabilidad(ventanas: dict[str, pd.DataFrame], completa: dict[str, float],
                    ruta: str | Path, ventana: int = 60, umbral: float = 0.10) -> Path:
    """Estabilidad de la demanda de dinero en ventanas móviles (dos paneles).

    Izquierda: coeficientes de largo plazo del primer agregado (``b_y``, ``b_i``) por
    fin de ventana, con la estimación de la muestra completa en línea fina. Derecha:
    p-valor de Engle-Granger de cada agregado; por debajo de ``umbral`` habría
    cointegración.

    Args:
        ventanas: agregado (rótulo) -> salida de
            :func:`monetario_demo.demanda_dinero.ventanas_moviles` (``b_y``, ``b_i``,
            ``p_coint``; índice = fin de ventana).
        completa: ``b_y`` y ``b_i`` de la muestra completa del primer agregado.
    """
    plt = _plt()
    import matplotlib.dates as md
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(ANCHO, 2.6), layout="constrained")
    primero = next(iter(ventanas))
    r = ventanas[primero]
    for col, rot, color, ls in (("b_y", "elasticidad ingreso ($b_y$)", VERDE, "-"),
                                ("b_i", "semielasticidad tasa ($b_i$)", PURPURA, "--")):
        a1.plot(r.index, r[col].astype(float), color=color, lw=1.6, ls=ls, label=rot)
        a1.axhline(completa[col], color=color, lw=0.8, ls=":")
    a1.axhline(0, color=GRIS, lw=0.8)
    a1.set_ylabel(f"coeficiente de largo plazo, {primero}")
    _formato_coma(a1, "y", 1)
    a1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.27), ncol=1, borderaxespad=0)
    for (nombre, t), color, ls in zip(ventanas.items(), (AZUL, NARANJA), ("-", "--")):
        a2.plot(t.index, t["p_coint"].astype(float), color=color, lw=1.6, ls=ls, label=nombre)
    a2.axhspan(0, umbral, color="#F3E3D3", lw=0)
    a2.text(a2.get_xlim()[0], umbral / 2, f"  zona de cointegración (p < {coma(umbral, 2)})",
            va="center", fontsize=FUENTE - 0.5, color=BERMELLON)
    a2.set_ylim(0, 1)
    a2.set_ylabel("p-valor de Engle-Granger")
    _formato_coma(a2, "y", 1)
    a2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.27), ncol=1, borderaxespad=0)
    for a in (a1, a2):
        a.xaxis.set_major_locator(md.YearLocator())
        a.xaxis.set_major_formatter(md.DateFormatter("%Y"))
        a.set_xlabel(f"último mes de la ventana de {ventana} meses")
        a.set_axisbelow(True)
        a.grid(axis="y", color=GRILLA, lw=0.6)
    return _guardar(fig, ruta)


# --------------------------------------------------------------------------- demo

def demo(carpeta: str | Path = "salidas", semilla: int = 426) -> list[Path]:
    """Dibuja todas las figuras con DATOS SINTÉTICOS DE DEMOSTRACIÓN, NO OFICIALES.

    Sirve para probar el dibujo sin los CSV reales; los archivos llevan ``demo`` en el
    nombre para no confundirlos con las figuras de los anexos.
    """
    rng = np.random.default_rng(semilla)
    c = Path(carpeta)
    base = pd.DataFrame({"cuentas_corrientes": [0.96, 0.97], "circulacion": [0.03, 0.02],
                         "covarianza": [0.01, 0.01]}, index=["período 1", "período 2"])
    fac = pd.DataFrame({"período 1": [0.5, 0.3, 0.2], "período 2": [0.6, np.nan, 0.4]},
                       index=["factor A", "factor B", "resto"])
    mae = pd.DataFrame({"período 1": [0.6, 1.02], "período 2": [0.8, 1.05]},
                       index=["serie A", "serie B"])
    p = pd.DataFrame({"período 1": [0.001, 0.7], "período 2": [0.04, 0.9]}, index=mae.index)
    idx = pd.bdate_range("2020-01-01", periods=600)
    from .datos import posicion_en_mes
    pos, pos_fin = posicion_en_mes(idx)
    posic = pd.DataFrame({"pos": pos, "pos_fin": pos_fin}, index=idx)
    e = pd.Series(rng.normal(0, 1, len(idx)) + 1.2 * (pos_fin <= 2), index=idx)
    t = pd.DataFrame([{"programa": k, "h": h, "cobertura_90": 0.9 - 0.05 * h * j,
                       "ancho_90_pp": 5 * h * (1 + j)} for j, k in enumerate(("a", "b"))
                      for h in (1, 2, 3)])
    fin = pd.date_range("2018-01-31", periods=40, freq="ME")
    ven = pd.DataFrame({"b_y": rng.normal(0.5, 0.3, 40), "b_i": rng.normal(-0.5, 0.2, 40),
                        "p_coint": rng.uniform(0.2, 0.9, 40)}, index=fin)
    return [fig_varianza(base, fac, c / "fig_demo_varianza.pdf"),
            fig_mae_relativo(mae, p, c / "fig_demo_mae.pdf", meta=0.95),
            fig_perfil_mes({"modelo": perfil_por_posicion(e, posic)},
                           c / "fig_demo_perfil.pdf", banda="modelo"),
            fig_cobertura({"agregado": t}, c / "fig_demo_cobertura.pdf", {"a": "(a)", "b": "(b)"}),
            fig_estabilidad({"agregado": ven}, {"b_y": 0.5, "b_i": -0.5},
                            c / "fig_demo_estabilidad.pdf")]


def main(argv: list[str] | None = None) -> list[Path]:
    """Punto de entrada: ``--demo`` dibuja las figuras con datos sintéticos rotulados."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--demo", action="store_true", required=True,
                    help="DATOS SINTÉTICOS DE DEMOSTRACIÓN, NO OFICIALES")
    ap.add_argument("--carpeta", default="salidas")
    a = ap.parse_args(argv)
    rutas = demo(a.carpeta)
    print("DATOS SINTÉTICOS DE DEMOSTRACIÓN, NO OFICIALES:\n" + "\n".join(map(str, rutas)))
    return rutas


if __name__ == "__main__":
    main()
