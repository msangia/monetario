"""Tests del módulo de evaluación (Diebold-Mariano con corrección HLN)."""

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from monetario_demo.evaluacion import cobertura, diebold_mariano, sesgo_por_dia, tabla_errores


def test_dm_formula_hln_h1():
    rng = np.random.default_rng(1)
    e1, e2 = rng.normal(0, 1, 100), rng.normal(0, 1.2, 100)
    d = np.abs(e1) - np.abs(e2)
    n = d.size
    dm = d.mean() / np.sqrt(d.var() / n)  # varianza con divisor n
    esperado = dm * np.sqrt((n + 1 - 2) / n)
    r = diebold_mariano(e1, e2, h=1, perdida="abs", alternativa="menor")
    assert r.estadistico == pytest.approx(esperado)
    assert r.p_valor == pytest.approx(stats.t.cdf(esperado, n - 1))


def test_dm_detecta_modelo_mejor_y_no_al_reves():
    rng = np.random.default_rng(2)
    bueno, malo = rng.normal(0, 1, 200), rng.normal(0, 2, 200)
    assert diebold_mariano(bueno, malo).rechaza(0.10)
    assert not diebold_mariano(malo, bueno).rechaza(0.10)


def test_dm_tamano_aproximado_bajo_la_nula():
    rng = np.random.default_rng(3)
    rechazos = [diebold_mariano(rng.normal(size=80), rng.normal(size=80)).rechaza(0.10)
                for _ in range(400)]
    assert 0.05 < np.mean(rechazos) < 0.15


def test_dm_horizonte_mayor_y_errores():
    rng = np.random.default_rng(4)
    e1, e2 = rng.normal(size=60), rng.normal(size=60)
    r = diebold_mariano(e1, e2, h=3, perdida="cuad", alternativa="distinta")
    assert 0 <= r.p_valor <= 1 and r.h == 3
    with pytest.raises(ValueError):
        diebold_mariano(e1, e1)
    with pytest.raises(ValueError):
        diebold_mariano(e1[:5], e2[:5])


def test_cobertura_tabla_y_sesgo():
    idx = pd.bdate_range("2024-01-01", periods=40)
    obs = pd.Series(np.arange(40.0), index=idx)
    assert cobertura(obs, obs - 1, obs + 1) == 1.0
    t = tabla_errores(obs, {"ingenuo": obs - 2, "m": obs - 1})
    assert t.loc["m", "MAE_rel"] == pytest.approx(0.5)
    assert (sesgo_por_dia(obs - (obs - 1)) == 1).all()
