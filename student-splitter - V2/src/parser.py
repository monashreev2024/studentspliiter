import re
from typing import Optional, List
import pandas as pd

def norm(s: str) -> str:
    return str(s or "").strip().lower().replace(" ", "").replace("_", "")

def find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    cols = list(df.columns)
    norm_map = {c: norm(c) for c in cols}

    # exact normalized match
    for want in candidates:
        w = norm(want)
        for c, nc in norm_map.items():
            if nc == w:
                return c

    # contains match
    for want in candidates:
        w = norm(want)
        for c, nc in norm_map.items():
            if w in nc:
                return c

    return None

def extract_year(regno: str, base_century: int = 2000) -> Optional[int]:
    r = str(regno or "").strip()

    m4 = re.match(r"^(\d{4})", r)
    if m4:
        y = int(m4.group(1))
        return y if 1990 <= y <= 2100 else None

    m2 = re.match(r"^(\d{2})", r)
    if m2:
        return base_century + int(m2.group(1))

    return None

def extract_dept_from_regno(regno: str) -> str:
    r = str(regno or "").strip()
    m = re.match(r"^\d{2,4}([A-Za-z]+)", r)
    return m.group(1).upper() if m else "UNKNOWN"

def safe_sheet_name(name: str) -> str:
    name = str(name).strip()
    name = re.sub(r"[\\/?*\[\]:]", "_", name)
    if not name:
        name = "UNKNOWN"
    return name[:31]
