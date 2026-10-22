"""Evaluación de pronósticos fuera de muestra.

Incluye el test de Diebold y Mariano (1995) con la corrección para muestras
pequeñas de Harvey, Leybourne y Newbold (1997) ("HLN"): el estadístico se
multiplica por sqrt((n + 1 - 2h + h(h-1)/n) / n) y se compara con una t de
Student con n - 1 grados de libertad.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


@dataclass(frozen=True)
class ResultadoDM:
    """Resultado del test de Diebold-Mariano con corrección HLN."""

    estadistico: float
    p_valor: float
    n: int
    h: int
    alternativa: str
    perdida: str

    def rechaza(self, nivel: float = 0.10) -> bool:
        """``True`` si se rechaza la igualdad de precisión al ``nivel`` dado."""
        return bool(self.p_valor < nivel)


def diebold_mariano(e1: np.ndarray | pd.Series, e2: np.ndarray | pd.Series, h: int = 1,
                    perdida: str = "abs", alternativa: str = "menor") -> ResultadoDM:
    """Test de Diebold-Mariano con corrección HLN.

    Args:
        e1: errores del modelo evaluado (observado - pronóstico).
        e2: errores del benchmark (p. ej., el ingenuo).
        h: horizonte del pronóstico; la varianza de largo plazo usa h-1 autocovarianzas.
        perdida: ``"abs"`` (error absoluto) o ``"cuad"`` (error cuadrático).
        alternativa: ``"menor"`` (H1: el modelo 1 tiene menor pérdida; unilateral)
            o ``"distinta"`` (bilateral).

    Returns:
        ``ResultadoDM``; estadístico negativo indica menor pérdida del modelo 1.
    """
    a1, a2 = np.asarray(e1, float), np.asarray(e2, float)
    ok = np.isfinite(a1) & np.isfinite(a2)
    a1, a2 = a1[ok], a2[ok]
    if perdida == "abs":
        d = np.abs(a1) - np.abs(a2)
    elif perdida == "cuad":
        d = a1 ** 2 - a2 ** 2
    else:
        raise ValueError("perdida debe ser 'abs' o 'cuad'")
    n = d.size
    if n < 10:
        raise ValueError("Se necesitan al menos 10 pares de errores.")
    dc = d - d.mean()
    gamma = [np.dot(dc[k:], dc[: n - k]) / n for k in range(h)]
    var_lp = gamma[0] + 2 * sum(gamma[1:])
    if var_lp <= 0:
        raise ValueError("Varianza de largo plazo no positiva (¿errores idénticos?).")
    dm = d.mean() / np.sqrt(var_lp / n)
    dm_hln = dm * np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    if alternativa == "menor":
        p = stats.t.cdf(dm_hln, df=n - 1)
    elif alternativa == "distinta":
        p = 2 * stats.t.sf(abs(dm_hln), df=n - 1)
    else:
        raise ValueError("alternativa debe ser 'menor' o 'distinta'")
    return ResultadoDM(float(dm_hln), float(p), n, h, alternativa, perdida)


def cobertura(obs: pd.Series, inf: pd.Series, sup: pd.Series) -> float:
    """Proporción de observaciones dentro del intervalo [inf, sup]."""
    dentro = (obs >= inf) & (obs <= sup)
    return float(dentro.mean())


def tabla_errores(obs: pd.Series, pronos: dict[str, pd.Series],
                  intervalos: dict[str, tuple[pd.Series, pd.Series]] | None = None,
                  benchmark: str = "ingenuo") -> pd.DataFrame:
    """MAE, MAE relativo al benchmark, sesgo medio y cobertura por modelo."""
    filas = {}
    mae_b = float((obs - pronos[benchmark]).abs().mean())
    for nombre, f in pronos.items():
        e = obs - f
        fila = {"MAE": float(e.abs().mean()), "MAE_rel": float(e.abs().mean()) / mae_b,
                "sesgo": float(e.mean())}
        if intervalos and nombre in intervalos:
            fila["cobertura"] = cobertura(obs, *intervalos[nombre])
        filas[nombre] = fila
    return pd.DataFrame(filas).T


def sesgo_por_dia(errores: pd.Series) -> pd.Series:
    """Error medio (observado - pronóstico) por día calendario del mes."""
    return errores.groupby(errores.index.day).mean().rename("sesgo")
