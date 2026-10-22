"""Tests del descargador de la API v4.0 del BCRA con respuestas simuladas (mock).

No se contacta la API real: la sesión HTTP se reemplaza por un objeto falso que
devuelve JSON con el esquema del OpenAPI público (referencia/).
"""

import json

import pandas as pd
import pytest

import descargar_bcra as d
from monetario_demo.datos import cargar_csv


class Respuesta:
    def __init__(self, payload, status=200):
        self.payload, self.status_code = payload, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise d.requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class SesionFalsa:
    """Simula /Monetarias, /Monetarias/{id} y /Metodologia/{id} con paginación."""

    def __init__(self, n_puntos=2500, count=None, catalogo=None):
        fechas = pd.bdate_range("2015-01-01", periods=n_puntos)
        self.puntos = [{"fecha": f.strftime("%Y-%m-%d"), "valor": float(i)}
                       for i, f in enumerate(fechas)][::-1]  # la API puede venir descendente
        self.count = n_puntos if count is None else count
        self.catalogo = catalogo or [
            {"idVariable": 15, "descripcion": "Base monetaria - Total", "categoria": "Principales",
             "periodicidad": "D", "ultFechaInformada": "2025-08-21"},
            {"idVariable": 7, "descripcion": "Tasa de interés de caución", "categoria": "Tasas"},
            {"idVariable": 104, "descripcion": "Depósitos del sector privado", "categoria": "X"}]
        self.llamadas = []

    def get(self, url, params=None, timeout=None):
        self.llamadas.append((url, dict(params or {})))
        p = params or {}
        off, lim = p.get("Offset", 0), p.get("Limit", 1000)
        meta = {"resultset": {"count": None, "offset": off, "limit": lim}}
        if url.endswith("/Monetarias"):
            meta["resultset"]["count"] = len(self.catalogo)
            return Respuesta({"status": 200, "metadata": meta,
                              "results": self.catalogo[off:off + lim]})
        if "/Metodologia/" in url:
            return Respuesta({"status": 200, "results": [{"id": 1, "detalle": "Metodología X"}]})
        if "/Monetarias/" in url:
            meta["resultset"]["count"] = self.count
            idv = int(url.rsplit("/", 1)[1])
            return Respuesta({"status": 200, "metadata": meta,
                              "results": [{"idVariable": idv,
                                           "detalle": self.puntos[off:off + lim]}]})
        return Respuesta({"status": 404, "errorMessages": ["no"]}, 404)


def test_paginacion_y_count():
    s = SesionFalsa(2500)
    filas, control = d.descargar_serie(s, 15, desde="2015-01-01")
    assert len(filas) == 2500 and control["validacion"] == "ok"
    assert filas[0][0] < filas[-1][0]  # ordenado ascendente
    offsets = [p["Offset"] for u, p in s.llamadas]
    assert offsets == [0, 1000, 2000]
    assert s.llamadas[0][1]["Desde"] == "2015-01-01" and "Hasta" not in s.llamadas[0][1]


def test_count_distinto_queda_registrado(caplog):
    filas, control = d.descargar_serie(SesionFalsa(1200, count=1300), 15)
    assert control["validacion"] == "diferencia"
    assert "count informado 1300" in caplog.text


def test_respuesta_inesperada():
    class Mala(SesionFalsa):
        def get(self, url, params=None, timeout=None):
            return Respuesta({"status": 200, "errorMessages": []})
    with pytest.raises(ValueError):
        d.descargar_serie(Mala(), 15)
    with pytest.raises(ValueError):
        d.descargar_serie(SesionFalsa(), 0)


def test_busqueda_sin_acentos():
    cat = SesionFalsa().catalogo
    assert [v["idVariable"] for v in d.buscar(cat, ["CAUCION"])] == [7]
    assert [v["idVariable"] for v in d.buscar(cat, ["base monetaria", "depósitos"])] == [15, 104]


def test_metodologia_formatos():
    s = SesionFalsa()
    assert d.descargar_metodologia(s, 15) == [{"id": 1, "detalle": "Metodología X"}]

    class Anidada(SesionFalsa):
        def get(self, url, params=None, timeout=None):
            return Respuesta({"status": 200, "results": [[{"id": 2, "detalle": "Y"}]]})
    assert d.descargar_metodologia(Anidada(), 15) == [{"id": 2, "detalle": "Y"}]


def test_ejecutar_escribe_archivos_legibles(tmp_path, monkeypatch):
    s = SesionFalsa(300)
    estado = d.ejecutar([15, 104], s, tmp_path)
    assert all("ok" in e for e in estado.values())
    meta = json.loads((tmp_path / "metadata_15.json").read_text(encoding="utf-8"))
    assert meta["catalogo"]["descripcion"] == "Base monetaria - Total"
    assert meta["metodologia"][0]["detalle"] == "Metodología X"
    assert meta["descarga"]["filas"] == 300
    serie = cargar_csv(tmp_path / "bcra_15_daily.csv")  # mismo formato que las rutinas
    assert len(serie) == 300 and serie.index.is_monotonic_increasing


def test_catalogo_y_lista_series(tmp_path):
    ruta = d.guardar_catalogo(d.descargar_catalogo(SesionFalsa()), tmp_path)
    assert len(d.leer_catalogo(tmp_path)) == 3 and ruta.name == "catalogo_monetarias.csv"
    (tmp_path / "s.txt").write_text("# comentario\n15  # base\n\n104\n# <id> pendiente\n")
    assert d.leer_lista_series(tmp_path / "s.txt") == [15, 104]


def test_proxy_opcional_sin_valor_por_defecto(monkeypatch):
    for var in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"):
        monkeypatch.delenv(var, raising=False)
    assert d.crear_sesion().proxies == {}
    assert d.crear_sesion("http://proxy.ejemplo:8080").proxies["https"] == "http://proxy.ejemplo:8080"
    assert d.crear_sesion().trust_env  # respeta HTTPS_PROXY/HTTP_PROXY del entorno
