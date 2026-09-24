import io
from typing import Tuple
import pandas as pd

from .config import BuildOptions
from .parser import find_column, extract_year, extract_dept_from_regno, safe_sheet_name
from .grouping import build_summary, get_group_cols


def process_excel(
    uploaded_file,
    opts: BuildOptions,
    event_name: str,
    event_date,
    start_time,
    end_time,
) -> Tuple[pd.DataFrame, pd.DataFrame, str, bytes]:
    xls = pd.ExcelFile(uploaded_file)
    first_sheet = xls.sheet_names[0]
    df = pd.read_excel(xls, sheet_name=first_sheet)
    df = df.dropna(how="all")

    if df.empty:
        raise ValueError("Excel has no data rows.")

    reg_col = find_column(df, ["regno", "reg no", "register no", "register number", "reg_no", "reg"])
    name_col = find_column(df, ["name", "student name", "studentname"])
    dept_col = find_column(df, ["department", "dept", "branch"])

    if not reg_col:
        raise ValueError("Column not found: Reg No (expected header like 'regno' / 'reg no').")
    if not name_col:
        raise ValueError("Column not found: Name (expected header like 'name').")

    df = df.copy()
    df[reg_col] = df[reg_col].astype(str).str.strip()
    df[name_col] = df[name_col].astype(str).str.strip()

    df["Year"] = df[reg_col].apply(lambda x: extract_year(x, base_century=opts.base_century))
    df["Year"] = df["Year"].fillna("UNKNOWN")

    if opts.dept_source == "From Department column" and dept_col:
        df["Department"] = df[dept_col].astype(str).str.strip().str.upper()
        df.loc[df["Department"].eq("") | df["Department"].isna(), "Department"] = "UNKNOWN"
    else:
        df["Department"] = df[reg_col].apply(extract_dept_from_regno)

    group_cols = get_group_cols(opts.group_mode)
    summary_df = build_summary(df, group_cols)

    # --- Event metadata strings ---
    event_date_str = event_date.strftime("%Y-%m-%d")
    start_time_str = start_time.strftime("%H:%M")
    end_time_str = end_time.strftime("%H:%M")

    # School count = total number of students/rows
    school_count = int(len(df))

    # Output name (you can still override this in UI based on event naming)
    out_name = (
        "Year_Department_Wise_Students.xlsx"
        if opts.group_mode == "Year + Department"
        else "Department_Wise_Students.xlsx"
    )

    # --- Build header blocks ---
    meta_block = pd.DataFrame(
        {
            "Event Name": [event_name],
            "Event Date": [event_date_str],
            "Start Time": [start_time_str],
            "End Time": [end_time_str],
        }
    )

    summary_meta_block = pd.DataFrame(
        {
            "Event Name": [event_name],
            "Event Date": [event_date_str],
            "Start Time": [start_time_str],
            "End Time": [end_time_str],
            "School Count": [school_count],
        }
    )

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        # --- Summary sheet: metadata + summary table ---
        if opts.add_summary:
            summary_meta_block.to_excel(writer, sheet_name="Summary", index=False, startrow=0)
            # leave one empty row between header and table
            summary_df.to_excel(writer, sheet_name="Summary", index=False, startrow=3)

        # --- Department sheets: metadata + student rows ---
        grouped = df.groupby(group_cols, dropna=False)
        for key, g in grouped:
            g2 = g.sort_values(by=[reg_col]) if opts.sort_by_regno else g

            if isinstance(key, tuple):
                sheet = safe_sheet_name(f"{key[0]}_{key[1]}")
            else:
                sheet = safe_sheet_name(str(key))

            # metadata
            meta_block.to_excel(writer, sheet_name=sheet, index=False, startrow=0)
            # data below metadata
            g2.to_excel(writer, sheet_name=sheet, index=False, startrow=3)

    output.seek(0)
    return df, summary_df, out_name, output.getvalue()