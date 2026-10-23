"""Controles de calidad de las series diarias bajadas de la API del BCRA (Eje 5).

Para cada ``datos/bcra_<id>_daily.csv`` (con su ``metadata_<id>.json``) informa:
filas, fechas duplicadas, observaciones en fin de semana, días hábiles (lunes a
viernes) sin dato, huecos de más de ``hueco`` días corridos, valores no positivos,
unidad según la metadata, saltos diarios anómalos (|cambio| mayor que ``k_mad``
desvíos absolutos medianos móviles) y concordancia del CSV con el último valor del
catálogo (la API revisa datos recientes, así que una diferencia chica es esperable).

Los saltos se miden en % (100 * diff log) para saldos y en puntos porcentuales para
tasas. Un salto no es un error: puede ser un cambio de régimen o de normativa (p. ej.,
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
    idx = s.index
    faltan = pd.bdate_range(idx[0], idx[-1]).difference(idx)
    saltos_dias = pd.Series(np.diff(idx.to_numpy()).astype("timedelta64[D]").astype(int))
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
        "no_positivos": int((s <= 0).sum()), "unidad": unidad,
        "medida_salto": "pp" if es_tasa else "%",
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
            f"{c['no_positivos']}, fin de semana {c['fin_semana'] or 'ninguno'}; "
            f"hábiles sin dato {c['habiles_sin_dato_por_anio']}/año (feriados); "
            f"huecos > 5 días: {c['huecos']} (máx. {c['hueco_max']} días); "
            f"saltos > 10 MAD: {c['saltos_anomalos']}; mayores ({c['medida_salto']}): "
            + ", ".join(f"{d} {v:+.1f}" for d, v in c["mayores_saltos"])
            + "; CSV vs. último valor del catálogo: "
            + ("fecha no disponible" if dif is None else f"{dif:+.4%}")
            + f"; metadata: {c['validacion']}")
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
