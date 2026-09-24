from dataclasses import dataclass

@dataclass
class BuildOptions:
    group_mode: str          # "Year + Department" or "Department only"
    dept_source: str         # "From RegNo" or "From Department column"
    add_summary: bool
    sort_by_regno: bool
    base_century: int        # 2000 or 1900
