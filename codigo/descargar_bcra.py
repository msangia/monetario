"""Descarga series públicas de la API de Estadísticas Monetarias v4.0 del BCRA.

Genera, en la carpeta ``datos/`` del repositorio:

* ``catalogo_monetarias.csv``: catálogo de variables (``GET /Monetarias``);
* ``bcra_<id>_daily.csv``: cada serie, columnas ``fecha,valor`` (fecha ISO);
* ``metadata_<id>.json``: fila del catálogo, metodología (``GET /Metodologia/<id>``)
  y control de la descarga (filas bajadas frente a ``count`` informado);
y, junto a este script (no se sube al repositorio), ``descarga_bcra.log`` con el
registro de la corrida.

Esquema según el OpenAPI público (``codigo/referencia/estadisticas-monetarias-v4.json``).
Probado con respuestas simuladas (mock) en ``tests/``; no contra la API real.

Proxy: opcional. Se toma de las variables de entorno estándar ``HTTPS_PROXY`` /
``HTTP_PROXY`` o del argumento ``--proxy``; el script no trae ningún valor por defecto.

Ejemplos::

    python descargar_bcra.py --catalogo
    python descargar_bcra.py --buscar "base monetaria" --buscar circulante --buscar caución
    python descargar_bcra.py --ids 104 --desde 2015-01-01
    python descargar_bcra.py --series series.txt
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL_BASE = "https://api.bcra.gob.ar/estadisticas/v4.0"
LIMITE = 1000
TIMEOUT = 30
CARPETA_DATOS = Path(__file__).resolve().parent.parent / "datos"
CAMPOS_CATALOGO = ["idVariable", "descripcion", "categoria", "tipoSerie", "periodicidad",
                   "unidadExpresion", "moneda", "primerFechaInformada", "ultFechaInformada",
                   "ultValorInformado"]

log = logging.getLogger("descargar_bcra")


def crear_sesion(proxy: str | None = None, reintentos: int = 4) -> requests.Session:
    """Sesión HTTP con reintentos (429 y 5xx) y proxy opcional.

    Sin ``proxy``, ``requests`` usa las variables de entorno ``HTTPS_PROXY`` /
    ``HTTP_PROXY`` si existen.
    """
    s = requests.Session()
    reintento = Retry(total=reintentos, backoff_factor=0.5, allowed_methods=["GET"],
                      status_forcelist=(429, 500, 502, 503, 504))
    s.mount("https://", HTTPAdapter(max_retries=reintento))
    s.mount("http://", HTTPAdapter(max_retries=reintento))
    if proxy:
        s.proxies.update({"http": proxy, "https": proxy})
    s.headers.update({"Accept": "application/json"})
    return s


def _get(sesion: requests.Session, ruta: str, params: dict[str, Any] | None = None) -> dict:
    r = sesion.get(f"{URL_BASE}/{ruta}", params=params, timeout=TIMEOUT)
    r.raise_for_status()
    datos = r.json()
    if not isinstance(datos, dict) or not isinstance(datos.get("results"), list):
        raise ValueError(f"Respuesta inesperada de {ruta}: falta la lista 'results'.")
    return datos


def _paginar(sesion: requests.Session, ruta: str, params: dict[str, Any],
             extraer) -> tuple[list[dict], int | None]:
    """Recorre páginas ``Limit``/``Offset`` hasta una página corta o vacía.

    Returns:
        (filas, count informado en la primera página o ``None``).
    """
    filas: list[dict] = []
    offset, total = 0, None
    while True:
        datos = _get(sesion, ruta, {**params, "Limit": LIMITE, "Offset": offset})
        if total is None:
            total = (datos.get("metadata") or {}).get("resultset", {}).get("count")
        pagina = extraer(datos)
        filas.extend(pagina)
        if len(pagina) < LIMITE:
            return filas, total
        offset += LIMITE
        time.sleep(0.2)


def descargar_catalogo(sesion: requests.Session) -> list[dict]:
    """Catálogo completo de variables monetarias (``GET /Monetarias``)."""
    filas, total = _paginar(sesion, "Monetarias", {}, lambda d: d["results"])
    if total is not None and total != len(filas):
        log.warning("Catálogo: %s filas bajadas, count informado %s", len(filas), total)
    return filas


def descargar_serie(sesion: requests.Session, id_variable: int, desde: str | None = None,
                    hasta: str | None = None) -> tuple[list[tuple[str, float]], dict]:
    """Datos de una variable (``GET /Monetarias/{id}``), con paginación y control de ``count``.

    Returns:
        (lista ordenada de (fecha ISO, valor), control de la descarga).
    """
    if int(id_variable) <= 0:
        raise ValueError("id_variable debe ser un entero positivo")
    params = {k: v for k, v in (("Desde", desde), ("Hasta", hasta)) if v}

    def extraer(d: dict) -> list[dict]:
        return [p for item in d["results"] for p in (item.get("detalle") or [])]

    crudos, total = _paginar(sesion, f"Monetarias/{int(id_variable)}", params, extraer)
    datos = {}
    for p in crudos:
        if p.get("fecha") and p.get("valor") is not None:
            datos[str(p["fecha"])[:10]] = float(p["valor"])
    filas = sorted(datos.items())
    control = {"filas": len(filas), "count_informado": total,
               "validacion": "ok" if total in (None, len(crudos)) else "diferencia"}
    if control["validacion"] != "ok":
        log.warning("Serie %s: %s filas bajadas, count informado %s",
                    id_variable, len(crudos), total)
    return filas, control


def descargar_metodologia(sesion: requests.Session, id_variable: int) -> list[dict]:
    """Metodología de una variable (``GET /Metodologia/{id}``): lista de ``{id, detalle}``."""
    res = _get(sesion, f"Metodologia/{int(id_variable)}")["results"]
    # /Metodologia (listado) devuelve listas anidadas; se aplanan por las dudas.
    return [x for r in res for x in (r if isinstance(r, list) else [r])]


def _normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return t.lower()


def buscar(catalogo: Iterable[dict], palabras: Iterable[str]) -> list[dict]:
    """Variables cuya descripción o categoría contiene alguna palabra (sin acentos ni mayúsculas)."""
    claves = [_normalizar(p) for p in palabras]
    return [v for v in catalogo
            if any(c in _normalizar(f"{v.get('descripcion')} {v.get('categoria')}")
                   for c in claves)]


def guardar_catalogo(catalogo: list[dict], carpeta: Path) -> Path:
    """Escribe ``catalogo_monetarias.csv``."""
    ruta = carpeta / "catalogo_monetarias.csv"
    with ruta.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS_CATALOGO, extrasaction="ignore")
        w.writeheader()
        w.writerows(catalogo)
    return ruta


def leer_catalogo(carpeta: Path) -> list[dict] | None:
    """Lee el catálogo local si existe."""
    ruta = carpeta / "catalogo_monetarias.csv"
    if not ruta.exists():
        return None
    with ruta.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def guardar_serie(id_variable: int, filas: list[tuple[str, float]], carpeta: Path,
                  meta: dict) -> tuple[Path, Path]:
    """Escribe ``bcra_<id>_daily.csv`` (``fecha,valor``) y ``metadata_<id>.json``."""
    csv_ruta = carpeta / f"bcra_{id_variable}_daily.csv"
    with csv_ruta.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fecha", "valor"])
        w.writerows(filas)
    meta_ruta = carpeta / f"metadata_{id_variable}.json"
    meta_ruta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return csv_ruta, meta_ruta


def leer_lista_series(ruta: Path) -> list[int]:
    """IDs de un archivo de texto: uno por línea; ``#`` inicia un comentario."""
    ids = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        dato = linea.split("#", 1)[0].strip()
        if dato:
            ids.append(int(dato))
    return ids


def ejecutar(ids: list[int], sesion: requests.Session, carpeta: Path,
             desde: str | None = None, hasta: str | None = None) -> dict[int, str]:
    """Descarga cada serie con su metodología; devuelve el estado por ID."""
    try:
        catalogo = leer_catalogo(carpeta) or descargar_catalogo(sesion)
    except (requests.RequestException, ValueError) as e:
        log.warning("No se pudo leer el catálogo (%s); se sigue sin él.", e)
        catalogo = []
    por_id = {int(v["idVariable"]): v for v in catalogo}
    estado: dict[int, str] = {}
    for i in ids:
        try:
            filas, control = descargar_serie(sesion, i, desde, hasta)
            try:
                metodologia = descargar_metodologia(sesion, i)
            except (requests.RequestException, ValueError) as e:
                metodologia, control["metodologia_error"] = [], str(e)
            meta = {"idVariable": i, "catalogo": por_id.get(i), "metodologia": metodologia,
                    "descarga": {"fecha_descarga": datetime.now().isoformat(timespec="seconds"),
                                 "desde": desde, "hasta": hasta, **control},
                    "fuente": f"{URL_BASE}/Monetarias/{i}"}
            guardar_serie(i, filas, carpeta, meta)
            estado[i] = f"{control['filas']} filas ({control['validacion']})"
            log.info("Serie %s: %s", i, estado[i])
        except (requests.RequestException, ValueError) as e:
            estado[i] = f"error: {e}"
            log.error("Serie %s: %s", i, e)
    return estado


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada de línea de comandos."""
    ap = argparse.ArgumentParser(description="Descarga series públicas del BCRA (API v4.0).")
    ap.add_argument("--catalogo", action="store_true", help="baja el catálogo de variables")
    ap.add_argument("--buscar", action="append", default=[], metavar="PALABRA",
                    help="busca en el catálogo (repetible)")
    ap.add_argument("--ids", type=int, nargs="*", default=[], help="IDs a descargar")
    ap.add_argument("--series", type=Path, help="archivo con un ID por línea (p. ej. series.txt)")
    ap.add_argument("--desde"), ap.add_argument("--hasta")
    ap.add_argument("--proxy", help="proxy HTTP(S) opcional; si no, se usan HTTPS_PROXY/HTTP_PROXY")
    ap.add_argument("--salida", type=Path, default=CARPETA_DATOS, help="carpeta de salida")
    a = ap.parse_args(argv)
    a.salida.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(),
                                  logging.FileHandler(Path(__file__).with_name("descarga_bcra.log"),
                                                      encoding="utf-8")])
    sesion = crear_sesion(a.proxy)
    try:
        return _correr(a, sesion, ap)
    except requests.RequestException as e:
        log.error("No se pudo conectar con la API del BCRA: %s", e)
        log.error("Revisar conexión o proxy (variables HTTPS_PROXY/HTTP_PROXY o --proxy).")
        return 1


def _correr(a: argparse.Namespace, sesion: requests.Session,
            ap: argparse.ArgumentParser) -> int:
    if a.catalogo or a.buscar:
        cat = descargar_catalogo(sesion) if a.catalogo else (leer_catalogo(a.salida)
                                                             or descargar_catalogo(sesion))
        log.info("Catálogo: %s variables -> %s", len(cat), guardar_catalogo(cat, a.salida))
        for v in buscar(cat, a.buscar):
            print(f"{v['idVariable']:>6}  {v.get('periodicidad') or '-':<2} "
                  f"{v.get('ultFechaInformada') or '':<10}  {v.get('descripcion')}")
    ids = list(a.ids) + (leer_lista_series(a.series) if a.series else [])
    if ids:
        for i, e in ejecutar(ids, sesion, a.salida, a.desde, a.hasta).items():
            print(f"{i}: {e}")
    if not (a.catalogo or a.buscar or ids):
        ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
