"""Tests de la rutina C (Eje 4): banda de tolerancia y fan chart."""

import numpy as np
import pandas as pd
import pytest

from monetario_demo.bandas import (banda_tolerancia, chequear_desvios, errores_historicos,
                                   fan_chart, main)
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
