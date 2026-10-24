"""Tests de las figuras de los anexos. DATOS SINTÉTICOS DE DEMOSTRACIÓN, NO OFICIALES
(salvo los marcados ``reales``, que usan los CSV de ``datos/`` y se saltean si faltan)."""

import numpy as np
import pandas as pd
import pytest

from monetario_demo import datos, graficos
from monetario_demo import factores as fa


@pytest.fixture
def figuras_capturadas(monkeypatch):
    """Captura cada figura antes de guardarla, para inspeccionar títulos y rótulos."""
    capturadas = []
    original = graficos._guardar

    def guardar(fig, ruta):
        capturadas.append(fig)
        return original(fig, ruta)

    monkeypatch.setattr(graficos, "_guardar", guardar)
    return capturadas


def test_coma_decimal():
    assert graficos.coma(0.954, 2) == "0,95"
    assert graficos.coma(-10.71) == "−10,7"


def test_perfil_por_posicion_recupera_sesgo_de_fin_de_mes():
    rng = np.random.default_rng(1)
    idx = pd.bdate_range("2018-01-01", "2023-12-31")
    pos, pos_fin = datos.posicion_en_mes(idx)
    e = pd.Series(rng.normal(0, 0.5, len(idx)) + 2.0 * (pos_fin == 1) - 1.0 * (pos == 2),
                  index=idx)
    t = graficos.perfil_por_posicion(e, pd.DataFrame({"pos": pos, "pos_fin": pos_fin},
                                                     index=idx), k=3)
    assert list(t.index) == ["1", "2", "3", "-3", "-2", "-1"]
    assert t.loc["-1", "media"] == pytest.approx(2.0, abs=0.15)
    assert t.loc["2", "media"] == pytest.approx(-1.0, abs=0.15)
    assert t.loc["3", "media"] == pytest.approx(0.0, abs=0.15)
    assert (t["inf"] < t["media"]).all() and (t["media"] < t["sup"]).all()
    assert t.loc["-1", "n"] == len(pd.period_range("2018-01", "2023-12", freq="M"))


def test_demo_escribe_figuras_sin_titulo(tmp_path, figuras_capturadas):
    rutas = graficos.demo(tmp_path)
    assert len(rutas) == 5
    for r in rutas:
        assert r.exists() and r.stat().st_size > 1000 and "demo" in r.name
    for fig in figuras_capturadas:
        assert fig._suptitle is None
        for ax in fig.axes:
            assert ax.get_title(loc="left") == ax.get_title() == ax.get_title(loc="right") == ""
            # ejes rotulados (con unidades) en todos los paneles con datos
            assert ax.get_xlabel() or ax.get_ylabel() or ax.get_xticklabels()


def test_fuentes_de_al_menos_9_pt(tmp_path, figuras_capturadas):
    graficos.demo(tmp_path)
    for fig in figuras_capturadas:
        assert fig.get_figwidth() == pytest.approx(graficos.ANCHO)
        for t in fig.findobj(lambda o: hasattr(o, "get_fontsize") and hasattr(o, "get_text")):
            if t.get_text().strip():
                assert t.get_fontsize() >= 9, t.get_text()   # 9,5 pt; anotaciones 9


def test_mae_relativo_marca_significancia(tmp_path, figuras_capturadas):
    mae = pd.DataFrame({"p1": [0.5, 1.1]}, index=["a", "b"])
    p = pd.DataFrame({"p1": [0.01, 0.8]}, index=["a", "b"])
    graficos.fig_mae_relativo(mae, p, tmp_path / "m.pdf", meta=0.95)
    ax = figuras_capturadas[0].axes[0]
    colecciones = [c for c in ax.collections if len(c.get_offsets())]
    llenos, huecos = colecciones[0], colecciones[1]
    assert llenos.get_offsets()[0][0] == pytest.approx(0.5)      # significativo: lleno
    assert huecos.get_offsets()[0][0] == pytest.approx(1.1)      # no significativo: hueco
    assert tuple(huecos.get_facecolor()[0][:3]) == (1.0, 1.0, 1.0)


@pytest.mark.skipif(not (datos.CARPETA_DATOS / "bcra_59_daily.csv").exists(),
                    reason="faltan CSV reales en datos/")
def test_reales_grupos_de_factores_suman_uno():
    from correr_reales import participacion_por_grupo
    y, F = fa.a_pp_base(fa.cargar_factores())
    g = participacion_por_grupo(y, F, "2022-01-03")
    assert g.sum() == pytest.approx(1.0, abs=1e-6)
    assert g["Pases (52)"] == pytest.approx(0.495, abs=0.001)
    g2 = participacion_por_grupo(y, F, "2025-07-11")
    assert np.isnan(g2["Pases (52)"]) and np.isnan(g2["LEFI (58)"])
    assert g2.sum() == pytest.approx(1.0, abs=1e-6)


def test_tabla_figura_a_ordena_series_y_periodos():
    from correr_reales import PERIODOS_FIG, SERIES_FIG, tabla_figura_a
    filas = [{"serie": s, "periodo": p, "MAE_rel": 1.0 + i / 10}
             for i, s in enumerate(SERIES_FIG) for p in PERIODOS_FIG]
    t = tabla_figura_a(pd.DataFrame(filas), "MAE_rel")
    assert list(t.index) == list(SERIES_FIG.values())
    assert list(t.columns) == list(PERIODOS_FIG.values())
    assert t.iloc[0, 0] == pytest.approx(1.0)


def test_mae_relativo_con_leyenda_interna_y_meta(tmp_path, figuras_capturadas):
    mae = pd.DataFrame({"p1": [0.5, 1.1], "p2": [0.6, 1.2]}, index=["a", "b"])
    p = pd.DataFrame({"p1": [0.01, 0.8], "p2": [0.2, 0.9]}, index=["a", "b"])
    graficos.fig_mae_relativo(mae, p, tmp_path / "m.pdf", meta=0.95, leyenda="lower left")
    fig = figuras_capturadas[0]
    ax = fig.axes[0]
    assert ax.get_legend() is not None and not fig.legends      # leyenda dentro del eje
    textos = [t.get_text() for t in ax.texts]
    assert any("0,95" in t for t in textos)                       # meta rotulada con coma
    assert ax.get_title() == "" and fig._suptitle is None
