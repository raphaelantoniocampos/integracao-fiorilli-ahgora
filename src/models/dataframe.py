import pandas as pd
from pathlib import Path

class DataFrame:
    def __init__(self, name: str, df: pd.DataFrame, path: Path, status: bool):
        self.name = name
        self.df = df
        self.path = path

    def filter_df(df: pd.DataFrame, ids: list[str]) -> pd.DataFrame:
        return df[df["id"].isin(ids)]

