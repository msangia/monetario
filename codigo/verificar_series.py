"""Verifica los IDs de ``series.txt`` contra el catálogo y controla las descargas.

Sólo usa la biblioteca estándar (se puede correr en la PC del BCRA junto a
``descargar_bcra.py``). Para cada ID muestra la descripción, la periodicidad y el
primer y último dato del catálogo (``datos/catalogo_monetarias.csv``) y, si ya
se bajó, las filas y el primer y último dato de ``datos/bcra_<id>_daily.csv``
y la validación de ``metadata_<id>.json``.

Uso (desde ``codigo/``)::

    python verificar_series.py --series series.txt
    python verificar_series.py --series series.txt --desde 2003-01-01

Estado: ``falta`` (no hay CSV), ``ok`` (empieza en max(catálogo, --desde) y
termina a lo sumo ``--tolerancia`` días antes del catálogo) o ``revisar``.
Devuelve código 1 si algún ID no está en el catálogo.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path

CARPETA_DATOS = Path(__file__).resolve().parent.parent / "datos"


def leer_ids(ruta: Path) -> list[int]:
    """IDs de un archivo de texto: uno por línea; ``#`` inicia un comentario."""
    ids = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        dato = linea.split("#", 1)[0].strip()
        if dato:
            ids.append(int(dato))
    return ids


def leer_catalogo(carpeta: Path) -> dict[int, dict]:
    """Catálogo local indexado por ``idVariable``."""
    with (carpeta / "catalogo_monetarias.csv").open(encoding="utf-8-sig", newline="") as f:
        return {int(r["idVariable"]): r for r in csv.DictReader(f)}


def resumir_descarga(carpeta: Path, id_variable: int) -> dict | None:
    """Filas, primer y último dato del CSV bajado y validación del metadata (o ``None``)."""
    ruta = carpeta / f"bcra_{id_variable}_daily.csv"
    if not ruta.exists():
        return None
    with ruta.open(encoding="utf-8", newline="") as f:
        fechas = sorted(r["fecha"] for r in csv.DictReader(f) if r.get("valor"))
    meta = carpeta / f"metadata_{id_variable}.json"
    validacion = "sin metadata"
    if meta.exists():
        control = json.loads(meta.read_text(encoding="utf-8")).get("descarga") or {}
        validacion = control.get("validacion", "?")
    return {"filas": len(fechas), "primero": fechas[0] if fechas else "",
            "ultimo": fechas[-1] if fechas else "", "validacion": validacion}


def estado(cat: dict, bajada: dict | None, desde: str | None, tolerancia: int) -> str:
    """``falta``, ``ok`` o ``revisar`` (ver docstring del módulo)."""
    if bajada is None:
        return "falta"
    if not bajada["filas"]:
        return "revisar (vacío)"
    inicio = max(cat["primerFechaInformada"], desde or "")
    fin_cat = date.fromisoformat(cat["ultFechaInformada"])
    ok_ini = bajada["primero"] <= (date.fromisoformat(inicio) + timedelta(days=10)).isoformat()
    ok_fin = date.fromisoformat(bajada["ultimo"]) >= fin_cat - timedelta(days=tolerancia)
    ok_val = bajada["validacion"] in ("ok", "sin metadata")
    return "ok" if ok_ini and ok_fin and ok_val else "revisar"


def tabla(ids: list[int], carpeta: Path, desde: str | None = None,
          tolerancia: int = 7) -> tuple[list[list[str]], list[int]]:
    """Filas de la tabla y lista de IDs ausentes del catálogo."""
    catalogo = leer_catalogo(carpeta)
    filas, ausentes = [], []
    for i in ids:
        cat = catalogo.get(i)
        if cat is None:
            ausentes.append(i)
            filas.append([str(i), "NO ESTÁ EN EL CATÁLOGO", "", "", "", "", "", "", ""])
            continue
        b = resumir_descarga(carpeta, i)
        filas.append([str(i), cat["descripcion"].strip()[:70], cat["periodicidad"],
                      cat["primerFechaInformada"], cat["ultFechaInformada"],
                      str(b["filas"]) if b else "-", b["primero"] if b else "-",
                      b["ultimo"] if b else "-", estado(cat, b, desde, tolerancia)])
    return filas, ausentes


def main(argv: list[str] | None = None) -> int:
    """Imprime la tabla de verificación."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--series", type=Path, default=Path(__file__).with_name("series.txt"))
    ap.add_argument("--datos", type=Path, default=CARPETA_DATOS)
    ap.add_argument("--desde", help="fecha usada en la descarga (AAAA-MM-DD)")
    ap.add_argument("--tolerancia", type=int, default=7,
                    help="días de atraso admitidos respecto del catálogo")
    a = ap.parse_args(argv)
    filas, ausentes = tabla(leer_ids(a.series), a.datos, a.desde, a.tolerancia)
    cab = ["id", "descripcion", "per", "cat_primero", "cat_ultimo",
           "filas", "csv_primero", "csv_ultimo", "estado"]
    anchos = [max(len(r[k]) for r in [cab, *filas]) for k in range(len(cab))]
    for r in [cab, *filas]:
        print("  ".join(c.ljust(w) for c, w in zip(r, anchos)).rstrip())
    if ausentes:
        print(f"IDs que no están en el catálogo: {ausentes}", file=sys.stderr)
    return 1 if ausentes else 0


if __name__ == "__main__":
    sys.exit(main())
