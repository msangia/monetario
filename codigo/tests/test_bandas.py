"""Tests de la rutina C (Eje 4): banda de tolerancia y fan chart."""

import pandas as pd
import pytest

from monetario_demo.bandas import (banda_tolerancia, chequear_desvios, errores_historicos,
                                   fan_chart, grafico_chequeo, main,
                                   pronostico_deriva)
from monetario_demo.datos import demo_agregado_mensual


def test_banda_sin_look_ahead_y_cuantiles_ordenados():
    serie = demo_agregado_mensual(shock_final=0.0)
    err = errores_historicos(serie)
    corte = err.index[100]
    b1 = banda_tolerancia(err, corte)
    err2 = err.copy()
    for h in err.columns:  # errores aún no observados al corte: origen + h > corte
        err2.iloc[100 - h + 1:, err.columns.get_loc(h)] = 99.0
    pd.testing.assert_frame_equal(b1, banda_tolerancia(err2, corte))
    assert (b1["inf_90"] < b1["inf_50"]).all() and (b1["sup_50"] < b1["sup_90"]).all()


def test_banda_exige_historia_minima():
    err = errores_historicos(demo_agregado_mensual())
    with pytest.raises(ValueError):
        banda_tolerancia(err, err.index[10])


def test_chequeo_detecta_shock_final():
    tabla = chequear_desvios(demo_agregado_mensual(shock_final=0.06), trimestres=4)
    assert len(tabla) == 12
    assert (tabla.tail(2)["estado"] == "fuera de banda").all()


def test_sin_shock_mayoria_dentro():
    tabla = chequear_desvios(demo_agregado_mensual(shock_final=0.0, semilla=7), trimestres=8)
    assert (tabla["estado"] == "dentro de banda").mean() >= 0.75


def test_fan_chart_y_cli(tmp_path):
    ruta = fan_chart(demo_agregado_mensual(), tmp_path / "fan.png")
    assert ruta.exists() and ruta.stat().st_size > 1000
    assert "SINTÉTICOS" in main(["--demo"])


def test_ventana_corta_permite_series_cortas():
    serie = demo_agregado_mensual(n_meses=62, shock_final=0.0)
    with pytest.raises(ValueError):
        chequear_desvios(serie, trimestres=2, ventana=36)
    assert len(chequear_desvios(serie, trimestres=2, ventana=24)) == 6


def test_grafico_chequeo_marca_meses_fuera(tmp_path):
    """DATOS SINTÉTICOS: con shock final, el gráfico se genera sobre los 4 trimestres."""
    serie = demo_agregado_mensual(shock_final=0.06)
    ruta = grafico_chequeo(serie, pronostico_deriva(serie), tmp_path / "chk.png")
    assert ruta.exists() and ruta.stat().st_size > 1000


def test_desvio_en_porcentaje_simple():
    """El desvío es 100 * (obs / prog - 1), no la diferencia logarítmica."""
    import numpy as np
    from monetario_demo.bandas import errores_de_pronostico
    idx = pd.period_range("2020-01", periods=3, freq="M").to_timestamp("M")
    log_obs = pd.Series(np.log([100.0, 92.1, 50.0]), index=idx)
    pron = pd.DataFrame({1: [np.log(100.0)]}, index=idx[:1])
    assert errores_de_pronostico(log_obs, pron).iloc[0, 0] == pytest.approx(-7.9)
