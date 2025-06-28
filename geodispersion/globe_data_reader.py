from pathlib import Path

import pandas as pd


def read_data(globe_data_path: str | Path = None):
    if globe_data_path is None:
        globe_data_path = Path("geodispersion") / "GLOBE-Phase-2-Aggregated-Societal-Culture-Data.xls"
    else:
        globe_data_path = Path(globe_data_path)

    return pd.read_excel(globe_data_path, index_col=0)
