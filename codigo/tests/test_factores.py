"""Tests del modelo por factores de las cuentas corrientes (Eje 1).

Los tests de formato e identidades usan los CSV reales de ``datos/`` (se saltean si
no están); los de lógica usan DATOS SINTÉTICOS DE DEMOSTRACIÓN, NO OFICIALES.
"""

import json

import numpy as np
import pandas as pd
import pytest

from monetario_demo import datos
from monetario_demo import factores as fa

HAY_REALES = all((datos.CARPETA_DATOS / f"bcra_{i}_daily.csv").exists()
                 for i in (15, 16, 19, 46, *fa.FACTORES))
reales = pytest.mark.skipif(not HAY_REALES, reason="faltan CSV reales en datos/")


@pytest.fixture(scope="module")
def demo():
    return fa.demo_factores(n_dias=700, semilla=7)


# ----------------------------------------------------------------- datos reales

@reales
def test_reales_formato_y_metadata():
    for i in fa.FACTORES:
        m = json.loads((datos.CARPETA_DATOS / f"metadata_{i}.json").read_text(encoding="utf-8"))
        assert m["catalogo"]["tipoSerie"] == "Flujo diario"
        assert m["catalogo"]["unidadExpresion"] == "En millones de ARS"
        assert m["descarga"]["validacion"] == "ok"
    df = fa.cargar_factores()
    assert df.index.is_monotonic_increasing and not df.index.duplicated().any()
    # Único sábado: 2005-12-31 en los saldos (15, 16, 19), no en los flujos; fuera de la muestra.
    finde = df.index[df.index.dayofweek >= 5]
    assert list(finde.strftime("%Y-%m-%d")) == ["2005-12-31"]
    assert df.loc[finde, list(fa.FACTORES)].isna().all().all()
    assert df.loc["2003":, list(fa.FACTORES)].dropna().shape[0] > 5000


@reales
def test_reales_identidades():
    v = fa.verificar_identidades(fa.cargar_factores())
    assert v["a_ok_desde_2019"] >= 0.999          # sin 56 y 57 la identidad es exacta desde 2019
    assert v["b_ok"] >= 0.98 and v["b_max"] < 5   # 46 = variación de 15 (redondeo)
    assert v["c_ok"] >= 0.999                     # 19 = 15 - 16


@reales
def test_reales_descomposicion_suma_uno():
    y, F = fa.a_pp_base(fa.cargar_factores())
    t = fa.descomponer_por_factor(y, F, "2022-01-03")
    assert abs(t["participacion"].sum() - 1) < 1e-6
    assert t["varianza_propia"].sum() > 1          # los factores se compensan entre sí


# ----------------------------------------------------------------- lógica (sintéticos)

def test_demo_identidades_exactas(demo):
    v = fa.verificar_identidades(demo)
    assert v["a_ok"] == 1 and v["b_ok"] == 1 and v["c_ok"] == 1
    y, F = fa.a_pp_base(demo)
    assert np.allclose(F.dropna().sum(axis=1), y.reindex(F.dropna().index))
    t = fa.descomponer_por_factor(y, F)
    assert abs(t["participacion"].sum() - 1) < 1e-9
    assert t["participacion"].idxmax() == 51       # el Tesoro domina por construcción


def test_sin_look_ahead_v1_v2(demo):
    y, F = fa.a_pp_base(demo)
    corte = demo.index[620]
    alt = demo.copy()
    alt.loc[alt.index > corte, list(fa.FACTORES)] *= 5          # se altera el futuro
    alt[46] = alt[list(fa.FACTORES)].sum(axis=1)
    alt[15] = demo[15].iloc[0] + alt[46].fillna(0).cumsum()
    alt[19] = alt[15] - alt[16]
    y2, F2 = fa.a_pp_base(alt)
    ini = demo.index[560]
    for rasgos in (fa.rasgos_v1, fa.rasgos_v2):
        p1 = fa.pronostico_ols(y, rasgos(F), ini, desde=demo.index[0])
        p2 = fa.pronostico_ols(y2, rasgos(F2), ini, desde=demo.index[0])
        assert np.allclose(p1.loc[:corte, "pron"], p2.loc[:corte, "pron"])


def test_dias_concentrados_causal_y_detecta(demo):
    _, F = fa.a_pp_base(demo)
    idx = F.index
    ind = fa.dias_concentrados(F[55], idx)
    pos = fa._posiciones(idx)["pos"]
    tarde = idx[idx > idx[300]]
    assert ind.loc[tarde][pos.loc[tarde] == 1].mean() == 1     # pago el 1er día hábil
    assert ind.loc[tarde][pos.loc[tarde] > 3].mean() < 0.05
    # un pico enorme en un mes no cambia la indicadora de ese mismo mes
    s = F[55].copy()
    mes = idx[(idx.year == idx[500].year) & (idx.month == idx[500].month)]
    s.loc[mes[5]] = 1e4
    ind2 = fa.dias_concentrados(s, idx)
    assert (ind2.loc[mes] == ind.loc[mes]).all()


def test_indicadoras_vencimientos():
    idx = pd.bdate_range("2024-01-01", periods=200)
    s = pd.Series(np.r_[np.full(100, 0.1), [5.0], np.full(99, 0.1)], index=idx, name=53)
    v = fa.indicadoras_vencimientos(s, idx)
    salto = idx[100]
    for h in (7, 14, 28):
        d = idx[idx.searchsorted(salto + pd.Timedelta(days=h))]
        assert v.loc[d, f"vto_53_{h}"] == 1 and v[f"vto_53_{h}"].sum() == 1
    assert v.loc[:salto].to_numpy().sum() == 0


def test_variantes_en_demo(demo):
    pr = fa.correr_variantes(demo, inicio_eval=str(demo.index[560].date()),
                             desde=str(demo.index[0].date()), con_ensamble=False, movil=None)
    ev = fa.evaluar(pr)
    assert ev.loc["V1", "MAE_rel"] < 0.97           # "otras" revierte: los rezagos ayudan
    assert ev.loc["V3_NF", "MAE_rel"] < 0.85        # previsión perfecta del Tesoro
    assert ev.loc["O51_55_NF", "MAE_rel"] < 0.85
    assert ev["n"].nunique() == 1                    # misma muestra para todos
    assert 0.6 < ev.loc["V1", "cobertura"] <= 1


def test_main_demo_rotulado(capsys):
    texto = fa.main(["--demo"])
    assert datos.ROTULO_SINTETICO in texto and "NO FACTIBLE" in texto
