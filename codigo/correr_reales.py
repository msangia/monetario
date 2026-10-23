"""Corre las rutinas A, B y C con los datos reales de ``datos/`` y guarda las salidas.

Escribe en ``codigo/salidas/``:

* ``real_verificacion_datos.txt``: tabla de ``verificar_series.py``, controles de
  calidad (:mod:`monetario_demo.calidad`) y control del empalme del IPC;
* ``real_liquidez.txt`` (rutina A), ``real_demanda_dinero.txt`` (rutina B, versión
  provisoria con base y billetes, NO M2), ``real_bandas.txt`` (rutina C) y
  ``fan_chart_real.pdf``.

Cada archivo lleva un encabezado con la fuente, el último dato de cada serie usada
y la fecha de ejecución. Las especificaciones (muestras, ventanas) están fijadas
aquí, antes de mirar los resultados, y se justifican en ``anexos.tex``.

Uso (desde ``codigo/``)::

    python correr_reales.py
"""

from __future__ import annotations

import contextlib
import io
from datetime import datetime
from pathlib import Path

from monetario_demo import bandas, calidad, demanda_dinero, liquidez
from monetario_demo.datos import (CARPETA_DATOS, a_mensual, cargar_csv, cargar_emae,
                                  cargar_ipc_historico, meses_completos)
import verificar_series

SALIDAS = Path(__file__).resolve().parent / "salidas"
DESCRIPCION = {15: "base monetaria", 17: "billetes y monedas en poder del público",
               104: "depósitos del sector privado", 197: "M2 transaccional privado",
               11: "BAIBAR", 150: "pases entre terceros a 1 día", 44: "TAMAR"}


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
        calidad.informe_calidad([15, 17, 104, 197, 11, 150, 44]), "",
        "## IPC", ipc.attrs["empalme"],
        f"Serie empalmada: {ipc.index[0]:%Y-%m} a {ipc.index[-1]:%Y-%m}, {len(ipc)} meses."])


def rutina_a() -> str:
    """Rutina A: base (15) y billetes en poder del público (17)."""
    partes = [encabezado([15, 17]),
              "Muestra: desde 2010-01-04; evaluación fuera de muestra desde 2022-01-03; "
              "reestimación cada 60 días hábiles. Feriados: días sin dato de la serie."]
    for csv, ventana in (("15", None), ("15", 500), ("17", None)):
        nombre = f"id {csv}, ventana " + (f"móvil de {ventana} días" if ventana else "expansiva")
        nivel = cargar_csv(csv).loc["2010-01-04":]
        pronos = liquidez.pronostico_fuera_de_muestra(nivel, "2022-01-03", cada=60,
                                                      ventana=ventana)
        for etiqueta, kw in (("2022-01 a 2026-10", {}),
                             ("posterior a las LEFI (desde 2025-07-11)", {"desde": "2025-07-11"}),
                             ("últimos 60 días", {"ultimos": 60})):
            ev = liquidez.evaluar(pronos, **kw)
            partes.append(liquidez.informe(ev, f"{nombre}; {etiqueta}"))
    return "\n\n".join(partes) + "\n"


def rutina_b() -> str:
    """Rutina B provisoria: base (15) o billetes (17) reales, IPC empalmado, EMAE, BAIBAR."""
    ipc = cargar_ipc_historico()
    partes = [encabezado([15, 17, 11], [
        f"EMAE desestacionalizado (INDEC): hasta {cargar_emae().index[-1]:%Y-%m}",
        ipc.attrs["empalme"]]),
        "VERSIÓN PROVISORIA: el 'dinero' es la base (15) o los billetes en poder del público "
        "(17), NO el M2 (109). Costo de oportunidad: BAIBAR (11), no plazo fijo (1189). Se "
        "re-corre cuando estén los IDs 109 y 1189."]
    for d in ("15", "17"):
        partes.append(_capturar(demanda_dinero.main, [
            "--dinero", d, "--tasa", "11", "--precios", "empalmado",
            "--actividad", "datos/emae_mensual.csv"]))
    return "\n\n".join(partes) + "\n"


def rutina_c() -> str:
    """Rutina C: M2 transaccional (197; deriva de 24 meses por la muestra) y base (15)."""
    partes = [encabezado([197, 15]),
              "Promedios mensuales de meses completos (se descarta 2026-10, parcial). "
              "Programa ilustrativo: deriva media de los últimos N meses (no es el programa "
              "del BCRA)."]
    partes.append("## id 197, deriva de 24 meses (la serie empieza en 2021-01)\n" + _capturar(
        bandas.main, ["--csv", "197", "--trimestres", "4", "--ventana", "24",
                      "--figura", str(SALIDAS / "fan_chart_real.pdf")]))
    partes.append("## id 15, deriva de 36 meses (muestra desde 2003-01)\n" + _capturar(
        bandas.main, ["--csv", "15", "--trimestres", "4", "--ventana", "36"]))
    serie = a_mensual(meses_completos(cargar_csv("197")))
    partes.append(f"Meses usados de id 197: {serie.index[0]:%Y-%m} a {serie.index[-1]:%Y-%m}.")
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
