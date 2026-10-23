"""Tests del prototipo exploratorio no lineal (LSTR). DATOS SINTÉTICOS, NO OFICIALES."""

import numpy as np
import pandas as pd
import pytest

from monetario_demo import bandas
from monetario_demo.no_lineal import (Datos, coeficientes_regimen, estimar, logistica, main,
                                      demo_panel, pronostico_expansivo)
from monetario_demo.no_lineal import test_linealidad as prueba_linealidad


@pytest.fixture(scope="module")
def panel():
    return demo_panel()


def test_logistica_limites_y_punto_medio():
    s = np.array([-10.0, 0.5, 10.0])
    g = logistica(s, gamma=5.0, c=0.5)
    assert g[0] < 1e-6 and abs(g[1] - 0.5) < 1e-12 and g[2] > 1 - 1e-6


def test_linealidad_rechaza_con_lstr_y_no_con_lineal(panel):
    assert prueba_linealidad(Datos.desde_panel(panel))["p_LM3"] < 0.01
    # Tamaño: con DGP lineal la proporción de rechazos al 5 % debe ser baja.
    rechazos = [prueba_linealidad(Datos.desde_panel(demo_panel(semilla=s, lineal=True)))["p_LM3"]
                < 0.05 for s in range(10)]
    assert sum(rechazos) <= 3


def test_lstr_recupera_regimenes(panel):
    d = Datos.desde_panel(panel)
    aj = estimar(d, len(d.x) - 1, "lstr")
    assert 0.3 < aj.trans[1] < 0.75                  # umbral verdadero 0,5
    cr = coeficientes_regimen(aj)
    assert cr.loc["di", "bajo"] < cr.loc["di", "alto"]   # efecto de di más fuerte con tasa baja
    assert aj.ssr < estimar(d, len(d.x) - 1, "lineal").ssr


def test_tendencia_recupera_caida(panel):
    d = Datos.desde_panel(panel)
    aj = estimar(d, len(d.x) - 1, "tec")
    assert aj.beta[3] < -0.2                         # caída verdadera: -0,4
    assert abs(aj.tec[1] - 0.7 * len(d.x)) < 30      # punto medio verdadero: 70 % de la muestra


def test_lineal_exacto_sin_ruido():
    """Si el dinero real está siempre en su equilibrio lineal (sin ruido), el MCE lineal
    pronostica sin error a 1-3 meses (condicional a y, i, P)."""
    n = 80
    idx = pd.period_range("2010-01", periods=n, freq="M").to_timestamp("M")
    rng = np.random.default_rng(1)
    y = 4.6 + np.cumsum(rng.normal(0.002, 0.01, n))
    i = 0.4 + np.cumsum(rng.normal(0, 0.03, n))
    x = 1 + y - 0.8 * i
    lp = np.linspace(0, 1, n)
    p = pd.DataFrame({"m_real": x, "y": y, "i": i, "log_p": lp, "log_m": x + lp}, index=idx)
    pr = pronostico_expansivo(Datos.desde_panel(p), "lineal", min_obs=40)
    err = bandas.errores_de_pronostico(p["log_m"], pr)
    assert np.nanmax(np.abs(err.to_numpy())) < 1e-6


@pytest.mark.parametrize("modelo", ["lstr", "tec"])
def test_sin_look_ahead(panel, modelo):
    """Alterar el dinero futuro no cambia los pronósticos de orígenes anteriores."""
    d1 = Datos.desde_panel(panel)
    alterado = panel.copy()
    alterado.iloc[-10:, alterado.columns.get_loc("m_real")] += 0.5
    d2 = Datos.desde_panel(alterado)
    p1 = pronostico_expansivo(d1, modelo, min_obs=150)
    p2 = pronostico_expansivo(d2, modelo, min_obs=150)
    corte = panel.index[-14]
    pd.testing.assert_frame_equal(p1.loc[:corte], p2.loc[:corte])


def test_modelo_invalido(panel):
    with pytest.raises(ValueError):
        estimar(Datos.desde_panel(panel), 100, "otro")


def test_main_demo_rotulado():
    texto = main(["--demo"])
    assert "SINTÉTICOS" in texto and "lstr_tec" in texto
