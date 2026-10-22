"""Tests de la rutina B (Eje 4): demanda de dinero con corrección de errores."""

import numpy as np
import pandas as pd
import pytest

from monetario_demo.datos import demo_demanda_dinero
from monetario_demo.demanda_dinero import (analizar, armar_panel, engle_granger, main,
                                           umbral_simulado)


def test_engle_granger_recupera_parametros_sin_quiebre():
    r = engle_granger(demo_demanda_dinero(mes_quiebre=None))
    assert r["b_y"] == pytest.approx(1.0, abs=0.25)
    assert r["b_i"] == pytest.approx(-2.0, abs=0.3)
    assert r["p_coint"] < 0.10
    assert r["g"] < 0


def test_detecta_quiebre_despues_de_ocurrido():
    df = demo_demanda_dinero(mes_quiebre=144)
    res = analizar(df, ventana=72, B=100)
    alerta = res["alertas"]["b_i"]
    quiebre = df.index[144]
    assert alerta is not None
    assert quiebre <= alerta <= quiebre + pd.DateOffset(months=12)
    assert res["rolling"]["b_i"].iloc[-1] == pytest.approx(-4.0, abs=0.5)


def test_umbral_controla_falsas_alarmas():
    """Bajo estabilidad, la alerta de b_i salta en pocas réplicas (nominal 10 %)."""
    alarmas = 0
    for s in range(10):
        df = demo_demanda_dinero(mes_quiebre=None, semilla=s)
        res = analizar(df, ventana=72, B=100)
        alarmas += res["alertas"]["b_i"] is not None
    assert alarmas <= 3


def test_umbral_positivo_y_reproducible():
    df = demo_demanda_dinero()
    u1, u2 = umbral_simulado(df, B=50), umbral_simulado(df, B=50)
    assert u1 == u2 and u1["b_i"] > 0 and u1["b_y"] > 0


def test_armar_panel_desde_series_diarias():
    idx = pd.date_range("2020-01-01", "2020-12-31", freq="D")
    uno = pd.Series(np.linspace(100, 200, len(idx)), index=idx)
    df = armar_panel(uno, uno / 2, uno, pd.Series(40.0, index=idx))
    assert list(df.columns) == ["m_real", "y", "i"] and len(df) == 12
    assert df["m_real"].iloc[0] == pytest.approx(np.log(2))
    assert df["i"].iloc[0] == pytest.approx(0.40)


def test_cli_demo_rotulada():
    assert "SINTÉTICOS" in main(["--demo"])
