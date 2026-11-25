"""Roll a template forward: add a new data year to every multi-year sheet.

Formulas are copied from the last year column and shifted with openpyxl's
formula Translator; cell styles and data-validation ranges are extended.
"""
from __future__ import annotations

from copy import copy
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.formula.translate import Translator
from openpyxl.utils import get_column_letter

from .spec import FIRST_YEAR_COL, HEADER_ROW, SHEET_META


def _last_year_col(ws) -> int:
    col = None
    for c in range(1, ws.max_column + 1):
        if isinstance(ws.cell(HEADER_ROW, c).value, int):
            col = c
    if col is None:
        raise ValueError(f"No year columns found on sheet {ws.title!r}")
    return col


def add_year(src: Path | str, dst: Path | str, new_version: str | None = None) -> dict:
    """Add one year column to every sheet listed in FIRST_YEAR_COL. Returns a change log."""
    wb = load_workbook(src)
    log = {}
    for name in FIRST_YEAR_COL:
        ws = wb[name]
        last = _last_year_col(ws)
        new = last + 1
        old_year = ws.cell(HEADER_ROW, last).value
        changes = 0
        for r in range(HEADER_ROW, ws.max_row + 1):
            s, d = ws.cell(r, last), ws.cell(r, new)
            if s.has_style:
                d._style = copy(s._style)
            if r == HEADER_ROW:
                d.value = old_year + 1
            elif isinstance(s.value, str) and s.value.startswith("="):
                d.value = Translator(s.value, origin=s.coordinate).translate_formula(d.coordinate)
                changes += 1
        # extend data validation that covered the old last column
        old_letter, new_letter = get_column_letter(last), get_column_letter(new)
        for dv in ws.data_validations.dataValidation:
            for rng in list(dv.sqref.ranges):
                if rng.min_col <= last <= rng.max_col:
                    dv.add(f"{new_letter}{rng.min_row}:{new_letter}{rng.max_row}")
        ws.column_dimensions[new_letter].width = ws.column_dimensions[old_letter].width
        log[name] = {"new_year": old_year + 1, "column": new_letter, "formulas_added": changes}
    if new_version:
        meta = wb[SHEET_META]
        for r in range(1, meta.max_row + 1):
            if meta.cell(r, 1).value == "Template version":
                meta.cell(r, 2).value = new_version
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    wb.save(dst)
    return log
