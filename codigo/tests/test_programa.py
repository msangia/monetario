"""Tests de los programas de la rutina C (Eje 4). DATOS SINTÉTICOS, NO OFICIALES."""

import numpy as np
import pandas as pd
import pytest

from monetario_demo import bandas
from monetario_demo.programa import (comparar, demo_panel, main, programas,
                                     pronostico_deriva_estacional, pronostico_mce,
                                     pronostico_velocidad)


@pytest.fixture(scope="module")
def panel():
    return demo_panel()


def test_mce_sin_look_ahead(panel):
    """Cambiar el futuro no altera los pronósticos de orígenes anteriores... salvo
    por las variables condicionantes de t + h (P, y, i), que son el escenario."""
    p1 = pronostico_mce(panel)
    alterado = panel.copy()
    alterado.iloc[-10:, alterado.columns.get_loc("m_real")] += 0.5
    alterado["log_m"] = alterado["m_real"] + alterado["log_p"]
    p2 = pronostico_mce(alterado)
    corte = panel.index[-11]
    pd.testing.assert_frame_equal(p1.loc[:panel.index[-14]], p2.loc[:panel.index[-14]])
    assert corte in p1.index


def test_velocidad_exacta_con_velocidad_constante():
    idx = pd.period_range("2010-01", periods=40, freq="M").to_timestamp("M")
    lp, y = np.linspace(0, 1, 40), np.linspace(4.6, 4.8, 40)
    panel = pd.DataFrame({"log_p": lp, "y": y, "log_m": lp + y - 0.3, "i": 0.3}, index=idx)
    panel["m_real"] = panel["log_m"] - panel["log_p"]
    err = bandas.errores_de_pronostico(panel["log_m"], pronostico_velocidad(panel))
    assert np.nanmax(np.abs(err.to_numpy())) < 1e-9


def test_deriva_estacional_capta_estacionalidad():
    idx = pd.period_range("2010-01", periods=120, freq="M").to_timestamp("M")
    g = 0.02 + 0.05 * (idx.month == 12) - 0.05 / 11 * (idx.month != 12)
    lm = pd.Series(np.cumsum(g), index=idx)
    err = bandas.errores_de_pronostico(lm, pronostico_deriva_estacional(lm))
    assert np.nanmax(np.abs(err.to_numpy())) < 1e-6


def test_comparar_y_cobertura(panel):
    t = comparar(panel, programas(panel), "2012-01")
    assert set(t["programa"]) == {"deriva", "deriva_estacional", "velocidad", "mce", "mce_sin_estac"}
    mce = t[t["programa"] == "mce"]
    assert (mce["MAE_rel_deriva"] < 1).all()           # el generador tiene demanda estable
    assert mce["cobertura_90"].between(0.7, 1.0).all()


def test_cobertura_banda_sin_look_ahead():
    rng = np.random.default_rng(0)
    idx = pd.period_range("2000-01", periods=200, freq="M").to_timestamp("M")
    err = pd.DataFrame({1: rng.normal(size=200), 2: rng.normal(size=200)}, index=idx)
    c = bandas.cobertura_banda(err, 0.9, minimo=24)
    assert c.loc[1, "n"] == 200 - 24 and c.loc[2, "n"] == 200 - 25
    assert c["cobertura"].between(0.8, 0.97).all()


def test_cli_demo_rotulada(tmp_path):
    texto = main(["--demo", "--figura", str(tmp_path / "f.png")])
    assert "SINTÉTICOS" in texto and (tmp_path / "f.png").exists()
