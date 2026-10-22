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
