"""Corre las rutinas A, B y C con los datos reales de ``datos/`` y guarda las salidas.

Escribe en ``codigo/salidas/``:

* ``real_verificacion_datos.txt``: tabla de ``verificar_series.py``, controles de
  calidad (:mod:`monetario_demo.calidad`), controles cruzados y empalme del IPC;
* ``real_liquidez.txt`` (rutina A: base, billetes, circulación, cuentas corrientes en
  el BCRA y pronóstico de la base por componentes);
* ``real_demanda_dinero.txt`` (rutina B: M2 (109) y base (15) reales con el IPC
  oficial de INDEC, desde dic-2016, EMAE s.e. y plazo fijo (1189) o BAIBAR (11), tasa
  en nivel y en log, y la submuestra 2017-2019; el IPC empalmado previo a 2016-12, de
  fuente no documentada, se descarta);
* ``real_bandas.txt`` (rutina C: programas de deriva, deriva estacional, velocidad y
  demanda MCE para M2 (109) y base (15), banda del 90 % y chequeo de desvíos) y
  ``fan_chart_real.pdf`` (M2, programa MCE armado en el último trimestre) y
  ``chequeo_real.pdf`` (M2, programa MCE: los cuatro trimestres chequeados, con la
  banda del 90 % y los meses fuera de banda);
* figuras de los anexos (sin título; :mod:`monetario_demo.graficos`):
  ``fig_varianza.pdf`` y ``fig_mae_componentes.pdf`` (A.1), ``fig_estabilidad.pdf`` (B) y
  ``fig_cobertura.pdf`` (C). Las de A.2 (``fig_cc_modelos.pdf``, ``fig_perfil_mes.pdf``)
  las escribe ``python -m monetario_demo.factores --reales --figuras salidas``.

Cada archivo lleva un encabezado con la fuente, el último dato de cada serie usada
y la fecha de ejecución. Las especificaciones (muestras, ventanas, variantes) están
fijadas aquí y se reportan todas, también las que no funcionan.

Uso (desde ``codigo/``)::

    python correr_reales.py
"""

from __future__ import annotations

import contextlib
import io
from datetime import datetime
from pathlib import Path

import pandas as pd

from monetario_demo import (bandas, calidad, demanda_dinero, factores, graficos,
                            liquidez, programa)
from monetario_demo.datos import (CARPETA_DATOS, cargar_csv, cargar_emae,
                                  cargar_ipc, cargar_ipc_historico)
import verificar_series

SALIDAS = Path(__file__).resolve().parent / "salidas"
DESCRIPCION = {15: "base monetaria", 16: "circulación monetaria",
               17: "billetes y monedas en poder del público",
               104: "depósitos del sector privado (incluye ME)",
               109: "M2 (público + cuentas a la vista en pesos, sectores privado y público)",
               197: "M2 transaccional privado", 46: "factores de explicación de la base (flujo)",
               11: "BAIBAR", 150: "pases entre terceros a 1 día",
               1189: "plazo fijo en pesos", 44: "TAMAR"}


def encabezado(ids: list[int], extra: list[str] | None = None) -> str:
    """Encabezado común: fuente, último dato de cada serie y fecha de ejecución."""
    lineas = ["# DATOS REALES. Fuente: BCRA, API de Estadísticas Monetarias v4.0 "
              "(archivos datos/bcra_<id>_daily.csv); INDEC (EMAE, IPC) cuando se indica."]
    for i in ids:
        s = cargar_csv(str(i))
        lineas.append(f"#   id {i} ({DESCRIPCION.get(i, '')}): {s.index[0]:%Y-%m-%d} a "
                      f"{s.index[-1]:%Y-%m-%d} (último dato)")
    lineas += [f"#   {e}" for e in (extra or [])]
    lineas.append(f"# Ejecución: {datetime.now():%Y-%m-%d %H:%M}")
    return "\n".join(lineas) + "\n"


def _capturar(funcion, *args) -> str:
    """Ejecuta ``funcion`` capturando lo que imprime (las rutinas imprimen y devuelven)."""
    with contextlib.redirect_stdout(io.StringIO()):
        return funcion(*args)


def verificacion() -> str:
    """Tabla de IDs, calidad de datos y empalme del IPC."""
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        verificar_series.main(["--series", str(Path(verificar_series.__file__).with_name(
            "series.txt")), "--desde", "2003-01-01"])
    ipc = cargar_ipc_historico()
    return "\n".join([
        encabezado(list(DESCRIPCION)), "## verificar_series.py --desde 2003-01-01",
        salida.getvalue(), "## Calidad (monetario_demo.calidad)",
        calidad.informe_calidad(list(DESCRIPCION)), "",
        "## Controles cruzados", calidad.controles_cruzados(), "",
        "## IPC (DESCARTADO para B y C: el tramo previo a 2016-12 de ipc_historico.csv "
        "es de fuente no documentada; sólo se controla que coincida con INDEC después)",
        ipc.attrs["empalme"],
        f"Serie empalmada: {ipc.index[0]:%Y-%m} a {ipc.index[-1]:%Y-%m}, {len(ipc)} meses."])


PERIODOS_A = (("2022-01 a 2026-10", {}), ("desde 2025-07-11", {"desde": "2025-07-11"}),
              ("últimos 60 días", {"ultimos": 60}))


DIA_LEFI = "2025-07-10"   # la base sube 30 % en un día (fin de las LEFI)


def ahorro_pp_base(modelo: pd.DataFrame, ingenuo: pd.DataFrame, peso: pd.Series,
                   desde: str | None = None, ultimos: int | None = None) -> float:
    """Significancia económica: reducción del MAE expresada en puntos porcentuales de la base.

    Los errores están en % del nivel previo de cada serie; se ponderan por el peso de la
    serie en la base el día anterior (``peso`` = serie / base), de modo que las mejoras
    de distintas series se comparan con la misma vara (el MAE ingenuo de la base).
    """
    m, g = modelo.loc[desde:], ingenuo.loc[desde:]
    if ultimos:
        m, g = m.iloc[-ultimos:], g.iloc[-ultimos:]
    w = peso.shift(1).reindex(m.index)
    return float(((g["obs"] - g["pron"]).abs() * w).mean()
                 - ((m["obs"] - m["pron"]).abs() * w).mean())


def rutina_a() -> str:
    """Rutina A: base (15), billetes (17), circulación (16), cuentas corrientes (15 - 16)
    y la base pronosticada por componentes. El total de factores (46) no se usa como
    regresor: es idéntico a la variación de la base (ver real_verificacion_datos.txt)."""
    partes = [encabezado([15, 16, 17, 46]),
              "Muestra: desde 2010-01-04; evaluación fuera de muestra desde 2022-01-03; "
              "reestimación cada 60 días hábiles. Feriados: días sin dato de la serie.",
              "Factores (46): el total es igual, día por día, a la variación de la base (15); "
              "usarlo el mismo día es look-ahead (es la variable a pronosticar) y rezagado "
              "repite la variación de ayer, que el AR(1) del ARIMAX ya incluye. Sólo los "
              "componentes (compras de divisas, Tesoro, pases...) conocidos o programados de "
              "antemano agregarían información; no están entre las series descargadas."]
    base, circ = cargar_csv("15").loc["2010-01-04":], cargar_csv("16").loc["2010-01-04":]
    cc = (base - circ).rename("cuentas_corrientes_bcra")
    resumen, sensib = [], []
    pesos = {"base (15)": base / base, "base (15), móvil 500": base / base,
             "billetes (17)": cargar_csv("17").loc["2010-01-04":] / base,
             "circulación (16)": circ / base, "cuentas corrientes en el BCRA (15 - 16)": cc / base}
    for nombre, nivel, ventana in (("base (15)", base, None), ("base (15), móvil 500", base, 500),
                                   ("billetes (17)", cargar_csv("17").loc["2010-01-04":], None),
                                   ("circulación (16)", circ, None),
                                   ("cuentas corrientes en el BCRA (15 - 16)", cc, None)):
        pronos = liquidez.pronostico_fuera_de_muestra(nivel, "2022-01-03", cada=60,
                                                      ventana=ventana)
        if nombre.startswith("base (15)") and ventana is None:
            ingenuo_base = pronos["ingenuo"]
        for etiqueta, kw in PERIODOS_A:
            ev = liquidez.evaluar(pronos, **kw)
            partes.append(liquidez.informe(ev, f"{nombre}; {etiqueta}"))
            sp = ev["sesgo_posicion"]
            resumen.append({"serie": nombre, "periodo": etiqueta, "n": ev["n"],
                            "MAE_rel": ev["tabla"].loc["ensamble", "MAE_rel"],
                            "p_DM": ev["dm"].p_valor,
                            "cob90": ev["tabla"].loc["ensamble", "cobertura"],
                            "ahorro_pp_base": ahorro_pp_base(pronos["ensamble"],
                                                             pronos["ingenuo"], pesos[nombre],
                                                             **kw),
                            "sesgo_fin_ens": sp.loc["fin de mes", "ensamble"],
                            "sesgo_fin_ing": sp.loc["fin de mes", "ingenuo"],
                            "sesgo_ini_ens": sp.loc["inicio de mes", "ensamble"],
                            "sesgo_ini_ing": sp.loc["inicio de mes", "ingenuo"]})
        if ventana is None and not nombre.startswith("billetes"):
            # Sensibilidad: 2022-2026 sin el día del salto de la base por las LEFI.
            sin = {m: d.drop(pd.Timestamp(DIA_LEFI), errors="ignore") for m, d in pronos.items()}
            ev = liquidez.evaluar(sin)
            e_ing = sin["ingenuo"]["obs"] - sin["ingenuo"]["pron"]
            sensib.append({"serie": nombre, "n": ev["n"],
                           "MAE_rel": ev["tabla"].loc["ensamble", "MAE_rel"],
                           "p_DM": ev["dm"].p_valor,
                           "cob90": ev["tabla"].loc["ensamble", "cobertura"],
                           "MAE_ingenuo": float(e_ing.abs().mean())})
    for cc_modelo in ("ingenuo", "ensamble"):
        comp = liquidez.pronostico_por_componentes(base, circ, "2022-01-03", 60,
                                                   cc_modelo=cc_modelo)
        for etiqueta, kw in PERIODOS_A:
            r = liquidez.evaluar_contra_ingenuo(comp, ingenuo_base, **kw)
            resumen.append({"serie": f"base por componentes (circ. ensamble + ctas. "
                                     f"{cc_modelo})", "periodo": etiqueta, "n": r["n"],
                            "MAE_rel": r["MAE_rel"], "p_DM": r["p_DM"], "cob90": r["cobertura"],
                            "ahorro_pp_base": ahorro_pp_base(comp, ingenuo_base, base / base,
                                                             **kw)})
    # Mismos días que la evaluación de pronósticos (la variación del primer día usa el
    # nivel del día hábil previo): n coincide con el de la tabla de resumen.
    descomp = {per: liquidez.descomponer_varianza(base, circ, per[0], per[1])
               for per in (("2010-01-05", "2021-12-31"), ("2022-01-03", None),
                           ("2025-07-11", None))}
    partes.insert(3, "## Resumen (ensamble vs. ingenuo; DM-HLN unilateral; cobertura del 90 %; "
                  "sesgo = observado - pronóstico, pp; ahorro_pp_base = MAE ingenuo - MAE ensamble, "
                  "en pp de la base, errores ponderados por el peso de la serie en la base)\n"
                  + pd.DataFrame(resumen).round(4).to_string(index=False)
                  + "\n\n## Varianza de la variación diaria de la base (en % de la base previa)\n"
                  + "Definición: dB_t = dC_t + dCC_t, con B = base (15), C = circulación (16) y "
                    "CC = cuentas corrientes de las entidades en el BCRA (15 - 16); cada variación "
                    "diaria en % de la base del día hábil anterior, de modo que var(dB) = var(dC) "
                    "+ var(dCC) + 2 cov(dC, dCC). Participación = término / var(dB) "
                    "(liquidez.descomponer_varianza).\n"
                  + "\n".join(f"{d['desde']:%Y-%m-%d} a {d['hasta']:%Y-%m-%d} (n = {d['n']} "
                               f"variaciones diarias): cuentas corrientes {d['cuentas_corrientes']:.1%}, "
                               f"circulación {d['circulacion']:.1%}, 2 cov {d['covarianza']:.1%}"
                               for d in descomp.values())
                  + f"\n\n## Sensibilidad: 2022-01 a 2026-10 sin el {DIA_LEFI} (salto de la base "
                    "por las LEFI; mismos pronósticos, se excluye ese día de la evaluación)\n"
                  + pd.DataFrame(sensib).round(4).to_string(index=False))
    figuras_a(pd.DataFrame(resumen), descomp)
    return "\n\n".join(partes) + "\n"


PERIODOS_FIG = {"2022-01 a 2026-10": "2022–2026", "desde 2025-07-11": "desde 11-07-2025",
                "últimos 60 días": "últimos 60 días"}
SERIES_FIG = {"circulación (16)": "Circulación (16)", "billetes (17)": "Billetes en público (17)",
              "cuentas corrientes en el BCRA (15 - 16)": "Ctas. ctes. en el BCRA (15−16)",
              "base (15)": "Base (15)",
              "base por componentes (circ. ensamble + ctas. ingenuo)": "Base por componentes"}
GRUPOS_FACTORES = {"Pases (52)": [52], "LEFI (58)": [58], "LELIQ y NOTALIQ (53)": [53],
                   "Otras del BCRA (59)": [59], "Tesoro, resto (51)": [51],
                   "Resto (47–50, 54, 55, circ.)": [47, 48, 49, 50, 54, 55, "circulacion",
                                                    "resto"]}


def tabla_figura_a(resumen: pd.DataFrame, columna: str) -> pd.DataFrame:
    """Pivota el resumen de la rutina A: filas = series de la figura, columnas = períodos."""
    t = resumen[resumen["serie"].isin(SERIES_FIG)].pivot(index="serie", columns="periodo",
                                                          values=columna)
    t = t.loc[list(SERIES_FIG), list(PERIODOS_FIG)]
    t.index = list(SERIES_FIG.values())
    t.columns = list(PERIODOS_FIG.values())
    return t


def participacion_por_grupo(y: pd.Series, F: pd.DataFrame, desde: str) -> pd.Series:
    """Participación de cada grupo de factores en la varianza de dCC (suma 1).

    Los grupos sin movimiento en el período (varianza nula) quedan como NaN.
    """
    t = factores.descomponer_por_factor(y, F, desde)
    out = {}
    for g, cols in GRUPOS_FACTORES.items():
        cols = [c for c in cols if c in t.index]
        out[g] = (float(t.loc[cols, "participacion"].sum())
                  if t.loc[cols, "varianza_propia"].sum() > 1e-6 else float("nan"))
    return pd.Series(out)


def figuras_a(resumen: pd.DataFrame, descomp: dict) -> list[Path]:
    """Figuras del Anexo A.1: quién mueve la base y error relativo por serie y período."""
    base = pd.DataFrame([{k: d[k] for k in ("cuentas_corrientes", "circulacion", "covarianza")}
                         for d in descomp.values()],
                        index=["2010–2021", "2022–2026", "desde 11-7-25"])
    y, F = factores.a_pp_base(factores.cargar_factores())
    fac = pd.DataFrame({"2022–2026": participacion_por_grupo(y, F, "2022-01-03"),
                        "desde 11-07-2025": participacion_por_grupo(y, F, "2025-07-11")})
    return [graficos.fig_varianza(base, fac, SALIDAS / "fig_varianza.pdf"),
            graficos.fig_mae_relativo(tabla_figura_a(resumen, "MAE_rel"),
                                      tabla_figura_a(resumen, "p_DM"),
                                      SALIDAS / "fig_mae_componentes.pdf", xlim=(0.45, 1.7), leyenda="lower left",
                                      columna=(1.3, 0.16, ["2022–26", "jul-25+", "60 días"]))]


ESPECIFICACIONES_B = (
    # (etiqueta, dinero, tasa, forma de la tasa, desde, hasta, ventana; None = sin ventanas)
    # Todas con el IPC oficial de INDEC (desde 2016-12); muestras fijadas de antemano.
    ("M2, plazo fijo, semielasticidad (principal)", "109", "1189", "nivel", "2017-01", None, 60),
    ("M2, plazo fijo, elasticidad (log i)", "109", "1189", "log", "2017-01", None, 60),
    ("M2, BAIBAR, semielasticidad", "109", "11", "nivel", "2017-01", None, 60),
    ("M2, BAIBAR, elasticidad (log i)", "109", "11", "log", "2017-01", None, 60),
    ("Base (15), plazo fijo, semielasticidad", "15", "1189", "nivel", "2017-01", None, 60),
    ("M2, plazo fijo, 2017-01 a 2019-12 (36 meses, sin ventanas)", "109", "1189", "nivel",
     "2017-01", "2019-12", None),
)


def rutina_b() -> str:
    """Rutina B: demanda de M2 (109) y base (15) reales con el IPC oficial de INDEC."""
    ipc = cargar_ipc()
    emae = cargar_emae()
    partes = [encabezado([109, 15, 1189, 11], [
        f"EMAE desestacionalizado (INDEC): {emae.index[0]:%Y-%m} a {emae.index[-1]:%Y-%m}",
        f"IPC oficial (INDEC, ipc_mensual.csv, dic-2016 = 100): {ipc.index[0]:%Y-%m} a "
        f"{ipc.index[-1]:%Y-%m}. No se usa el IPC empalmado previo (fuente no documentada)."]),
        "M2 (109) = M2 total (billetes y monedas en poder del público + cuentas a la vista en "
        "pesos de los sectores privado y público); el M2 transaccional privado (197) empieza "
        "en 2021. IPC observado (no inflación esperada). Especificaciones fijadas de antemano; "
        "se informan todas."]
    filas, ventanas_fig, completa_fig = [], {}, {}
    for etiqueta, d, tasa, forma, desde, hasta, ventana in ESPECIFICACIONES_B:
        df = demanda_dinero.armar_panel(cargar_csv(d), ipc, emae, cargar_csv(tasa), forma)
        df = df.loc[desde:hasta]
        if ventana is None:
            res = demanda_dinero.analizar_completa(df)
        else:
            res = demanda_dinero.analizar(df, ventana=ventana)
        c, rol, al = res["completa"], res.get("rolling"), res.get("alertas", {})
        if etiqueta.endswith("(principal)"):
            ventanas_fig["M2 (109)"], completa_fig = rol, c
        elif etiqueta.startswith("Base (15)"):
            ventanas_fig["Base (15)"] = rol
        fmt = lambda f: f.strftime("%Y-%m") if f is not None else "-"
        filas.append({
            "especificación": etiqueta, "muestra": f"{df.index[0]:%Y-%m} a {df.index[-1]:%Y-%m}",
            "n": len(df), "b_y": c["b_y"], "b_i": c["b_i"], "p_EG": c["p_coint"], "g": c["g"],
            "t_g": c["t_g"], "p_CUSUM": res["p_cusum"], "ventana": ventana or "-",
            "sin_coint_%": (100 * float((rol["p_coint"] > 0.10).mean())
                            if rol is not None else float("nan")),
            "ADF_niv_m/y/i": "/".join(f"{v:.2f}" for v in res["adf"]["p_niveles"]),
            "alerta_b_y": fmt(al.get("b_y")), "alerta_b_i": fmt(al.get("b_i"))})
        if ventana is None:
            partes.append(f"[{etiqueta}; dinero {d}, tasa {tasa} ({forma})]\n"
                          f"Panel {df.index[0]:%Y-%m} a {df.index[-1]:%Y-%m}: {len(df)} meses "
                          "(sin ventanas móviles; poder bajo)\n"
                          f"Muestra completa: b_y = {c['b_y']:.2f}, b_i = {c['b_i']:.2f}, "
                          f"p Engle-Granger = {c['p_coint']:.3f}, ajuste g = {c['g']:.3f} "
                          f"(t = {c['t_g']:.1f}); CUSUM p = {res['p_cusum']:.3f}")
        else:
            partes.append(demanda_dinero.informe(res, f"{etiqueta}; dinero {d}, tasa {tasa} "
                                                 f"({forma})", demanda_dinero.verificar_muestra(
                                                     df, ventana)))
    partes.insert(2, "## Resumen\n" + pd.DataFrame(filas).round(3).to_string(index=False))
    rango = ["## Ventanas móviles de 60 meses (figura fig_estabilidad.pdf): rango de los "
             "coeficientes y ventanas con p EG < 0,10"]
    for nombre, r in ventanas_fig.items():
        r = r.astype(float)
        rango.append(f"{nombre}: {len(r)} ventanas ({r.index[0]:%Y-%m} a {r.index[-1]:%Y-%m}); "
                     f"b_y {r['b_y'].min():.2f} a {r['b_y'].max():.2f}; b_i {r['b_i'].min():.2f} "
                     f"a {r['b_i'].max():.2f}; ventanas con p EG < 0,10: "
                     f"{int((r['p_coint'] < 0.10).sum())} (mínimo p = {r['p_coint'].min():.3f})")
    partes.insert(3, "\n".join(rango))
    graficos.fig_estabilidad(ventanas_fig, completa_fig, SALIDAS / "fig_estabilidad.pdf")
    return "\n\n".join(partes) + "\n"


PROGRAMAS_FIG = {"deriva": "(a)\nderiva", "deriva_estacional": "(b)\nestac.",
                 "velocidad": "(c)\nveloc.", "mce": "(d)\nMCE", "mce_sin_estac": "(e)\nMCE s/m"}


def rutina_c() -> str:
    """Rutina C: programas y banda para M2 (109) y base (15); deriva para 197 (referencia)."""
    partes = [encabezado([109, 15, 1189, 197], [
        f"EMAE desestacionalizado (INDEC) hasta {cargar_emae().index[-1]:%Y-%m}; "
        "IPC oficial de INDEC desde 2016-12 (sin empalme previo)"]),
        "Promedios mensuales de meses completos (se descarta 2026-10, parcial). Programas: "
        "deriva (36 meses) y deriva estacional (efectos de 72 meses), con toda la historia "
        "del agregado; velocidad constante y demanda MCE (ventana de 48 meses desde 2016-12, "
        "plazo fijo 1189, dummies mensuales), que necesitan el IPC oficial. Orígenes "
        "evaluados desde 2021-01. Velocidad y MCE son condicionales al IPC, EMAE y tasa "
        "observados. Ninguno es el programa del BCRA."]
    partes.append("## M2 (109)\n" + _capturar(programa.main, [
        "--dinero", "109", "--tasa", "1189", "--figura", str(SALIDAS / "fan_chart_real.pdf"),
        "--figura-chequeo", str(SALIDAS / "chequeo_real.pdf"),
        "--tabla-csv", str(SALIDAS / "real_programa_109.csv")]))
    partes.append("## Base monetaria (15)\n" + _capturar(programa.main, [
        "--dinero", "15", "--tasa", "1189", "--tabla-csv", str(SALIDAS / "real_programa_15.csv")]))
    graficos.fig_cobertura({"M2 (109)": pd.read_csv(SALIDAS / "real_programa_109.csv"),
                            "Base (15)": pd.read_csv(SALIDAS / "real_programa_15.csv")},
                           SALIDAS / "fig_cobertura.pdf", PROGRAMAS_FIG)
    partes.append("## Referencia: M2 transaccional privado (197), deriva de 24 meses "
                  "(la serie empieza en 2021-01)\n" + _capturar(
                      bandas.main, ["--csv", "197", "--trimestres", "4", "--ventana", "24"]))
    return "\n\n".join(partes) + "\n"


def main() -> None:
    """Corre todo y escribe ``salidas/real_*.txt``."""
    SALIDAS.mkdir(exist_ok=True)
    for nombre, funcion in (("verificacion_datos", verificacion), ("liquidez", rutina_a),
                            ("demanda_dinero", rutina_b), ("bandas", rutina_c)):
        texto = funcion()
        (SALIDAS / f"real_{nombre}.txt").write_text(texto, encoding="utf-8")
        print(f"salidas/real_{nombre}.txt")
    assert CARPETA_DATOS.exists()


if __name__ == "__main__":
    main()
