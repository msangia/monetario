"""Anexo C (Eje 4): programas de base o M2 a 1-3 meses y su error histórico.

La banda de tolerancia del núcleo se deriva del error histórico del pronóstico. Este
módulo arma tres programas mensuales, siempre con parámetros estimados sólo con datos
hasta el origen t (sin *look-ahead* en la estimación):

* ``deriva``: log M_{t+h} = log M_t + h * crecimiento medio de los últimos 36 meses
  (incondicional; es el programa mecánico ilustrativo);
* ``deriva_estacional``: la deriva más un efecto de cada mes calendario (crecimiento
  medio de ese mes menos el medio, en los últimos 72 meses); separa la ganancia que
  sólo se debe a la estacionalidad (aguinaldo, diciembre) de la que aporta la demanda;
* ``velocidad``: velocidad constante (cantidad): M crece con el PIB nominal,
  log M_{t+h} = log M_t + (log P_{t+h} - log P_t) + (y_{t+h} - y_t);
* ``mce``: demanda de dinero real con corrección de errores (largo plazo
  m - p = c + b_y y + b_i i; corto plazo con u_{t-1}, dy, di, dm_{t-1} y dummies
  mensuales, porque el M2 no está desestacionalizado), estimada en una ventana móvil
  de 72 meses y proyectada en forma recursiva; ``mce_sin_estac`` es el mismo modelo
  sin dummies (control: cuánto de la ganancia es sólo estacionalidad).

``velocidad`` y ``mce`` son **condicionales**: usan el IPC, el EMAE y la tasa
observados entre t y t + h (como si el escenario macro se hubiera acertado). Su error
es el error *de la demanda* que define la banda del núcleo; el error total de un
programa real suma además el error del escenario, por lo que estas bandas son un
piso. ``deriva`` no usa información posterior a t.

Uso::

    python -m monetario_demo.programa --demo
    python -m monetario_demo.programa --dinero 109 --tasa 1189 --figura salidas/fan_chart_m2.pdf

Con datos reales usa por defecto sólo el IPC oficial de INDEC (desde dic-2016): el MCE
se estima en ventanas de 48 meses y se evalúa desde 2021-01. Las derivas usan toda la
historia del agregado (no dependen del IPC).
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from . import bandas
from .datos import (ROTULO_SINTETICO, a_mensual, cargar_csv, cargar_emae, cargar_ipc,
                    cargar_ipc_historico, demo_demanda_dinero, meses_completos)
from .evaluacion import diebold_mariano

H = bandas.H


def armar_panel_programa(dinero: pd.Series, precios: pd.Series, actividad: pd.Series,
                         tasa_pct: pd.Series) -> pd.DataFrame:
    """Panel mensual con ``log_m`` (nominal), ``log_p``, ``m_real``, ``y`` e ``i``.

    El dinero diario se promedia sólo en meses completos; ``i`` en tanto por uno.
    """
    df = pd.concat([a_mensual(meses_completos(dinero)), precios, actividad,
                    a_mensual(tasa_pct)], axis=1, sort=True,
                   keys=["dinero", "precios", "actividad", "tasa"]).dropna()
    out = pd.DataFrame({"log_m": np.log(df["dinero"]), "log_p": np.log(df["precios"]),
                        "y": np.log(df["actividad"]), "i": df["tasa"] / 100})
    out["m_real"] = out["log_m"] - out["log_p"]
    return out


def pronostico_velocidad(panel: pd.DataFrame, h_max: int = H) -> pd.DataFrame:
    """Log de M programado con velocidad constante, condicional a P e y observados."""
    lm, lp, y = (panel[c].to_numpy() for c in ("log_m", "log_p", "y"))
    filas = {}
    for t in range(len(panel) - 1):
        filas[panel.index[t]] = {h: lm[t] + (lp[t + h] - lp[t]) + (y[t + h] - y[t])
                                 if t + h < len(panel) else np.nan
                                 for h in range(1, h_max + 1)}
    return pd.DataFrame(filas).T


def pronostico_deriva_estacional(log_m: pd.Series, ventana: int = 36,
                                 ventana_est: int = 72, h_max: int = H) -> pd.DataFrame:
    """Deriva de ``ventana`` meses más efectos mensuales estimados en ``ventana_est`` meses."""
    g = log_m.diff().to_numpy()
    meses = log_m.index.month.to_numpy()
    lm = log_m.to_numpy()
    filas = {}
    for t in range(max(ventana, ventana_est), len(lm) - 1):
        mu = np.mean(g[t - ventana + 1:t + 1])
        ge, me = g[t - ventana_est + 1:t + 1], meses[t - ventana_est + 1:t + 1]
        efecto = {k: ge[me == k].mean() - ge.mean() for k in range(1, 13)}
        nivel, fila = lm[t], {}
        for h in range(1, h_max + 1):
            mes = (meses[t] + h - 1) % 12 + 1
            nivel = nivel + mu + efecto[mes]
            fila[h] = nivel
        filas[log_m.index[t]] = fila
    return pd.DataFrame(filas).T


def _dummies_mes(meses: np.ndarray) -> np.ndarray:
    """Dummies de febrero a diciembre (enero es la base)."""
    return (meses[:, None] == np.arange(2, 13)[None, :]).astype(float)


def pronostico_mce(panel: pd.DataFrame, ventana: int = 72, h_max: int = H,
                   estacional: bool = True) -> pd.DataFrame:
    """Log de M programado con la demanda de dinero (MCE), condicional a P, y, i observados.

    En cada origen t se estiman, con las filas t - ventana + 1 .. t: (1) el largo
    plazo por MCO y (2) el MCE de corto plazo; luego se proyecta m_real en forma
    recursiva para t + 1 .. t + h y se suma log P observado.
    """
    m, y, i, lp = (panel[c].to_numpy() for c in ("m_real", "y", "i", "log_p"))
    dum = _dummies_mes(panel.index.month.to_numpy()) if estacional else np.zeros((len(m), 0))
    filas = {}
    for t in range(ventana - 1, len(panel) - 1):
        a = t - ventana + 1
        X = np.column_stack([np.ones(ventana), y[a:t + 1], i[a:t + 1]])
        beta = np.linalg.lstsq(X, m[a:t + 1], rcond=None)[0]
        u = m - beta[0] - beta[1] * y - beta[2] * i          # sólo usa beta (hasta t)
        r = np.arange(a + 2, t + 1)
        Z = np.column_stack([np.ones(len(r)), u[r - 1], y[r] - y[r - 1], i[r] - i[r - 1],
                             m[r - 1] - m[r - 2], dum[r]])
        gam = np.linalg.lstsq(Z, m[r] - m[r - 1], rcond=None)[0]
        actual, previo, fila = m[t], m[t - 1], {}
        for h in range(1, h_max + 1):
            s = t + h
            if s >= len(m):
                fila[h] = np.nan
                continue
            u_1 = actual - beta[0] - beta[1] * y[s - 1] - beta[2] * i[s - 1]
            z = np.r_[1.0, u_1, y[s] - y[s - 1], i[s] - i[s - 1], actual - previo, dum[s]]
            previo, actual = actual, actual + float(z @ gam)
            fila[h] = actual + lp[s]
        filas[panel.index[t]] = fila
    return pd.DataFrame(filas).T


def programas(panel: pd.DataFrame, ventana_deriva: int = 36, ventana_mce: int = 72,
              log_m_largo: pd.Series | None = None) -> dict[str, pd.DataFrame]:
    """Los cinco programas (log de M por origen y horizonte).

    ``log_m_largo``: log del agregado en una muestra más larga que el panel (las derivas
    no usan precios ni actividad, así que pueden estimarse con toda la historia del
    dinero aunque el IPC empiece después).
    """
    lm = panel["log_m"] if log_m_largo is None else log_m_largo
    return {"deriva": bandas.pronostico_deriva(np.exp(lm), ventana_deriva),
            "deriva_estacional": pronostico_deriva_estacional(lm, ventana_deriva),
            "velocidad": pronostico_velocidad(panel),
            "mce": pronostico_mce(panel, ventana_mce),
            # Control de atribución: el mismo MCE sin dummies mensuales.
            "mce_sin_estac": pronostico_mce(panel, ventana_mce, estacional=False)}


def comparar(panel: pd.DataFrame, pron: dict[str, pd.DataFrame], desde: str | None = None,
             nivel: float = 0.9, log_obs: pd.Series | None = None) -> pd.DataFrame:
    """MAE (%), DM-HLN contra la deriva (y contra la deriva estacional) y calibración de la banda, por programa y horizonte.

    Todos los programas se evalúan en los mismos orígenes (los comunes, desde ``desde``).
    La cobertura es fuera de muestra (banda armada sólo con errores anteriores a t) y se
    evalúa en los orígenes comunes que tengan al menos 24 errores previos.
    ``log_obs``: serie observada contra la que se miden los errores (por defecto, la
    del panel; puede ser más larga, ver :func:`programas`).
    """
    obs = panel["log_m"] if log_obs is None else log_obs
    err = {k: bandas.errores_de_pronostico(obs, v) for k, v in pron.items()}
    comunes = err["deriva"].index
    for e in err.values():
        comunes = comunes.intersection(e.dropna().index)
    if desde:
        comunes = comunes[comunes >= pd.Timestamp(desde)]
    filas = []
    for k, e in err.items():
        cob = bandas.cobertura_banda(e.loc[: comunes[-1]], nivel, desde=comunes[0])
        for h in e.columns:
            ec, ed = e.loc[comunes, h], err["deriva"].loc[comunes, h]
            dm = None if k == "deriva" else diebold_mariano(ec, ed, h=int(h), perdida="abs")
            es = err.get("deriva_estacional")
            dm_e = (diebold_mariano(ec, es.loc[comunes, h], h=int(h), perdida="abs")
                    if es is not None and k not in ("deriva", "deriva_estacional") else None)
            # cobertura sólo en los orígenes comunes evaluados
            filas.append({"programa": k, "h": int(h), "n": len(ec),
                          "MAE_%": float(ec.abs().mean()),
                          "MAE_rel_deriva": float(ec.abs().mean() / ed.abs().mean()),
                          "p_DM_vs_deriva": np.nan if dm is None else dm.p_valor,
                          "p_DM_vs_estac": np.nan if dm_e is None else dm_e.p_valor,
                          "n_cob": int(cob.loc[h, "n"]),
                          "cobertura_90": float(cob.loc[h, "cobertura"]),
                          "ancho_90_pp": float(cob.loc[h, "ancho"])})
    return pd.DataFrame(filas)


def resumen_cobertura(tabla: pd.DataFrame) -> str:
    """Rango (mínimo-máximo entre h = 1..3) de la cobertura de la banda del 90 %, por programa.

    Es el número que se cita en los anexos: sale directamente de :func:`comparar`.
    """
    lineas = ["Rango de cobertura de la banda del 90 % entre h = 1 y h = 3 (por programa):"]
    for k, g in tabla.groupby("programa", sort=False):
        c = 100 * g.sort_values("h")["cobertura_90"]
        lineas.append(f"  {k}: {c.min():.1f}-{c.max():.1f} % "
                      f"(h=1/2/3: {' / '.join(f'{v:.1f}' for v in c)})")
    return "\n".join(lineas)


def demo_panel(semilla: int = 426) -> pd.DataFrame:
    """Panel para el programa. DATOS SINTÉTICOS DE DEMOSTRACIÓN, NO OFICIALES."""
    df = demo_demanda_dinero(mes_quiebre=None, semilla=semilla)
    rng = np.random.default_rng(semilla)
    log_p = np.cumsum(0.02 + rng.normal(0, 0.005, len(df)))
    return pd.DataFrame({"log_m": df["m_real"] + log_p, "log_p": log_p, "y": df["y"],
                         "i": df["i"], "m_real": df["m_real"]}, index=df.index)


def main(argv: list[str] | None = None) -> str:
    """Punto de entrada de línea de comandos."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--demo", action="store_true", help="datos sintéticos de demostración")
    g.add_argument("--dinero", help="id o CSV diario del agregado (109 = M2, 15 = base)")
    ap.add_argument("--tasa", default="1189", help="id o CSV de la tasa (%% anual)")
    ap.add_argument("--desde", default="2021-01", help="primer origen evaluado (AAAA-MM)")
    ap.add_argument("--ventana-mce", type=int, default=48, help="meses de la ventana del MCE")
    ap.add_argument("--precios", choices=("oficial", "empalmado"), default="oficial",
                    help="oficial = IPC INDEC desde dic-2016 (defecto); empalmado = con "
                         "ipc_historico.csv antes (fuente no documentada; descartado)")
    ap.add_argument("--trimestres", type=int, default=4)
    ap.add_argument("--figura", default=None, help="fan chart del programa MCE (PDF o PNG)")
    ap.add_argument("--figura-chequeo", default=None,
                    help="gráfico del chequeo de los últimos trimestres, programa MCE (PDF o PNG)")
    a = ap.parse_args(argv)
    if a.demo:
        panel, rotulo = demo_panel(), ROTULO_SINTETICO
        lm_largo = panel["log_m"]
        desde = "2012-01" if a.desde == "2021-01" else a.desde
        ventana_mce = 72 if a.ventana_mce == 48 else a.ventana_mce
    else:
        dinero = cargar_csv(a.dinero)
        precios = cargar_ipc_historico() if a.precios == "empalmado" else cargar_ipc()
        panel = armar_panel_programa(dinero, precios, cargar_emae(), cargar_csv(a.tasa))
        lm_largo = np.log(a_mensual(meses_completos(dinero))).loc[:panel.index[-1]]
        desde, ventana_mce = a.desde, a.ventana_mce
        nombre = {"109": "M2", "15": "base monetaria"}.get(a.dinero, "agregado")
        rotulo = (f"{nombre} (BCRA id {a.dinero}), promedio mensual; tasa id {a.tasa}; "
                  f"IPC {a.precios} y EMAE (INDEC).\nDatos reales; cálculo propio, no oficial")
    pron = programas(panel, ventana_mce=ventana_mce, log_m_largo=lm_largo)
    tabla = comparar(panel, pron, desde, log_obs=lm_largo)
    nivel = np.exp(lm_largo)
    chequeos = {k: bandas.chequear_programa(nivel, v, a.trimestres) for k, v in pron.items()}
    partes = [f"[{rotulo.replace(chr(10), ' ')}]",
              f"Panel {panel.index[0]:%Y-%m} a {panel.index[-1]:%Y-%m} ({len(panel)} meses)",
              f"Error fuera de muestra a h meses (% simple: 100 * (observado / programado - 1)), orígenes desde {desde}; MCE en ventanas de "
              f"{ventana_mce} meses; DM-HLN "
              "unilateral contra la deriva y contra la deriva estacional; cobertura y ancho "
              "de la banda del 90 % armada sin look-ahead",
              tabla.round(3).to_string(index=False),
              resumen_cobertura(tabla)]
    for k, c in chequeos.items():
        partes.append(f"Chequeo de los últimos {a.trimestres} trimestres "
                      f"({c['mes'].iloc[0]} a {c['mes'].iloc[-1]}), programa {k}: "
                      f"{(c['estado'] == 'fuera de banda').sum()} de {len(c)} meses fuera")
    partes.append("Chequeo del programa MCE; desvío y límites de la banda en % simple "
                  "(observado / programado - 1):")
    partes.append(chequeos["mce"][["mes", "h", "desvio_%", "inf_%", "sup_%", "estado"]]
                  .round(1).to_string(index=False))
    texto = "\n".join(partes)
    print(texto)
    if a.figura:
        unidad = "nivel (unidades sintéticas)" if a.demo else "billones de ARS"
        serie = nivel / (1e6 if not a.demo else 1)
        bandas.fan_chart(serie, a.figura, rotulo=rotulo, unidad=unidad,
                         pron_log=pron["mce"] - (np.log(1e6) if not a.demo else 0),
                         etiqueta="programa (demanda MCE, condicional)")
    if a.figura_chequeo:
        unidad = "nivel (unidades sintéticas)" if a.demo else "billones de ARS"
        bandas.grafico_chequeo(nivel / (1e6 if not a.demo else 1),
                               pron["mce"] - (np.log(1e6) if not a.demo else 0),
                               a.figura_chequeo, a.trimestres, rotulo=rotulo, unidad=unidad,
                               etiqueta="programa MCE (condicional)")
    return texto


if __name__ == "__main__":
    main()
