"""Tests de la rutina B (Eje 4): demanda de dinero con corrección de errores."""

import numpy as np
import pandas as pd
import pytest

from monetario_demo.datos import CARPETA_DATOS, demo_demanda_dinero
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


def _diaria_sintetica(ruta, inicio, fin, nivel, crec_anual, ruido, semilla):
    """Escribe un CSV fecha,valor diario. DATOS SINTÉTICOS DE PRUEBA, NO OFICIALES."""
    rng = np.random.default_rng(semilla)
    idx = pd.bdate_range(inicio, fin)
    log_v = np.log(nivel) + np.cumsum(crec_anual / 250 + rng.normal(0, ruido, len(idx)))
    pd.DataFrame({"fecha": idx.strftime("%Y-%m-%d"), "valor": np.exp(log_v)}).to_csv(
        ruta, index=False)
    return ruta


@pytest.mark.skipif(not (CARPETA_DATOS / "ipc_mensual.csv").exists()
                    or not (CARPETA_DATOS / "emae_mensual.csv").exists(),
                    reason="faltan EMAE/IPC en datos/")
@pytest.mark.parametrize("ventana, n_ventanas", [(72, 46), (60, 58)])
def test_cli_con_emae_ipc_reales_y_diarias_sinteticas(tmp_path, ventana, n_ventanas):
    """Smoke test: EMAE e IPC reales de datos/; M2 y tasa diarias SINTÉTICAS (sólo test)."""
    m2 = _diaria_sintetica(tmp_path / "m2_sintetico.csv", "2016-11-01", "2026-10-16",
                           1e6, 0.45, 0.004, 1)
    tasa = _diaria_sintetica(tmp_path / "tasa_sintetica.csv", "2016-11-01", "2026-10-20",
                             35.0, 0.0, 0.01, 2)
    texto = main(["--dinero", str(m2), "--tasa", str(tasa), "--ventana", str(ventana),
                  "--precios", "datos/ipc_mensual.csv", "--actividad", "datos/emae_mensual.csv"])
    # IPC desde 2016-12, EMAE hasta 2026-08 -> 117 meses
    assert f"Panel 2016-12 a 2026-08: 117 meses, {n_ventanas} ventanas de {ventana}" in texto
    assert "b_i" in texto


def test_cli_avisa_si_faltan_diarias(tmp_path, monkeypatch, capsys):
    import monetario_demo.datos as datos
    monkeypatch.setattr(datos, "CARPETA_DATOS", tmp_path)
    (tmp_path / "ipc_mensual.csv").write_text("mes,ipc_ng\ndic-16,100\n")
    (tmp_path / "emae_mensual.csv").write_text("mes,emae_orig,emae_se\n1/12/2016,1,1\n")
    with pytest.raises(SystemExit):
        main(["--dinero", "109", "--tasa", "1189", "--precios", "ipc_mensual.csv",
              "--actividad", "emae_mensual.csv"])
    assert "bcra_109_daily.csv" in capsys.readouterr().err


def test_verificar_muestra_corta():
    from monetario_demo.demanda_dinero import verificar_muestra
    df = demo_demanda_dinero(n_meses=80)
    with pytest.raises(ValueError, match="--ventana 60"):
        verificar_muestra(df, 72)
