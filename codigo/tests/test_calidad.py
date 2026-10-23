"""Tests de los controles de calidad de series diarias (contenido de prueba, no oficial)."""

import json

import numpy as np
import pandas as pd

from monetario_demo.calidad import controlar_serie, informe_calidad


def _escribir(tmp_path, valores, fechas, unidad="En millones de ARS"):
    pd.DataFrame({"fecha": fechas, "valor": valores}).to_csv(
        tmp_path / "bcra_1_daily.csv", index=False)
    meta = {"catalogo": {"unidadExpresion": unidad, "tipoSerie": "Saldos",
                         "ultFechaInformada": fechas[-1], "ultValorInformado": str(valores[-1])},
            "descarga": {"validacion": "ok"}}
    (tmp_path / "metadata_1.json").write_text(json.dumps(meta))


def test_controles_detectan_duplicado_salto_y_finde(tmp_path):
    idx = pd.bdate_range("2024-01-01", "2024-12-31")
    v = 100 * np.exp(np.cumsum(np.random.default_rng(1).normal(0, 0.01, len(idx))))
    v[200:] *= 1.5                                   # salto de +40 % en log
    fechas = list(idx.strftime("%Y-%m-%d")) + ["2024-12-31"]   # duplicado
    fechas[100] = "2024-05-25"                       # sábado
    _escribir(tmp_path, list(v) + [v[-1]], fechas)
    c = controlar_serie(1, tmp_path)
    assert c["duplicados"] == 1 and c["fin_semana"] == ["2024-05-25"]
    assert c["saltos_anomalos"] >= 1 and c["mayores_saltos"][0][1] > 30
    assert abs(c["dif_ultimo_catalogo"]) < 1e-9 and c["medida_salto"] == "%"
    assert "falta el CSV" in informe_calidad([2], tmp_path)


def test_flujo_negativo_no_es_error(tmp_path):
    """Una serie de flujo (p. ej. factores de la base) puede ser negativa."""
    idx = pd.bdate_range("2024-01-01", "2024-12-31")
    v = np.random.default_rng(2).normal(0, 100, len(idx))
    pd.DataFrame({"fecha": idx.strftime("%Y-%m-%d"), "valor": v}).to_csv(
        tmp_path / "bcra_1_daily.csv", index=False)
    meta = {"catalogo": {"unidadExpresion": "En millones de ARS", "tipoSerie": "Flujo diario"},
            "descarga": {"validacion": "ok"}}
    (tmp_path / "metadata_1.json").write_text(json.dumps(meta))
    c = controlar_serie(1, tmp_path)
    assert c["no_positivos"] is None and c["medida_salto"].startswith("millones")
    assert np.isfinite([x[1] for x in c["mayores_saltos"]]).all()


def test_controles_cruzados(tmp_path):
    from monetario_demo.calidad import controles_cruzados
    idx = pd.bdate_range("2024-01-01", periods=50)
    base = pd.Series(np.linspace(100, 150, 50), index=idx)
    series = {15: base, 16: base * 0.6, 17: base * 0.5, 46: base.diff().fillna(0),
              109: base * 2, 197: base * 1.5}
    for i, s in series.items():
        pd.DataFrame({"fecha": idx.strftime("%Y-%m-%d"), "valor": s.values}).to_csv(
            tmp_path / f"bcra_{i}_daily.csv", index=False)
    texto = controles_cruzados(tmp_path)
    assert "|dif| <= 1 millón en 100.0%" in texto and "16 >= 17: se cumple en 100.0%" in texto
