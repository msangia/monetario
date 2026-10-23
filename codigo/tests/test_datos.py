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


# ---------------------------------------------------------------------------
# Formatos mensuales de INDEC (archivos reales de datos/, públicos)
# ---------------------------------------------------------------------------
EMAE = datos.CARPETA_DATOS / "emae_mensual.csv"
IPC = datos.CARPETA_DATOS / "ipc_mensual.csv"
con_archivo = lambda p: pytest.mark.skipif(not p.exists(), reason=f"falta {p.name}")


@pytest.mark.parametrize("texto, esperado", [
    ("1/1/2004", "2004-01-31"), ("1/12/2010", "2010-12-31"), ("dic-16", "2016-12-31"),
    ("sept-26", "2026-09-30"), ("set-26", "2026-09-30"), ("sep-26", "2026-09-30"),
    (" Ene.2017 ", "2017-01-31"), ("feb-2024", "2024-02-29"), ("2024-02-01", "2024-02-29")])
def test_parsear_mes(texto, esperado):
    assert datos.parsear_mes(texto) == pd.Timestamp(esperado)


@pytest.mark.parametrize("texto", ["sem-26", "13/13/2004", "2024", ""])
def test_parsear_mes_rechaza(texto):
    with pytest.raises(ValueError):
        datos.parsear_mes(texto)


def _consecutivos(s: pd.Series) -> bool:
    esperado = pd.date_range(s.index[0], s.index[-1], freq="ME")
    return s.index.equals(esperado)


@con_archivo(EMAE)
@pytest.mark.parametrize("columna", ["emae_se", "emae_orig"])
def test_emae_real(columna):
    s = datos.cargar_emae(EMAE, columna)
    assert s.index[0] == pd.Timestamp("2004-01-31")
    assert s.index[-1] == pd.Timestamp("2026-08-31")
    assert len(s) == 272 and _consecutivos(s)
    assert s.notna().all() and (s > 0).all() and s.index.is_monotonic_increasing
    assert s.iloc[0] == pytest.approx(98.5 if columna == "emae_se" else 92.6)


@con_archivo(IPC)
def test_ipc_real():
    s = datos.cargar_ipc(IPC)
    assert s.index[0] == pd.Timestamp("2016-12-31") and s.iloc[0] == pytest.approx(100.0)
    assert s.index[-1] == pd.Timestamp("2026-09-30")
    assert len(s) == 118 and _consecutivos(s)
    assert s.notna().all() and s.is_monotonic_increasing  # nivel de precios creciente


@con_archivo(EMAE)
def test_cargar_csv_detecta_formato_mensual():
    por_defecto = datos.cargar_csv(EMAE)
    pd.testing.assert_series_equal(por_defecto, datos.cargar_emae(EMAE))
    orig = datos.cargar_csv(f"{EMAE}:emae_orig")
    assert orig.iloc[0] == pytest.approx(92.6)
    # fin de mes: a_mensual no cambia la serie
    pd.testing.assert_series_equal(datos.a_mensual(por_defecto), por_defecto, check_freq=False)


def test_mensual_tolerancias_y_errores(tmp_path):
    p = tmp_path / "m.csv"
    p.write_text('mes,ipc_ng\r\ndic-16,100.0 \r\nene-17, "101,6"\r\n,\r\n')
    s = datos.cargar_mensual(p)
    assert list(s) == [100.0, 101.6]
    (tmp_path / "dup.csv").write_text("mes,v\n1/1/2004,1\n2/1/2004,2\n")  # m/d mal leído
    with pytest.raises(ValueError, match="repetidos"):
        datos.cargar_mensual(tmp_path / "dup.csv")
    (tmp_path / "dos.csv").write_text("mes,a,b\n1/1/2004,1,2\n")
    with pytest.raises(ValueError, match="indicar la columna"):
        datos.cargar_mensual(tmp_path / "dos.csv")
    (tmp_path / "malo.csv").write_text("mes,v\n1/1/2004,s/d\n")
    with pytest.raises(ValueError, match="no numéricos"):
        datos.cargar_mensual(tmp_path / "malo.csv")


# ---------------------------------------------------------------------------
# IPC empalmado y meses completos
# ---------------------------------------------------------------------------
def _ipc_prueba(tmp_path, factor=1.0, quiebre=None):
    """Archivos IPC de prueba (valores inventados, no oficiales)."""
    meses = pd.date_range("2016-10-01", "2017-03-01", freq="MS")
    hist = np.array([95.0, 98.0, 100.0, 101.6, 103.7, 106.2])
    ofic = hist[2:] * factor
    if quiebre is not None:
        ofic[quiebre:] *= 1.05
    (tmp_path / "hist.csv").write_text("fecha,ipc\n" + "".join(
        f"{m.day}/{m.month}/{m.year},{v:.2f}\n" for m, v in zip(meses, hist)))
    nombres = ["dic-16", "ene-17", "feb-17", "mar-17"]
    (tmp_path / "ofic.csv").write_text("mes,ipc_ng\n" + "".join(
        f"{n},{v:.4f}\n" for n, v in zip(nombres, ofic)))
    return tmp_path / "hist.csv", tmp_path / "ofic.csv"


def test_ipc_historico_empalma_hacia_atras(tmp_path):
    h, o = _ipc_prueba(tmp_path, factor=2.0)
    s = datos.cargar_ipc_historico(h, o)
    assert s.index[0] == pd.Timestamp("2016-10-31") and len(s) == 6
    assert s.loc["2016-12-31"] == pytest.approx(200.0)       # oficial desde dic-2016
    assert s.loc["2016-10-31"] == pytest.approx(190.0)       # histórico reescalado
    assert "hist.csv hasta 2016-11" in s.attrs["empalme"]


def test_ipc_historico_rechaza_razon_no_constante(tmp_path):
    h, o = _ipc_prueba(tmp_path, quiebre=2)
    with pytest.raises(ValueError, match="no es constante"):
        datos.cargar_ipc_historico(h, o)


HIST = datos.CARPETA_DATOS / "ipc_historico.csv"


@con_archivo(HIST)
def test_ipc_historico_real():
    s = datos.cargar_ipc_historico()
    assert s.index[0] == pd.Timestamp("1992-12-31") and _consecutivos(s)
    oficial = datos.cargar_ipc(IPC)
    pd.testing.assert_series_equal(s.loc["2016-12":], oficial, check_names=False)


def test_meses_completos():
    idx = pd.bdate_range("2026-09-01", "2026-10-20")
    s = pd.Series(1.0, index=idx)
    assert datos.meses_completos(s).index[-1] == pd.Timestamp("2026-09-30")
    s2 = pd.Series(1.0, index=pd.bdate_range("2026-09-01", "2026-10-28"))
    assert datos.meses_completos(s2).index[-1] == pd.Timestamp("2026-10-28")
