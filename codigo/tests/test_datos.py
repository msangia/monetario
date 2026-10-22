"""Tests de carga de CSV y de los generadores sintéticos."""

import numpy as np
import pandas as pd
import pytest

import monetario_demo.datos as datos


def test_csv_iso(tmp_path):
    p = tmp_path / "serie.csv"
    p.write_text("fecha,valor\n2024-01-03,2.5\n2024-01-02,1.5\n2024-01-03,3.0\n")
    s = datos.cargar_csv(p)
    assert list(s.index) == [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")]
    assert s.iloc[-1] == 3.0  # duplicado: queda el último


def test_csv_planilla_en_espanol(tmp_path):
    p = tmp_path / "serie.csv"
    p.write_text("fecha;valor\n2024-01-02;1.234,5\n2024-01-03;1.300,0\n")
    s = datos.cargar_csv(p)
    assert s.iloc[0] == pytest.approx(1234.5)


def test_csv_por_id_y_errores(tmp_path, monkeypatch):
    monkeypatch.setattr(datos, "CARPETA_DATOS", tmp_path)
    (tmp_path / "bcra_104_daily.csv").write_text("fecha,valor\n2024-01-02,10\n")
    assert datos.cargar_csv("104").iloc[0] == 10
    with pytest.raises(FileNotFoundError):
        datos.cargar_csv("999")
    (tmp_path / "malo.csv").write_text("dia,monto\n2024-01-02,1\n")
    with pytest.raises(ValueError):
        datos.cargar_csv(tmp_path / "malo.csv")


def test_a_mensual():
    idx = pd.date_range("2024-01-01", "2024-02-29", freq="D")
    s = pd.Series(1.0, index=idx)
    assert len(datos.a_mensual(s)) == 2 and len(datos.a_mensual(s, "fin")) == 2


def test_generadores_reproducibles():
    a, b = datos.demo_liquidez_diaria(), datos.demo_liquidez_diaria()
    pd.testing.assert_series_equal(a, b)
    assert (a > 0).all() and a.index.dayofweek.max() <= 4
    assert datos.demo_demanda_dinero().shape == (252, 3)
    assert np.isfinite(datos.demo_agregado_mensual()).all()
