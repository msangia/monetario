"""Corre las rutinas A, B y C con los datos reales de ``datos/`` y guarda las salidas.

Escribe en ``codigo/salidas/``:

* ``real_verificacion_datos.txt``: tabla de ``verificar_series.py``, controles de
  calidad (:mod:`monetario_demo.calidad`), controles cruzados y empalme del IPC;
* ``real_liquidez.txt`` (rutina A: base, billetes, circulación, cuentas corrientes en
  el BCRA y pronóstico de la base por componentes);
* ``real_demanda_dinero.txt`` (rutina B: M2 (109) real con IPC empalmado, EMAE s.e.
  y plazo fijo (1189) o BAIBAR (11), tasa en nivel y en log, y submuestras);
* ``real_bandas.txt`` (rutina C: programas de deriva, deriva estacional, velocidad y
  demanda MCE para M2 (109) y base (15), banda del 90 % y chequeo de desvíos) y
  ``fan_chart_real.pdf`` (M2, programa MCE).

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

from monetario_demo import bandas, calidad, demanda_dinero, liquidez, programa
from monetario_demo.datos import (CARPETA_DATOS, cargar_csv, cargar_emae,
                                  cargar_ipc_historico)
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
        "## IPC", ipc.attrs["empalme"],
        f"Serie empalmada: {ipc.index[0]:%Y-%m} a {ipc.index[-1]:%Y-%m}, {len(ipc)} meses."])


PERIODOS_A = (("2022-01 a 2026-10", {}), ("desde 2025-07-11", {"desde": "2025-07-11"}),
              ("últimos 60 días", {"ultimos": 60}))


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
    resumen = []
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
                            "sesgo_fin_ens": sp.loc["fin de mes", "ensamble"],
                            "sesgo_fin_ing": sp.loc["fin de mes", "ingenuo"],
                            "sesgo_ini_ens": sp.loc["inicio de mes", "ensamble"],
                            "sesgo_ini_ing": sp.loc["inicio de mes", "ingenuo"]})
    for cc_modelo in ("ingenuo", "ensamble"):
        comp = liquidez.pronostico_por_componentes(base, circ, "2022-01-03", 60,
                                                   cc_modelo=cc_modelo)
        for etiqueta, kw in PERIODOS_A:
            r = liquidez.evaluar_contra_ingenuo(comp, ingenuo_base, **kw)
            resumen.append({"serie": f"base por componentes (circ. ensamble + ctas. "
                                     f"{cc_modelo})", "periodo": etiqueta, "n": r["n"],
                            "MAE_rel": r["MAE_rel"], "p_DM": r["p_DM"], "cob90": r["cobertura"]})
    descomp = {per: liquidez.descomponer_varianza(cargar_csv("15").loc[per[0]:per[1]],
                                                  cargar_csv("16").loc[per[0]:per[1]])
               for per in (("2010-01-04", "2021-12-31"), ("2022-01-01", "2026-12-31"),
                           ("2025-07-11", "2026-12-31"))}
    partes.insert(3, "## Resumen (ensamble vs. ingenuo; DM-HLN unilateral; cobertura del 90 %; "
                  "sesgo = observado - pronóstico, pp)\n"
                  + pd.DataFrame(resumen).round(3).to_string(index=False)
                  + "\n\n## Varianza de la variación diaria de la base (en % de la base previa)\n"
                  + "\n".join(f"{a} a {b}: circulación {d['circulacion']:.1%}, cuentas "
                               f"corrientes {d['cuentas_corrientes']:.1%}, 2 cov "
                               f"{d['covarianza']:.1%} (n = {d['n']})"
                               for (a, b), d in descomp.items()))
    return "\n\n".join(partes) + "\n"


ESPECIFICACIONES_B = (
    # (etiqueta, dinero, tasa, forma de la tasa, desde, hasta, ventana)
    ("M2, plazo fijo, semielasticidad (principal)", "109", "1189", "nivel", None, None, 72),
    ("M2, plazo fijo, elasticidad (log i)", "109", "1189", "log", None, None, 72),
    ("M2, BAIBAR, semielasticidad", "109", "11", "nivel", None, None, 72),
    ("M2, BAIBAR, elasticidad (log i)", "109", "11", "log", None, None, 72),
    ("M2, plazo fijo, sólo IPC oficial (2017-01 en adelante)", "109", "1189", "nivel",
     "2017-01", None, 60),
    ("M2, plazo fijo, 2004-01 a 2019-12", "109", "1189", "nivel", None, "2019-12", 60),
    ("Base (15), plazo fijo, semielasticidad (comparación)", "15", "1189", "nivel",
     None, None, 72),
)


def rutina_b() -> str:
    """Rutina B: demanda de M2 (109) real con IPC empalmado, EMAE s.e. y plazo fijo/BAIBAR."""
    ipc = cargar_ipc_historico()
    emae = cargar_emae()
    partes = [encabezado([109, 15, 1189, 11], [
        f"EMAE desestacionalizado (INDEC): {emae.index[0]:%Y-%m} a {emae.index[-1]:%Y-%m}",
        ipc.attrs["empalme"]]),
        "M2 (109) = billetes y monedas en poder del público + cuentas corrientes y cajas de "
        "ahorro en pesos de los sectores privado y público (no es el M2 privado; el M2 "
        "transaccional privado, 197, empieza en 2021). Especificaciones fijadas de antemano; "
        "se informan todas."]
    filas = []
    for etiqueta, d, tasa, forma, desde, hasta, ventana in ESPECIFICACIONES_B:
        df = demanda_dinero.armar_panel(cargar_csv(d), ipc, emae, cargar_csv(tasa), forma)
        df = df.loc[desde:hasta]
        res = demanda_dinero.analizar(df, ventana=ventana)
        c, rol, al = res["completa"], res["rolling"], res["alertas"]
        filas.append({
            "especificación": etiqueta, "muestra": f"{df.index[0]:%Y-%m} a {df.index[-1]:%Y-%m}",
            "b_y": c["b_y"], "b_i": c["b_i"], "p_EG": c["p_coint"], "g": c["g"], "t_g": c["t_g"],
            "p_CUSUM": res["p_cusum"], "ventana": ventana,
            "sin_coint_%": 100 * float((rol["p_coint"] > 0.10).mean()),
            "ADF_niv_m/y/i": "/".join(f"{v:.2f}" for v in res["adf"]["p_niveles"]),
            "alerta_b_y": al["b_y"].strftime("%Y-%m") if al["b_y"] is not None else "-",
            "alerta_b_i": al["b_i"].strftime("%Y-%m") if al["b_i"] is not None else "-"})
        partes.append(demanda_dinero.informe(res, f"{etiqueta}; dinero {d}, tasa {tasa} "
                                             f"({forma})", demanda_dinero.verificar_muestra(
                                                 df, ventana)))
    partes.insert(2, "## Resumen\n" + pd.DataFrame(filas).round(3).to_string(index=False))
    return "\n\n".join(partes) + "\n"


def rutina_c() -> str:
    """Rutina C: programas y banda para M2 (109) y base (15); deriva para 197 (referencia)."""
    partes = [encabezado([109, 15, 1189, 197], [
        f"EMAE desestacionalizado (INDEC) hasta {cargar_emae().index[-1]:%Y-%m}; "
        "IPC empalmado (ver real_demanda_dinero.txt)"]),
        "Promedios mensuales de meses completos (se descarta 2026-10, parcial). Programas: "
        "deriva (36 meses), deriva estacional, velocidad constante y demanda MCE (ventana "
        "de 72 meses, plazo fijo 1189, dummies mensuales). Velocidad y MCE son condicionales "
        "al IPC, EMAE y tasa observados. Ninguno es el programa del BCRA."]
    partes.append("## M2 (109)\n" + _capturar(programa.main, [
        "--dinero", "109", "--tasa", "1189", "--figura", str(SALIDAS / "fan_chart_real.pdf")]))
    partes.append("## Base monetaria (15)\n" + _capturar(programa.main, [
        "--dinero", "15", "--tasa", "1189"]))
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
