"""Build the blank multi-year template (formulas, validation, protection-ready styling)."""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from .spec import (FIRST_DATA_ROW, FIRST_YEAR_COL, HEADER_ROW, SHEET_AGE, SHEET_ENROL,
                   SHEET_IND, SHEET_META, SHEET_POP, TemplateSpec)

DISCLAIMER = "Synthetic demonstration template. Not an official UNESCO/UIS instrument."
INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")   # yellow = country input
CALC_FILL = PatternFill("solid", fgColor="E2EFDA")    # green = calculated
HEAD_FILL = PatternFill("solid", fgColor="1F4E79")
THIN = Side(style="thin", color="A6A6A6")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def _title(ws, title: str) -> None:
    ws["A1"] = title
    ws["A1"].font = Font(bold=True, size=13)
    ws["A2"] = DISCLAIMER
    ws["A2"].font = Font(italic=True, size=9, color="808080")


def _header(ws, labels: list, first_col: int = 1) -> None:
    for i, label in enumerate(labels):
        c = ws.cell(HEADER_ROW, first_col + i, label)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = HEAD_FILL
        c.alignment = Alignment(horizontal="center", wrap_text=True)
        c.border = BOX


def level_sex_rows(spec: TemplateSpec) -> list[tuple[str, str, int]]:
    """(level name, sex, row) for the Enrolment / Population / Indicators sheets."""
    rows, r = [], FIRST_DATA_ROW
    for lv in spec.levels:
        for sex in spec.sexes:
            rows.append((lv.name, sex, r))
            r += 1
    return rows


def build_template(spec: TemplateSpec, out: Path | str) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET_META
    _title(ws, SHEET_META)
    _header(ws, ["Field", "Value"])
    for i, f in enumerate(spec.metadata_fields + ["Template version"]):
        ws.cell(FIRST_DATA_ROW + i, 1, f).border = BOX
        v = ws.cell(FIRST_DATA_ROW + i, 2, spec.template_version if f == "Template version" else None)
        v.fill, v.border = (CALC_FILL if f == "Template version" else INPUT_FILL), BOX
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 26, 40

    rows = level_sex_rows(spec)
    for name, title in [(SHEET_ENROL, "Enrolment by level of education and sex"),
                        (SHEET_POP, "School-age population")]:
        ws = wb.create_sheet(name)
        _title(ws, title)
        fc = FIRST_YEAR_COL[name]
        _header(ws, ["Level", "Sex"] + spec.years)
        dv = DataValidation(type="whole", operator="greaterThanOrEqual", formula1="0",
                            showErrorMessage=True, error="Enter a whole number >= 0")
        ws.add_data_validation(dv)
        for lv_name, sex, r in rows:
            ws.cell(r, 1, lv_name).border = BOX
            ws.cell(r, 2, sex).border = BOX
            for j, _ in enumerate(spec.years):
                c = ws.cell(r, fc + j)
                c.border = BOX
                if sex == "Total":
                    col = get_column_letter(fc + j)
                    c.value = f"={col}{r - 2}+{col}{r - 1}"
                    c.fill = CALC_FILL
                else:
                    c.fill = INPUT_FILL
                    dv.add(c.coordinate)
        ws.column_dimensions["A"].width = 18

    ws = wb.create_sheet(SHEET_AGE)
    _title(ws, "Enrolment in primary education by single year of age")
    fc = FIRST_YEAR_COL[SHEET_AGE]
    _header(ws, ["Age"] + spec.years)
    dv = DataValidation(type="whole", operator="greaterThanOrEqual", formula1="0")
    ws.add_data_validation(dv)
    last = FIRST_DATA_ROW + len(spec.age_detail_ages) - 1
    for i, age in enumerate(spec.age_detail_ages):
        r = FIRST_DATA_ROW + i
        ws.cell(r, 1, age).border = BOX
        for j, _ in enumerate(spec.years):
            c = ws.cell(r, fc + j)
            c.fill, c.border = INPUT_FILL, BOX
            dv.add(c.coordinate)
    tr = last + 1
    ws.cell(tr, 1, "Total").font = Font(bold=True)
    for j, _ in enumerate(spec.years):
        col = get_column_letter(fc + j)
        c = ws.cell(tr, fc + j, f"=SUM({col}{FIRST_DATA_ROW}:{col}{last})")
        c.fill, c.border = CALC_FILL, BOX

    ws = wb.create_sheet(SHEET_IND)
    _title(ws, SHEET_IND)
    fc = FIRST_YEAR_COL[SHEET_IND]
    _header(ws, ["Indicator", "Level", "Sex"] + spec.years)
    src_fc = FIRST_YEAR_COL[SHEET_ENROL]
    for lv_name, sex, r in rows:
        ws.cell(r, 1, "Gross enrolment ratio (%)").border = BOX
        ws.cell(r, 2, lv_name).border = BOX
        ws.cell(r, 3, sex).border = BOX
        for j, _ in enumerate(spec.years):
            s = f"{get_column_letter(src_fc + j)}{r}"
            c = ws.cell(r, fc + j, f"=IF({SHEET_POP}!{s}=0,\"\",{SHEET_ENROL}!{s}/{SHEET_POP}!{s}*100)")
            c.fill, c.border, c.number_format = CALC_FILL, BOX, "0.0"
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 18

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out
