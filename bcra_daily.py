import matplotlib.pyplot as plt
import logging
from typing import Optional
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------
# CONFIG
# ---------------------------------
BASE_URL = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias"
TIMEOUT = 30
PAGE_LIMIT = 1000

RETRY_STRATEGY = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=(429, 500, 502, 503, 504),
)

PROXIES = {
    "http": "http://proxy2.bcra.net:80",
    "https": "http://proxy2.bcra.net:80",
}

logger = logging.getLogger(__name__)


def _build_session() -> requests.Session:
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=RETRY_STRATEGY)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.proxies.update(PROXIES)
    session.trust_env = False
    return session


def get_bcra_daily_series(
    series_id: int,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    """
    Download full daily BCRA monetarias series (v4) with pagination.
    Returns DataFrame with columns: fecha, valor
    """

    if not isinstance(series_id, int) or series_id <= 0:
        raise ValueError("series_id must be a positive integer")

    base_params = {}
    if start:
        base_params["desde"] = start
    if end:
        base_params["hasta"] = end

    session = _build_session()
    url = f"{BASE_URL}/{series_id}"

    all_rows = []
    offset = 0
    total_count = None

    while True:
        params = {
            **base_params,
            "limit": PAGE_LIMIT,
            "offset": offset,
        }

        resp = session.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()

        try:
            resultset = payload["metadata"]["resultset"]
            detalle = payload["results"][0]["detalle"]
        except (KeyError, IndexError, TypeError):
            raise ValueError("Unexpected API response structure")

        if total_count is None:
            total_count = resultset["count"]

        if not detalle:
            break

        all_rows.extend(detalle)
        offset += PAGE_LIMIT

        if offset >= total_count:
            break

    df = pd.DataFrame(all_rows)

    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")

    df = (
        df.dropna()
          .sort_values("fecha")
          .reset_index(drop=True)
    )

    # Validación dura
    if len(df) != total_count:
        logger.warning(
            "Downloaded %s rows but metadata reports %s",
            len(df),
            total_count,
        )

    return df


# ---------------------------------
# MAIN
# ---------------------------------
if __name__ == "__main__":

    SERIES_ID = 104
    START_DATE = None # e.g., "2020-01-01"

    df = get_bcra_daily_series(series_id=SERIES_ID, start=START_DATE,  )

    df = (df.set_index("fecha"))

    # Guardado
    df.to_csv(f"bcra_{SERIES_ID}_daily.csv")

    # Gráfico
    plt.figure()
    plt.plot(df.index, df["valor"])
    plt.title(f"BCRA – Serie diaria monetaria (ID {SERIES_ID})")
    plt.xlabel("Fecha")
    plt.ylabel("Valor")
    plt.grid(True)
    plt.tight_layout()
    plt.show()
