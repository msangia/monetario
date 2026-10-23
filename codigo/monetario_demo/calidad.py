"""Controles de calidad de las series diarias bajadas de la API del BCRA (Eje 5).

Para cada ``datos/bcra_<id>_daily.csv`` (con su ``metadata_<id>.json``) informa:
filas, fechas duplicadas, observaciones en fin de semana, días hábiles (lunes a
viernes) sin dato, huecos de más de ``hueco`` días corridos, valores no positivos,
unidad según la metadata, saltos diarios anómalos (|cambio| mayor que ``k_mad``
desvíos absolutos medianos móviles) y concordancia del CSV con el último valor del
catálogo (la API revisa datos recientes, así que una diferencia chica es esperable).

Los saltos se miden en % (100 * diff log) para saldos y en puntos porcentuales para
tasas. Las series de flujo (``tipoSerie`` "Flujo diario", p. ej. id 46, factores de la
base) pueden ser negativas: se controla el valor del día (no su variación) contra la
mediana y el MAD móviles, y los valores no positivos no se cuentan como anomalía.
:func:`controles_cruzados` contrasta identidades contables entre series. Un salto no es un error: puede ser un cambio de régimen o de normativa (p. ej.,
encajes); el control sólo lo señala para revisarlo.

Uso (desde ``codigo/``)::

    python -m monetario_demo.calidad 15 17 104 197 11 150 44
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import datos


def controlar_serie(id_variable: int, carpeta: Path | None = None, hueco: int = 5,
                    k_mad: float = 10.0) -> dict[str, object]:
    """Controles de calidad de una serie diaria (ver docstring del módulo).

    Raises:
        FileNotFoundError: si no está el CSV.
    """
    carpeta = carpeta or datos.CARPETA_DATOS
    ruta = carpeta / f"bcra_{id_variable}_daily.csv"
    crudo = pd.read_csv(ruta, dtype={"fecha": str})
    s = datos.cargar_csv(ruta)
    meta_ruta = carpeta / f"metadata_{id_variable}.json"
    meta = json.loads(meta_ruta.read_text(encoding="utf-8")) if meta_ruta.exists() else {}
    cat = meta.get("catalogo", {})
    unidad = cat.get("unidadExpresion", "?")
    es_tasa = "porcentaje" in unidad.lower() or cat.get("tipoSerie", "").startswith("Tasa")
    es_flujo = cat.get("tipoSerie", "").lower().startswith("flujo")
    idx = s.index
    faltan = pd.bdate_range(idx[0], idx[-1]).difference(idx)
    saltos_dias = pd.Series(np.diff(idx.to_numpy()).astype("timedelta64[D]").astype(int))
    if es_flujo:
        cambio = s                       # el flujo ya es una variación (millones)
    else:
        cambio = s.diff() if es_tasa else 100 * np.log(s).diff()
    centro = cambio.rolling(250, min_periods=60).median()
    mad = (cambio - centro).abs().rolling(250, min_periods=60).median()
    anomalos = ((cambio - centro).abs() > k_mad * 1.4826 * mad) & mad.gt(0)
    top = cambio.abs().nlargest(3).index
    concordancia = None
    if cat.get("ultFechaInformada"):
        f = pd.Timestamp(cat["ultFechaInformada"])
        if f in s.index:
            v_cat = float(cat["ultValorInformado"])
            concordancia = float(s.loc[f] / v_cat - 1) if v_cat else None
    return {
        "id": id_variable, "filas": len(s), "primero": idx[0].date(), "ultimo": idx[-1].date(),
        "duplicados": int(crudo["fecha"].duplicated().sum()),
        "vacios": int(pd.to_numeric(crudo["valor"], errors="coerce").isna().sum()),
        "fin_semana": [d.date().isoformat() for d in idx[idx.dayofweek >= 5]],
        "habiles_sin_dato_por_anio": round(len(faltan) / max((idx[-1] - idx[0]).days / 365.25,
                                                              1e-9), 1),
        "huecos": int((saltos_dias > hueco).sum()), "hueco_max": int(saltos_dias.max()),
        "no_positivos": None if es_flujo else int((s <= 0).sum()), "unidad": unidad,
        "medida_salto": "millones, flujo" if es_flujo else ("pp" if es_tasa else "%"),
        "saltos_anomalos": int(anomalos.sum()),
        "mayores_saltos": [(d.date().isoformat(), round(float(cambio[d]), 1)) for d in top],
        "dif_ultimo_catalogo": concordancia,
        "validacion": meta.get("descarga", {}).get("validacion", "sin metadata"),
    }


def informe_calidad(ids: list[int], carpeta: Path | None = None) -> str:
    """Texto con una línea por serie (las que no están se informan como faltantes)."""
    lineas = []
    for i in ids:
        try:
            c = controlar_serie(i, carpeta)
        except FileNotFoundError:
            lineas.append(f"id {i}: falta el CSV")
            continue
        dif = c["dif_ultimo_catalogo"]
        lineas.append(
            f"id {i} ({c['unidad']}): {c['filas']} filas {c['primero']} a {c['ultimo']}; "
            f"duplicados {c['duplicados']}, vacíos {c['vacios']}, no positivos "
            f"{'n/c (flujo)' if c['no_positivos'] is None else c['no_positivos']}, fin de semana {c['fin_semana'] or 'ninguno'}; "
            f"hábiles sin dato {c['habiles_sin_dato_por_anio']}/año (feriados); "
            f"huecos > 5 días: {c['huecos']} (máx. {c['hueco_max']} días); "
            f"saltos > 10 MAD: {c['saltos_anomalos']}; mayores ({c['medida_salto']}): "
            + ", ".join(f"{d} {v:+.1f}" for d, v in c["mayores_saltos"])
            + "; CSV vs. último valor del catálogo: "
            + ("fecha no disponible" if dif is None else f"{dif:+.4%}")
            + f"; metadata: {c['validacion']}")
    return "\n".join(lineas)


def controles_cruzados(carpeta: Path | None = None) -> str:
    """Identidades y desigualdades contables entre series (si están los CSV).

    * factores de explicación (46) = variación diaria de la base (15);
    * circulación monetaria (16) >= billetes y monedas en poder del público (17);
    * M2 (109) >= M2 transaccional privado (197) y M2 (109) > billetes (17).
    """
    carpeta = carpeta or datos.CARPETA_DATOS
    try:
        s = {i: datos.cargar_csv(carpeta / f"bcra_{i}_daily.csv") for i in (15, 16, 17, 46, 109, 197)}
    except FileNotFoundError as e:
        return f"controles cruzados: falta un CSV ({e})"
    df = pd.concat(s, axis=1, sort=True)
    lineas = []
    par = pd.concat([df[15].dropna().diff(), df[46]], axis=1).dropna()
    dif = (par[15] - par[46]).abs()
    rel = dif / df[15].shift().reindex(par.index)
    exacto = dif <= 1.0                                  # redondeo a 1 millón
    lineas.append(
        f"46 vs. variación diaria de 15: {len(par)} días; |dif| <= 1 millón en "
        f"{exacto.mean():.1%} (desde 2016: {exacto.loc['2016':].mean():.1%}); "
        f"máx. |dif| / base = {rel.max():.1e}; correlación {par[15].corr(par[46]):.6f}")
    for a, b, signo in ((16, 17, ">="), (109, 197, ">="), (109, 17, ">")):
        x = df[[a, b]].dropna()
        ok = (x[a] >= x[b]) if signo == ">=" else (x[a] > x[b])
        lineas.append(f"{a} {signo} {b}: se cumple en {ok.mean():.1%} de {len(x)} días")
    return "\n".join(lineas)


def main(argv: list[str] | None = None) -> str:
    """Punto de entrada de línea de comandos."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("ids", type=int, nargs="+")
    a = ap.parse_args(argv)
    texto = informe_calidad(a.ids)
    print(texto)
    return texto


if __name__ == "__main__":
    main()
