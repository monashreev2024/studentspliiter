from typing import List
import pandas as pd

def get_group_cols(group_mode: str) -> List[str]:
    return ["Year", "Department"] if group_mode == "Year + Department" else ["Department"]

def build_summary(df: pd.DataFrame, group_cols: List[str]) -> pd.DataFrame:
    return (
        df.groupby(group_cols, dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(group_cols)
    )
