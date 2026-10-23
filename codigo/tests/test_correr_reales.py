"""Tests de la medida de significancia económica de la rutina A. DATOS SINTÉTICOS."""

import numpy as np
import pandas as pd
import pytest

from correr_reales import ahorro_pp_base


def test_ahorro_pp_base_pondera_por_peso_en_la_base():
    idx = pd.bdate_range("2024-01-01", periods=50)
    obs = pd.Series(1.0, index=idx)
    modelo = pd.DataFrame({"obs": obs, "pron": 0.5})      # error 0,5 %
    ingenuo = pd.DataFrame({"obs": obs, "pron": 0.0})     # error 1 %
    peso = pd.Series(0.4, index=idx)                      # la serie es el 40 % de la base
    # mejora de 0,5 % de la serie = 0,2 pp de la base (el primer día no tiene peso previo)
    assert ahorro_pp_base(modelo, ingenuo, peso) == pytest.approx(0.2)
    assert ahorro_pp_base(modelo, ingenuo, peso, ultimos=10) == pytest.approx(0.2)
