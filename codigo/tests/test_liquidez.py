"""Tests de la rutina A (Eje 1): pronóstico diario de liquidez."""

import numpy as np
import pandas as pd
import pytest

from monetario_demo.datos import ROTULO_SINTETICO, demo_liquidez_diaria
from monetario_demo.liquidez import (evaluar, informe, main, pronostico_fuera_de_muestra,
                                     variables_calendario)


@pytest.fixture(scope="module")
def nivel():
    return demo_liquidez_diaria("2021-01-01", "2024-12-31")


@pytest.fixture(scope="module")
def pronos(nivel):
    return pronostico_fuera_de_muestra(nivel, cada=120)


def test_calendario_fin_de_mes_y_mes_incompleto():
    idx = pd.bdate_range("2024-01-01", "2024-02-14")
    cal = variables_calendario(idx)
    assert cal.loc["2024-01-30", "fin_mes"] == 1 and cal.loc["2024-01-31", "fin_mes"] == 1
    assert cal.loc["2024-01-01", "ini_mes"] == 1 and cal.loc["2024-01-03", "ini_mes"] == 0
    # La muestra termina a mitad de febrero: no debe marcarse fin de mes.
    assert cal.loc["2024-02-13":, "fin_mes"].sum() == 0
    jun = variables_calendario(pd.bdate_range("2024-06-03", "2024-06-28"))
    assert jun.loc["2024-06-17", "aguinaldo"] == 1 and jun.loc["2024-06-10", "aguinaldo"] == 0


def test_sin_look_ahead(nivel, pronos):
    """Alterar los últimos datos no cambia los pronósticos de bloques anteriores."""
    alterado = nivel.copy()
    alterado.iloc[-30:] *= 1.5
    p2 = pronostico_fuera_de_muestra(alterado, cada=120)
    corte = p2["ensamble"].index[-121]
    for m in ("ingenuo", "regresion", "arimax", "ensamble"):
        pd.testing.assert_series_equal(pronos[m]["pron"].loc[:corte], p2[m]["pron"].loc[:corte])


def test_ensamble_supera_al_ingenuo_y_cobertura(pronos):
    ev = evaluar(pronos)
    assert ev["tabla"].loc["ensamble", "MAE_rel"] < 1
    assert ev["dm"].rechaza(0.10)
    assert 0.80 <= ev["tabla"].loc["ensamble", "cobertura"] <= 0.97
    # El ingenuo tiene sesgo positivo a fin de mes; el ensamble lo corrige.
    sp = ev["sesgo_posicion"]
    assert abs(sp.loc["fin de mes", "ensamble"]) < abs(sp.loc["fin de mes", "ingenuo"])


def test_ultimos_60_e_informe(pronos):
    ev = evaluar(pronos, ultimos=60)
    assert ev["n"] == 60
    assert "n >= 60: cumple" in informe(ev, ROTULO_SINTETICO)


def test_cli_demo_rotulada():
    assert ROTULO_SINTETICO in main(["--demo", "--cada", "250"])


def test_calendario_usa_dias_observados_con_feriados():
    """Si el último día hábil del mes es feriado (sin dato), el fin de mes se corre."""
    idx = pd.bdate_range("2024-03-01", "2024-04-30").drop(pd.Timestamp("2024-03-29"))
    cal = variables_calendario(idx)
    assert cal.loc["2024-03-27", "fin_mes"] == 1 and cal.loc["2024-03-28", "fin_mes"] == 1


def test_inicio_por_fecha_ventana_movil_y_deriva(nivel):
    p = pronostico_fuera_de_muestra(nivel, "2023-01-02", cada=120, ventana=250)
    assert p["ensamble"].index[0] == pd.Timestamp("2023-01-02")
    assert {"ingenuo", "deriva", "regresion", "arimax", "ensamble"} <= set(p)
    ev = evaluar(p, desde="2024-01-01")
    assert ev["periodo"][0] >= pd.Timestamp("2024-01-01") and ev["dm_deriva"] is not None
    with pytest.raises(ValueError):
        pronostico_fuera_de_muestra(nivel, "2030-01-01")


def test_componentes_y_varianza(nivel):
    """Base sintética = circulación sintética + cuentas; sólo la circulación tiene calendario."""
    from monetario_demo.liquidez import (descomponer_varianza, evaluar_contra_ingenuo,
                                         pronostico_por_componentes)
    rng = np.random.default_rng(5)
    cc = pd.Series(500 * np.exp(np.cumsum(rng.normal(0, 0.01, len(nivel)))), index=nivel.index)
    base = nivel + cc
    d = descomponer_varianza(base, nivel)
    assert d["circulacion"] + d["cuentas_corrientes"] + d["covarianza"] == pytest.approx(1)
    assert d["n"] == len(base) - 1 and d["desde"] == base.index[1] and d["hasta"] == base.index[-1]
    # recorte sobre variaciones: el primer día del período conserva su variación
    corte = base.index[100]
    d2 = descomponer_varianza(base, nivel, desde=corte)
    assert d2["desde"] == corte and d2["n"] == len(base.loc[corte:])
    comp = pronostico_por_componentes(base, nivel, "2023-01-02", cada=120)
    ing = pronostico_fuera_de_muestra(base, "2023-01-02", cada=120)["ingenuo"]
    r = evaluar_contra_ingenuo(comp, ing)
    assert r["MAE_rel"] < 1 and 0.75 <= r["cobertura"] <= 1
    # sin look-ahead: alterar el final no cambia los pronósticos del primer bloque
    b2 = base.copy()
    b2.iloc[-20:] *= 1.3
    comp2 = pronostico_por_componentes(b2, nivel, "2023-01-02", cada=120)
    pd.testing.assert_series_equal(comp["pron"].iloc[:120], comp2["pron"].iloc[:120])
