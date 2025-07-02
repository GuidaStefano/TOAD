from pathlib import Path

import pandas as pd


def read_data(globe_data_path: str | Path = None):
    if globe_data_path is None:
        # Ottieni la directory dello script corrente
        script_dir = Path(file).parent
        globe_data_path = script_dir / "GLOBE-Phase-2-Aggregated-Societal-Culture-Data.xls"
    else:
        globe_data_path = Path(globe_data_path)

    return pd.read_excel(globe_data_path, index_col=0)