"""Read submitted workbooks into one tidy (long) table.

Rows and columns are located by their labels and year headers, not by
fixed cell positions, so small layout differences between template
versions do not break extraction. Every value keeps its cell address
so QC issues can point the country to the exact cell.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from .spec import FIRST_DATA_ROW, HEADER_ROW, SHEET_AGE, SHEET_ENROL, SHEET_IND, SHEET_META, SHEET_POP

COLUMNS = ["country", "table", "indicator", "level", "sex", "age", "year", "value", "cell", "file"]


def _year_cols(ws) -> dict[int, int]:
    return {c: ws.cell(HEADER_ROW, c).value for c in range(1, ws.max_column + 1)
            if isinstance(ws.cell(HEADER_ROW, c).value, int)}


def read_metadata(wb) -> dict:
    ws = wb[SHEET_META]
    return {ws.cell(r, 1).value: ws.cell(r, 2).value
            for r in range(FIRST_DATA_ROW, ws.max_row + 1) if ws.cell(r, 1).value}


def extract_workbook(path: Path | str) -> tuple[dict, pd.DataFrame]:
    path = Path(path)
    wb = load_workbook(path, data_only=True)
    meta = read_metadata(wb)
    iso = meta.get("Country code") or path.stem.split("_")[0]
    recs = []

    def add(table, ws, r, label_cols, indicator=None):
        labels = [ws.cell(r, c).value for c in label_cols]
        if all(v is None for v in labels):
            return
        for c, year in years.items():
            v = ws.cell(r, c).value
            rec = dict(country=iso, table=table, indicator=indicator, level=None, sex=None, age=None,
                       year=year, value=v if isinstance(v, (int, float)) else None,
                       cell=f"{ws.title}!{ws.cell(r, c).coordinate}", file=path.name)
            if table == "age":
                rec["age"] = labels[0]
            else:
                rec["level"], rec["sex"] = labels[-2], labels[-1]
            recs.append(rec)

    for sheet, table in ((SHEET_ENROL, "enrolment"), (SHEET_POP, "population")):
        ws = wb[sheet]
        years = _year_cols(ws)
        for r in range(FIRST_DATA_ROW, ws.max_row + 1):
            add(table, ws, r, [1, 2])
    ws = wb[SHEET_AGE]
    years = _year_cols(ws)
    for r in range(FIRST_DATA_ROW, ws.max_row + 1):
        add("age", ws, r, [1])
    ws = wb[SHEET_IND]
    years = _year_cols(ws)
    for r in range(FIRST_DATA_ROW, ws.max_row + 1):
        if ws.cell(r, 1).value:
            add("indicator", ws, r, [2, 3], indicator="GER")
    return meta, pd.DataFrame(recs, columns=COLUMNS)


def extract_folder(folder: Path | str) -> tuple[dict[str, dict], pd.DataFrame]:
    metas, frames = {}, []
    for p in sorted(Path(folder).glob("*.xlsx")):
        if p.name.startswith(("~$", "_")):
            continue
        meta, df = extract_workbook(p)
        metas[df["country"].iat[0] if len(df) else p.stem] = meta
        frames.append(df)
    data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLUMNS)
    return metas, data
