"""Tests de verificar_series.py (IDs de series.txt contra el catálogo real)."""

import json
import shutil
from pathlib import Path

import pytest

import verificar_series as vs

RAIZ = Path(__file__).resolve().parents[2]
CATALOGO = RAIZ / "datos" / "catalogo_monetarias.csv"
pytestmark = pytest.mark.skipif(not CATALOGO.exists(), reason="falta el catálogo")

ESPERADAS = {15: "Base monetaria", 16: "Circulación monetaria",
             17: "Billetes y monedas en poder del público",
             104: "Depósitos del sector privado no financiero", 109: "M2",
             197: "M2 transaccional del sector privado",
             46: "Total de factores de explicación de la base monetaria",
             11: "BAIBAR", 150: "pases entre terceros a 1 día",
             1189: "depósitos a plazo fijo en pesos", 44: "TAMAR"}


def test_ids_de_series_txt_en_catalogo():
    ids = vs.leer_ids(RAIZ / "codigo" / "series.txt")
    assert set(ids) == set(ESPERADAS)
    cat = vs.leer_catalogo(CATALOGO.parent)
    for i, texto in ESPERADAS.items():
        assert texto.lower() in cat[i]["descripcion"].lower()
        assert cat[i]["periodicidad"] == "D"


def test_estado_de_descarga(tmp_path):
    shutil.copy(CATALOGO, tmp_path)
    (tmp_path / "bcra_109_daily.csv").write_text(
        "fecha,valor\n2003-01-02,1\n2026-10-16,2\n")  # contenido de prueba, no oficial
    (tmp_path / "metadata_109.json").write_text(json.dumps({"descarga": {"validacion": "ok"}}))
    (tmp_path / "bcra_15_daily.csv").write_text("fecha,valor\n2003-01-02,1\n2025-01-02,2\n")
    filas, ausentes = vs.tabla([109, 15, 17, 999999], tmp_path, desde="2003-01-01")
    estados = {f[0]: f[-1] for f in filas}
    assert estados == {"109": "ok", "15": "revisar", "17": "falta", "999999": ""}
    assert ausentes == [999999]
